DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS tag;
DROP TABLE IF EXISTS itemtags;

CREATE TABLE item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name TEXT NOT NULL,
    seller_id INTEGER NOT NULL,
    price FLOAT NOT NULL,
    description TEXT NOT NULL,
    image_path TEXT NOT NULL,

    FOREIGN KEY(seller_id) REFERENCES user(id)
);

CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL,
    description TEXT NOT NULL,
    -- 😬
    password TEXT NOT NULL
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    background_color TEXT NOT NULL,
    text_color TEXT NOT NULL  
);

CREATE TABLE itemtags (
    item_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,

    FOREIGN KEY(item_id) REFERENCES item(id),
    FOREIGN KEY(tag_id) REFERENCES tag(id)
)