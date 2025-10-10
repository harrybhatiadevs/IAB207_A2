from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class EventStatus(str, Enum):
    OPEN = "Open"
    INACTIVE = "Inactive"
    SOLD_OUT = "Sold Out"
    CANCELLED = "Cancelled"

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name  = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(30), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events   = db.relationship("Event", backref="owner", lazy=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80))
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    venue = db.Column(db.String(160), nullable=False)
    city  = db.Column(db.String(80), nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.Enum(EventStatus), nullable=False, default=EventStatus.OPEN)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = db.relationship("Booking", backref="event", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="event", lazy=True, cascade="all, delete-orphan")

    @property
    def remaining_capacity(self) -> int:
        return max(0, self.capacity - sum(b.qty for b in self.bookings))

class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, index=True, nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total(self):
        return float(self.qty) * float(self.unit_price)

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
