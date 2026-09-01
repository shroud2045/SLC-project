from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash
from app.extensions import db
from app.models.challenge import Challenge, UserChallenge
from app.services.streak_service import StreakService
from app.utils.decorators import login_required, get_current_user

challenges_bp = Blueprint('challenges', __name__, url_prefix='/challenges')


@challenges_bp.route('/')
@login_required
def index():
    """Lists community productivity challenges and user progress."""
    current_user = get_current_user()
    active_challenges = Challenge.query.filter_by(is_active=True).all()
    user_challenges_map = {
        uc.challenge_id: uc for uc in UserChallenge.query.filter_by(user_id=current_user.id).all()
    }

    stats = StreakService.calculate_streaks(current_user.id)

    return render_template(
        'challenges/challenges.html',
        current_user=current_user,
        challenges=active_challenges,
        user_challenges=user_challenges_map,
        stats=stats
    )


@challenges_bp.route('/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id: int):
    """Enrolls current user in a challenge."""
    current_user = get_current_user()
    challenge = db.get_or_404(Challenge, challenge_id)

    existing = UserChallenge.query.filter_by(user_id=current_user.id, challenge_id=challenge.id).first()
    if existing:
        flash('You are already enrolled in this challenge.', 'info')
    else:
        uc = UserChallenge(
            user_id=current_user.id,
            challenge_id=challenge.id,
            joined_at=datetime.now(timezone.utc)
        )
        db.session.add(uc)
        db.session.commit()
        flash(f'Enrolled in challenge: {challenge.title}! Push your limits.', 'success')

    return redirect(url_for('challenges.index'))
