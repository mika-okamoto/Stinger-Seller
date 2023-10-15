import os
import uuid
import secrets
import collections
import shutil
import json

from flask import Flask, render_template, send_from_directory, request, redirect, url_for, make_response, flash, g, jsonify

# import spacy
# from spacy import displacy
# import en_core_web_sm

def create_app(test_config=None):
    users = {}
    payments = {}

    # activate spacy 
    # nlp = spacy.load("en_core_web_sm")

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'items.sqlite'),
        # allow up to 16MB uploads
        MAX_CONTENT_LENGTH=16 * 1000 * 1000,
        UPLOAD_FOLDER=os.path.join(app.instance_path, "images"),
        STRIPE=False,
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

    if app.config["STRIPE"]:
        import stripe
        stripe.api_key = app.config["STRIPE_SECRET_KEY"]

    @app.route('/', methods=["GET", "POST"])
    def index():
        g.users = users
        database = db.get_db()
        if request.method == "POST": 
            keywords = request.form.get("keywords")
            items = []
            seen_items = set()
            if keywords != "":
                for i in keywords.split():
                    search_results = database.execute("""
                        SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                        FROM item JOIN user ON user.id=item.seller_id WHERE name LIKE ? AND processing = FALSE
                        """, ("%" + i + "%",)).fetchall()
                    
                    items.extend([i for i in search_results if i[0] not in seen_items])
                    seen_items |= {i[0] for i in search_results}
            else:
                items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id WHERE processing = FALSE
                """).fetchall() 

            taglist = request.form.getlist('tag-group')
            print(len(taglist))
            if len(taglist) != 0:
                tagged_items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id JOIN itemtags ON item.id = itemtags.item_id 
                WHERE """ + "OR ".join("itemtags.tag_id = ?" for _ in range(len(taglist))) +
                "GROUP BY item.id HAVING COUNT(*) = ?", (*taglist, len(taglist),)).fetchall()
            else: 
                tagged_items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id
                """).fetchall() 
            
            tagged_items = {item[0] for item in tagged_items}

            items = [item for item in items if item[0] in tagged_items]
        else: 
            items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id WHERE processing = FALSE
                """).fetchall()

        tags = database.execute("SELECT id, name, background_color, text_color FROM tag").fetchall()
        item_tags_from_db = database.execute("SELECT item_id, tag_id FROM itemtags").fetchall()
            
        # make it easier to work with
        tags = {
            row[0]: {
                "name": row[1],
                "background_color": row[2],
                "text_color": row[3],
                "id": row[0]
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

        return render_template("index.html", items=items, tags=tags)

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

    @app.route("/sellers/<id>", methods=("GET", "POST"))
    def seller_page(id):
        g.users = users
        database = db.get_db()

        if request.method == "POST": 
            keywords = request.form.get("keywords")
            items = []
            seen_items = set()
            if keywords != "":
                for i in keywords.split():
                    search_results = database.execute("""
                        SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                        FROM item JOIN user ON user.id=item.seller_id WHERE user.id = ? AND name LIKE ?
                        """, (id, "%" + i + "%")).fetchall()
                    
                    items.extend([i for i in search_results if i[0] not in seen_items])
                    seen_items |= {i[0] for i in search_results}
            else:
                items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id WHERE user.id = ?
                """, (id,)).fetchall() 

            taglist = request.form.getlist('tag-group')
            print(len(taglist))
            if len(taglist) != 0:
                tagged_items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id JOIN itemtags ON item.id = itemtags.item_id WHERE user.id = ?
                AND """ + "OR ".join("itemtags.tag_id = ?" for _ in range(len(taglist))) +
                "GROUP BY item.id HAVING COUNT(*) = ?", (id, *taglist, len(taglist))).fetchall()
            else: 
                tagged_items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id WHERE user.id = ?
                """, (id,)).fetchall() 
            
            tagged_items = {item[0] for item in tagged_items}

            items = [item for item in items if item[0] in tagged_items]
        else: 
            items = database.execute("""
                SELECT item.id, item.name, user.display_name, item.price, item.description, item.image_path, item.created, item.seller_id
                FROM item JOIN user ON user.id=item.seller_id WHERE user.id = ?
                """, (id,)).fetchall()

        tags = database.execute("SELECT id, name, background_color, text_color FROM tag").fetchall()
        item_tags_from_db = database.execute("SELECT item_id, tag_id FROM itemtags").fetchall()
            
        # make it easier to work with
        tags = {
            row[0]: {
                "name": row[1],
                "background_color": row[2],
                "text_color": row[3],
                "id": row[0]
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

        seller_info = database.execute("""
        SELECT display_name, description, contact_method FROM user WHERE user.id = ?""", (id,)).fetchone()

        seller = {
            "name": seller_info[0],
            "description": seller_info[1],
            "contact_method": seller_info[2]
        }

        return render_template("seller.html", id=id, items=items, seller=seller, tags = tags)

    @app.route("/checkout/<id>", methods=("GET", "POST"))
    def checkout(id):
        g.users = users

        if request.method == "POST" and request.form["note"]:
            database = db.get_db()
            if app.config["STRIPE"]:
                price_id, account_id = database.execute("SELECT item.stripe_price_id, user.stripe_id FROM item JOIN user ON user.id=item.seller_id WHERE item.id = ?", (id,)).fetchone()
                to = stripe.checkout.Session.create(
                    mode="payment",
                    line_items=[{"price": price_id, "quantity": 1}],
                    payment_intent_data={
                        #"application_fee_amount": 123,
                        "transfer_data": {"destination": account_id},
                    },
                    success_url=url_for("index", _external=True),
                    cancel_url=url_for("index", _external=True),
                )

                payments[to.id] = (id, request.form["note"])
                return redirect(to.url)
            else:
                database.execute("UPDATE item SET processing = ?, note = ? WHERE id = ?", (True, request.form["note"], id))
                database.commit()
                return redirect(url_for("index"))
        elif request.method == "POST":
            flash("please add a note")

        return render_template("checkout.html")

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
                if app.config["STRIPE"]:
                    product = stripe.Product.create(
                        name=request.form["name"]
                    )
                    price = stripe.Price.create(
                        unit_amount=int(round(float(request.form["price"]), 2) * 100),
                        currency="usd",
                        product=product.id,
                    ).id
                else:
                    price = None

                id_row = database.execute(
                    "INSERT INTO item (name, seller_id, price, description, image_path, stripe_price_id) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
                    (request.form["name"], users[request.cookies["token"]], round(float(request.form["price"]), 2), request.form["description"], image_filename, price)
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
            contact_method = request.form.get("contactmethod")

            if not email or not password:
                return redirect(request.url)

            database = db.get_db()
            records = database.execute("SELECT count(*) FROM user WHERE email = ?", (email,)).fetchone()[0]
            if records >= 1:
                records = database.execute("SELECT count(*) FROM user WHERE email = ? AND password = ?", (email, password)).fetchone()[0]
                if records == 0:
                    flash("incorrect password")
                    return render_template("login.html")
            elif display_name and description and contact_method:
                if app.config["STRIPE"]:
                    account = stripe.Account.create(type="express").id
                else:
                    account = None
                database.execute(
                    "INSERT INTO user (email, password, display_name, description, contact_method, stripe_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (email, password, display_name, description, contact_method, account)
                )
                database.commit()

                if app.config["STRIPE"]:
                    url = stripe.AccountLink.create(
                        account=account,
                        # I don't think this will be relevant for the demo...
                        refresh_url=url_for("login", _external=True),
                        return_url=url_for("index", _external=True),
                        type="account_onboarding"
                    ).url
                    return redirect(url)
            else:
                if display_name == "":
                    flash("missing display name")
                if description == "":
                    flash("missing description")
                if contact_method == "":
                    flash("missing contact method")
                
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
                new_contact_method = request.form["contact_method"]

                if not (new_display_name or new_description or new_contact_method):
                    flash("either update display name, description, contact method, or all three")
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
                    if new_contact_method:
                        database.execute(
                            "UPDATE user SET contact_method = ? WHERE id = ?",
                            (new_contact_method, users[token],)
                        )
                    database.commit()

                    return redirect(request.url)

            display_name, description, contact_method = database.execute("SELECT display_name, description, contact_method FROM user WHERE id = ?", (users[token],)).fetchone()
            # this should really be things that are fully paid for, but don't have that kind of time during a demo.
            processing_items = database.execute("SELECT id, name, note FROM item WHERE seller_id = ? AND processing = TRUE", (users[token],)).fetchall()
            processing_items = [{"id": row[0], "name": row[1], "note": row[2]} for row in processing_items]
            return render_template("profile.html", display_name=display_name, description=description, processing_items=processing_items, contact_method=contact_method)
        else:
            return redirect(url_for("login"))
    
    @app.route("/dashboard")
    def go_to_dashboard():
        g.users = users

        if "token" in request.cookies and request.cookies["token"] in users and app.config["STRIPE"]:
            database = db.get_db()
            account_id = database.execute("SELECT stripe_id FROM user WHERE id = ?", (users[request.cookies["token"]],)).fetchone()[0]
            login = stripe.Account.create_login_link(account_id).url
            return redirect(login)

        return redirect(url_for("index"))

    # stripe webhook code (taken from https://stripe.com/docs/webhooks/quickstart with modifications)
    @app.route('/webhook', methods=("POST",))
    def webhook():
        if not app.config["STRIPE"]:
            return jsonify(success=False)

        event = None
        payload = request.data

        try:
            event = json.loads(payload)
        except json.decoder.JSONDecodeError as e:
            print('⚠️  Webhook error while parsing basic request.' + str(e))
            return jsonify(success=False)
        if app.config["STRIPE_WEBHOOK_SECRET"]:
            # Only verify the event if there is an endpoint secret defined
            # Otherwise use the basic event deserialized with json
            sig_header = request.headers.get('stripe-signature')
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, app.config["STRIPE_WEBHOOK_SECRET"]
                )
            except stripe.error.SignatureVerificationError as e:
                print('⚠️  Webhook signature verification failed.' + str(e))
                return jsonify(success=False)

        # Handle the event
        if event and event['type'] == 'checkout.session.completed':
            session_complete = event['data']['object']
            database = db.get_db()
            transaction_data = payments.pop(session_complete["id"])
            database.execute("UPDATE item SET processing = ?, note = ? WHERE id = ?", (True, transaction_data[1], transaction_data[0]))
            database.commit()
        elif event and event['type'] == 'checkout.session.async_payment_succeeded':
            # we don't use this because it wouldn't complete in time for the demo.
            payment_complete = event['data']['object']
            print("payment complete!", payment_complete)
            # Then define and call a method to handle the successful attachment of a PaymentMethod.
            # handle_payment_method_attached(payment_method)
        else:
            # Unexpected event type
            print('Unhandled event type {}'.format(event['type']))

        return jsonify(success=True)

    from . import db
    db.init_app(app)

    return app
