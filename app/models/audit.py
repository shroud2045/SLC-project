from datetime import datetime, timezone
from app.extensions import db


class AuditAction:
    USER_SUSPEND = 'USER_SUSPEND'
    USER_RESTORE = 'USER_RESTORE'
    USER_MUTE = 'USER_MUTE'
    USER_UNMUTE = 'USER_UNMUTE'
    ROLE_CHANGE = 'ROLE_CHANGE'
    POST_DELETE = 'POST_DELETE'
    COMMENT_DELETE = 'COMMENT_DELETE'
    CHAT_DELETE = 'CHAT_DELETE'
    REPORT_RESOLVE = 'REPORT_RESOLVE'
    FILTER_ADD = 'FILTER_ADD'
    FILTER_DELETE = 'FILTER_DELETE'
    BADGE_CREATE = 'BADGE_CREATE'
    CHALLENGE_CREATE = 'CHALLENGE_CREATE'
    ADMIN_LOGIN = 'ADMIN_LOGIN'
    ALL = [
        USER_SUSPEND, USER_RESTORE, USER_MUTE, USER_UNMUTE,
        ROLE_CHANGE, POST_DELETE, COMMENT_DELETE, CHAT_DELETE,
        REPORT_RESOLVE, FILTER_ADD, FILTER_DELETE, BADGE_CREATE,
        CHALLENGE_CREATE, ADMIN_LOGIN
    ]


class AuditLog(db.Model):
    """Audit log tracking sensitive administrative and moderation operations."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(100), nullable=True)
    details = db.Column(db.Text, default='', nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    admin = db.relationship('User', back_populates='audit_logs', foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AuditLog {self.action} by Admin {self.admin_id} at {self.timestamp}>"
