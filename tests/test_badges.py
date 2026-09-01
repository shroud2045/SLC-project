from datetime import date, timedelta
from app.extensions import db
from app.models.post import LockInPost
from app.models.timer import TimerSession
from app.models.badge import Badge, UserBadge
from app.services.badge_service import BadgeService


def test_first_lockin_badge_unlock(app, regular_user):
    """Verifies that posting a daily log unlocks the 'First Lock-In' badge."""
    with app.app_context():
        p = LockInPost(
            user_id=regular_user.id,
            post_date=date.today(),
            title='Day 1 Kickoff',
            description='First post',
            hours_worked=2.0
        )
        db.session.add(p)
        db.session.commit()

        unlocked = BadgeService.evaluate_user_badges(regular_user.id)
        slugs = [b.slug for b in unlocked]
        assert 'streak_1' in slugs

        # Running again should not award duplicate badges
        unlocked_again = BadgeService.evaluate_user_badges(regular_user.id)
        assert len(unlocked_again) == 0

        user_badges = UserBadge.query.filter_by(user_id=regular_user.id).all()
        assert len(user_badges) >= 1


def test_hours_milestone_badge_unlock(app, regular_user):
    """Verifies that reaching 10 hours unlocks the '10 Hours Locked' badge."""
    with app.app_context():
        p = LockInPost(
            user_id=regular_user.id,
            post_date=date.today(),
            title='Marathon Day',
            description='Deep work marathon',
            hours_worked=12.0
        )
        db.session.add(p)
        db.session.commit()

        unlocked = BadgeService.evaluate_user_badges(regular_user.id)
        slugs = [b.slug for b in unlocked]
        assert 'hours_10' in slugs
