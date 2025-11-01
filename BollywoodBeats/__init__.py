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
    """Application factory so tests and CLI tasks can create isolated apps."""
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

        demo_owner = db.session.scalar(
            db.select(User).where(User.username == "demo_owner")
        )
        if demo_owner is None:
            # Seed a predictable owner so the catalogue and tests have data.
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
        demo_events_data = [
            {
                "title": "Bollywood Night Live",
                "category": "Bollywood",
                "description": "A high-energy evening featuring the best Bollywood hits with live dancers and an immersive light show.",
                "image_url": "concert1.jpg",
                "venue": "Sydney Opera House",
                "city": "Sydney",
                "start_dt": now + timedelta(days=14),
                "capacity": 250,
                "price": Decimal("79.00"),
                "status": EventStatus.OPEN,
            },
            {
                "title": "Desi Beats Festival",
                "category": "EDM",
                "description": "A fusion night of desi EDM with top DJs and surprise guest performers keeping the dance floor packed till late.",
                "image_url": "concert4.jpg",
                "venue": "The Forum",
                "city": "Melbourne",
                "start_dt": now + timedelta(days=30),
                "capacity": 0,
                "price": Decimal("65.00"),
                "status": EventStatus.SOLD_OUT,
            },
            {
                "title": "Classical Raagas Evening",
                "category": "Classical",
                "description": "An intimate concert celebrating timeless raagas with renowned vocalists and instrumental maestros.",
                "image_url": "concert3.jpg",
                "venue": "QPAC Concert Hall",
                "city": "Brisbane",
                "start_dt": datetime(2026, 1, 1, 18, 0),
                "capacity": 180,
                "price": Decimal("45.00"),
                "status": EventStatus.OPEN,
            },
            {
                "title": "Sufi Soul Sessions",
                "category": "Sufi",
                "description": "Experience a spiritual evening of qawwali-inspired vocals and traditional instrumentation in an intimate setting.",
                "image_url": "concert2.jpg",
                "venue": "State Theatre",
                "city": "Sydney",
                "start_dt": now + timedelta(days=21),
                "capacity": 220,
                "price": Decimal("55.00"),
                "status": EventStatus.OPEN,
            },
            {
                "title": "Bollywood Beats Brunch",
                "category": "Fusion",
                "description": "A daytime brunch party with live DJs spinning Bollywood remixes, dance workshops and street-food pop-ups.",
                "image_url": "concert5.jpg",
                "venue": "Howard Smith Wharves",
                "city": "Brisbane",
                "start_dt": now + timedelta(days=7, hours=5),
                "capacity": 150,
                "price": Decimal("39.00"),
                "status": EventStatus.OPEN,
            },
            {
                "title": "Monsoon Melodies Tour",
                "category": "Folk",
                "description": "Celebrate the sounds of the monsoon with folk artists from across India showcasing regional instruments and storytelling.",
                "image_url": "concert6.jpg",
                "venue": "Thebarton Theatre",
                "city": "Adelaide",
                "start_dt": now + timedelta(days=45),
                "capacity": 300,
                "price": Decimal("49.00"),
                "status": EventStatus.OPEN,
            },
            {
                "title": "Desi Comedy Night",
                "category": "Comedy",
                "description": "An evening of stand-up featuring Australian-Indian comedians delivering desi humour, improv and audience roasting.",
                "image_url": "concert7.jpg",
                "venue": "Comedy Republic",
                "city": "Melbourne",
                "start_dt": now - timedelta(days=2),
                "capacity": 120,
                "price": Decimal("30.00"),
                "status": EventStatus.CANCELLED,
            },
        ]

        existing_titles = set(
            db.session.scalars(
                db.select(Event.title).where(Event.owner_id == demo_owner.id)
            ).all()
        )
        new_events = []
        for event_data in demo_events_data:
            if event_data["title"] in existing_titles:
                continue
            # Store the raw dictionary so SQLAlchemy assigns defaults (e.g. relationships).
            new_events.append(
                Event(
                    owner_id=demo_owner.id,
                    **event_data,
                )
            )
        if new_events:
            db.session.add_all(new_events)
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
        # Keep dynamic statuses in sync so pages never render stale availability.
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
