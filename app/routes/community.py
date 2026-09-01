from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from app.extensions import db
from app.models.post import LockInPost, PostPrivacy, Tag
from app.models.community import Comment, PostReaction, Report, ReactionType, ReportTargetType, ReportStatus
from app.models.user import User
from app.services.moderation_service import ModerationService
from app.utils.decorators import login_required, get_current_user

community_bp = Blueprint('community', __name__, url_prefix='/community')


@community_bp.route('/')
def feed():
    """Community public feed displaying shared lock-in logs."""
    current_user = get_current_user()
    tag_filter = request.args.get('tag', '').strip().lower()
    page = request.args.get('page', 1, type=int)

    query = LockInPost.query.filter_by(privacy=PostPrivacy.COMMUNITY, is_moderated=False)

    if tag_filter:
        query = query.join(LockInPost.tags).filter(Tag.name == tag_filter)

    pagination = query.order_by(LockInPost.post_date.desc(), LockInPost.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    popular_tags = Tag.query.all()

    return render_template(
        'community/feed.html',
        current_user=current_user,
        posts=pagination.items,
        pagination=pagination,
        tag_filter=tag_filter,
        popular_tags=popular_tags,
        ReactionType=ReactionType
    )


@community_bp.route('/post/<int:post_id>')
def post_detail(post_id: int):
    """Detailed view of a community lock-in post with comments and reactions."""
    current_user = get_current_user()
    post = db.get_or_404(LockInPost, post_id)

    if not post.can_view(current_user):
        abort(403)

    comments = Comment.query.filter_by(post_id=post.id, is_deleted=False)\
        .order_by(Comment.created_at.asc()).all()

    # User's active reactions
    user_reactions = set()
    if current_user:
        user_reactions = {
            r.reaction_type for r in PostReaction.query.filter_by(post_id=post.id, user_id=current_user.id).all()
        }

    return render_template(
        'community/post_detail.html',
        current_user=current_user,
        post=post,
        comments=comments,
        user_reactions=user_reactions,
        ReactionType=ReactionType
    )


@community_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id: int):
    """Adds a comment to a community post with server-side moderation."""
    current_user = get_current_user()
    post = db.get_or_404(LockInPost, post_id)

    if not post.can_view(current_user):
        abort(403)

    if current_user.is_muted:
        flash('Your account has been muted from posting comments.', 'danger')
        return redirect(url_for('community.post_detail', post_id=post.id))

    content = request.form.get('content', '').strip()
    if not content:
        flash('Comment cannot be empty.', 'warning')
        return redirect(url_for('community.post_detail', post_id=post.id))

    # Content moderation check
    is_allowed, cleaned_content, reason = ModerationService.check_content(content)
    if not is_allowed:
        flash(f"Comment blocked: {reason}", 'danger')
        return redirect(url_for('community.post_detail', post_id=post.id))

    comment = Comment(
        post_id=post.id,
        user_id=current_user.id,
        content=cleaned_content
    )
    db.session.add(comment)
    db.session.commit()

    flash('Comment posted.', 'success')
    return redirect(url_for('community.post_detail', post_id=post.id))


@community_bp.route('/post/<int:post_id>/react', methods=['POST'])
@login_required
def toggle_reaction(post_id: int):
    """Toggles a user reaction on a community post (AJAX friendly)."""
    current_user = get_current_user()
    post = db.get_or_404(LockInPost, post_id)

    if not post.can_view(current_user):
        return jsonify({'error': 'Forbidden'}), 403

    reaction_type = request.form.get('reaction_type') or (request.get_json() or {}).get('reaction_type')
    if reaction_type not in ReactionType.ALL:
        return jsonify({'error': 'Invalid reaction type'}), 400

    existing = PostReaction.query.filter_by(
        post_id=post.id,
        user_id=current_user.id,
        reaction_type=reaction_type
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        toggled = False
    else:
        new_reaction = PostReaction(
            post_id=post.id,
            user_id=current_user.id,
            reaction_type=reaction_type
        )
        db.session.add(new_reaction)
        db.session.commit()
        toggled = True

    counts = post.reaction_counts()
    return jsonify({
        'success': True,
        'toggled': toggled,
        'reaction_type': reaction_type,
        'counts': counts
    })


@community_bp.route('/report', methods=['POST'])
@login_required
def file_report():
    """Submits a report on abusive or inappropriate content."""
    current_user = get_current_user()
    target_type = request.form.get('target_type', '').strip()
    target_id = request.form.get('target_id', type=int)
    reason = request.form.get('reason', '').strip()

    if target_type not in ReportTargetType.ALL or not target_id or not reason:
        flash('Invalid report parameters.', 'danger')
        return redirect(request.referrer or url_for('community.feed'))

    report = Report(
        reporter_id=current_user.id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        status=ReportStatus.PENDING
    )
    db.session.add(report)
    db.session.commit()

    flash('Report submitted. Our moderation team will review this promptly.', 'info')
    return redirect(request.referrer or url_for('community.feed'))
