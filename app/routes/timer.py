from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, flash
from sqlalchemy import func
from app.extensions import db
from app.models.timer import TimerSession, TimerMode, TimerCategory
from app.services.badge_service import BadgeService
from app.services.streak_service import StreakService
from app.utils.decorators import login_required, get_current_user

timer_bp = Blueprint('timer', __name__, url_prefix='/timer')


@timer_bp.route('/')
@login_required
def index():
    """Interactive productivity timer interface."""
    current_user = get_current_user()
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    week_start = today - timedelta(days=today.weekday())

    # Daily total
    daily_mins = db.session.query(func.coalesce(func.sum(TimerSession.duration_minutes), 0.0))\
        .filter(TimerSession.user_id == current_user.id, func.date(TimerSession.start_time) == today).scalar() or 0.0

    # Weekly total
    weekly_mins = db.session.query(func.coalesce(func.sum(TimerSession.duration_minutes), 0.0))\
        .filter(TimerSession.user_id == current_user.id, func.date(TimerSession.start_time) >= week_start).scalar() or 0.0

    # Lifetime total
    lifetime_mins = db.session.query(func.coalesce(func.sum(TimerSession.duration_minutes), 0.0))\
        .filter(TimerSession.user_id == current_user.id).scalar() or 0.0

    # Recent timer sessions
    recent_sessions = TimerSession.query.filter_by(user_id=current_user.id)\
        .order_by(TimerSession.created_at.desc()).limit(10).all()

    return render_template(
        'timer/timer.html',
        current_user=current_user,
        daily_mins=daily_mins,
        weekly_mins=weekly_mins,
        lifetime_mins=lifetime_mins,
        recent_sessions=recent_sessions,
        modes=TimerMode.ALL,
        categories=TimerCategory.ALL
    )


@timer_bp.route('/save', methods=['POST'])
@login_required
def save_session():
    """
    Saves a completed timer session with strict server-side validation.
    Validates timestamps against client-reported durations to prevent manipulation.
    """
    current_user = get_current_user()
    data = request.get_json() or request.form

    start_str = data.get('start_time')
    end_str = data.get('end_time')
    duration_sec_raw = data.get('duration_seconds')
    mode = data.get('mode', TimerMode.POMODORO)
    category = data.get('category', TimerCategory.STUDY)
    notes = data.get('notes', '').strip()[:255]

    if not start_str or not end_str or duration_sec_raw is None:
        return jsonify({'success': False, 'error': 'Missing session parameters.'}), 400

    try:
        duration_seconds = int(duration_sec_raw)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid duration format.'}), 400

    if duration_seconds < 60:  # Minimum 1 minute to record
        return jsonify({'success': False, 'error': 'Session too short (minimum 1 minute required).'}), 400

    # Max single session 16 hours
    if duration_seconds > 16 * 3600:
        return jsonify({'success': False, 'error': 'Session exceeds max realistic duration.'}), 400

    # Parse timestamps
    try:
        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid ISO timestamp format.'}), 400

    # Validation: start must be before end
    if start_time >= end_time:
        return jsonify({'success': False, 'error': 'Start time must be before end time.'}), 400

    # Validation: calculated wall-clock difference should match duration_seconds within reasonable tolerance (e.g. paused time is <= wall-clock time)
    wall_clock_seconds = (end_time - start_time).total_seconds()
    if duration_seconds > (wall_clock_seconds + 30):  # cannot have elapsed more than wall clock time + 30s buffer
        return jsonify({'success': False, 'error': 'Duration exceeds elapsed wall-clock time.'}), 400

    # Validation: timestamps cannot be in the distant future
    now_utc = datetime.now(timezone.utc)
    if start_time > (now_utc + timedelta(minutes=5)) or end_time > (now_utc + timedelta(minutes=5)):
        return jsonify({'success': False, 'error': 'Timestamps cannot be in the future.'}), 400

    if category not in TimerCategory.ALL:
        category = TimerCategory.OTHER

    if mode not in TimerMode.ALL:
        mode = TimerMode.CUSTOM

    duration_minutes = round(duration_seconds / 60.0, 2)

    # Create session record
    session_record = TimerSession(
        user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        duration_minutes=duration_minutes,
        mode=mode,
        category=category,
        notes=notes
    )
    db.session.add(session_record)
    db.session.commit()

    # Trigger badge evaluation
    newly_earned = BadgeService.evaluate_user_badges(current_user.id)
    new_badge_names = [b.name for b in newly_earned]

    # Recalculate streak/hours
    stats = StreakService.calculate_streaks(current_user.id)

    return jsonify({
        'success': True,
        'message': f'Session logged: {session_record.formatted_duration} in {category}.',
        'duration_formatted': session_record.formatted_duration,
        'today_hours': stats['today_hours'],
        'total_hours': stats['total_hours'],
        'current_streak': stats['current_streak'],
        'new_badges': new_badge_names
    })
