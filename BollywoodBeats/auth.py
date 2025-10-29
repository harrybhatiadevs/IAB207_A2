from flask import Blueprint, flash, render_template, url_for, redirect
from sqlalchemy import or_
from flask_login import login_user, logout_user, login_required
from .models import User
from .forms import LoginForm, RegisterForm
from . import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error = None

    if form.validate_on_submit():
        identifier = form.user_name.data.strip()
        password = form.password.data
        user = db.session.scalar(
            db.select(User).where(
                or_(
                    User.email == identifier,
                    User.username == identifier,
                )
            )
        )

        if user is None:
            error = 'Invalid username or email.'
        elif not user.check_password(password):
            error = 'Invalid password.'

        if error is None:
            login_user(user)
            return redirect(url_for('main.index'))
        flash(error)

    return render_template('user.html', form=form, heading='Login')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        first_name = form.first_name.data.strip()
        last_name = form.last_name.data.strip()
        username = form.username.data.strip()
        contact_number = form.contact_number.data.strip()
        street_address = form.street_address.data.strip()

        existing_user = db.session.scalar(db.select(User).where(User.email == email))
        if existing_user:
            flash('Email already registered, please log in.')
            return redirect(url_for('auth.login'))

        existing_username = db.session.scalar(
            db.select(User).where(User.username == username)
        )
        if existing_username:
            flash('Username already taken, please choose another.')
            return redirect(url_for('auth.register'))

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            contact_number=contact_number,
            street_address=street_address
        )
        
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('auth.login'))

    return render_template('user.html', form=form, heading='Register')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))
