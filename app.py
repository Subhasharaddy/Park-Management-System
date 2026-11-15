"""ParkCare 3D - Flask application factory."""
import secrets
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import db
import security
from config import BASE_DIR, Config
from constants import CATEGORIES, CATEGORY_NAMES, STATUSES
from utils import fmt_dt, slug


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"))
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):  # generate once, keep out of git (instance/ is ignored)
        key_file = Path(app.instance_path) / ".secret_key"
        if not key_file.exists():
            key_file.write_text(secrets.token_hex(32))
        app.config["SECRET_KEY"] = key_file.read_text().strip()

    db.init_app(app)
    security.init_app(app)

    from routes import admin, auth, citizen, complaints, staff
    for bp in (complaints.bp, auth.bp, citizen.bp, admin.bp, staff.bp):
        app.register_blueprint(bp)

    app.jinja_env.filters["dt"] = fmt_dt
    app.jinja_env.filters["slug"] = slug
    app.jinja_env.globals.update(
        CATEGORIES=CATEGORIES, CATEGORY_NAMES=CATEGORY_NAMES, STATUSES=STATUSES,
        category_meta={c[0]: c for c in CATEGORIES})

    def wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(404)
    def not_found(_e):
        if wants_json():
            return jsonify(error="Not found"), 404
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, title="Access denied",
                               message="You don't have permission to view this page."), 403

    @app.errorhandler(400)
    def bad_request(e):
        if wants_json():
            return jsonify(error=getattr(e, "description", "Bad request")), 400
        return render_template("error.html", code=400, title="Request problem",
                               message=getattr(e, "description", "Bad request.")), 400

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413, title="File too large",
                               message="Uploads are limited to 8 MB in total. Please choose a smaller photo."), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", code=500, title="Something went wrong",
                               message="An unexpected error occurred. Please try again shortly."), 500

    @app.cli.command("init-db")
    def init_db_command():
        """Create tables and seed parks (flask --app app init-db)."""
        db.init_schema(db.get_db())
        print("Database initialised.")

    return app


app = create_app() if __name__ != "__main__" else None

if __name__ == "__main__":
    create_app().run(debug=True)
