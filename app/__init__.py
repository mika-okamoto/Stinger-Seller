import os
import uuid

from flask import Flask, render_template, send_from_directory, request, redirect, url_for


def create_app(test_config=None):
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
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    @app.route('/')
    def index():
        database = db.get_db()
        items = database.execute("SELECT id, name, seller, price, description, image_path, created FROM item").fetchall()
        # make it easier to work with
        items = [
            {
                "id": item[0],
                "name": item[1],
                "seller": item[2],
                "price": item[3],
                "description": item[4],
                "created": item[6],
                "image": url_for("get_image", name=item[5])
            } for item in items
        ]
        return render_template("index.html", items=items)

    @app.route("/items/<id>")
    def item_page(id):
        database = db.get_db()
        item = database.execute("SELECT name, seller, price, description, image_path, created FROM item WHERE id=?", (id,)).fetchone()
        # make it easier to work with
        item = {
            "name": item[0],
            "seller": item[1],
            "price": item[2],
            "description": item[3],
            "created": item[5],
            "image": url_for("get_image", name=item[4])
        }
        return render_template("item.html", id=id, item=item)

    @app.route('/add-item', methods=("GET", "POST"))
    def add_item():
        if request.method == "POST":
            if "image" not in request.files or request.files["image"].filename == "":
                return redirect(request.url)
            if "description" not in request.form or request.form["description"] == "":
                return redirect(request.url)
            if "name" not in request.form or request.form["name"] == "":
                return redirect(request.url)
            if "seller" not in request.form or request.form["seller"] == "":
                return redirect(request.url)
            if "price" not in request.form or request.form["price"] == "":
                return redirect(request.url)
            image_filename = str(uuid.uuid4())
            database = db.get_db()
            request.files["image"].save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            database.execute(
                "INSERT INTO item (name, seller, price, description, image_path) VALUES (?, ?, ?, ?, ?)",
                (request.form["name"], request.form["seller"], request.form["price"], request.form["description"], image_filename)
            )
            database.commit()
            return redirect(url_for("index"))
        return render_template("add.html")
    
    @app.route("/images/<name>")
    def get_image(name):
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]
            display_name = request.form.get("displayname")

            if not email or not password:
                return redirect(request.url)
        
            database = db.get_db()
            records = database.execute("SELECT count(*) FROM user WHERE email = ?", (email,)).fetchone()[0]
            if records >= 1:
                records = database.execute("SELECT count(*) FROM user WHERE email = ? AND password = ?", (email, password)).fetchone()[0]
                if records >= 1:
                    # logged in
                    print("logged in")
                else:
                    return render_template("login.html", signup=True)
            elif display_name:
                database.execute("INSERT INTO user (email, password, display_name) VALUES (?, ?, ?)", (email, password, display_name))
                database.commit()
        
            return render_template("login.html", signup=True)

        return render_template("login.html")

    from . import db
    db.init_app(app)

    return app
