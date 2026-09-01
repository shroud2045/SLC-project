from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.extensions import db
from app.models.chat import ChatMessage
from app.services.moderation_service import ModerationService
from app.utils.decorators import login_required, get_current_user, rate_limit

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def index():
    """Community live chat interface."""
    current_user = get_current_user()
    recent_messages = ChatMessage.query.order_by(ChatMessage.id.desc()).limit(50).all()
    recent_messages.reverse()
    return render_template('chat/chat.html', current_user=current_user, messages=recent_messages)


@chat_bp.route('/api/messages')
@login_required
def get_messages():
    """Polls recent messages after a given message ID."""
    after_id = request.args.get('after_id', 0, type=int)
    messages = ChatMessage.query.filter(ChatMessage.id > after_id)\
        .order_by(ChatMessage.id.asc()).limit(50).all()

    return jsonify({
        'success': True,
        'messages': [m.to_dict() for m in messages]
    })


@chat_bp.route('/api/send', methods=['POST'])
@login_required
@rate_limit(limit=10, window_seconds=10, key_prefix='chat_send')
def send_message():
    """Sends a chat message with server-side content filtering and anti-spam controls."""
    current_user = get_current_user()

    if current_user.is_muted:
        return jsonify({'success': False, 'error': 'Your account is muted from the chatroom.'}), 403

    data = request.get_json() or request.form
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({'success': False, 'error': 'Message cannot be empty.'}), 400

    if len(content) > 500:
        return jsonify({'success': False, 'error': 'Message exceeds 500 characters limit.'}), 400

    # Content moderation
    is_allowed, cleaned_content, reason = ModerationService.check_content(content)
    if not is_allowed:
        return jsonify({'success': False, 'error': f"Message rejected: {reason}"}), 400

    msg = ChatMessage(
        user_id=current_user.id,
        content=cleaned_content
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': msg.to_dict()
    })


@chat_bp.route('/api/delete/<int:msg_id>', methods=['POST'])
@login_required
def delete_message(msg_id: int):
    """Deletes a chat message (author or moderator only)."""
    current_user = get_current_user()
    msg = db.get_or_404(ChatMessage, msg_id)

    if msg.user_id != current_user.id and not current_user.is_moderator():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    msg.is_deleted = True
    db.session.commit()

    return jsonify({'success': True, 'message_id': msg.id})
