from datetime import datetime, timezone
from app.extensions import db


class ModerationSeverity:
    BLOCK = 'BLOCK'  # Automatically blocks the post/message from being submitted
    FLAG = 'FLAG'    # Allows message but flags for urgent moderator review
    WARN = 'WARN'    # Replaces matches with asterisks
    ALL = [BLOCK, FLAG, WARN]


class BannedWord(db.Model):
    """Configurable server-side content filter terms and regex patterns."""
    __tablename__ = 'banned_words'

    id = db.Column(db.Integer, primary_key=True)
    word_or_pattern = db.Column(db.String(150), unique=True, nullable=False, index=True)
    severity = db.Column(db.String(20), default=ModerationSeverity.BLOCK, nullable=False)
    is_regex = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<BannedWord '{self.word_or_pattern}' ({self.severity})>"
