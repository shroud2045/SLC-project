from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role:
    USER = 'USER'
    MODERATOR = 'MODERATOR'
    ADMIN = 'ADMIN'
    ALL = [USER, MODERATOR, ADMIN]


class User(db.Model):
    """User database model representing member accounts."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default=Role.USER, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_muted = db.Column(db.Boolean, default=False, nullable=False)
    bio = db.Column(db.String(500), default='', nullable=False)
    avatar_filename = db.Column(db.String(255), nullable=True)
    is_profile_public = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    posts = db.relationship('LockInPost', back_populates='author', lazy='dynamic', cascade='all, delete-orphan')
    timer_sessions = db.relationship('TimerSession', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    user_badges = db.relationship('UserBadge', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    user_challenges = db.relationship('UserChallenge', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='author', lazy='dynamic', cascade='all, delete-orphan')
    reactions = db.relationship('PostReaction', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', back_populates='author', lazy='dynamic', cascade='all, delete-orphan')
    reports_filed = db.relationship('Report', back_populates='reporter', lazy='dynamic', foreign_keys='Report.reporter_id')
    audit_logs = db.relationship('AuditLog', back_populates='admin', lazy='dynamic', foreign_keys='AuditLog.admin_id')

    def set_password(self, password: str):
        """Hashes the password with Werkzeug's secure scrypt method."""
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password: str) -> bool:
        """Verifies the password against stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_authenticated(self) -> bool:
        return True

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_moderator(self) -> bool:
        return self.role in (Role.ADMIN, Role.MODERATOR)

    def has_role(self, role: str) -> bool:
        if self.role == Role.ADMIN:
            return True
        if self.role == Role.MODERATOR and role == Role.MODERATOR:
            return True
        return self.role == role

    def to_dict(self, include_private: bool = False) -> dict:
        """Serializes user info safely without leaking sensitive hashes or email if private."""
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'bio': self.bio,
            'avatar_filename': self.avatar_filename,
            'is_profile_public': self.is_profile_public,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_private:
            data.update({
                'email': self.email,
                'is_active': self.is_active,
                'is_muted': self.is_muted,
                'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
            })
        return data

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
