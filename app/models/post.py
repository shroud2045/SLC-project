from datetime import datetime, timezone, date
from app.extensions import db


class PostPrivacy:
    PRIVATE = 'PRIVATE'
    COMMUNITY = 'COMMUNITY'
    ALL = [PRIVATE, COMMUNITY]


# Association table for post tags
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('lock_in_posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Tag(db.Model):
    """Categorical tags for lock-in posts (e.g. #networking, #cybersecurity, #gym, #coding)."""
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)

    posts = db.relationship('LockInPost', secondary=post_tags, back_populates='tags')

    def __repr__(self):
        return f"<Tag #{self.name}>"


class LockInPost(db.Model):
    """Daily Lock-In journal entries recorded by users."""
    __tablename__ = 'lock_in_posts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    worked_on = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Text, nullable=True)
    learned = db.Column(db.Text, nullable=True)
    hours_worked = db.Column(db.Float, default=0.0, nullable=False)
    privacy = db.Column(db.String(20), default=PostPrivacy.PRIVATE, nullable=False, index=True)
    is_moderated = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    author = db.relationship('User', back_populates='posts')
    images = db.relationship('ProgressImage', back_populates='post', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='post', lazy='dynamic', cascade='all, delete-orphan')
    reactions = db.relationship('PostReaction', back_populates='post', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=post_tags, back_populates='posts')

    def is_public(self) -> bool:
        return self.privacy == PostPrivacy.COMMUNITY

    def can_view(self, user) -> bool:
        """Object-level authorization check: User can view if community post, or if they own it, or are admin/moderator."""
        if self.privacy == PostPrivacy.COMMUNITY:
            return True
        if not user or not user.is_authenticated:
            return False
        return self.user_id == user.id or user.is_moderator()

    def can_edit(self, user) -> bool:
        """Only the author or an admin can edit a post."""
        if not user or not user.is_authenticated:
            return False
        return self.user_id == user.id or user.is_admin()

    def can_delete(self, user) -> bool:
        """Author, moderator, or admin can delete."""
        if not user or not user.is_authenticated:
            return False
        return self.user_id == user.id or user.is_moderator()

    def reaction_counts(self) -> dict:
        """Returns aggregated counts of each reaction type."""
        counts = {}
        for r in self.reactions:
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
        return counts

    def __repr__(self):
        return f"<LockInPost {self.id}: {self.title} by User {self.user_id}>"


class ProgressImage(db.Model):
    """Uploaded screenshots or photos attached to a lock-in post."""
    __tablename__ = 'progress_images'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('lock_in_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = db.relationship('LockInPost', back_populates='images')
    user = db.relationship('User')

    def __repr__(self):
        return f"<ProgressImage {self.filename}>"
