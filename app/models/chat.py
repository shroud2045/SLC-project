from datetime import datetime, timezone
from app.extensions import db


class ChatMessage(db.Model):
    """Real-time community chat messages with anti-abuse controls."""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_flagged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    author = db.relationship('User', back_populates='chat_messages')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.author.username if self.author else 'Unknown',
            'role': self.author.role if self.author else 'USER',
            'avatar_filename': self.author.avatar_filename if self.author else None,
            'content': '[Message removed by moderator]' if self.is_deleted else self.content,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.strftime('%H:%M:%S'),
            'timestamp': self.created_at.isoformat()
        }

    def __repr__(self):
        return f"<ChatMessage {self.id} by User {self.user_id}>"
