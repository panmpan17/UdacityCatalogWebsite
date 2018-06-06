from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from model import Base, Post, User

DEFAULT_USERS = [
    {
        "email": "panmpan@gmail.com",
        "name": "Michael",
    },
    {
        "email": "test@user.com",
        "name": "Test",
    },
]

CATALOGS = {
    1: "Rock",
    2: "Country",
    3: "Pop",
}

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

engine = create_engine("sqlite:///database.db", connect_args={
    "check_same_thread": False})
Base.metadata.create_all(engine)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def create_user(user):
    new_user = User(email=user["email"], name=user["name"])
    session.add(new_user)
    session.commit()
    return find_user_email(user["email"]).id


def find_user_email(email):
    return session.query(User).filter_by(email=email).one()


def create_default_users():
    for user in DEFAULT_USERS:
        try:
            find_user_email(user["email"])
        except NoResultFound:
            create_user(user)


def create_post(post, user_id):
    new_post = Post(title=post["title"], body=post["body"],
                    catalog=post["catalog"], author=user_id)
    session.add(new_post)
    session.commit()
    return session.query(Post).order_by(Post.create_at.desc()).first()


@app.route("/", methods=["GET"])
def index():
    try:
        user_id = login_session["userid"]
    except KeyError:
        user_id = None

    posts = [i.jsonlize for i in session.query(Post).order_by(
        Post.create_at.desc()).all()]
    return render_template("menu.html", user=user_id, catalogs=CATALOGS,
                           posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        if not request.form["email"]:
            return render_template("login.html", error="missing")

        try:
            user = find_user_email(request.form["email"])
        except NoResultFound:
            return render_template("login.html", error="wrong")

        login_session["userid"] = user.id
        return redirect("/")


@app.route("/logout", methods=["GET"])
def logout():
    login_session.pop("userid", None)
    return redirect("/")


@app.route("/new", methods=["GET", "POST"])
def new_post():
    if request.method == "GET":
        try:
            user_id = login_session["userid"]
            return render_template("new_post.html", user=user_id,
                                   catalogs=CATALOGS)
        except KeyError:
            return render_template("login_required.html")
    else:
        if ((not request.form["title"]) or (not request.form["body"]) or
           (not request.form["catalog"])):
            return render_template("new_post.html", catalogs=CATALOGS,
                                   error="missing")

        post = create_post(request.form, login_session["userid"])
        return redirect(url_for("post_detail", post_id=post.id))


@app.route("/catalog/<catalog>", methods=["GET"])
@app.route("/catalog/<catalog>/items", methods=["GET"])
def catalog_posts(catalog):
    try:
        user_id = login_session["userid"]
    except KeyError:
        user_id = None

    posts = [i.jsonlize for i in session.query(Post).order_by(
             Post.create_at.desc()).filter_by(catalog=catalog).all()]
    return render_template("catalog_menu.html", user=user_id,
                           catalog=int(catalog), posts=posts,
                           catalogs=CATALOGS)


@app.route("/catalog/<int:post_id>", methods=["GET"])
def post_detail(post_id):
    try:
        user_id = login_session["userid"]
    except KeyError:
        user_id = None

    post = session.query(Post).filter_by(id=post_id).one()
    return render_template("post_detail.html", user=user_id, post=post,
                           catalogs=CATALOGS)


@app.route("/catalog/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    try:
        user_id = login_session["userid"]
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
    except KeyError:
        return render_template("login_required.html")


@app.route("/catalog/<int:post_id>/delete", methods=["GET", "POST"])
def delete_post(post_id):
    try:
        user_id = login_session["userid"]
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
    except KeyError:
        return render_template("login_required.html")


@app.route("/catalog.json")
def jsonfy_data():
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


if __name__ == "__main__":
    create_default_users()

    app.debug = True
    app.run(host="0.0.0.0", port=5000)
