from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize database
db = SQLAlchemy()

def create_app():
    """
    Factory function to create and configure the Flask app.
    This initializes extensions (Bootstrap, SQLAlchemy, LoginManager)
    and registers Blueprints for modular structure.
    """
    app = Flask(__name__)

    # Configuration
    app.debug = True  # Disable for production
    app.secret_key = os.environ.get("SECRET_KEY", "somesecretkey")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sitedata.sqlite"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Suppress warning logs

    # Initialize extensions
    Bootstrap5(app)
    db.init_app(app)

    # Login manager setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    # Import models here to avoid circular import issues
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return db.session.get(User, user_id)

    # Register blueprints (main routes + auth routes)
    from . import views
    from . import auth
    app.register_blueprint(views.main_bp)
    app.register_blueprint(auth.auth_bp)

    return app