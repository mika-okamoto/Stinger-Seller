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

    # a simple page that says hello
    
    @app.route('/')
    def index():
        return render_template("index.html")

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

    from . import db
    db.init_app(app)

    return app
