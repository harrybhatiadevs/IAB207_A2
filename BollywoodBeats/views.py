from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    current_app,
)
from flask_login import current_user, login_required, logout_user
from sqlalchemy.orm import selectinload

from . import db
from .forms import (
    UpdateAccountForm,
    DeleteAccountForm,
    EventForm,
    EventUpdateForm,
    DeleteEventForm,
    CancelEventForm,
    BookingForm,
    CommentForm,
    EVENT_CATEGORY_CHOICES,
)
from .models import (
    User,
    Event,
    EventStatus,
    TicketType,
    Booking,
    Comment,
)

main_bp = Blueprint("main", __name__)


def _generate_order_id() -> str:
    return uuid4().hex[:8].upper()


def _sync_event_statuses(events: list[Event]) -> None:
    """Ensure status values reflect timing/capacity rules."""
    if not events:
        return

    now = datetime.utcnow()
    status_changed = False
    for event in events:
        status_changed |= event.refresh_status(now=now)
    if status_changed:
        db.session.commit()


@main_bp.route("/")
@main_bp.route("/home")
def index():
    selected_category = request.args.get("category", "All")
    search_term = (request.args.get("q") or "").strip()

    stmt = (
        db.select(Event)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.bookings),
        )
        .order_by(Event.start_dt.asc())
    )
    if selected_category != "All":
        stmt = stmt.where(Event.category == selected_category)
    if search_term:
        stmt = stmt.where(Event.title.ilike(f"%{search_term}%"))

    events = db.session.scalars(stmt).all()
    _sync_event_statuses(events)

    categories = ["All"] + [choice[0] for choice in EVENT_CATEGORY_CHOICES]

    return render_template(
        "index.html",
        events=events,
        categories=categories,
        selected_category=selected_category,
        search_term=search_term,
    )


@main_bp.route("/event/<int:event_id>")
def event_details(event_id: int):
    stmt = (
        db.select(Event)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.bookings),
            selectinload(Event.comments).selectinload(Comment.user),
        )
        .where(Event.id == event_id)
    )
    event = db.session.execute(stmt).scalar_one_or_none()
    if event is None:
        abort(404)

    _sync_event_statuses([event])

    booking_form = BookingForm()
    comment_form = CommentForm()
    booking_form.qty.data = booking_form.qty.data or 1

    comments = sorted(event.comments, key=lambda c: c.posted_at, reverse=True)

    return render_template(
        "event.html",
        event=event,
        booking_form=booking_form,
        comment_form=comment_form,
        comments=comments,
    )


@main_bp.post("/event/<int:event_id>/book")
@login_required
def book_event(event_id: int):
    stmt = (
        db.select(Event)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.bookings),
        )
        .where(Event.id == event_id)
    )
    event = db.session.execute(stmt).scalar_one_or_none()
    if event is None:
        abort(404)

    form = BookingForm()
    if not form.validate_on_submit():
        for error in form.qty.errors:
            flash(error)
        return redirect(url_for("main.event_details", event_id=event_id))

    _sync_event_statuses([event])

    if event.status in {EventStatus.CANCELLED, EventStatus.INACTIVE}:
        flash("This event is not available for booking.")
        return redirect(url_for("main.event_details", event_id=event_id))

    qty = form.qty.data or 0
    if qty <= 0:
        flash("Select at least one ticket.")
        return redirect(url_for("main.event_details", event_id=event_id))

    if qty > event.remaining_capacity:
        flash("Not enough tickets remaining for that quantity.")
        return redirect(url_for("main.event_details", event_id=event_id))

    order_id = _generate_order_id()
    while db.session.scalar(db.select(Booking).where(Booking.order_id == order_id)):
        order_id = _generate_order_id()

    unit_price = event.price or Decimal("0")
    booking = Booking(
        order_id=order_id,
        user_id=current_user.id,
        qty=qty,
        unit_price=unit_price,
    )
    event.bookings.append(booking)
    db.session.add(booking)

    if event.refresh_status():
        db.session.add(event)

    db.session.commit()
    flash(f"Booking confirmed! Your order ID is {order_id}.")
    return redirect(url_for("main.booking_history"))


@main_bp.post("/event/<int:event_id>/comment")
@login_required
def post_comment(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)

    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            event_id=event_id,
            user_id=current_user.id,
            body=form.body.data.strip(),
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted!")
    else:
        for error in form.body.errors:
            flash(error)
    return redirect(url_for("main.event_details", event_id=event_id))


