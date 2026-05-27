DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS anime_tags;
DROP TABLE IF EXISTS animes;
DROP TABLE IF EXISTS rates;
DROP TABLE IF EXISTS collects;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS history;
DROP TABLE IF EXISTS episodes;
DROP TABLE IF EXISTS characters;
DROP TABLE IF EXISTS follow;
DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS like_comment;
DROP TABLE IF EXISTS anime_like;
DROP TABLE IF EXISTS notice;

-- 用户表（扩展）
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    avatar TEXT DEFAULT '/static/images/avatar.png',
    nickname TEXT,
    bio TEXT,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    is_vip INTEGER DEFAULT 0,
    dark_mode INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 公告表
CREATE TABLE notice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 动漫主表（扩展）
CREATE TABLE animes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    cover TEXT,
    director TEXT,
    actors TEXT,
    release_date TEXT,
    descr TEXT,
    company TEXT,
    episodes_total INTEGER,
    status TEXT DEFAULT '连载', -- 连载/完结/停更
    type TEXT DEFAULT 'TV', -- TV/剧场版/OVA
    area TEXT DEFAULT '日本',
    year INTEGER,
    plot TEXT,
    theme_song TEXT,
    trailer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 标签表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

-- 动漫-标签关联
CREATE TABLE anime_tags (
    anime_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (anime_id,tag_id)
);

-- 评分表（扩展：多维度）
CREATE TABLE rates (
    user_id INTEGER,
    anime_id INTEGER,
    score INTEGER,
    plot INTEGER,
    art INTEGER,
    voice INTEGER,
    music INTEGER,
    pace INTEGER,
    reason TEXT,
    PRIMARY KEY (user_id,anime_id)
);

-- 收藏表
CREATE TABLE collects (
    user_id INTEGER,
    anime_id INTEGER,
    is_public INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id,anime_id)
);

-- 评论表（扩展）
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    anime_id INTEGER,
    content TEXT,
    parent_id INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 评论点赞
CREATE TABLE like_comment (
    user_id INTEGER,
    comment_id INTEGER,
    PRIMARY KEY (user_id,comment_id)
);

-- 动漫点赞
CREATE TABLE anime_like (
    user_id INTEGER,
    anime_id INTEGER,
    PRIMARY KEY (user_id,anime_id)
);

-- 浏览历史
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    anime_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分集表
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER,
    ep_num INTEGER,
    title TEXT,
    air_date TEXT,
    descr TEXT
);

-- 角色表
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER,
    name TEXT,
    voice TEXT,
    avatar TEXT,
    descr TEXT
);

-- 关注表
CREATE TABLE follow (
    user_id INTEGER,
    follow_id INTEGER,
    PRIMARY KEY (user_id,follow_id)
);

-- 消息表
CREATE TABLE message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_uid INTEGER,
    to_uid INTEGER,
    content TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始数据
INSERT INTO users(username,password,is_admin) VALUES ('admin','123456',1);

INSERT INTO notice(content) VALUES ('欢迎来到动漫推荐网站！新番持续更新中~');

INSERT INTO tags(name) VALUES ('热血'),('治愈'),('科幻'),('恋爱'),('战斗'),('校园'),('悬疑');

INSERT INTO animes(title,cover,director,actors,release_date,descr,company,episodes_total,status,type,area,year) VALUES
('进击的巨人','/static/images/1.png','荒木哲郎','梶裕贵,石川由依','2013','人类为生存对抗巨人的史诗故事。','WIT STUDIO',75,'完结','TV','日本',2013),
('鬼灭之刃','/static/images/2.jpg','外崎春雄','花江夏树,鬼头明里','2019','少年炭治郎踏上斩鬼之旅。','ufotable',26,'完结','TV','日本',2019),
('夏目友人帐','/static/images/3.jpg','大森贵弘','神谷浩史','2008','温柔治愈的妖怪故事。','Brain''s Base',100,'完结','TV','日本',2008),
('你的名字','/static/images/4.jpg','新海诚','神木隆之介','2016','跨越时空的相遇。','CoMix Wave Films',1,'完结','剧场版','日本',2016),
('紫罗兰永恒花园','/static/images/5.jpg','石立太一','石川由依','2018','寻找爱的真谛。','京都动画',13,'完结','TV','日本',2018);

INSERT INTO anime_tags(anime_id,tag_id) VALUES
(1,1),(1,3),(1,7),
(2,1),(2,5),
(3,2),
(4,2),(4,4),
(5,2),(5,4);