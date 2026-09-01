from flask import Blueprint, render_template
from app.models.badge import Badge, UserBadge, BadgeCategory, BadgeRequirement
from app.services.streak_service import StreakService
from app.services.badge_service import BadgeService
from app.models.post import LockInPost
from app.models.timer import TimerSession
from app.models.challenge import UserChallenge
from app.utils.decorators import login_required, get_current_user

badges_bp = Blueprint('badges', __name__, url_prefix='/badges')


@badges_bp.route('/')
@login_required
def index():
    """Badges and achievements showcase with dynamic progress tracking."""
    current_user = get_current_user()

    # Re-evaluate in case any new badges unlocked
    BadgeService.evaluate_user_badges(current_user.id)

    # Fetch stats for progress bars
    stats = StreakService.calculate_streaks(current_user.id)
    post_count = LockInPost.query.filter_by(user_id=current_user.id).count()
    timer_count = TimerSession.query.filter_by(user_id=current_user.id).count()
    challenge_count = UserChallenge.query.filter_by(user_id=current_user.id, is_completed=True).count()

    metrics = {
        BadgeRequirement.STREAK_DAYS: max(stats['current_streak'], stats['longest_streak']),
        BadgeRequirement.TOTAL_HOURS: stats['total_hours'],
        BadgeRequirement.POST_COUNT: post_count,
        BadgeRequirement.TIMER_COUNT: timer_count,
        BadgeRequirement.CHALLENGE_COUNT: challenge_count,
    }

    # Fetch earned badges map
    user_badges = {
        ub.badge_id: ub for ub in UserBadge.query.filter_by(user_id=current_user.id).all()
    }

    all_badges = Badge.query.order_by(Badge.threshold.asc()).all()

    # Group by category
    badges_by_category = {}
    for cat in BadgeCategory.ALL:
        badges_by_category[cat] = [b for b in all_badges if b.category == cat]

    return render_template(
        'badges/badges.html',
        current_user=current_user,
        badges_by_category=badges_by_category,
        user_badges=user_badges,
        metrics=metrics,
        earned_count=len(user_badges),
        total_count=len(all_badges)
    )