@main_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_event():
    form = EventForm()

    if request.method == "GET":
        while len(form.ticket_types.entries) < form.ticket_types.min_entries:
            form.ticket_types.append_entry()

    if form.validate_on_submit():
        image_path = None
        if form.image.data and form.image.data.filename:
            upload_folder = Path(current_app.static_folder) / "uploads"
            upload_folder.mkdir(parents=True, exist_ok=True)
            original_name = Path(form.image.data.filename).name
            unique_name = f"{uuid4().hex}_{original_name}"
            destination = upload_folder / unique_name
            form.image.data.save(destination)
            image_path = f"uploads/{unique_name}"

        ticket_tiers: list[TicketType] = []
        for entry in form.ticket_types.entries:
            name = (entry.form.name.data or "").strip()
            if not name:
                continue
            price = entry.form.price.data
            if price is None:
                price = Decimal("0")
            quantity = entry.form.quantity.data or 0
            ticket_tiers.append(
                TicketType(
                    name=name,
                    price=price,
                    quantity=quantity,
                )
            )

        total_capacity = sum(tier.quantity for tier in ticket_tiers) or form.capacity.data
        base_price = form.price.data
        if ticket_tiers:
            base_price = min(
                (tier.price for tier in ticket_tiers if tier.price is not None),
                default=base_price,
            )
        if base_price is None:
            base_price = Decimal("0")

        event = Event(
            title=form.title.data.strip(),
            category=form.category.data,
            description=form.description.data.strip(),
            image_url=image_path,
            venue=form.venue.data.strip(),
            city=form.city.data.strip(),
            start_dt=form.start_dt.data,
            capacity=total_capacity,
            price=base_price,
            status=EventStatus.OPEN,
            owner_id=current_user.id,
        )
        event.ticket_types = ticket_tiers
        db.session.add(event)
        db.session.commit()
        flash("Event created successfully!")
        return redirect(url_for("main.event_details", event_id=event.id))

    elif request.method == "POST":
        flash("Please correct the highlighted errors before submitting.")

    return render_template("create.html", form=form)


@main_bp.route("/events/mine")
@login_required
def my_events():
    events = db.session.scalars(
        db.select(Event)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.bookings),
        )
        .where(Event.owner_id == current_user.id)
        .order_by(Event.start_dt.asc())
    ).all()

    _sync_event_statuses(events)
    return render_template("my_events.html", events=events)


@main_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id: int):
    stmt = (
        db.select(Event)
        .options(selectinload(Event.ticket_types), selectinload(Event.bookings))
        .where(Event.id == event_id)
    )
    event = db.session.execute(stmt).scalar_one_or_none()
    if event is None or event.owner_id != current_user.id:
        abort(404)

    form = EventUpdateForm()
    delete_form = DeleteEventForm()
    cancel_form = CancelEventForm()

    if request.method == "GET":
        form.title.data = event.title
        form.category.data = event.category
        form.description.data = event.description
        form.venue.data = event.venue
        form.city.data = event.city
        form.start_dt.data = event.start_dt
        form.capacity.data = event.total_capacity or event.capacity
        form.price.data = event.lowest_ticket_price or event.price

        while len(form.ticket_types.entries):
            form.ticket_types.pop_entry()
        for ticket in event.ticket_types[:5]:
            entry = form.ticket_types.append_entry()
            entry.form.name.data = ticket.name
            entry.form.price.data = ticket.price
            entry.form.quantity.data = ticket.quantity
        while len(form.ticket_types.entries) < 3:
            form.ticket_types.append_entry()

    if form.validate_on_submit():
        image_path = event.image_url
        if form.image.data and form.image.data.filename:
            upload_folder = Path(current_app.static_folder) / "uploads"
            upload_folder.mkdir(parents=True, exist_ok=True)
            original_name = Path(form.image.data.filename).name
            unique_name = f"{uuid4().hex}_{original_name}"
            destination = upload_folder / unique_name
            form.image.data.save(destination)
            image_path = f"uploads/{unique_name}"

        ticket_tiers: list[TicketType] = []
        for entry in form.ticket_types.entries:
            name = (entry.form.name.data or "").strip()
            if not name:
                continue
            price = entry.form.price.data
            if price is None:
                price = Decimal("0")
            quantity = entry.form.quantity.data or 0
            ticket_tiers.append(
                TicketType(
                    name=name,
                    price=price,
                    quantity=quantity,
                )
            )

        total_capacity = sum(tier.quantity for tier in ticket_tiers) or form.capacity.data
        base_price = form.price.data
        if ticket_tiers:
            base_price = min(
                (tier.price for tier in ticket_tiers if tier.price is not None),
                default=base_price,
            )
        if base_price is None:
            base_price = Decimal("0")

        event.title = form.title.data.strip()
        event.category = form.category.data
        event.description = form.description.data.strip()
        event.image_url = image_path
        event.venue = form.venue.data.strip()
        event.city = form.city.data.strip()
        event.start_dt = form.start_dt.data
        event.capacity = total_capacity
        event.price = base_price

        event.ticket_types.clear()
        for tier in ticket_tiers:
            event.ticket_types.append(tier)

        event.refresh_status()
        db.session.commit()
        flash("Event updated successfully!")
        return redirect(url_for("main.my_events"))

    elif request.method == "POST":
        flash("Please correct the highlighted errors before submitting.")

    return render_template(
        "edit_event.html",
        form=form,
        delete_form=delete_form,
        cancel_form=cancel_form,
        event=event,
    )


