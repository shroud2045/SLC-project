from datetime import datetime, timezone, date
from flask import Blueprint, render_template
from app.utils.decorators import login_required, get_current_user
from app.services.streak_service import StreakService
from app.services.badge_service import BadgeService
from app.models.post import LockInPost
from app.models.timer import TimerSession
from app.models.badge import Badge, UserBadge, BadgeRequirement
from app.models.challenge import Challenge, UserChallenge

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """User personal productivity dashboard with streak stats, badges, and quick controls."""
    current_user = get_current_user()
    today = datetime.now(timezone.utc).date()

    # Automatically evaluate badges upon dashboard load
    newly_earned = BadgeService.evaluate_user_badges(current_user.id)

    # Calculate streak and time stats
    stats = StreakService.calculate_streaks(current_user.id, reference_date=today)

    # Today's post if any
    today_post = LockInPost.query.filter_by(user_id=current_user.id, post_date=today).first()

    # Recent posts (last 5)
    recent_posts = LockInPost.query.filter_by(user_id=current_user.id)\
        .order_by(LockInPost.post_date.desc(), LockInPost.created_at.desc())\
        .limit(5).all()

    # Recent timer sessions (last 5)
    recent_timers = TimerSession.query.filter_by(user_id=current_user.id)\
        .order_by(TimerSession.created_at.desc())\
        .limit(5).all()

    # Earned badges
    earned_badges = Badge.query.join(UserBadge, UserBadge.badge_id == Badge.id)\
        .filter(UserBadge.user_id == current_user.id)\
        .order_by(UserBadge.earned_at.desc()).all()

    earned_badge_ids = {b.id for b in earned_badges}

    # Next badge to unlock
    next_streak_badge = Badge.query.filter(
        Badge.requirement_type == BadgeRequirement.STREAK_DAYS,
        Badge.threshold > stats['current_streak'],
        ~Badge.id.in_(earned_badge_ids) if earned_badge_ids else True
    ).order_by(Badge.threshold.asc()).first()

    # Active challenges
    active_challenges = Challenge.query.filter_by(is_active=True).all()
    user_challenges = {
        uc.challenge_id: uc for uc in UserChallenge.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        'dashboard/dashboard.html',
        current_user=current_user,
        stats=stats,
        today_post=today_post,
        recent_posts=recent_posts,
        recent_timers=recent_timers,
        earned_badges=earned_badges,
        next_streak_badge=next_streak_badge,
        active_challenges=active_challenges,
        user_challenges=user_challenges,
        newly_earned=newly_earned
    )
