from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import current_user, login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing():
    # Always show the landing page
    return render_template('landing.html')

@main_bp.route('/home')
@login_required
def index():
    events = [
        {'id': 1, 'title': 'Bollywood Beats', 'genre': 'Bollywood', 'status': 'Open'},
        {'id': 2, 'title': 'Rhythm Nation', 'genre': 'HipHop', 'status': 'Sold Out'},
    ]
    return render_template('index.html', events=events)


# Event details page route
@main_bp.route('/event/<int:event_id>')
@login_required
def event_details(event_id):
    # Placeholder event data
    event = {
        'id': event_id,
        'title': 'Bollywood Beats',
        'genre': 'Bollywood',
        'description': 'Experience live music and dance!'
    }
    return render_template('event.html', event=event)

# Event creation page route
@main_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        # Placeholder form handling
        print(request.form)
    return render_template('create.html')

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
