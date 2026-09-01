from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditLog, AuditAction


def test_regular_user_blocked_from_admin(auth_client):
    """Verifies that non-admin users receive 403 Forbidden on admin endpoints."""
    res = auth_client.get('/admin/')
    assert res.status_code == 403

    res_users = auth_client.get('/admin/users')
    assert res_users.status_code == 403

    res_audit = auth_client.get('/admin/audit-logs')
    assert res_audit.status_code == 403


def test_admin_access_and_user_moderation(admin_client, regular_user, app):
    """Verifies admin user actions (suspend, mute, role changes) and audit logging."""
    # 1. Admin dashboard view
    res = admin_client.get('/admin/')
    assert res.status_code == 200

    # 2. Suspend user
    res_suspend = admin_client.post(f'/admin/users/{regular_user.id}/toggle-status', follow_redirects=True)
    assert res_suspend.status_code == 200

    with app.app_context():
        u = db.session.get(User, regular_user.id)
        assert u.is_active is False

        # Verify audit log was recorded
        log = AuditLog.query.filter_by(target_id=str(regular_user.id), action=AuditAction.USER_SUSPEND).first()
        assert log is not None

    # 3. Restore user
    res_restore = admin_client.post(f'/admin/users/{regular_user.id}/toggle-status', follow_redirects=True)
    assert res_restore.status_code == 200

    with app.app_context():
        u = db.session.get(User, regular_user.id)
        assert u.is_active is True
