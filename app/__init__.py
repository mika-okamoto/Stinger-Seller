import os
import uuid
import secrets

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, make_response


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
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    @app.route('/', methods=["GET", "POST"])
    def index():
        database = db.get_db()
        if request.method == "POST": 
            keywords = request.form.get("keywords") 
            for i in keywords.split(): 
                items = database.execute("SELECT id, name, seller, price, description, image_path, created FROM item WHERE name LIKE ?", ('%'+ i +'%',)).fetchall()
        else: 
            items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created
                FROM item JOIN user ON user.id=item.seller_id
                """).fetchall()
            
        # make it easier to work with
        if len(items) != 0: 
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
        item = database.execute("""
        SELECT item.name, user.display_name, item.price, item.description, item.image_path, item.created
        FROM item JOIN user ON user.id=item.seller_id WHERE item.id = ?
        """, (id,)).fetchone()
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
            if "price" not in request.form or request.form["price"] == "":
                return redirect(request.url)
            if request.cookies["token"] not in users:
                return redirect(request.url)
            image_filename = str(uuid.uuid4())
            database = db.get_db()
            request.files["image"].save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            database.execute(
                "INSERT INTO item (name, seller_id, price, description, image_path) VALUES (?, ?, ?, ?, ?)",
                (request.form["name"], users[request.cookies["token"]]["id"], request.form["price"], request.form["description"], image_filename)
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
                if records == 0:
                    return render_template("login.html", signup=True)
            elif display_name:
                database.execute("INSERT INTO user (email, password, display_name) VALUES (?, ?, ?)", (email, password, display_name))
                database.commit()
            else:
                return render_template("login.html", signup=True)
        
            display_name, id = database.execute("SELECT display_name, id FROM user WHERE email = ? AND password = ?", (email, password)).fetchone()
            token = secrets.token_hex(16)
            users[token] = {
                "display_name": display_name,
                "id": id
            }
            resp = make_response(redirect(url_for("index")))
            resp.set_cookie('token', token)
            return resp 


        return render_template("login.html")
    
    # @app.route("/search=<keywords>", methods=["GET", "POST"])
    # def search(keywords): 
    #     if request.method == "POST": 
    #         keywords = request.form.get("keywords")
    #     database = db.get_db()
    #     filtered_items = [] 
    #     for i in keywords.split(): 
    #         filtered_items.append(database.execute("SELECT * FROM item WHERE name LIKE ?", (keywords.split(i),)).fetchall())
    #     filtered_items = [
    #         {
    #             "id": item[0],
    #             "name": item[1],
    #             "seller": item[2],
    #             "price": item[3],
    #             "description": item[4],
    #             "created": item[6],
    #             "image": url_for("get_image", name=item[5])
    #         } for item in filtered_items
    #     ]
    #     return render_template("index.html", keywords=keywords, items=filtered_items)
        

    @app.route("/me")
    def check_me():
        token = request.cookies["token"]
        if token in users:
            return str(users[token])
        else:
            return redirect(url_for("login"))

    from . import db
    db.init_app(app)

    return app
