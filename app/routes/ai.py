from flask import Blueprint, render_template, request, jsonify
from app.services.ai_service import AIService
from app.services.streak_service import StreakService
from app.utils.decorators import login_required, get_current_user, rate_limit

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


@ai_bp.route('/')
@login_required
def index():
    """AI Productivity Assistant dashboard."""
    current_user = get_current_user()
    stats = StreakService.calculate_streaks(current_user.id)
    return render_template('ai/assistant.html', current_user=current_user, stats=stats)


@ai_bp.route('/suggest', methods=['POST'])
@login_required
@rate_limit(limit=15, window_seconds=60, key_prefix='ai_suggest')
def suggest_plan():
    """
    Generates structured productivity schedules and lock-in strategies.
    API keys remain strictly server-side.
    """
    current_user = get_current_user()
    data = request.get_json() or request.form
    query = (data.get('query') or '').strip()

    if not query:
        return jsonify({'success': False, 'error': 'Please provide a task or goal description.'}), 400

    if len(query) > 500:
        return jsonify({'success': False, 'error': 'Query exceeds 500 characters.'}), 400

    # Build safe user context
    stats = StreakService.calculate_streaks(current_user.id)
    user_context = {
        'username': current_user.username,
        'streak': stats['current_streak'],
        'total_hours': stats['total_hours'],
        'today_hours': stats['today_hours']
    }

    plan = AIService.generate_productivity_plan(query, user_context)

    return jsonify({
        'success': True,
        'plan': plan
    })
