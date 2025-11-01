"""WTForms definitions for accounts, events, bookings, and comments."""

from datetime import datetime
from flask_wtf import FlaskForm
from wtforms.fields import (
    TextAreaField,
    SubmitField,
    StringField,
    PasswordField,
    DateTimeLocalField,
    IntegerField,
    DecimalField,
    SelectField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    Email,
    EqualTo,
    Optional,
    NumberRange,
    ValidationError,
)
from flask_wtf.file import FileField, FileAllowed
from wtforms import FieldList, FormField, Form

# Creates the login information
class LoginForm(FlaskForm):
    user_name=StringField(
        "Email or Username", validators=[InputRequired("Enter your email or username")]
    )
    password=PasswordField("Password", validators=[InputRequired('Enter user password')])
    submit = SubmitField("Login")

 # Registration form
class RegisterForm(FlaskForm):
    first_name = StringField(
        "First Name",
        validators=[InputRequired("Enter first name"), Length(max=80)],
    )
    last_name = StringField(
        "Last Name",
        validators=[InputRequired("Enter last name"), Length(max=80)],
    )
    username = StringField(
        "Username",
        validators=[InputRequired("Enter a username"), Length(max=80)],
    )
    email = StringField(
        "Email Address",
        validators=[InputRequired("Enter an email"), Email("Please enter a valid email")],
    )
    contact_number = StringField(
        "Phone Number",
        validators=[
            InputRequired("Enter a phone number"),
            Length(min=8, max=20, message="Phone number must be between 8 and 20 characters"),
        ],
    )
    street_address = StringField(
        "Street Address",
        validators=[InputRequired("Enter a street address"), Length(max=255)],
    )
    # Confirming password, passwords should match between fields
    password=PasswordField("Password", validators=[InputRequired(),
                  EqualTo('confirm', message="Passwords should match")])
    confirm = PasswordField("Confirm Password")

    # submit button
    submit = SubmitField("Register")

class UpdateAccountForm(FlaskForm):
    first_name = StringField(
        "First Name",
        validators=[InputRequired("Enter first name"), Length(max=80)],
    )
    last_name = StringField(
        "Last Name",
        validators=[InputRequired("Enter last name"), Length(max=80)],
    )
    username = StringField(
        "Username",
        validators=[InputRequired("Enter a username"), Length(max=80)],
    )
    email = StringField(
        "Email Address",
        validators=[InputRequired("Enter an email"), Email("Please enter a valid email")],
    )
    contact_number = StringField(
        "Phone Number",
        validators=[
            InputRequired("Enter a phone number"),
            Length(min=8, max=20, message="Phone number must be between 8 and 20 characters"),
        ],
    )
    street_address = StringField(
        "Street Address",
        validators=[InputRequired("Enter a street address"), Length(max=255)],
    )
    new_password = PasswordField(
        "New Password",
        validators=[Optional(), Length(min=6, message="Password must be at least 6 characters")],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[EqualTo("new_password", message="Passwords should match")],
    )
    submit = SubmitField("Save Changes")

class DeleteAccountForm(FlaskForm):
    delete = SubmitField("Delete Account")

EVENT_CATEGORY_CHOICES = [
    ("Rock", "Rock"),
    ("Indie", "Indie"),
    ("Classical", "Classical"),
    ("DNB", "DNB"),
    ("EDM", "EDM"),
    ("Jazz", "Jazz"),
    ("Hip-Hop", "Hip-Hop"),
    ("Bollywood", "Bollywood"),
    ("Pop", "Pop"),
    ("Other", "Other"),
]


class TicketTierForm(Form):
    name = StringField(
        "Ticket Name",
        validators=[Optional(), Length(max=120)],
    )
    price = DecimalField(
        "Price",
        places=2,
        validators=[Optional(), NumberRange(min=0, message="Price cannot be negative")],
    )
    quantity = IntegerField(
        "Quantity",
        validators=[Optional(), NumberRange(min=0, message="Quantity cannot be negative")],
    )

    def has_value(self) -> bool:
        """Used to detect whether the admin actually filled this placeholder row."""
        return bool((self.name.data or "").strip())


