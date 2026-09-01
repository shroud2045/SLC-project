import time
from functools import wraps
from typing import List, Callable, Union
from collections import defaultdict
from flask import session, redirect, url_for, flash, request, abort, jsonify
from app.extensions import db
from app.models.user import User, Role


# In-memory sliding window rate limiter
_rate_limits = defaultdict(list)


def get_current_user() -> Union[User, None]:
    """Retrieves the currently authenticated user from session or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    db.session.expire_all()
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.clear()
        return None
    return user


def login_required(f: Callable) -> Callable:
    """Decorator requiring a valid authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles: str) -> Callable:
    """Decorator restricting route access to specified roles (e.g. ADMIN, MODERATOR)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            if user.role not in allowed_roles and user.role != Role.ADMIN:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden: Insufficient privileges'}), 403
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def rate_limit(limit: int = 5, window_seconds: int = 60, key_prefix: str = 'general') -> Callable:
    """
    Sliding window rate-limiter decorator per IP or user ID.
    Blocks requests exceeding `limit` within `window_seconds`.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Identify caller
            user_id = session.get('user_id')
            ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
            identifier = f"{key_prefix}:{user_id or ip}"

            now = time.time()
            cutoff = now - window_seconds

            # Clean old timestamps
            _rate_limits[identifier] = [t for t in _rate_limits[identifier] if t > cutoff]

            if len(_rate_limits[identifier]) >= limit:
                retry_after = int(window_seconds - (now - _rate_limits[identifier][0]))
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Too many requests. Slow down.',
                        'retry_after_seconds': max(1, retry_after)
                    }), 429
                abort(429)

            _rate_limits[identifier].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
