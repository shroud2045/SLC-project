from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from app.extensions import db
from app.models.user import User, Role
from app.models.post import LockInPost
from app.models.community import Comment, Report, ReportStatus, ReportTargetType
from app.models.chat import ChatMessage
from app.models.moderation import BannedWord, ModerationSeverity
from app.models.badge import Badge, BadgeCategory, BadgeRequirement, BadgeRarity
from app.models.challenge import Challenge
from app.models.audit import AuditLog, AuditAction
from app.models.timer import TimerSession
from app.services.audit_service import AuditService
from app.services.upload_service import UploadService
from app.utils.decorators import role_required, get_current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@role_required(Role.ADMIN, Role.MODERATOR)
def index():
    """Admin dashboard overview with statistics and pending report counts."""
    current_user = get_current_user()

    total_users = User.query.count()
    total_posts = LockInPost.query.count()
    total_timer_sessions = TimerSession.query.count()
    pending_reports = Report.query.filter_by(status=ReportStatus.PENDING).count()

    recent_reports = Report.query.filter_by(status=ReportStatus.PENDING)\
        .order_by(Report.created_at.desc()).limit(5).all()

    recent_audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        current_user=current_user,
        total_users=total_users,
        total_posts=total_posts,
        total_timer_sessions=total_timer_sessions,
        pending_reports_count=pending_reports,
        recent_reports=recent_reports,
        recent_audit_logs=recent_audit_logs
    )


@admin_bp.route('/users')
@role_required(Role.ADMIN, Role.MODERATOR)
def users_list():
    """Manages users with search and moderation actions."""
    current_user = get_current_user()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    query = User.query
    if search:
        query = query.filter((User.username.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%')))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template(
        'admin/users.html',
        current_user=current_user,
        users=pagination.items,
        pagination=pagination,
        search=search,
        roles=Role.ALL
    )


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@role_required(Role.ADMIN)
def toggle_user_status(user_id: int):
    """Suspends or restores a user account."""
    current_user = get_current_user()
    target_user = db.get_or_404(User, user_id)

    if target_user.id == current_user.id:
        flash('You cannot suspend your own account.', 'danger')
        return redirect(url_for('admin.users_list'))

    target_user.is_active = not target_user.is_active
    db.session.commit()

    action = AuditAction.USER_RESTORE if target_user.is_active else AuditAction.USER_SUSPEND
    AuditService.log_action(
        admin_id=current_user.id,
        action=action,
        target_type='USER',
        target_id=str(target_user.id),
        details=f"User {target_user.username} {'restored' if target_user.is_active else 'suspended'}."
    )

    flash(f"User {target_user.username} has been {'restored' if target_user.is_active else 'suspended'}.", 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/toggle-mute', methods=['POST'])
@role_required(Role.ADMIN, Role.MODERATOR)
def toggle_user_mute(user_id: int):
    """Mutes or unmutes a user from community interactions."""
    current_user = get_current_user()
    target_user = db.get_or_404(User, user_id)

    target_user.is_muted = not target_user.is_muted
    db.session.commit()

    action = AuditAction.USER_MUTE if target_user.is_muted else AuditAction.USER_UNMUTE
    AuditService.log_action(
        admin_id=current_user.id,
        action=action,
        target_type='USER',
        target_id=str(target_user.id),
        details=f"User {target_user.username} {'muted' if target_user.is_muted else 'unmuted'}."
    )

    flash(f"User {target_user.username} has been {'muted' if target_user.is_muted else 'unmuted'}.", 'info')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@role_required(Role.ADMIN)
def change_user_role(user_id: int):
    """Changes a user's role (Admin only)."""
    current_user = get_current_user()
    target_user = db.get_or_404(User, user_id)
    new_role = request.form.get('role', '').strip()

    if target_user.id == current_user.id:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('admin.users_list'))

    if new_role in Role.ALL:
        old_role = target_user.role
        target_user.role = new_role
        db.session.commit()

        AuditService.log_action(
            admin_id=current_user.id,
            action=AuditAction.ROLE_CHANGE,
            target_type='USER',
            target_id=str(target_user.id),
            details=f"Changed role of {target_user.username} from {old_role} to {new_role}."
        )
        flash(f"Updated {target_user.username} role to {new_role}.", 'success')

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/reports')
@role_required(Role.ADMIN, Role.MODERATOR)
def reports_list():
    """Reviews user reports filed on content."""
    current_user = get_current_user()
    reports = Report.query.order_by(
        Report.status == ReportStatus.PENDING,
        Report.created_at.desc()
    ).all()

    return render_template('admin/reports.html', current_user=current_user, reports=reports)


@admin_bp.route('/reports/<int:report_id>/resolve', methods=['POST'])
@role_required(Role.ADMIN, Role.MODERATOR)
def resolve_report(report_id: int):
    """Resolves or dismisses a moderation report."""
    current_user = get_current_user()
    report = db.get_or_404(Report, report_id)
    action_type = request.form.get('action_type', 'RESOLVED')
    admin_notes = request.form.get('admin_notes', '').strip()

    report.status = ReportStatus.RESOLVED if action_type == 'RESOLVED' else ReportStatus.DISMISSED
    report.admin_notes = admin_notes
    report.resolved_at = datetime.now(timezone.utc)
    db.session.commit()

    AuditService.log_action(
        admin_id=current_user.id,
        action=AuditAction.REPORT_RESOLVE,
        target_type='REPORT',
        target_id=str(report.id),
        details=f"Report #{report.id} marked as {report.status}. Notes: {admin_notes}"
    )

    flash(f'Report #{report.id} marked as {report.status}.', 'success')
    return redirect(url_for('admin.reports_list'))


@admin_bp.route('/filters', methods=['GET', 'POST'])
@role_required(Role.ADMIN, Role.MODERATOR)
def filters_management():
    """Manages banned keywords and regex content moderation rules."""
    current_user = get_current_user()

    if request.method == 'POST':
        word = request.form.get('word_or_pattern', '').strip()
        severity = request.form.get('severity', ModerationSeverity.BLOCK)
        is_regex = request.form.get('is_regex') == 'on'

        if not word:
            flash('Word/Pattern cannot be empty.', 'danger')
        elif BannedWord.query.filter_by(word_or_pattern=word).first():
            flash('Filter rule already exists.', 'warning')
        else:
            bw = BannedWord(word_or_pattern=word, severity=severity, is_regex=is_regex)
            db.session.add(bw)
            db.session.commit()

            AuditService.log_action(
                admin_id=current_user.id,
                action=AuditAction.FILTER_ADD,
                target_type='FILTER',
                target_id=str(bw.id),
                details=f"Added filter: '{word}' ({severity})"
            )
            flash('Filter rule added.', 'success')

    banned_words = BannedWord.query.order_by(BannedWord.created_at.desc()).all()
    return render_template('admin/filters.html', current_user=current_user, banned_words=banned_words, severities=ModerationSeverity.ALL)


@admin_bp.route('/filters/<int:filter_id>/delete', methods=['POST'])
@role_required(Role.ADMIN, Role.MODERATOR)
def delete_filter(filter_id: int):
    """Deletes a content filter rule."""
    current_user = get_current_user()
    bw = db.get_or_404(BannedWord, filter_id)

    word_pattern = bw.word_or_pattern
    db.session.delete(bw)
    db.session.commit()

    AuditService.log_action(
        admin_id=current_user.id,
        action=AuditAction.FILTER_DELETE,
        target_type='FILTER',
        target_id=str(filter_id),
        details=f"Deleted filter: '{word_pattern}'"
    )

    flash('Filter rule removed.', 'info')
    return redirect(url_for('admin.filters_management'))


@admin_bp.route('/audit-logs')
@role_required(Role.ADMIN)
def audit_logs():
    """Inspects all administrative audit logs."""
    current_user = get_current_user()
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')

    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'admin/audit_logs.html',
        current_user=current_user,
        logs=pagination.items,
        pagination=pagination,
        actions=AuditAction.ALL,
        selected_action=action_filter
    )


