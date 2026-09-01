import pytest
from app.extensions import db
from app.models.user import User, Role
from app.services.auth_service import AuthService


def test_password_strength_policy():
    """Verifies that password policy rules are strictly enforced."""
    # Too short
    valid, err = AuthService.validate_password_strength("Short1!")
    assert not valid
    assert "at least 8 characters" in err

    # Missing uppercase
    valid, err = AuthService.validate_password_strength("lowercase123!")
    assert not valid
    assert "uppercase letter" in err

    # Missing lowercase
    valid, err = AuthService.validate_password_strength("UPPERCASE123!")
    assert not valid
    assert "lowercase letter" in err

    # Missing number
    valid, err = AuthService.validate_password_strength("NoNumbersHere!")
    assert not valid
    assert "number" in err

    # Missing special symbol
    valid, err = AuthService.validate_password_strength("NoSymbols1234")
    assert not valid
    assert "special character" in err

    # Valid strong password
    valid, err = AuthService.validate_password_strength("ValidPass123!@#")
    assert valid
    assert err is None


def test_user_registration(client, app):
    """Tests successful user registration and ensures role defaults safely to USER."""
    res = client.post('/auth/register', data={
        'username': 'new_operator',
        'email': 'new@lockin.com',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!',
        'role': 'ADMIN'  # Attempting privilege escalation in post body
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Welcome to' in res.data

    with app.app_context():
        user = User.query.filter_by(username='new_operator').first()
        assert user is not None
        assert user.role == Role.USER  # Escalation prevented
        assert user.check_password('SecurePassword123!')
        assert not user.check_password('WrongPassword')


def test_duplicate_registration_rejected(client, regular_user):
    """Tests that duplicate username or email is rejected."""
    res = client.post('/auth/register', data={
        'username': regular_user.username,
        'email': 'different@lockin.com',
        'password': 'StrongPassword123!',
        'confirm_password': 'StrongPassword123!'
    }, follow_redirects=True)

    assert b'already exists' in res.data


def test_user_login_and_logout(client, regular_user):
    """Tests login flow and session clearing on logout."""
    # Valid login
    res = client.post('/auth/login', data={
        'identifier': regular_user.username,
        'password': 'StrongPass123!'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Welcome back' in res.data

    # Logout
    res_logout = client.post('/auth/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b'logged out' in res_logout.data


def test_suspended_user_login_blocked(client, app, regular_user):
    """Verifies suspended users cannot authenticate."""
    with app.app_context():
        u = db.session.get(User, regular_user.id)
        u.is_active = False
        db.session.commit()

    res = client.post('/auth/login', data={
        'identifier': regular_user.username,
        'password': 'StrongPass123!'
    }, follow_redirects=True)

    assert b'suspended' in res.data
