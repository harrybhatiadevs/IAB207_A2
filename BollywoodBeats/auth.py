from flask import Blueprint, flash, render_template, request, url_for, redirect
from werkzeug.security import check_password_hash
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
        user_name = form.user_name.data
        password = form.password.data
        user = db.session.scalar(db.select(User).where(User.email == user_name))

        if user is None:
            error = 'Invalid username or email.'
        elif not check_password_hash(user.password_hash, password):
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
        email = form.email.data
        password = form.password.data
        user_name = form.user_name.data

        existing_user = db.session.scalar(db.select(User).where(User.email == email))
        if existing_user:
            flash('Email already registered, please log in.')
            return redirect(url_for('auth.login'))

        new_user = User(
            first_name=user_name,
            last_name="",
            email=email,
            contact_number="",
            street_address=""
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
    return redirect(url_for('main.landing'))
