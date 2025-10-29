from datetime import datetime, timedelta
from decimal import Decimal
import os

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import func

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config: dict | None = None) -> Flask:
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
        from .models import User, Event, EventStatus

        has_events = db.session.scalar(db.select(Event).limit(1))
        if not has_events:
            demo_owner = db.session.scalar(
                db.select(User).where(User.username == "demo_owner")
            )
            if demo_owner is None:
                demo_owner = User(
                    first_name="Bollywood",
                    last_name="Beats",
                    username="demo_owner",
                    email="demo@bollywoodbeats.com",
                    contact_number="0000000000",
                    street_address="Online Only",
                )
                demo_owner.set_password("demo1234")
                db.session.add(demo_owner)
                db.session.flush()

            now = datetime.utcnow()
            demo_events = [
                Event(
                    title="Bollywood Night Live",
                    category="Bollywood",
                    description="A high-energy evening featuring the best Bollywood hits with live dancers and an immersive light show.",
                    image_url="concert1.jpg",
                    venue="Sydney Opera House",
                    city="Sydney",
                    start_dt=now + timedelta(days=14),
                    capacity=250,
                    price=Decimal("79.00"),
                    status=EventStatus.OPEN,
                    owner_id=demo_owner.id,
                ),
                Event(
                    title="Desi Beats Festival",
                    category="EDM",
                    description="A fusion night of desi EDM with top DJs and surprise guest performers keeping the dance floor packed till late.",
                    image_url="concert4.jpg",
                    venue="The Forum",
                    city="Melbourne",
                    start_dt=now + timedelta(days=30),
                    capacity=0,
                    price=Decimal("65.00"),
                    status=EventStatus.SOLD_OUT,
                    owner_id=demo_owner.id,
                ),
                Event(
                    title="Classical Raagas Evening",
                    category="Classical",
                    description="An intimate concert celebrating timeless raagas with renowned vocalists and instrumental maestros.",
                    image_url="concert3.jpg",
                    venue="QPAC Concert Hall",
                    city="Brisbane",
                    start_dt=now - timedelta(days=7),
                    capacity=180,
                    price=Decimal("45.00"),
                    status=EventStatus.INACTIVE,
                    owner_id=demo_owner.id,
                ),
            ]
            db.session.add_all(demo_events)
            db.session.commit()

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return db.session.get(User, int(user_id))

    # Blueprints already in repo
    from . import views, auth
    app.register_blueprint(views.main_bp)
    app.register_blueprint(auth.auth_bp, url_prefix="/auth")

    @app.context_processor
    def inject_navigation_data():
        from .models import Event, EventStatus

        now = datetime.utcnow()
        categories = db.session.scalars(
            db.select(Event.category)
            .where(Event.category.isnot(None))
            .distinct()
            .order_by(Event.category.asc())
        ).all()
        upcoming_event_count = db.session.scalar(
            db.select(func.count())
            .select_from(Event)
            .where(
                Event.start_dt.isnot(None),
                Event.start_dt >= now,
                Event.status != EventStatus.CANCELLED,
            )
        ) or 0

        return {
            "nav_categories": categories,
            "upcoming_event_count": int(upcoming_event_count),
        }

    # Errors
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.before_request
    def auto_refresh_event_statuses():
        if request.endpoint == "static":
            return None

        from .models import Event, EventStatus

        now = datetime.utcnow()
        check_statuses = (EventStatus.OPEN, EventStatus.SOLD_OUT, EventStatus.INACTIVE)
        events = db.session.scalars(
            db.select(Event).where(Event.status.in_(check_statuses))
        ).all()
        updated = False
        for event in events:
            updated |= event.refresh_status(now=now)
        if updated:
            db.session.commit()

    return app
