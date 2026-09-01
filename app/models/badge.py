from datetime import datetime, timezone
from app.extensions import db


class BadgeCategory:
    STREAK = 'STREAK'
    HOURS = 'HOURS'
    ACTIVITY = 'ACTIVITY'
    CHALLENGE = 'CHALLENGE'
    SPECIAL = 'SPECIAL'
    ALL = [STREAK, HOURS, ACTIVITY, CHALLENGE, SPECIAL]


class BadgeRequirement:
    STREAK_DAYS = 'STREAK_DAYS'
    TOTAL_HOURS = 'TOTAL_HOURS'
    POST_COUNT = 'POST_COUNT'
    TIMER_COUNT = 'TIMER_COUNT'
    CHALLENGE_COUNT = 'CHALLENGE_COUNT'
    ALL = [STREAK_DAYS, TOTAL_HOURS, POST_COUNT, TIMER_COUNT, CHALLENGE_COUNT]


class BadgeRarity:
    COMMON = 'COMMON'
    UNCOMMON = 'UNCOMMON'
    RARE = 'RARE'
    EPIC = 'EPIC'
    LEGENDARY = 'LEGENDARY'
    MYTHIC = 'MYTHIC'
    ALL = [COMMON, UNCOMMON, RARE, EPIC, LEGENDARY, MYTHIC]


class Badge(db.Model):
    """System achievement badges unlockable through deterministic milestones."""
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=False, default='🔥')
    category = db.Column(db.String(30), default=BadgeCategory.STREAK, nullable=False, index=True)
    requirement_type = db.Column(db.String(50), nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    rarity = db.Column(db.String(30), default=BadgeRarity.COMMON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user_badges = db.relationship('UserBadge', back_populates='badge', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Badge {self.name} ({self.slug}) - Req: {self.requirement_type} >= {self.threshold}>"


class UserBadge(db.Model):
    """Records which badges a user has earned and when."""
    __tablename__ = 'user_badges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id', ondelete='CASCADE'), nullable=False, index=True)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship('User', back_populates='user_badges')
    badge = db.relationship('Badge', back_populates='user_badges')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),
    )

    def __repr__(self):
        return f"<UserBadge User {self.user_id} - Badge {self.badge_id}>"
