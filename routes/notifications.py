from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from user_model import Notification, db

notifications_bp = Blueprint("notifications", __name__, url_prefix="/dashboard/notifications")


def _serialize(item):
    return {
        "id": item.id, "title": item.title, "message": item.message,
        "category": item.category, "link": item.link, "is_read": item.is_read,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@notifications_bp.get("")
@login_required
def list_notifications():
    items = db.session.execute(
        db.select(Notification).where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc()).limit(20)
    ).scalars().all()
    unread = db.session.scalar(
        db.select(db.func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read.is_(False)
        )
    ) or 0
    return jsonify({"success": True, "unread": unread, "notifications": [_serialize(x) for x in items]})


@notifications_bp.patch("/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    item = db.session.get(Notification, notification_id)
    if not item or item.user_id != current_user.id:
        return jsonify({"success": False, "error": "Notification not found"}), 404
    item.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@notifications_bp.post("/read-all")
@login_required
def read_all():
    items = db.session.execute(
        db.select(Notification).where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    ).scalars().all()
    for item in items:
        item.is_read = True
    db.session.commit()
    return jsonify({"success": True})
