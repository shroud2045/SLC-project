import os
from flask import Blueprint, send_from_directory, abort, current_app
from app.models.post import ProgressImage, PostPrivacy
from app.models.user import User
from app.utils.decorators import get_current_user

uploads_bp = Blueprint('uploads', __name__, url_prefix='/uploads')


@uploads_bp.route('/<string:filename>')
def serve_upload(filename: str):
    """
    Serves user uploaded images with access control checks.
    Ensures private post images cannot be accessed via direct link tampering.
    """
    # Strict filename sanitization against path traversal
    if '/' in filename or '\\' in filename or '..' in filename:
        abort(400)

    current_user = get_current_user()
    upload_dir = current_app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads'))

    # Check if this image belongs to a post
    prog_img = ProgressImage.query.filter_by(filename=filename).first()
    if prog_img:
        post = prog_img.post
        if post and not post.can_view(current_user):
            abort(403)

    # Check if this image is a user avatar
    avatar_user = User.query.filter_by(avatar_filename=filename).first()
    if avatar_user and not avatar_user.is_profile_public:
        if not current_user or (current_user.id != avatar_user.id and not current_user.is_admin()):
            abort(403)

    # Check if file exists on disk
    file_path = os.path.join(upload_dir, filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(upload_dir, filename, mimetype='image/webp')
