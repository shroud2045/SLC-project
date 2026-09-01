from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.extensions import db
from app.models.user import User
from app.models.post import LockInPost, PostPrivacy
from app.models.badge import Badge, UserBadge
from app.services.streak_service import StreakService
from app.services.upload_service import UploadService
from app.services.badge_service import BadgeService
from app.utils.decorators import login_required, get_current_user

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/')
@login_required
def my_profile():
    """Redirects to the current user's profile view."""
    current_user = get_current_user()
    return redirect(url_for('profile.view_profile', username=current_user.username))


@profile_bp.route('/<string:username>')
def view_profile(username: str):
    """Views a user profile with privacy enforcement."""
    target_user = User.query.filter_by(username=username).first_or_404()
    current_user = get_current_user()

    is_owner = current_user and current_user.id == target_user.id
    is_admin = current_user and current_user.is_admin()

    # Privacy check: If profile is private and viewer is not owner/admin
    if not target_user.is_profile_public and not is_owner and not is_admin:
        return render_template('profile/private_profile.html', target_user=target_user, current_user=current_user)

    # Calculate target user stats
    stats = StreakService.calculate_streaks(target_user.id)

    # Badges
    earned_badges = Badge.query.join(UserBadge, UserBadge.badge_id == Badge.id)\
        .filter(UserBadge.user_id == target_user.id)\
        .order_by(UserBadge.earned_at.desc()).all()

    # Public posts or all posts if owner
    if is_owner or is_admin:
        posts = LockInPost.query.filter_by(user_id=target_user.id)\
            .order_by(LockInPost.post_date.desc()).all()
    else:
        posts = LockInPost.query.filter_by(user_id=target_user.id, privacy=PostPrivacy.COMMUNITY, is_moderated=False)\
            .order_by(LockInPost.post_date.desc()).all()

    return render_template(
        'profile/profile.html',
        target_user=target_user,
        current_user=current_user,
        stats=stats,
        earned_badges=earned_badges,
        posts=posts,
        is_owner=is_owner
    )


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edits bio, privacy preferences, and uploads a custom profile avatar."""
    current_user = get_current_user()

    if request.method == 'POST':
        bio = request.form.get('bio', '').strip()[:500]
        is_public = request.form.get('is_profile_public') == 'on'

        current_user.bio = bio
        current_user.is_profile_public = is_public

        # Handle avatar upload
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            saved_filename, err = UploadService.validate_and_save_image(avatar_file, current_user.id)
            if err:
                flash(f"Avatar upload failed: {err}", 'danger')
                return render_template('profile/edit_profile.html', current_user=current_user)
            # Delete old avatar if existing
            if current_user.avatar_filename:
                UploadService.delete_image(current_user.avatar_filename)
            current_user.avatar_filename = saved_filename

        db.session.commit()
        flash('Profile settings updated successfully.', 'success')
        return redirect(url_for('profile.view_profile', username=current_user.username))

    return render_template('profile/edit_profile.html', current_user=current_user)
