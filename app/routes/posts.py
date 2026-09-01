from datetime import datetime, timezone, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.extensions import db
from app.models.post import LockInPost, ProgressImage, Tag, PostPrivacy
from app.services.upload_service import UploadService
from app.services.moderation_service import ModerationService
from app.services.badge_service import BadgeService
from app.utils.decorators import login_required, get_current_user

posts_bp = Blueprint('posts', __name__, url_prefix='/posts')


@posts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Creates a new daily lock-in journal post with optional images and privacy selector."""
    current_user = get_current_user()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        worked_on = request.form.get('worked_on', '').strip()
        completed = request.form.get('completed', '').strip()
        learned = request.form.get('learned', '').strip()
        hours_str = request.form.get('hours_worked', '0').strip()
        privacy = request.form.get('privacy', PostPrivacy.PRIVATE)
        post_date_str = request.form.get('post_date', '').strip()
        tags_raw = request.form.get('tags', '').strip()

        if not title or not description:
            flash('Title and description are required.', 'danger')
            return render_template('posts/create.html', PostPrivacy=PostPrivacy)

        # Parse hours
        try:
            hours_worked = max(0.0, min(float(hours_str), 24.0))
        except ValueError:
            hours_worked = 0.0

        # Parse post date (prevent future dates)
        try:
            post_date = datetime.strptime(post_date_str, '%Y-%m-%d').date() if post_date_str else date.today()
            if post_date > date.today():
                flash('Cannot create a lock-in post for a future date.', 'danger')
                return render_template('posts/create.html', PostPrivacy=PostPrivacy)
        except ValueError:
            post_date = date.today()

        # Validate privacy enum
        if privacy not in PostPrivacy.ALL:
            privacy = PostPrivacy.PRIVATE

        # Server-side moderation check
        full_text_to_check = f"{title} {description} {worked_on} {completed} {learned}"
        is_allowed, _, reason = ModerationService.check_content(full_text_to_check)
        if not is_allowed:
            flash(f"Submission rejected: {reason}", 'danger')
            return render_template('posts/create.html', PostPrivacy=PostPrivacy)

        # Create post record
        post = LockInPost(
            user_id=current_user.id,
            post_date=post_date,
            title=title,
            description=description,
            worked_on=worked_on,
            completed=completed,
            learned=learned,
            hours_worked=hours_worked,
            privacy=privacy
        )
        db.session.add(post)
        db.session.flush()  # assign post.id before adding images and tags

        # Handle tags
        if tags_raw:
            tag_names = [t.strip().lstrip('#').lower() for t in tags_raw.split(',') if t.strip()]
            for t_name in tag_names[:10]:  # limit to 10 tags
                tag = Tag.query.filter_by(name=t_name).first()
                if not tag:
                    tag = Tag(name=t_name)
                    db.session.add(tag)
                post.tags.append(tag)

        # Handle image uploads
        uploaded_files = request.files.getlist('images')
        saved_images_count = 0
        for file_obj in uploaded_files:
            if file_obj and file_obj.filename:
                if saved_images_count >= 5:
                    break  # max 5 images per post
                saved_filename, err = UploadService.validate_and_save_image(file_obj, current_user.id)
                if err:
                    flash(f"Image upload warning: {err}", 'warning')
                    continue
                file_obj.seek(0, 2)
                fsize = file_obj.tell()
                prog_img = ProgressImage(
                    post_id=post.id,
                    user_id=current_user.id,
                    filename=saved_filename,
                    original_filename=file_obj.filename[:100],
                    file_size=fsize,
                    mime_type='image/webp'
                )
                db.session.add(prog_img)
                saved_images_count += 1

        db.session.commit()

        # Trigger badge evaluation
        BadgeService.evaluate_user_badges(current_user.id)

        flash('Lock-In post recorded successfully! Keep grinding.', 'success')
        return redirect(url_for('posts.view_post', post_id=post.id))

    return render_template('posts/create.html', PostPrivacy=PostPrivacy, today=date.today().isoformat())


@posts_bp.route('/<int:post_id>')
def view_post(post_id: int):
    """Views a specific post with strict object-level authorization."""
    post = db.get_or_404(LockInPost, post_id)
    current_user = get_current_user()

    if not post.can_view(current_user):
        abort(403)

    return render_template('posts/view.html', post=post, current_user=current_user)


@posts_bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id: int):
    """Edits an existing post with strict ownership verification."""
    post = db.get_or_404(LockInPost, post_id)
    current_user = get_current_user()

    if not post.can_edit(current_user):
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        worked_on = request.form.get('worked_on', '').strip()
        completed = request.form.get('completed', '').strip()
        learned = request.form.get('learned', '').strip()
        hours_str = request.form.get('hours_worked', '0').strip()
        privacy = request.form.get('privacy', post.privacy)

        if not title or not description:
            flash('Title and description cannot be empty.', 'danger')
            return render_template('posts/edit.html', post=post, PostPrivacy=PostPrivacy)

        try:
            post.hours_worked = max(0.0, min(float(hours_str), 24.0))
        except ValueError:
            pass

        if privacy in PostPrivacy.ALL:
            post.privacy = privacy

        # Moderation check
        full_text_to_check = f"{title} {description} {worked_on} {completed} {learned}"
        is_allowed, _, reason = ModerationService.check_content(full_text_to_check)
        if not is_allowed:
            flash(f"Update rejected: {reason}", 'danger')
            return render_template('posts/edit.html', post=post, PostPrivacy=PostPrivacy)

        post.title = title
        post.description = description
        post.worked_on = worked_on
        post.completed = completed
        post.learned = learned
        post.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        flash('Lock-In post updated.', 'success')
        return redirect(url_for('posts.view_post', post_id=post.id))

    return render_template('posts/edit.html', post=post, PostPrivacy=PostPrivacy)


@posts_bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id: int):
    """Deletes a lock-in post with authorization checks and cleans up uploaded images."""
    post = db.get_or_404(LockInPost, post_id)
    current_user = get_current_user()

    if not post.can_delete(current_user):
        abort(403)

    # Delete physical image files
    for img in post.images:
        UploadService.delete_image(img.filename)

    db.session.delete(post)
    db.session.commit()

    flash('Post deleted successfully.', 'info')
    return redirect(url_for('posts.my_posts'))


@posts_bp.route('/my-posts')
@login_required
def my_posts():
    """Lists all personal lock-in posts for the current user."""
    current_user = get_current_user()
    posts = LockInPost.query.filter_by(user_id=current_user.id)\
        .order_by(LockInPost.post_date.desc(), LockInPost.created_at.desc()).all()
    return render_template('posts/my_posts.html', posts=posts, current_user=current_user)
