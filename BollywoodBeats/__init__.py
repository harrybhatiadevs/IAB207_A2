from flask import Flask, render_template
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from typing import Optional
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config: Optional[dict] = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Config: SQLite lives in instance/ for easy packaging
    app.config.from_mapping(
        # Generate a fresh secret key every start to invalidate sessions
        SECRET_KEY=os.urandom(32),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "app.db")
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    # Extensions
    Bootstrap5(app)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Import models so metadata is registered
    from . import models  # noqa: F401

    # Ensure database/tables exist for first run
    with app.app_context():
        db.create_all()

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return db.session.get(User, int(user_id))

    # Blueprints already in repo
    from . import views, auth
    app.register_blueprint(views.main_bp)
    app.register_blueprint(auth.auth_bp, url_prefix="/auth")

    # Errors
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
