import os
from datetime import datetime, timezone
from flask import Flask
from app.config import config_by_name
from app.extensions import db, migrate, csrf
from app.utils.security import apply_security_headers
from app.utils.decorators import get_current_user
from app.services.streak_service import StreakService


def create_app(config_name: str = None) -> Flask:
    """Application factory for Shroud's Lockin Crib (SLC)."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Ensure uploads and instance directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, '..', 'uploads')), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register Blueprints
    from app.routes import (
        main_bp, auth_bp, dashboard_bp, posts_bp, timer_bp,
        badges_bp, challenges_bp, community_bp, chat_bp,
        profile_bp, ai_bp, admin_bp, uploads_bp, errors_bp
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(timer_bp)
    app.register_blueprint(badges_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(errors_bp)

    # Global security headers
    @app.after_request
    def security_headers_hook(response):
        return apply_security_headers(response)

    # Global template context processor
    @app.context_processor
    def inject_global_template_vars():
        current_user = get_current_user()
        user_streak = 0
        if current_user:
            stats = StreakService.calculate_streaks(current_user.id)
            user_streak = stats['current_streak']

        return {
            'current_user': current_user,
            'current_user_streak': user_streak,
            'current_year': datetime.now(timezone.utc).year,
            'app_name': app.config.get('APP_NAME', "Shroud's Lockin Crib"),
            'app_tagline': app.config.get('APP_TAGLINE', "Lock In. Build Your Streak.")
        }

    return app
