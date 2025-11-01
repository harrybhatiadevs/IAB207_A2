"""Database models and status calculation helpers for Bollywood Beats."""

from datetime import datetime
from enum import Enum
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


# ---------------------------
# Enums
# ---------------------------
class EventStatus(str, Enum):
    OPEN = "Open"
    INACTIVE = "Inactive"
    SOLD_OUT = "Sold Out"
    CANCELLED = "Cancelled"


# ---------------------------
# Models
# ---------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(30), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    events = db.relationship("Event", backref="owner", lazy=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)

    # ---- Auth helpers ----
    def set_password(self, raw: str) -> None:
        """
        Use PBKDF2 explicitly so it works on macOS Python 3.9
        (some builds lack hashlib.scrypt which Werkzeug might choose).
        """
        self.password_hash = generate_password_hash(raw, method="pbkdf2:sha256")

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80))  # e.g., city/genre/category as your UI needs
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    venue = db.Column(db.String(160), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.Enum(EventStatus), nullable=False, default=EventStatus.OPEN)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings = db.relationship(
        "Booking", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    ticket_types = db.relationship(
        "TicketType", backref="event", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def booked_quantity(self) -> int:
        return sum(b.qty or 0 for b in self.bookings)

    @property
    def remaining_capacity(self) -> int:
        return max(0, (self.total_capacity or 0) - self.booked_quantity)

    @property
    def total_capacity(self) -> int:
        if self.ticket_types:
            return sum(tt.quantity or 0 for tt in self.ticket_types)
        return self.capacity or 0

    @property
    def lowest_ticket_price(self) -> Decimal:
        prices = [tt.price for tt in self.ticket_types if tt.price is not None]
        if prices:
            return min(prices)
        return self.price or Decimal("0")

    def refresh_status(self, *, now: datetime | None = None) -> bool:
        """
        Update the event status based on timing and capacity rules.
        Returns True when status changes.
        """
        if self.status == EventStatus.CANCELLED:
            # Respect manual cancellation; admins flip this switch explicitly.
            return False

        if now is None:
            now = datetime.utcnow()

        new_status = EventStatus.OPEN

        if self.start_dt and self.start_dt < now:
            # Past events fall back to INACTIVE so bookings close automatically.
            new_status = EventStatus.INACTIVE
        elif self.remaining_capacity <= 0:
            # Otherwise treat zero stock as sold out (before time makes it inactive).
            new_status = EventStatus.SOLD_OUT

        if self.status != new_status:
            self.status = new_status
            return True

        return False

    def __repr__(self) -> str:
        return f"<Event {self.title} #{self.id}>"


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total(self) -> Decimal:
        # Keep as Decimal to avoid float rounding issues in templates
        return (self.unit_price or Decimal("0")) * Decimal(self.qty or 0)

    def __repr__(self) -> str:
        return f"<Booking {self.order_id}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Comment {self.id} on event {self.event_id}>"


class TicketType(db.Model):
    __tablename__ = "ticket_types"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TicketType {self.name} for event {self.event_id}>"
