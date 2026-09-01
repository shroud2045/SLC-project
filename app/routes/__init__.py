from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.posts import posts_bp
from app.routes.timer import timer_bp
from app.routes.badges import badges_bp
from app.routes.challenges import challenges_bp
from app.routes.community import community_bp
from app.routes.chat import chat_bp
from app.routes.profile import profile_bp
from app.routes.ai import ai_bp
from app.routes.admin import admin_bp
from app.routes.uploads import uploads_bp
from app.routes.errors import errors_bp

__all__ = [
    'main_bp',
    'auth_bp',
    'dashboard_bp',
    'posts_bp',
    'timer_bp',
    'badges_bp',
    'challenges_bp',
    'community_bp',
    'chat_bp',
    'profile_bp',
    'ai_bp',
    'admin_bp',
    'uploads_bp',
    'errors_bp',
]
