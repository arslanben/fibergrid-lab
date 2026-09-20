"""FiberGrid GIS portal pages."""
from flask import Blueprint, redirect, render_template, request, session, url_for

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        error = "Kimlik doğrulama başarısız. Kurumsal dizin kaydınızı kontrol edin."
    return render_template("login.html", error=error)


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.index"))
