from flask import Blueprint, render_template, request, abort
from .models import Event

# Blueprint for public/main routes
main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    """Home page: show upcoming events (from DB)."""
    events = Event.query.order_by(Event.start_dt.asc()).limit(12).all()
    return render_template("index.html", events=events)

@main_bp.route("/event/<int:event_id>")
def event_details(event_id: int):
    """Event details from DB."""
    event = Event.query.get(event_id)
    if not event:
        return abort(404)
    return render_template("event.html", event=event)

@main_bp.route("/create", methods=["GET", "POST"])
def create_event():
    """Placeholder for now (Ben will implement form/validation)."""
    if request.method == "POST":
        print(request.form)  # temporary
    return render_template("create.html")

@main_bp.route("/history")
def booking_history():
    """Stub: will later show real bookings for the logged-in user."""
    bookings = []
    return render_template("history.html", bookings=bookings)
