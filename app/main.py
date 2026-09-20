"""FiberGrid CTF - target application entry point."""
import logging
import os

from flask import Flask, jsonify, redirect, request

from arcgis import bp as arcgis_bp
from web import bp as web_bp
from webservice import bp as webservice_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "fibergrid-lab-secret")

    app.register_blueprint(arcgis_bp)
    app.register_blueprint(webservice_bp)
    app.register_blueprint(web_bp)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.get("/arcgis3d/rest/")
    @app.get("/arcgis3d/rest/<path:rest>")
    def arcgis3d(rest: str = ""):
        # The 3D service root sits behind the corporate SSO (unlike /arcgis/rest).
        return redirect("/login?returnUrl=" + request.full_path, code=302)

    @app.get("/robots.txt")
    def robots():
        body = ("User-agent: *\n"
                "Disallow: /webservice/\n"
                "Disallow: /arcgis3d/\n"
                "Allow: /arcgis/rest/services\n")
        return app.response_class(body, mimetype="text/plain")

    return app


app = create_app()
