from typing import Optional
from flask import request
from app.extensions import db
from app.models.audit import AuditLog


class AuditService:
    """Service to record administrative and moderation audit logs."""

    @staticmethod
    def log_action(admin_id: Optional[int], action: str, target_type: Optional[str] = None,
                   target_id: Optional[str] = None, details: str = '') -> AuditLog:
        """Creates and commits an audit log entry."""
        ip_addr = None
        if request:
            # Check X-Forwarded-For if behind reverse proxy, otherwise remote_addr
            if request.headers.get('X-Forwarded-For'):
                ip_addr = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip_addr = request.remote_addr

        log_entry = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip_address=ip_addr
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
