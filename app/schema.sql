DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS user;

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
    -- 😬
    password TEXT NOT NULL
);
