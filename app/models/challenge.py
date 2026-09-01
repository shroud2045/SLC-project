from datetime import datetime, timezone
from app.extensions import db


class Challenge(db.Model):
    """Community productivity challenges (e.g. '7-Day Cyber Sprint', '30-Day Beast Mode')."""
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_days = db.Column(db.Integer, default=0, nullable=False)
    target_hours = db.Column(db.Float, default=0.0, nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    badge = db.relationship('Badge')
    participants = db.relationship('UserChallenge', back_populates='challenge', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Challenge {self.title}>"


class UserChallenge(db.Model):
    """Tracks a user's participation and progress toward a specific challenge."""
    __tablename__ = 'user_challenges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False, index=True)
    progress_days = db.Column(db.Integer, default=0, nullable=False)
    progress_hours = db.Column(db.Float, default=0.0, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', back_populates='user_challenges')
    challenge = db.relationship('Challenge', back_populates='participants')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'challenge_id', name='uq_user_challenge'),
    )

    def __repr__(self):
        return f"<UserChallenge User {self.user_id} - Challenge {self.challenge_id} (Done: {self.is_completed})>"
