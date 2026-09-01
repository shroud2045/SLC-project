from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.services.auth_service import AuthService
from app.utils.decorators import get_current_user, rate_limit

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(limit=5, window_seconds=60, key_prefix='register')
def register():
    """User registration with strict input validation and secure password hashing."""
    if get_current_user():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        user, err = AuthService.register_user(username, email, password)
        if err:
            flash(err, 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Log user in directly after successful registration
        session.clear()
        session['user_id'] = user.id
        session.permanent = True
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        flash('Welcome to Shroud’s Lockin Crib! Your journey starts now. Lock in.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=10, window_seconds=60, key_prefix='login')
def login():
    """User authentication with rate limiting and generic error messages."""
    if get_current_user():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not identifier or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('auth/login.html', identifier=identifier)

        user, err = AuthService.authenticate_user(identifier, password)
        if err:
            flash(err, 'danger')
            return render_template('auth/login.html', identifier=identifier)

        session.clear()
        session['user_id'] = user.id
        session.permanent = remember
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        flash(f'Welcome back, {user.username}. Lock in today!', 'success')
        next_page = request.args.get('next')
        # Validate next_page to prevent open redirect vulnerabilities
        if next_page and next_page.startswith('/') and not next_page.startswith('//'):
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clears user session and logs out."""
    session.clear()
    flash('You have been securely logged out. Stay disciplined.', 'info')
    return redirect(url_for('main.index'))