@main_bp.post("/events/<int:event_id>/cancel")
@login_required
def cancel_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None or event.owner_id != current_user.id:
        abort(404)

    cancel_form = CancelEventForm()
    if not cancel_form.validate_on_submit():
        flash("Invalid cancel request.")
        return redirect(url_for("main.edit_event", event_id=event_id))

    if event.status == EventStatus.CANCELLED:
        flash("Event already cancelled.")
    else:
        event.status = EventStatus.CANCELLED
        db.session.commit()
        flash("Event cancelled successfully.")
    return redirect(url_for("main.event_details", event_id=event_id))


@main_bp.post("/events/<int:event_id>/delete")
@login_required
def delete_event(event_id: int):
    event = db.session.get(Event, event_id)
    if event is None or event.owner_id != current_user.id:
        abort(404)

    delete_form = DeleteEventForm()
    if not delete_form.validate_on_submit():
        flash("Invalid delete request.")
        return redirect(url_for("main.edit_event", event_id=event_id))

    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.")
    return redirect(url_for("main.my_events"))


@main_bp.route("/history")
@login_required
def booking_history():
    search_term = (request.args.get("q") or "").strip()

    stmt = (
        db.select(Booking)
        .options(selectinload(Booking.event))
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.booked_at.desc())
    )
    if search_term:
        stmt = stmt.join(Booking.event).where(Event.title.ilike(f"%{search_term}%"))

    bookings = db.session.scalars(stmt).all()
    _sync_event_statuses([booking.event for booking in bookings if booking.event])

    return render_template(
        "history.html",
        bookings=bookings,
        search_term=search_term,
    )


@main_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm(obj=current_user)
    delete_form = DeleteAccountForm()

    if form.submit.data and form.validate_on_submit():
        new_email = form.email.data.strip()
        new_username = form.username.data.strip()

        email_owner = db.session.scalar(
            db.select(User).where(User.email == new_email, User.id != current_user.id)
        )
        if email_owner:
            flash("Email is already in use by another account.")
            return redirect(url_for("main.account"))

        username_owner = db.session.scalar(
            db.select(User).where(User.username == new_username, User.id != current_user.id)
        )
        if username_owner:
            flash("Username is already taken. Please choose another.")
            return redirect(url_for("main.account"))

        current_user.first_name = form.first_name.data.strip()
        current_user.last_name = form.last_name.data.strip()
        current_user.username = new_username
        current_user.email = new_email
        current_user.contact_number = form.contact_number.data.strip()
        current_user.street_address = form.street_address.data.strip()

        new_password = (form.new_password.data or "").strip()
        if new_password:
            current_user.set_password(new_password)

        db.session.commit()
        flash("Account details updated successfully.")
        return redirect(url_for("main.account"))

    if delete_form.delete.data and delete_form.validate_on_submit():
        user_to_remove = current_user._get_current_object()
        logout_user()
        db.session.delete(user_to_remove)
        db.session.commit()
        flash("Your account has been deleted.")
        return redirect(url_for("main.index"))

    return render_template("account.html", form=form, delete_form=delete_form)
