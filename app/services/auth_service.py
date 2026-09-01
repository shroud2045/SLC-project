import re
from typing import Tuple, Optional
from app.extensions import db
from app.models.user import User, Role


class AuthService:
    """Service handling user authentication, registration, and password security policies."""

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
        """
        Enforces strong password policy:
        - At least 8 characters
        - Contains at least 1 uppercase letter
        - Contains at least 1 lowercase letter
        - Contains at least 1 number
        - Contains at least 1 special character
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if len(password) > 128:
            return False, "Password cannot exceed 128 characters."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter (A-Z)."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter (a-z)."
        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one number (0-9)."
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/`~]", password):
            return False, "Password must contain at least one special character (!@#$%^&*...)."
        return True, None

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, Optional[str]]:
        """Validates username format and length."""
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long."
        if len(username) > 30:
            return False, "Username cannot exceed 30 characters."
        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            return False, "Username can only contain letters, numbers, underscores, dashes, and periods."
        return True, None

    @staticmethod
    def register_user(username: str, email: str, password: str, role: str = Role.USER) -> Tuple[Optional[User], Optional[str]]:
        """Registers a new user after validation, ensuring role is never elevated by untrusted inputs."""
        # Validate username
        is_valid_user, user_err = AuthService.validate_username(username)
        if not is_valid_user:
            return None, user_err

        # Validate password strength
        is_valid_pwd, pwd_err = AuthService.validate_password_strength(password)
        if not is_valid_pwd:
            return None, pwd_err

        # Normalize inputs
        username_clean = username.strip()
        email_clean = email.strip().lower()

        # Check uniqueness
        if User.query.filter_by(username=username_clean).first():
            return None, "A user with that username already exists."
        if User.query.filter_by(email=email_clean).first():
            return None, "An account with that email address already exists."

        # Ensure safe role assignment
        assigned_role = Role.USER if role not in (Role.ADMIN, Role.MODERATOR) else role

        user = User(
            username=username_clean,
            email=email_clean,
            role=assigned_role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user, None

    @staticmethod
    def authenticate_user(identifier: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticates user by username or email.
        Uses generic error messages to prevent account enumeration.
        """
        clean_id = identifier.strip()
        db.session.expire_all()
        # Search by username or email
        user = User.query.filter(
            (User.username == clean_id) | (User.email == clean_id.lower())
        ).first()

        if not user or not user.check_password(password):
            return None, "Invalid username/email or password."

        if not user.is_active:
            return None, "This account has been suspended. Please contact an administrator."

        return user, None
