import os
import uuid
import secrets
import collections
import shutil

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, make_response, flash, g


def create_app(test_config=None):
    users = {}

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'items.sqlite'),
        # allow up to 16MB uploads
        MAX_CONTENT_LENGTH=16 * 1000 * 1000,
        UPLOAD_FOLDER=os.path.join(app.instance_path, "images"),
    )

    # make sure the folder to upload images to exists
    try:
        os.mkdir(app.config["UPLOAD_FOLDER"])
    except FileExistsError:
        pass

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(os.path.join(app.instance_path, "images"))
    except OSError:
        pass
    
    @app.route('/', methods=["GET", "POST"])
    def index():
        g.users = users
        database = db.get_db()
        if request.method == "POST": 
            keywords = request.form.get("keywords")
            items = []
            seen_items = set()
            for i in keywords.split():
                search_results = database.execute("""
                    SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                    FROM item JOIN user ON user.id=item.seller_id WHERE name LIKE ?
                    """, ("%" + i + "%",)).fetchall()
                
                items.extend([i for i in search_results if i[0] not in seen_items])
                seen_items |= {i[0] for i in search_results}
        else: 
            items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id
                """).fetchall()

        tags = database.execute("SELECT id, name, background_color, text_color FROM tag").fetchall()
        item_tags_from_db = database.execute("SELECT item_id, tag_id FROM itemtags").fetchall()
            
        # make it easier to work with
        tags = {
            row[0]: {
                "name": row[1],
                "background_color": row[2],
                "text_color": row[3]
            }
            for row in tags
        }
        item_tags = collections.defaultdict(list)
        for item_tag_pair in item_tags_from_db:
            item_tags[item_tag_pair[0]].append(tags[item_tag_pair[1]])
        
        items = [
            {
                "id": item[0],
                "name": item[1],
                "seller": item[2],
                "seller_id": item[7],
                "price": item[3],
                "description": item[4],
                "created": item[6],
                "image": url_for("get_image", name=item[5]),
                "tags": item_tags[item[0]]
            } for item in items
        ]

        return render_template("index.html", items=items)

    @app.route("/items/<id>", methods=("GET", "POST"))
    def item_page(id):
        g.users = users
        database = db.get_db()
        if request.method == "POST":
            count = database.execute("""
            SELECT COUNT(*)
            FROM item WHERE item.id = ? AND item.seller_id = ?
            """, (id, users[request.cookies["token"]])).fetchone()[0]
            if count >= 1:
                database.execute("DELETE FROM item WHERE item.id = ? AND item.seller_id = ?", (id, users[request.cookies["token"]]))
                database.commit()
                return redirect(url_for("index"))
            else:
                return redirect(request.url)

        item = database.execute("""
        SELECT item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
        FROM item JOIN user ON user.id=item.seller_id WHERE item.id = ?
        """, (id,)).fetchone()
        tags = database.execute("SELECT id, name, background_color, text_color FROM tag").fetchall()
        tags = {
            row[0]: {
                "name": row[1],
                "background_color": row[2],
                "text_color": row[3]
            }
            for row in tags
        }
        items_from_db = database.execute("SELECT tag_id FROM itemtags WHERE item_id = ?", (id,)).fetchall()

        # make it easier to work with
        item = {
            "name": item[0],
            "seller": item[1],
            "seller_id": item[6],
            "price": item[2],
            "description": item[3],
            "created": item[5],
            "image": url_for("get_image", name=item[4]),
            "tags": [tags[row[0]] for row in items_from_db]
        }
        return render_template("item.html", id=id, item=item, current_user=users.get(request.cookies.get("token")))

    @app.route("/sellers/<id>")
    def seller_page(id):
        g.users = users
        database = db.get_db()
        items = database.execute("""
        SELECT item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
        FROM item JOIN user ON user.id=item.seller_id WHERE user.id = ?""", (id,)).fetchall()
        seller_info = database.execute("""
        SELECT display_name, description FROM user WHERE user.id = ?""", (id,)).fetchone()

        items = [{
            "name": item[0],
            "seller": item[1],
            "seller_id": item[6],
            "price": item[2],
            "description": item[3],
            "created": item[5],
            "image": url_for("get_image", name=item[4])
            } for item in items]

        seller = {
            "name": seller_info[0],
            "description": seller_info[1]
        }

        return render_template("seller.html", id=id, items=items, seller=seller)

    @app.route('/add-item', methods=("GET", "POST"))
    def add_item():
        g.users = users
        if "token" not in request.cookies or request.cookies["token"] not in users:
            return redirect(url_for("login"))

        database = db.get_db()
        tags = database.execute("SELECT id, name, background_color, text_color FROM tag").fetchall()
        tags = [
            {
                "id": tag[0],
                "name": tag[1],
                "background_color": tag[2],
                "text_color": tag[3]
            } for tag in tags
        ]
        if request.method == "POST":
            errored = False
            if "token" not in request.cookies or request.cookies["token"] not in users:
                flash("you need to be logged in", category="error")
                errored = True
            if "description" not in request.form or request.form["description"] == "":
                flash("description needed", category="error")
                errored = True
            if "name" not in request.form or request.form["name"] == "":
                flash("name needed", category="error")
                errored = True
            if "price" not in request.form or request.form["price"] == "":
                flash("price needed", category="error")
                errored = True
                
            if not errored:
                image_filename = str(uuid.uuid4())
                database = db.get_db()
                if "image" not in request.files or request.files["image"].filename == "":
                    shutil.copy("app/static/images/logo.png", os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                else:
                    request.files["image"].save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                id_row = database.execute(
                    "INSERT INTO item (name, seller_id, price, description, image_path) VALUES (?, ?, ?, ?, ?) RETURNING id",
                    (request.form["name"], users[request.cookies["token"]], round(float(request.form["price"]), 2), request.form["description"], image_filename)
                ).fetchone()
                database.executemany(
                    "INSERT INTO itemtags (item_id, tag_id) VALUES (?, ?)",
                    [(id_row[0], tag) for tag in request.form.getlist("tag-group")]
                )
                database.commit()
                return redirect(url_for("index"))
        return render_template("add.html", tags=tags)
    
    @app.route("/images/<name>")
    def get_image(name):
        g.users = users
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    @app.route("/login", methods=("GET", "POST"))
    def login():
        g.users = users
        if "token" in request.cookies:
            resp = make_response(redirect(url_for("index")))
            resp.delete_cookie('token')
            return resp 

        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]
            display_name = request.form.get("displayname")
            description = request.form.get("description")

            if not email or not password:
                return redirect(request.url)
        
            database = db.get_db()
            records = database.execute("SELECT count(*) FROM user WHERE email = ?", (email,)).fetchone()[0]
            if records >= 1:
                records = database.execute("SELECT count(*) FROM user WHERE email = ? AND password = ?", (email, password)).fetchone()[0]
                if records == 0:
                    flash("incorrect password")
                    return render_template("login.html")
            elif display_name and description:
                database.execute(
                    "INSERT INTO user (email, password, display_name, description) VALUES (?, ?, ?, ?)",
                    (email, password, display_name, description)
                )
                database.commit()
            else:
                if display_name == "":
                    flash("missing display name")
                if description == "":
                    flash("missing description")
                return render_template("login.html", signup=True)
        
            id = database.execute("SELECT id FROM user WHERE email = ? AND password = ?", (email, password)).fetchone()[0]
            token = secrets.token_hex(16)
            users[token] = id
            resp = make_response(redirect(url_for("index")))
            resp.set_cookie('token', token)
            return resp 


        return render_template("login.html")
    
    @app.route("/me", methods=("GET", "POST"))
    def check_me():
        g.users = users
        if "token" in request.cookies and request.cookies["token"] in users:
            token = request.cookies["token"]
            database = db.get_db()
            if request.method == "POST":
                new_display_name = request.form["displayname"]
                new_description = request.form["description"]

                if not (new_display_name or new_description):
                    flash("either update display name, description, or both")
                else:
                    if new_display_name:
                        database.execute(
                            "UPDATE user SET display_name = ? WHERE id = ?",
                            (new_display_name, users[token],)
                        )
                    if new_description:
                        database.execute(
                            "UPDATE user SET description = ? WHERE id = ?",
                            (new_description, users[token],)
                        )
                    database.commit()

                    return redirect(request.url)

            display_name, description = database.execute("SELECT display_name, description FROM user WHERE id = ?", (users[token],)).fetchone()
            return render_template("profile.html", display_name=display_name, description=description)
        else:
            return redirect(url_for("login"))

    from . import db
    db.init_app(app)

    return app
