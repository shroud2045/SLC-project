from flask import Blueprint, render_template, request, jsonify

errors_bp = Blueprint('errors', __name__)


@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Bad request'}), 400
    return render_template('errors/400.html'), 400


@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Access denied: Forbidden'}), 403
    return render_template('errors/403.html'), 403


@errors_bp.app_errorhandler(404)
def not_found_error(error):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(429)
def ratelimit_handler(error):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Too many requests. Please slow down.'}), 429
    return render_template('errors/429.html'), 429


@errors_bp.app_errorhandler(500)
def internal_server_error(error):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500
