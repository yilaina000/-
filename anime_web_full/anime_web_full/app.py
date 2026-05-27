from flask import Flask, render_template, request, redirect, url_for, g, session, abort, jsonify
import sqlite3
import os
import webbrowser
from datetime import datetime

app = Flask(__name__)
app.secret_key = "anime_web_2026_full"
DATABASE = "anime.db"

# 全局访问统计
visit_count = 0

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(e):
    db = getattr(g, "_database", None)
    if db:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open("schema.sql", encoding="utf-8") as f:
            db.executescript(f.read())
        db.commit()

# 平均分
def avg_rate(anime_id):
    db = get_db()
    r = db.execute("SELECT AVG(score) a FROM rates WHERE anime_id=?", (anime_id,)).fetchone()
    return round(r["a"],1) if r["a"] else "暂无评分"

# 标签
def get_tags(anime_id):
    db = get_db()
    return db.execute("SELECT t.name FROM tags t JOIN anime_tags at ON t.id=at.tag_id WHERE at.anime_id=?",(anime_id,)).fetchall()

# 浏览历史
def add_history(user_id, anime_id):
    db = get_db()
    exist = db.execute("SELECT * FROM history WHERE user_id=? AND anime_id=?",(user_id,anime_id)).fetchone()
    if not exist:
        db.execute("INSERT INTO history(user_id,anime_id) VALUES (?,?)",(user_id,anime_id))
    db.commit()

# 首页（含公告、分页、排行榜、暗黑模式）
@app.route("/")
def index():
    global visit_count
    visit_count += 1
    db = get_db()
    sort = request.args.get("sort","default")
    page = int(request.args.get("page",1))
    per_page = 10
    tags = db.execute("SELECT * FROM tags").fetchall()
    notice = db.execute("SELECT * FROM notice ORDER BY id DESC LIMIT 1").fetchone()

    # 分页总数
    total = db.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    total_pages = (total + per_page -1) // per_page
    offset = (page-1)*per_page

    # 排序
    if sort == "score":
        animes = db.execute("""
            SELECT a.*,AVG(r.score) s FROM animes a
            LEFT JOIN rates r ON a.id=r.anime_id
            GROUP BY a.id ORDER BY s DESC LIMIT ? OFFSET ?
        """,(per_page,offset)).fetchall()
    elif sort == "new":
        animes = db.execute("SELECT * FROM animes ORDER BY id DESC LIMIT ? OFFSET ?",(per_page,offset)).fetchall()
    else:
        animes = db.execute("SELECT * FROM animes LIMIT ? OFFSET ?",(per_page,offset)).fetchall()

    carousels = db.execute("SELECT * FROM animes LIMIT 3").fetchall()
    # 热门榜
    hot_animes = db.execute("""
        SELECT a.*,COUNT(h.id) cnt FROM animes a
        LEFT JOIN history h ON a.id=h.anime_id
        GROUP BY a.id ORDER BY cnt DESC LIMIT 5
    """).fetchall()

    dark_mode = session.get("dark_mode",0)
    return render_template("index.html",
        animes=animes,tags=tags,carousels=carousels,
        visit_count=visit_count,sort=sort,
        page=page,total_pages=total_pages,
        notice=notice,hot_animes=hot_animes,
        dark_mode=dark_mode)

# 标签筛选（支持分页版）
@app.route("/tag/<int:tid>")
def tag(tid):
    db = get_db()
    tags = db.execute("SELECT * FROM tags").fetchall()
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    # 带分页的标签筛选查询
    animes = db.execute("""
        SELECT a.* FROM animes a
        JOIN anime_tags at ON a.id=at.anime_id
        WHERE at.tag_id=?
        LIMIT ? OFFSET ?
    """, (tid, per_page, offset)).fetchall()

    # 计算总页数
    total = db.execute("""
        SELECT COUNT(*) FROM animes a
        JOIN anime_tags at ON a.id=at.anime_id
        WHERE at.tag_id=?
    """, (tid,)).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    sort = "default"
    notice = db.execute("SELECT * FROM notice ORDER BY id DESC LIMIT 1").fetchone()
    hot_animes = db.execute("""
        SELECT a.*,COUNT(h.id) cnt FROM animes a
        LEFT JOIN history h ON a.id=h.anime_id
        GROUP BY a.id ORDER BY cnt DESC LIMIT 5
    """).fetchall()
    dark_mode = session.get("dark_mode", 0)

    return render_template("index.html",
        animes=animes, tags=tags,
        page=page, total_pages=total_pages,
        sort=sort, notice=notice,
        hot_animes=hot_animes,
        dark_mode=dark_mode)
# 搜索
@app.route("/search")
def search():
    wd = request.args.get("wd","").strip()
    if not wd:
        return redirect("/")
    db = get_db()
    tags = db.execute("SELECT * FROM tags").fetchall()
    animes = db.execute("SELECT * FROM animes WHERE title LIKE ?",(f"%{wd}%",)).fetchall()
    return render_template("index.html",animes=animes,tags=tags)

