from flask import Flask, request, render_template, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model import Base, Post, User


CATALOGS = {
    1: "Ass",
    2: "Hole",
    3: "Dick",
}

app = Flask(__name__)

engine = create_engine("sqlite:///database.db")
Base.metadata.create_all(engine)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def create_user(login_session):
    new_user = User(email=login_session["email"], name=login_session["name"])
    session.add(new_user)
    session.commit()
    return session.query(User).filter_by(
        email=login_session["email"]).one().id

@app.route("/", methods=["GET"])
def index():
    posts = [i.jsonlize for i in session.query(Post).all()]
    return render_template("menu.html", catalogs=CATALOGS, posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        return jsonify(request.form)


@app.route("/logout", methods=["GET"])
def logout():
    return "Logout"


@app.route("/new", methods=["GET", "POST"])
def new_post():
    return render_template("new_post.html")


@app.route("/catalog/<catalog>", methods=["GET"])
@app.route("/catalog/<catalog>/items", methods=["GET"])
def catalog_posts(catalog):
    return render_template("catalog_menu.html")


@app.route("/catalog/<int:post_id>", methods=["GET"])
def post_detail(post_id):
    return render_template("post_detail.html")


@app.route("/catalog/<int:post_id>/edit", methods=["GET", "PUT"])
def edit_post(post_id):
    return render_template("post_edit.html")


@app.route("/catalog/<int:post_id>/delete", methods=["GET", "DELETE"])
def delete_post(post_id):
    return render_template("post_delete.html")


if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=5000)