@admin_bp.route('/badges', methods=['GET', 'POST'])
@role_required(Role.ADMIN)
def badges_management():
    """Creates and manages achievement badges."""
    current_user = get_current_user()

    if request.method == 'POST':
        slug = request.form.get('slug', '').strip().lower()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', '🔥').strip()
        category = request.form.get('category', BadgeCategory.STREAK)
        requirement_type = request.form.get('requirement_type', BadgeRequirement.STREAK_DAYS)
        threshold_val = float(request.form.get('threshold', '1'))
        rarity = request.form.get('rarity', BadgeRarity.COMMON)

        if not slug or not name or not description:
            flash('All fields are required.', 'danger')
        elif Badge.query.filter_by(slug=slug).first():
            flash('Badge with that slug already exists.', 'warning')
        else:
            badge = Badge(
                slug=slug,
                name=name,
                description=description,
                icon=icon,
                category=category,
                requirement_type=requirement_type,
                threshold=threshold_val,
                rarity=rarity
            )
            db.session.add(badge)
            db.session.commit()

            AuditService.log_action(
                admin_id=current_user.id,
                action=AuditAction.BADGE_CREATE,
                target_type='BADGE',
                target_id=str(badge.id),
                details=f"Created badge '{badge.name}' (req: {requirement_type} >= {threshold_val})"
            )
            flash(f"Badge '{name}' created successfully.", 'success')

    badges = Badge.query.order_by(Badge.threshold.asc()).all()
    return render_template(
        'admin/badges.html',
        current_user=current_user,
        badges=badges,
        categories=BadgeCategory.ALL,
        requirements=BadgeRequirement.ALL,
        rarities=BadgeRarity.ALL
    )


@admin_bp.route('/challenges', methods=['GET', 'POST'])
@role_required(Role.ADMIN)
def challenges_management():
    """Creates and toggles community challenges."""
    current_user = get_current_user()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        target_days = int(request.form.get('target_days', '0'))
        target_hours = float(request.form.get('target_hours', '0.0'))
        is_active = request.form.get('is_active') == 'on'

        if not title or not description:
            flash('Title and description required.', 'danger')
        else:
            ch = Challenge(
                title=title,
                description=description,
                target_days=target_days,
                target_hours=target_hours,
                is_active=is_active
            )
            db.session.add(ch)
            db.session.commit()

            AuditService.log_action(
                admin_id=current_user.id,
                action=AuditAction.CHALLENGE_CREATE,
                target_type='CHALLENGE',
                target_id=str(ch.id),
                details=f"Created challenge '{title}' (target: {target_days} days, {target_hours}h)"
            )
            flash('Challenge created.', 'success')

    challenges = Challenge.query.all()
    return render_template('admin/challenges.html', current_user=current_user, challenges=challenges)