# 详情页（扩展：分集、角色、点赞、多维度评分）
@app.route("/anime/<int:aid>")
def anime_detail(aid):
    db = get_db()
    anime = db.execute("SELECT * FROM animes WHERE id=?",(aid,)).fetchone()
    if not anime:
        abort(404)
    tags = get_tags(aid)
    avg = avg_rate(aid)
    comments = db.execute("""
        SELECT c.*,u.username FROM comments c
        JOIN users u ON c.user_id=u.id
        WHERE c.anime_id=? AND c.parent_id=0
        ORDER BY c.id DESC
    """,(aid,)).fetchall()
    episodes = db.execute("SELECT * FROM episodes WHERE anime_id=?",(aid,)).fetchall()
    characters = db.execute("SELECT * FROM characters WHERE anime_id=?",(aid,)).fetchall()

    is_collect = False
    has_rated = False
    like_num = db.execute("SELECT COUNT(*) FROM anime_like WHERE anime_id=?",(aid,)).fetchone()[0]
    is_liked = False

    if "user_id" in session:
        uid = session["user_id"]
        if db.execute("SELECT * FROM collects WHERE user_id=? AND anime_id=?",(uid,aid)).fetchone():
            is_collect = True
        if db.execute("SELECT * FROM rates WHERE user_id=? AND anime_id=?",(uid,aid)).fetchone():
            has_rated = True
        if db.execute("SELECT * FROM anime_like WHERE user_id=? AND anime_id=?",(uid,aid)).fetchone():
            is_liked = True
        add_history(uid,aid)

    return render_template("detail.html",
        anime=anime,tags=tags,avg=avg,
        comments=comments,episodes=episodes,characters=characters,
        is_collect=is_collect,has_rated=has_rated,
        like_num=like_num,is_liked=is_liked)

# 多维度评分
@app.route("/rate/<int:aid>",methods=["POST"])
def rate(aid):
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    score = request.form.get("score","5")
    plot = request.form.get("plot","5")
    art = request.form.get("art","5")
    voice = request.form.get("voice","5")
    music = request.form.get("music","5")
    pace = request.form.get("pace","5")
    reason = request.form.get("reason","").strip()
    db = get_db()
    db.execute("REPLACE INTO rates(user_id,anime_id,score,plot,art,voice,music,pace,reason) VALUES (?,?,?,?,?,?,?,?,?)",
               (uid,aid,score,plot,art,voice,music,pace,reason))
    db.commit()
    return redirect(f"/anime/{aid}")

# 收藏
@app.route("/collect/<int:aid>")
def collect(aid):
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    db.execute("INSERT OR IGNORE INTO collects(user_id,anime_id) VALUES (?,?)",(uid,aid))
    db.commit()
    return redirect(f"/anime/{aid}")

# 取消收藏
@app.route("/uncollect/<int:aid>")
def uncollect(aid):
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    db.execute("DELETE FROM collects WHERE user_id=? AND anime_id=?",(uid,aid))
    db.commit()
    return redirect(f"/anime/{aid}")

# 动漫点赞
@app.route("/like_anime/<int:aid>")
def like_anime(aid):
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    exist = db.execute("SELECT * FROM anime_like WHERE user_id=? AND anime_id=?",(uid,aid)).fetchone()
    if exist:
        db.execute("DELETE FROM anime_like WHERE user_id=? AND anime_id=?",(uid,aid))
    else:
        db.execute("INSERT INTO anime_like(user_id,anime_id) VALUES (?,?)",(uid,aid))
    db.commit()
    return redirect(f"/anime/{aid}")

# 评论
@app.route("/comment/<int:aid>",methods=["POST"])
def comment(aid):
    if "user_id" not in session:
        return redirect("/login")
    content = request.form.get("content","").strip()
    parent_id = int(request.form.get("parent_id",0))
    if not content:
        return redirect(f"/anime/{aid}")
    uid = session["user_id"]
    db = get_db()
    db.execute("INSERT INTO comments(user_id,anime_id,content,parent_id) VALUES (?,?,?,?)",(uid,aid,content,parent_id))
    db.commit()
    return redirect(f"/anime/{aid}")

# 删除评论
@app.route("/del_comment/<int:cid>/<int:aid>")
def del_comment(cid,aid):
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    cm = db.execute("SELECT * FROM comments WHERE id=?",(cid,)).fetchone()
    if cm:
        if cm["user_id"]==uid or session.get("is_admin")==1:
            db.execute("DELETE FROM comments WHERE id=?",(cid,))
            db.commit()
    return redirect(f"/anime/{aid}")

