from datetime import date, timedelta
from app.extensions import db
from app.models.post import LockInPost
from app.services.streak_service import StreakService


def test_streak_calculation_consecutive_days(app, regular_user):
    """Verifies that consecutive daily logs increment the streak properly."""
    today = date(2026, 9, 5)

    with app.app_context():
        # Day 1, Day 2, Day 3
        p1 = LockInPost(user_id=regular_user.id, post_date=today - timedelta(days=2), title='Day 1', description='D1', hours_worked=2.0)
        p2 = LockInPost(user_id=regular_user.id, post_date=today - timedelta(days=1), title='Day 2', description='D2', hours_worked=2.0)
        p3 = LockInPost(user_id=regular_user.id, post_date=today, title='Day 3', description='D3', hours_worked=3.0)
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        stats = StreakService.calculate_streaks(regular_user.id, reference_date=today)
        assert stats['current_streak'] == 3
        assert stats['longest_streak'] == 3
        assert stats['is_active_today'] is True
        assert stats['total_hours'] == 7.0
        assert stats['today_hours'] == 3.0


def test_streak_reset_after_gap(app, regular_user):
    """Verifies that a gap of > 1 day breaks the current streak while preserving the longest streak."""
    today = date(2026, 9, 10)

    with app.app_context():
        # Historic streak of 4 days: Sept 1, 2, 3, 4
        for d in range(1, 5):
            p = LockInPost(user_id=regular_user.id, post_date=date(2026, 9, d), title=f'Day {d}', description='D', hours_worked=1.0)
            db.session.add(p)
        db.session.commit()

        # Missed Sept 5, 6, 7, 8, 9. Logged today on Sept 10
        p_today = LockInPost(user_id=regular_user.id, post_date=today, title='Day 10', description='D', hours_worked=2.0)
        db.session.add(p_today)
        db.session.commit()

        stats = StreakService.calculate_streaks(regular_user.id, reference_date=today)
        assert stats['current_streak'] == 1  # Reset to 1 on today's new log
        assert stats['longest_streak'] == 4  # Preserved historic best
        assert stats['total_active_days'] == 5
