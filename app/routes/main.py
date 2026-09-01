from flask import Blueprint, render_template, redirect, url_for, send_file, current_app
from app.utils.decorators import get_current_user
from app.utils.helpers import get_archetype_cards
from app.models.badge import Badge
from app.models.challenge import Challenge
from app.models.post import LockInPost, PostPrivacy
from pathlib import Path

main_bp = Blueprint('main', __name__)

@main_bp.route('/google55c3db374be43eeb.html')
def google_verification():
    verification_file = Path(current_app.root_path).parent / 'google55c3db374be43eeb.html'
    return send_file(verification_file, mimetype='text/html')


@main_bp.route('/')
def index():
    """Public landing page showcasing SLC features without exposing private user data."""
    current_user = get_current_user()
    if current_user:
        return redirect(url_for('dashboard.index'))

    archetypes = get_archetype_cards()
    sample_badges = Badge.query.order_by(Badge.threshold.asc()).limit(6).all()
    active_challenges = Challenge.query.filter_by(is_active=True).limit(3).all()
    recent_public_posts_count = LockInPost.query.filter_by(privacy=PostPrivacy.COMMUNITY).count()

    return render_template(
        'main/index.html',
        archetypes=archetypes,
        sample_badges=sample_badges,
        active_challenges=active_challenges,
        public_posts_count=recent_public_posts_count
    )


@main_bp.route('/guidelines')
def guidelines():
    """Community rules and moderation guidelines."""
    current_user = get_current_user()
    return render_template('main/guidelines.html', current_user=current_user)
