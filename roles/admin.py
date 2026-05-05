"""
admin.py — Functions for admin accounts.

Admins have unrestricted access to the platform:
  - View and manage all users (including banning / unbanning)
  - Edit or hard-delete any item regardless of owner
  - Audit / flag items for review
  - View the full order history and sales history across all vendors
  - Access the complete ban / unban log

DB compatibility
----------------
Pass a PEP 249-compliant cursor as `db` when the database branch is merged.
When db=None the module runs on in-memory mock data shared with other modules.

All functions return:
    {"success": True,  "data": <payload>}
    {"success": False, "error": <message>}
"""

from datetime import datetime

# Shared mock stores — mutations here are visible to other modules in local mode.
from .guest import _MOCK_ITEMS
from .user import _MOCK_USERS, _MOCK_USER_ORDERS
from .vendor import _MOCK_VENDOR_ITEMS, _MOCK_VENDOR_ORDERS

_MOCK_BAN_LOG = []

# ---------------------------------------------------------------------------
# Internal guard
# ---------------------------------------------------------------------------

def _require_admin(admin_id, db=None):
    """Return True only when admin_id belongs to an active, unbanned admin."""
    if db is None:
        user = next((u for u in _MOCK_USERS if u["id"] == admin_id), None)
        return (
            user is not None
            and user.get("role") == "admin"
            and not user.get("banned")
        )

    db.execute(
        "SELECT id FROM users WHERE id = %s AND role = 'admin' AND banned = 0",
        (admin_id,),
    )
    return db.fetchone() is not None


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def get_all_users(admin_id, db=None):
    """Return every registered user on the platform (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        safe = [{k: v for k, v in u.items() if k != "password_hash"} for u in _MOCK_USERS]
        return {"success": True, "data": safe}

    db.execute(
        "SELECT id, username, email, name, signup_date, role, banned"
        " FROM users ORDER BY signup_date DESC"
    )
    return {"success": True, "data": db.fetchall()}


def get_user_details(admin_id, target_user_id, db=None):
    """Return full profile details for any user (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        user = next((u for u in _MOCK_USERS if u["id"] == target_user_id), None)
        if user is None:
            return {"success": False, "error": "User not found"}
        safe = {k: v for k, v in user.items() if k != "password_hash"}
        return {"success": True, "data": safe}

    db.execute(
        "SELECT id, username, email, name, signup_date, role, banned"
        " FROM users WHERE id = %s",
        (target_user_id,),
    )
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": "User not found"}
    return {"success": True, "data": row}


def ban_user(admin_id, target_user_id, reason, db=None):
    """
    Ban a user account.  A non-empty reason is required (admin only).
    Admins cannot ban other admins.
    """
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}
    if not reason or not reason.strip():
        return {"success": False, "error": "A reason must be provided to ban a user"}

    if db is None:
        user = next((u for u in _MOCK_USERS if u["id"] == target_user_id), None)
        if user is None:
            return {"success": False, "error": "User not found"}
        if user.get("role") == "admin":
            return {"success": False, "error": "Cannot ban another admin"}
        user["banned"] = True
        _MOCK_BAN_LOG.append({
            "admin_id": admin_id, "user_id": target_user_id,
            "action": "ban", "reason": reason.strip(),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"success": True, "data": {"user_id": target_user_id, "banned": True}}

    db.execute("SELECT role FROM users WHERE id = %s", (target_user_id,))
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": "User not found"}
    if row["role"] == "admin":
        return {"success": False, "error": "Cannot ban another admin"}

    db.execute("UPDATE users SET banned = 1 WHERE id = %s", (target_user_id,))
    db.execute(
        "INSERT INTO ban_log (admin_id, user_id, action, reason, timestamp)"
        " VALUES (%s, %s, %s, %s, %s)",
        (admin_id, target_user_id, "ban", reason.strip(), datetime.utcnow().isoformat()),
    )
    return {"success": True, "data": {"user_id": target_user_id, "banned": True}}


def unban_user(admin_id, target_user_id, db=None):
    """Lift a ban from a user account (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        user = next((u for u in _MOCK_USERS if u["id"] == target_user_id), None)
        if user is None:
            return {"success": False, "error": "User not found"}
        user["banned"] = False
        _MOCK_BAN_LOG.append({
            "admin_id": admin_id, "user_id": target_user_id,
            "action": "unban", "reason": None,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"success": True, "data": {"user_id": target_user_id, "banned": False}}

    db.execute("UPDATE users SET banned = 0 WHERE id = %s", (target_user_id,))
    db.execute(
        "INSERT INTO ban_log (admin_id, user_id, action, reason, timestamp)"
        " VALUES (%s, %s, %s, %s, %s)",
        (admin_id, target_user_id, "unban", None, datetime.utcnow().isoformat()),
    )
    return {"success": True, "data": {"user_id": target_user_id, "banned": False}}


def get_ban_log(admin_id, db=None):
    """Return the full history of ban and unban actions (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        return {"success": True, "data": list(_MOCK_BAN_LOG)}

    db.execute("SELECT * FROM ban_log ORDER BY timestamp DESC")
    return {"success": True, "data": db.fetchall()}


# ---------------------------------------------------------------------------
# Item management (unrestricted)
# ---------------------------------------------------------------------------

def edit_item(admin_id, item_id, updates, db=None):
    """
    Edit any item on the platform regardless of owner (admin only).

    Allowed fields: name, price, quantity, category, description, active
    """
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    allowed = {"name", "price", "quantity", "category", "description", "active"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return {"success": False, "error": "No valid fields to update"}

    if db is None:
        all_items = _MOCK_ITEMS + _MOCK_VENDOR_ITEMS
        item = next((i for i in all_items if i["id"] == item_id), None)
        if item is None:
            return {"success": False, "error": "Item not found"}
        item.update(filtered)
        return {"success": True, "data": item}

    db.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if db.fetchone() is None:
        return {"success": False, "error": "Item not found"}

    set_clause = ", ".join(f"{k} = %s" for k in filtered)
    db.execute(
        f"UPDATE items SET {set_clause} WHERE id = %s",
        (*filtered.values(), item_id),
    )
    return {"success": True, "data": filtered}


def delete_item(admin_id, item_id, db=None):
    """
    Hard-delete any item from the platform (admin only).
    In local mode this is a soft-delete (active = False) to preserve references.
    """
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        all_items = _MOCK_ITEMS + _MOCK_VENDOR_ITEMS
        item = next((i for i in all_items if i["id"] == item_id), None)
        if item is None:
            return {"success": False, "error": "Item not found"}
        item["active"] = False
        return {"success": True, "data": {"item_id": item_id, "deleted": True}}

    db.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if db.fetchone() is None:
        return {"success": False, "error": "Item not found"}

    db.execute("DELETE FROM items WHERE id = %s", (item_id,))
    return {"success": True, "data": {"item_id": item_id, "deleted": True}}


def audit_item(admin_id, item_id, note, db=None):
    """Flag an item for review with a note (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}
    if not note or not note.strip():
        return {"success": False, "error": "An audit note is required"}

    if db is None:
        all_items = _MOCK_ITEMS + _MOCK_VENDOR_ITEMS
        item = next((i for i in all_items if i["id"] == item_id), None)
        if item is None:
            return {"success": False, "error": "Item not found"}
        item.setdefault("audit_notes", []).append({
            "admin_id":  admin_id,
            "note":      note.strip(),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"success": True, "data": {"item_id": item_id, "note": note.strip()}}

    db.execute(
        "INSERT INTO item_audit_log (item_id, admin_id, note, timestamp)"
        " VALUES (%s, %s, %s, %s)",
        (item_id, admin_id, note.strip(), datetime.utcnow().isoformat()),
    )
    return {"success": True, "data": {"item_id": item_id, "note": note.strip()}}


# ---------------------------------------------------------------------------
# Platform-wide order visibility
# ---------------------------------------------------------------------------

def get_all_orders(admin_id, db=None):
    """Return every order on the platform across all users and vendors (admin only)."""
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    if db is None:
        all_orders = _MOCK_USER_ORDERS + _MOCK_VENDOR_ORDERS
        return {"success": True, "data": all_orders}

    db.execute("SELECT * FROM orders ORDER BY order_date DESC")
    return {"success": True, "data": db.fetchall()}


def get_selling_history(admin_id, db=None):
    """
    Return the full delivered/completed selling history across all vendors (admin only).
    This is the "selling history window" visible on the admin dashboard.
    """
    if not _require_admin(admin_id, db=db):
        return {"success": False, "error": "Admin access required"}

    completed = {"delivered", "completed"}

    if db is None:
        history = [
            o for o in (_MOCK_USER_ORDERS + _MOCK_VENDOR_ORDERS)
            if o["status"] in completed
        ]
        return {"success": True, "data": history}

    db.execute(
        "SELECT o.*, u.username AS seller_username"
        " FROM orders o"
        " LEFT JOIN users u ON o.vendor_id = u.id"
        " WHERE o.status IN ('delivered', 'completed')"
        " ORDER BY o.order_date DESC"
    )
    return {"success": True, "data": db.fetchall()}
