import sqlite3
import shutil
import os

import click
from flask import current_app, g
import csv


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    init_tag_table()

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def seed_db_command(app):
    @click.command("seed-db")
    def inner():
        db = get_db()
        row = db.execute(
            "INSERT INTO user (display_name, email, description, password) VALUES (?, ?, ?, ?) RETURNING id",
            ("Demo User", "demo@example.com", "hello hello hello", "password")
        ).fetchone()
        try:
            os.makedirs(os.path.join(app.instance_path, "images"))
        except OSError:
            pass

        file = open("app/data/items.csv")
        shutil.copy("app/data/demo.png", os.path.join(app.instance_path, "images", "demo"))

        contents = list(csv.reader(file))
        insert_records = "INSERT INTO item (name, seller_id, price, description, image_path) VALUES(?, ?, ?, ?, ?) RETURNING id"
        rows = []
        for content in contents:
            rows.append(db.execute(insert_records, (content[0], row[0], content[1], content[2], "demo")).fetchone())
        db.executemany("INSERT INTO itemtags (item_id, tag_id) VALUES(?, ?)", [(r[0], tag) for r, content in zip(rows, contents) for tag in content[3].split("!") if tag])
        db.commit()
        
        click.echo("Seeded the database")
    return inner

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command(app))

def init_tag_table():
    db = get_db()
    file = open("app/data/tags.csv")
    contents = csv.reader(file)
    insert_records = "INSERT INTO tag (name, background_color, text_color) VALUES(?, ?, ?)"
    db.executemany(insert_records, contents)
    db.commit()