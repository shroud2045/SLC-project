from datetime import datetime, timezone
from app.extensions import db


class ReactionType:
    FIRE = 'FIRE'          # 🔥
    MUSCLE = 'MUSCLE'      # 💪
    TARGET = 'TARGET'      # 🎯
    ROCKET = 'ROCKET'      # 🚀
    BRAIN = 'BRAIN'        # 🧠
    ALL = [FIRE, MUSCLE, TARGET, ROCKET, BRAIN]
    EMOJIS = {
        FIRE: '🔥',
        MUSCLE: '💪',
        TARGET: '🎯',
        ROCKET: '🚀',
        BRAIN: '🧠'
    }


class ReportTargetType:
    POST = 'POST'
    COMMENT = 'COMMENT'
    CHAT_MESSAGE = 'CHAT_MESSAGE'
    USER = 'USER'
    ALL = [POST, COMMENT, CHAT_MESSAGE, USER]


class ReportStatus:
    PENDING = 'PENDING'
    RESOLVED = 'RESOLVED'
    DISMISSED = 'DISMISSED'
    ALL = [PENDING, RESOLVED, DISMISSED]


class Comment(db.Model):
    """Comments on community lock-in posts."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('lock_in_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = db.relationship('LockInPost', back_populates='comments')
    author = db.relationship('User', back_populates='comments')

    def can_delete(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        return self.user_id == user.id or user.is_moderator() or self.post.user_id == user.id

    def __repr__(self):
        return f"<Comment {self.id} on Post {self.post_id} by User {self.user_id}>"


class PostReaction(db.Model):
    """User reactions (fire, muscle, target, rocket, brain) on community posts."""
    __tablename__ = 'post_reactions'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('lock_in_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reaction_type = db.Column(db.String(20), default=ReactionType.FIRE, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = db.relationship('LockInPost', back_populates='reactions')
    user = db.relationship('User', back_populates='reactions')

    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', 'reaction_type', name='uq_post_user_reaction'),
    )

    def __repr__(self):
        return f"<PostReaction {self.reaction_type} on Post {self.post_id} by User {self.user_id}>"


class Report(db.Model):
    """User reports filed on abusive content or harassment."""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    target_type = db.Column(db.String(30), nullable=False, index=True)  # POST, COMMENT, CHAT_MESSAGE, USER
    target_id = db.Column(db.Integer, nullable=False, index=True)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default=ReportStatus.PENDING, nullable=False, index=True)
    admin_notes = db.Column(db.Text, default='', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    reporter = db.relationship('User', back_populates='reports_filed', foreign_keys=[reporter_id])

    def __repr__(self):
        return f"<Report {self.id}: {self.target_type} #{self.target_id} - Status: {self.status}>"
