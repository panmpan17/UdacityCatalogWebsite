from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask import make_response
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from model import Base, Post, User
from functools import wraps

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import string
import random
import json
import requests


CATALOGS = {
    1: "Rock",
    2: "Country",
    3: "Pop",
}

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

GOOGLE_CLIENT_ID = json.loads(open("client_secret.json",
                                   "r").read())["web"]["client_id"]
FB_APP_ID = json.loads(open("fb_client_secret.json").read())["web"]["app_id"]
FB_APP_SECRET = json.loads(open("fb_client_secret.json").read())[
    "web"]["app_secret"]

engine = create_engine("sqlite:///database.db", connect_args={
    "check_same_thread": False})
Base.metadata.create_all(engine)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def createUser(userinfo):
    """
    Create user
    """

    newUser = User(name=userinfo['name'], email=userinfo['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=userinfo['email']).one()
    return user.id


def find_user_email(email):
    """
    Find user by email
    """

    try:
        return session.query(User).filter_by(email=email).one().id
    except NoResultFound:
        return False


def json_response(text, code):
    """
    Make json response
    """

    response = make_response(json.dumps(text), code)
    response.headers["Content-Type"] = "application/json"
    return response


def requied_login(func):
    """
    Check for user login
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            login_session["user_id"]
            return func(*args, **kwargs)
        except KeyError:
            return render_template("login_required.html")
    return wrapper


@app.route("/", methods=["GET"])
def index():
    """
    Index page
    """

    try:
        user_id = login_session["user_id"]
    except KeyError:
        user_id = None

    posts = [i.jsonlize for i in session.query(Post).order_by(
        Post.create_at.desc()).all()]
    return render_template("menu.html", user=user_id, catalogs=CATALOGS,
                           posts=posts)


@app.route("/login", methods=["GET"])
def login():
    """
    Login page
    """

    state = "".join(random.choice(string.ascii_uppercase + string.digits)
                    for i in range(32))
    login_session["state"] = state
    return render_template("login.html", STATE=state)


@app.route("/logout", methods=["GET"])
@requied_login
def logout():
    """
    Logout page
    """

    if login_session["login_as"] == "google":
        gdisconnect()
    else:
        fbdisconnect()

    login_session.clear()
    return redirect("/")


@app.route("/gconnect", methods=["POST"])
def gconnect():
    """
    Google account login
    Ajax used
    """

    if request.args.get("state") != login_session["state"]:
        return json_response("Invalid state parameter.", 401)
    del login_session["state"]

    code = request.data

    try:
        # Upgrade the authorization code
        oauth_flow = flow_from_clientsecrets("client_secret.json", scope="")
        oauth_flow.redirect_uri = "postmessage"
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        return json_response("Failed to upgrade the authorization code.", 401)

    # Check token is valid
    access_token = credentials.access_token
    r = requests.get("https://www.googleapis.com/oauth2/v1/tokeninfo?"
                     "access_token=%s" % access_token).json()

    # Abort if there is error
    if r.get("error") is not None:
        return json_response(r.get("error"), 500)

    # Check token is used for right user
    gplus_id = credentials.id_token["sub"]
    if r["user_id"] != gplus_id:
        return json_response("Token's user ID doesn't match given user ID.",
                             401)

    # Check token is valid for this app.
    if r["issued_to"] != GOOGLE_CLIENT_ID:
        return json_response("Token's client ID does not match app's.", 401)

    stored_access_token = login_session.get("access_token")
    stored_gplus_id = login_session.get("gplus_id")
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        return json_response(json.dumps("Current user is already connected."),
                             200)

    login_session["access_token"] = credentials.access_token
    login_session["gplus_id"] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {"access_token": credentials.access_token, "alt": "json"}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session["name"] = data["name"]
    login_session["email"] = data["email"]
    login_session["login_as"] = "google"

    user_id = find_user_email(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return json_response("Success", 200)


def gdisconnect():
    """
    Deactivate Google account access token
    """

    access_token = login_session.get("access_token")
    if access_token is None:
        return False

    r = requests.get("https://accounts.google.com/o/oauth2/revoke?token=%s" %
                     login_session["access_token"])

    if r.status_code == 200:
        return True
    else:
        return False


@app.route("/fbconnect", methods=["POST"])
def fbconnect():
    """
    Facebook account login
    For Ajax
    """

    if request.args.get("state") != login_session["state"]:
        response = make_response(json.dumps("Invalid state parameter."), 401)
        response.headers["Content-Type"] = "application/json"
        return response
    access_token = request.data

    r = requests.get("https://graph.facebook.com/oauth/access_token?"
                     "grant_type=fb_exchange_token&client_id=%s&client_secret"
                     "=%s&fb_exchange_token=%s" % (FB_APP_ID, FB_APP_SECRET,
                                                   access_token))
    token = r.json()["access_token"]

    r = requests.get("https://graph.facebook.com/v2.8/me?access_token=%s"
                     "&fields=name,id,email" % token)
    data = r.json()

    # Store data in session
    login_session["login_as"] = "facebook"
    login_session["name"] = data["name"]
    login_session["email"] = data["email"]
    login_session["facebook_id"] = data["id"]
    login_session["access_token"] = token

    user_id = find_user_email(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session["user_id"] = user_id

    return json_response("Success", 200)


def fbdisconnect():
    """
    Deactivate Facebook account access token
    """

    facebook_id = login_session["facebook_id"]
    access_token = login_session["access_token"]
    requests.get("https://graph.facebook.com/%s/permissions?access_token=%s" %
                 (facebook_id, access_token))
    return True


@app.route("/new", methods=["GET", "POST"])
@requied_login
def new_post():
    """
    New post page
    """

    user_id = login_session["user_id"]
    if request.method == "GET":
        return render_template("new_post.html", user=user_id,
                               catalogs=CATALOGS)
    else:
        if ((not request.form["title"]) or (not request.form["body"]) or
                (not request.form["catalog"])):
            return render_template("new_post.html", catalogs=CATALOGS,
                                   error="missing")

        new_post = Post(title=request.form["title"],
                        body=request.form["body"],
                        catalog=request.form["catalog"], author=user_id)
        session.add(new_post)
        session.commit()

        post = session.query(Post).order_by(Post.create_at.desc()).first()
        return redirect(url_for("post_detail", post_id=post.id))


@app.route("/catalog/<int:catalog>", methods=["GET"])
@app.route("/catalog/<int:catalog>/items", methods=["GET"])
def catalog_posts(catalog):
    """
    Items in certain catagory
    """

    try:
        user_id = login_session["user_id"]
    except KeyError:
        user_id = None

    posts = [i.jsonlize for i in session.query(Post).order_by(
             Post.create_at.desc()).filter_by(catalog=catalog).all()]
    return render_template("catalog_menu.html", user=user_id,
                           catalog=int(catalog), posts=posts,
                           catalogs=CATALOGS)


@app.route("/catalog/<int:post_id>", methods=["GET"])
def post_detail(post_id):
    """
    Post detail page, include title & body
    """

    try:
        user_id = login_session["user_id"]
    except KeyError:
        user_id = None

    post = session.query(Post).filter_by(id=post_id).one()
    return render_template("post_detail.html", user=user_id, post=post,
                           catalogs=CATALOGS)


@app.route("/catalog/<int:post_id>/edit", methods=["GET", "POST"])
@requied_login
def edit_post(post_id):
    """
    Post edit page
    """

    user_id = login_session["user_id"]
    try:
        post = session.query(Post).filter_by(id=post_id,
                                             author=user_id).one()

        if request.method == "GET":
            return render_template("post_edit.html", post=post,
                                   catalogs=CATALOGS)
        else:
            post.title = request.form["title"]
            post.body = request.form["body"]
            post.catalog = int(request.form["catalog"])

            session.add(post)
            session.commit()
            # flash
            return redirect(url_for("post_detail", post_id=post_id))
    except NoResultFound:
        return "Not this post author"


@app.route("/catalog/<int:post_id>/delete", methods=["GET", "POST"])
@requied_login
def delete_post(post_id):
    """
    Post delete page
    """

    user_id = login_session["user_id"]
    try:
        post = session.query(Post).filter_by(id=post_id,
                                             author=user_id).one()

        if request.method == "GET":
            return render_template("post_delete.html", post=post)
        else:
            session.delete(post)
            session.commit()
            # flash
            return redirect("/")
    except NoResultFound:
        return "Not this post author"


@app.route("/rest/catalog")
def rest_all_data():
    """
    Get all catalogs & posts json
    """

    catagories = []

    for catalog in CATALOGS:
        catagory = {
            "id": catalog,
            "name": CATALOGS[catalog],
        }

        posts = session.query(Post).filter_by(catalog=catalog).all()
        catagory["Items"] = [i.jsonlize for i in posts]
        catagories.append(catagory)

    return jsonify(catagories=catagories)


@app.route("/rest/catalog/<int:catalog>")
def rest_catalog_data(catalog):
    """
    Get single catalog posts json
    """

    posts = [i.jsonlize for i in session.query(Post).order_by(
             Post.create_at.desc()).filter_by(catalog=catalog).all()]
    return jsonify(name=CATALOGS[catalog], posts=posts)


@app.route("/rest/catalog/item/<int:post_id>")
def rest_single_post(post_id):
    """
    Get single post json
    """

    try:
        post = session.query(Post).filter_by(id=post_id).one()
        return jsonify(post.jsonlize)
    except NoResultFound:
        return json_response("Post id not exist", 400)


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=5000)