# 我的收藏
@app.route("/my/collect")
def my_collect():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    list_data = db.execute("""
        SELECT a.* FROM animes a
        JOIN collects c ON a.id=c.anime_id
        WHERE c.user_id=?
    """,(uid,)).fetchall()
    return render_template("collect.html",list_data=list_data)

# 浏览历史
@app.route("/my/history")
def my_history():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    list_data = db.execute("""
        SELECT DISTINCT a.*,h.created_at FROM animes a
        JOIN history h ON a.id=h.anime_id
        WHERE h.user_id=?
        ORDER BY h.id DESC
    """,(uid,)).fetchall()
    return render_template("history.html",list_data=list_data)

# 清空历史
@app.route("/my/clear_history")
def clear_history():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    db.execute("DELETE FROM history WHERE user_id=?",(uid,))
    db.commit()
    return redirect("/my/history")

# 登录
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        un = request.form["username"].strip()
        pw = request.form["password"].strip()
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username=? AND password=?",(un,pw)).fetchone()
        if u:
            session["user_id"] = u["id"]
            session["username"] = u["username"]
            session["is_admin"] = u["is_admin"]
            session["dark_mode"] = u["dark_mode"]
            return redirect("/")
        return "账号密码错误！"
    return render_template("login.html")

# 注册
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        un = request.form["username"].strip()
        pw = request.form["password"].strip()
        if not un or not pw:
            return "账号密码不能为空！"
        db = get_db()
        try:
            db.execute("INSERT INTO users(username,password) VALUES (?,?)",(un,pw))
            db.commit()
        except:
            return "用户名已存在！"
        return redirect("/login")
    return render_template("register.html")

# 退出
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# 个人中心
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    collect_num = db.execute("SELECT COUNT(*) FROM collects WHERE user_id=?",(uid,)).fetchone()[0]
    history_num = db.execute("SELECT COUNT(*) FROM history WHERE user_id=?",(uid,)).fetchone()[0]
    return render_template("profile.html",user=user,collect_num=collect_num,history_num=history_num)

# 切换暗黑模式
@app.route("/toggle_dark")
def toggle_dark():
    if "user_id" not in session:
        return redirect("/login")
    uid = session["user_id"]
    db = get_db()
    user = db.execute("SELECT dark_mode FROM users WHERE id=?",(uid,)).fetchone()
    new_mode = 1 if user["dark_mode"]==0 else 0
    db.execute("UPDATE users SET dark_mode=? WHERE id=?",(new_mode,uid))
    db.commit()
    session["dark_mode"] = new_mode
    return redirect(request.referrer or "/")

# 后台首页
@app.route("/admin")
def admin():
    if session.get("is_admin")!=1:
        return "无权限"
    db = get_db()
    animes = db.execute("SELECT * FROM animes").fetchall()
    users = db.execute("SELECT * FROM users").fetchall()
    comments = db.execute("SELECT * FROM comments").fetchall()
    return render_template("admin.html",animes=animes,users=users,comments=comments)

# 添加动漫
@app.route("/add_anime",methods=["POST"])
def add_anime():
    if session.get("is_admin")!=1:
        return "无权限"
    f = request.form
    db = get_db()
    db.execute("""
        INSERT INTO animes(title,cover,director,actors,release_date,descr,company,episodes_total,status,type,area,year)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """,(f["title"],f["cover"],f["director"],f["actors"],f["date"],f["descr"],
        f["company"],f["episodes_total"],f["status"],f["type"],f["area"],f["year"]))
    db.commit()
    return redirect("/admin")

# 编辑页
@app.route("/edit/<int:aid>")
def edit(aid):
    if session.get("is_admin")!=1:
        return "无权限"
    db = get_db()
    anime = db.execute("SELECT * FROM animes WHERE id=?",(aid,)).fetchone()
    return render_template("edit.html",anime=anime)

# 更新
@app.route("/update/<int:aid>",methods=["POST"])
def update(aid):
    if session.get("is_admin")!=1:
        return "无权限"
    f = request.form
    db = get_db()
    db.execute("""
        UPDATE animes SET title=?,cover=?,director=?,actors=?,release_date=?,descr=?,
        company=?,episodes_total=?,status=?,type=?,area=?,year=?
        WHERE id=?
    """,(f["title"],f["cover"],f["director"],f["actors"],f["date"],f["descr"],
        f["company"],f["episodes_total"],f["status"],f["type"],f["area"],f["year"],aid))
    db.commit()
    return redirect("/admin")

# 删除动漫
@app.route("/del_anime/<int:aid>")
def del_anime(aid):
    if session.get("is_admin")!=1:
        return "无权限"
    db = get_db()
    db.execute("DELETE FROM animes WHERE id=?",(aid,))
    db.commit()
    return redirect("/admin")

# 404
@app.errorhandler(404)
def page404(e):
    return render_template("404.html"),404

if __name__=="__main__":
    if not os.path.exists(DATABASE):
        init_db()
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True,use_reloader=False)