class EventForm(FlaskForm):
    title = StringField(
        "Event Title",
        validators=[InputRequired("Enter an event title"), Length(max=160)],
    )
    category = SelectField(
        "Category",
        choices=EVENT_CATEGORY_CHOICES,
        validators=[InputRequired("Select a category")],
    )
    description = TextAreaField(
        "Description",
        validators=[InputRequired("Enter a description"), Length(min=10)],
    )
    image = FileField(
        "Event Image",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Image files only"),
        ],
    )
    venue = StringField(
        "Venue",
        validators=[InputRequired("Enter a venue"), Length(max=160)],
    )
    city = StringField(
        "City",
        validators=[InputRequired("Enter a city"), Length(max=80)],
    )
    start_dt = DateTimeLocalField(
        "Start Date & Time",
        format="%Y-%m-%dT%H:%M",
        validators=[InputRequired("Provide a start date and time")],
    )
    capacity = IntegerField(
        "Capacity",
        validators=[
            InputRequired("Enter capacity"),
            NumberRange(min=1, message="Capacity must be at least 1"),
        ],
    )
    price = DecimalField(
        "Default Ticket Price",
        places=2,
        rounding=None,
        validators=[
            InputRequired("Enter ticket price"),
            NumberRange(min=0, message="Price cannot be negative"),
        ],
    )
    ticket_types = FieldList(FormField(TicketTierForm), min_entries=3, max_entries=5)
    submit = SubmitField("Create Event")

    def validate_start_dt(self, field):
        if field.data is None:
            return
        # Prevent organisers from accidentally creating already-expired events.
        if field.data <= datetime.utcnow():
            raise ValidationError("Start date must be in the future.")


class EventUpdateForm(FlaskForm):
    title = StringField(
        "Event Title",
        validators=[InputRequired("Enter an event title"), Length(max=160)],
    )
    category = SelectField(
        "Category",
        choices=EVENT_CATEGORY_CHOICES,
        validators=[InputRequired("Select a category")],
    )
    description = TextAreaField(
        "Description",
        validators=[InputRequired("Enter a description"), Length(min=10)],
    )
    image = FileField(
        "Event Image",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Image files only")],
    )
    venue = StringField(
        "Venue",
        validators=[InputRequired("Enter a venue"), Length(max=160)],
    )
    city = StringField(
        "City",
        validators=[InputRequired("Enter a city"), Length(max=80)],
    )
    start_dt = DateTimeLocalField(
        "Start Date & Time",
        format="%Y-%m-%dT%H:%M",
        validators=[InputRequired("Provide a start date and time")],
    )
    capacity = IntegerField(
        "Capacity",
        validators=[
            InputRequired("Enter capacity"),
            NumberRange(min=1, message="Capacity must be at least 1"),
        ],
    )
    price = DecimalField(
        "Default Ticket Price",
        places=2,
        rounding=None,
        validators=[
            InputRequired("Enter ticket price"),
            NumberRange(min=0, message="Price cannot be negative"),
        ],
    )
    ticket_types = FieldList(FormField(TicketTierForm), min_entries=3, max_entries=5)
    submit = SubmitField("Save Changes")

    def validate_start_dt(self, field):
        if field.data is None:
            return
        # Keep edits from moving events back into the past, which breaks availability logic.
        if field.data <= datetime.utcnow():
            raise ValidationError("Start date must be in the future.")


class DeleteEventForm(FlaskForm):
    submit = SubmitField("Delete Event")


class CancelEventForm(FlaskForm):
    submit = SubmitField("Cancel Event")


class BookingForm(FlaskForm):
    qty = IntegerField(
        "Number of Tickets",
        validators=[
            InputRequired("Enter how many tickets to book"),
            NumberRange(min=1, message="You must book at least one ticket"),
        ],
    )
    submit = SubmitField("Confirm Booking")


class CommentForm(FlaskForm):
    body = TextAreaField(
        "Leave a comment",
        validators=[
            InputRequired("Enter a comment"),
            Length(min=5, max=500, message="Comment must be between 5 and 500 characters"),
        ],
    )
    submit = SubmitField("Post Comment")
