from datetime import datetime, timezone
from app.extensions import db


class TimerMode:
    POMODORO = 'POMODORO'
    CUSTOM = 'CUSTOM'
    STOPWATCH = 'STOPWATCH'
    ALL = [POMODORO, CUSTOM, STOPWATCH]


class TimerCategory:
    STUDY = 'STUDY'
    CODING = 'CODING'
    CYBERSECURITY = 'CYBERSECURITY'
    FITNESS = 'FITNESS'
    WORK = 'WORK'
    READING = 'READING'
    OTHER = 'OTHER'
    ALL = [STUDY, CODING, CYBERSECURITY, FITNESS, WORK, READING, OTHER]


class TimerSession(db.Model):
    """Completed productivity timer sessions validated server-side."""
    __tablename__ = 'timer_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False)
    duration_minutes = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(20), default=TimerMode.POMODORO, nullable=False)
    category = db.Column(db.String(30), default=TimerCategory.STUDY, nullable=False, index=True)
    notes = db.Column(db.String(255), default='', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User', back_populates='timer_sessions')

    @property
    def formatted_duration(self) -> str:
        """Returns human-friendly duration string (e.g. '1h 25m' or '45m')."""
        total_mins = int(self.duration_minutes)
        hours = total_mins // 60
        mins = total_mins % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def __repr__(self):
        return f"<TimerSession {self.id}: User {self.user_id} - {self.duration_minutes:.1f} mins ({self.mode})>"
