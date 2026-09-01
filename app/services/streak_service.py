from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Set, Tuple
from sqlalchemy import func
from app.extensions import db
from app.models.post import LockInPost
from app.models.timer import TimerSession


class StreakService:
    """
    Deterministic streak and consistency engine.
    Calculates consecutive active days, lifetime best streaks, and total hours worked.
    """

    @staticmethod
    def get_user_qualifying_dates(user_id: int) -> Set[date]:
        """
        Retrieves all distinct dates where the user logged qualifying progress:
        - A LockInPost created for that date (hours_worked > 0 or detailed submission)
        - OR a validated TimerSession with duration >= 10 minutes
        """
        post_dates = db.session.query(LockInPost.post_date)\
            .filter(LockInPost.user_id == user_id)\
            .distinct().all()

        timer_dates = db.session.query(func.date(TimerSession.start_time))\
            .filter(TimerSession.user_id == user_id, TimerSession.duration_minutes >= 10.0)\
            .distinct().all()

        qualifying = set()
        for p in post_dates:
            if p[0]:
                qualifying.add(p[0] if isinstance(p[0], date) else datetime.strptime(str(p[0]), '%Y-%m-%d').date())

        for t in timer_dates:
            if t[0]:
                if isinstance(t[0], date):
                    qualifying.add(t[0])
                else:
                    try:
                        qualifying.add(datetime.strptime(str(t[0]), '%Y-%m-%d').date())
                    except ValueError:
                        pass

        return qualifying

    @classmethod
    def calculate_streaks(cls, user_id: int, reference_date: date = None) -> Dict:
        """
        Calculates:
        - current_streak: consecutive days leading up to today or yesterday
        - longest_streak: maximum historic streak
        - is_active_today: whether progress was logged today
        - total_active_days: count of unique qualifying days
        - total_hours_worked: sum of logged hours
        - today_hours_worked: sum of hours logged today
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc).date()

        dates_set = cls.get_user_qualifying_dates(user_id)
        sorted_dates = sorted(list(dates_set))

        if not sorted_dates:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'is_active_today': False,
                'total_active_days': 0,
                'total_hours': 0.0,
                'today_hours': 0.0,
                'streak_freeze_active': False
            }

        is_active_today = reference_date in dates_set
        yesterday = reference_date - timedelta(days=1)

        # 1. Calculate Current Streak
        current_streak = 0
        if is_active_today:
            current_streak = 1
            check_date = yesterday
        elif yesterday in dates_set:
            current_streak = 1
            check_date = yesterday - timedelta(days=1)
        else:
            current_streak = 0
            check_date = None

        if current_streak > 0 and check_date:
            while check_date in dates_set:
                current_streak += 1
                check_date -= timedelta(days=1)

        # 2. Calculate Longest Historic Streak
        longest_streak = 0
        current_run = 0
        prev_date = None

        for d in sorted_dates:
            if prev_date is None:
                current_run = 1
            elif (d - prev_date).days == 1:
                current_run += 1
            elif (d - prev_date).days == 0:
                pass  # duplicate date
            else:
                current_run = 1
            if current_run > longest_streak:
                longest_streak = current_run
            prev_date = d

        longest_streak = max(longest_streak, current_streak)

        # 3. Calculate Total Hours & Today's Hours
        total_post_hours = db.session.query(func.coalesce(func.sum(LockInPost.hours_worked), 0.0))\
            .filter(LockInPost.user_id == user_id).scalar() or 0.0

        total_timer_mins = db.session.query(func.coalesce(func.sum(TimerSession.duration_minutes), 0.0))\
            .filter(TimerSession.user_id == user_id).scalar() or 0.0

        total_hours = round(total_post_hours + (total_timer_mins / 60.0), 2)

        # Today's hours
        today_post_hours = db.session.query(func.coalesce(func.sum(LockInPost.hours_worked), 0.0))\
            .filter(LockInPost.user_id == user_id, LockInPost.post_date == reference_date).scalar() or 0.0

        today_timer_mins = db.session.query(func.coalesce(func.sum(TimerSession.duration_minutes), 0.0))\
            .filter(
                TimerSession.user_id == user_id,
                func.date(TimerSession.start_time) == reference_date
            ).scalar() or 0.0

        today_hours = round(today_post_hours + (today_timer_mins / 60.0), 2)

        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'is_active_today': is_active_today,
            'total_active_days': len(sorted_dates),
            'total_hours': total_hours,
            'today_hours': today_hours
        }
