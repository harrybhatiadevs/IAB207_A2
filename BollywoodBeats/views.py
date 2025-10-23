<<<<<<< HEAD
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
=======
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

from . import db
from .forms import (
    UpdateAccountForm,
    DeleteAccountForm,
    EventForm,
    EventUpdateForm,
    DeleteEventForm,
    EVENT_CATEGORY_CHOICES,
)
from .models import User, Event, EventStatus, TicketType
from werkzeug.utils import secure_filename
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import selectinload
from decimal import Decimal

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    # Always show the landing page
    return render_template('landing.html')

@main_bp.route('/home')
@login_required
def index():
    selected_category = request.args.get('category', 'All')

    stmt = db.select(Event).options(selectinload(Event.ticket_types)).order_by(Event.start_dt.asc())
    if selected_category != 'All':
        stmt = stmt.where(Event.category == selected_category)
    events = db.session.scalars(stmt).all()

    categories = ['All'] + [choice[0] for choice in EVENT_CATEGORY_CHOICES]
    return render_template(
        'index.html',
        events=events,
        categories=categories,
        selected_category=selected_category,
    )


# Event details page route
@main_bp.route('/event/<int:event_id>')
@login_required
def event_details(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    return render_template('event.html', event=event)

# Event creation page route
@main_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()

    if request.method == 'GET':
        while len(form.ticket_types.entries) < form.ticket_types.min_entries:
            form.ticket_types.append_entry()

    if form.validate_on_submit():
        image_path = None
        if form.image.data and form.image.data.filename:
            upload_folder = Path(current_app.static_folder) / "uploads"
            upload_folder.mkdir(parents=True, exist_ok=True)
            original_name = secure_filename(form.image.data.filename)
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
        flash('Event created successfully!')
        return redirect(url_for('main.event_details', event_id=event.id))

    return render_template('create.html', form=form)


@main_bp.route('/events/mine')
@login_required
def my_events():
    events = db.session.scalars(
        db.select(Event)
        .options(selectinload(Event.ticket_types))
        .where(Event.owner_id == current_user.id)
        .order_by(Event.start_dt.asc())
    ).all()
    return render_template('my_events.html', events=events)


@main_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None or event.owner_id != current_user.id:
        abort(404)

    form = EventUpdateForm()
    delete_form = DeleteEventForm()

    if request.method == 'GET':
        form.title.data = event.title
        form.category.data = event.category
        form.status.data = event.status.name if event.status else EventStatus.OPEN.name
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
            original_name = secure_filename(form.image.data.filename)
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
        event.status = EventStatus[form.status.data]
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

        db.session.commit()
        flash('Event updated successfully!')
        return redirect(url_for('main.my_events'))

    while len(form.ticket_types.entries) < 3:
        form.ticket_types.append_entry()

    while len(form.ticket_types.entries) < 3:
        form.ticket_types.append_entry()

    return render_template('edit_event.html', form=form, delete_form=delete_form, event=event)


@main_bp.post('/events/<int:event_id>/delete')
@login_required
def delete_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None or event.owner_id != current_user.id:
        abort(404)

    delete_form = DeleteEventForm()
    if not delete_form.validate_on_submit():
        flash('Invalid delete request.')
        return redirect(url_for('main.edit_event', event_id=event_id))

    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully.')
    return redirect(url_for('main.my_events'))

# Booking history page route
@main_bp.route('/history')
@login_required
def booking_history():
    # Placeholder booking data
    bookings = [
        {'event_name': 'Bollywood Beats', 'order_id': 'A123', 'date': '2025-10-01'},
        {'event_name': 'Rhythm Nation', 'order_id': 'B456', 'date': '2025-09-15'},
    ]
    return render_template('history.html', bookings=bookings)

@main_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm(obj=current_user)
    delete_form = DeleteAccountForm()

    if form.submit.data and form.validate_on_submit():
        new_email = form.email.data.strip()
        new_username = form.username.data.strip()

        # Check for duplicate email
        email_owner = db.session.scalar(
            db.select(User).where(User.email == new_email, User.id != current_user.id)
        )
        if email_owner:
            flash('Email is already in use by another account.')
            return redirect(url_for('main.account'))

        # Check for duplicate username
        username_owner = db.session.scalar(
            db.select(User).where(User.username == new_username, User.id != current_user.id)
        )
        if username_owner:
            flash('Username is already taken. Please choose another.')
            return redirect(url_for('main.account'))

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
        flash('Account details updated successfully.')
        return redirect(url_for('main.account'))

    if delete_form.delete.data and delete_form.validate_on_submit():
        user_to_remove = current_user._get_current_object()
        logout_user()
        db.session.delete(user_to_remove)
        db.session.commit()
        flash('Your account has been deleted.')
        return redirect(url_for('main.landing'))

    return render_template('account.html', form=form, delete_form=delete_form)
>>>>>>> origin/main
