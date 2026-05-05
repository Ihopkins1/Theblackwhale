"""
user.py — Functions for registered (logged-in) users.

Extends guest capabilities with:
  - Profile management (view / update name and email)
  - Authenticated checkout
  - Order tracking: pending orders stay visible until delivered,
    then move to past orders

DB compatibility
----------------
Pass a PEP 249-compliant cursor as `db` when the database branch is merged.
When db=None the module runs on in-memory mock data.

All functions return:
    {"success": True,  "data": <payload>}
    {"success": False, "error": <message>}
"""

from datetime import datetime

# Re-export guest capabilities so callers only need to import from this module.
from .guest import (  # noqa: F401
    get_all_items,
    get_item,
    search_items,
    get_vendor_listings,
)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

# Roles: "user", "vendor", "admin"
_MOCK_USERS = [
    {
        "id": 1, "username": "john_doe", "email": "john@example.com",
        "name": "John Doe", "signup_date": "2025-01-15",
        "role": "user", "banned": False,
    },
    {
        "id": 2, "username": "vendor_store", "email": "vendor@example.com",
        "name": "Vendor Store", "signup_date": "2025-01-10",
        "role": "vendor", "banned": False,
    },
    {
        "id": 99, "username": "site_admin", "email": "admin@blackwhale.com",
        "name": "Site Admin", "signup_date": "2025-01-01",
        "role": "admin", "banned": False,
    },
]

# Order statuses: "pending" → "shipped" → "delivered" | "cancelled"
_MOCK_USER_ORDERS = [
    {
        "order_id": 1, "user_id": 1, "item_id": 101,
        "item_name": "Wireless Headphones", "quantity": 1,
        "unit_price": 79.99, "total_price": 79.99,
        "seller": "TechStore", "order_date": "2025-03-01", "status": "delivered",
    },
    {
        "order_id": 2, "user_id": 1, "item_id": 103,
        "item_name": "Laptop Stand", "quantity": 2,
        "unit_price": 34.99, "total_price": 69.98,
        "seller": "OfficeGear", "order_date": "2025-04-20", "status": "pending",
    },
]

_next_user_order_id = 100

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ACTIVE_ORDER_STATUSES = {"pending", "shipped"}
_COMPLETED_ORDER_STATUSES = {"delivered", "cancelled"}


def _find_mock_user(user_id):
    return next((u for u in _MOCK_USERS if u["id"] == user_id), None)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def get_user_profile(user_id, db=None):
    """Return public profile fields for a registered user."""
    if db is None:
        user = _find_mock_user(user_id)
        if user is None or user.get("banned"):
            return {"success": False, "error": "User not found"}
        safe = {k: v for k, v in user.items() if k != "password_hash"}
        return {"success": True, "data": safe}

    db.execute(
        "SELECT id, username, email, name, signup_date, role"
        " FROM users WHERE id = %s AND banned = 0",
        (user_id,),
    )
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": "User not found"}
    return {"success": True, "data": row}


def update_user_profile(user_id, updates, db=None):
    """
    Update allowed profile fields for the logged-in user.

    Allowed fields: name, email
    """
    allowed = {"name", "email"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return {"success": False, "error": "No valid fields to update"}

    if db is None:
        user = _find_mock_user(user_id)
        if user is None:
            return {"success": False, "error": "User not found"}
        user.update(filtered)
        return {"success": True, "data": {k: user[k] for k in filtered}}

    set_clause = ", ".join(f"{k} = %s" for k in filtered)
    db.execute(
        f"UPDATE users SET {set_clause} WHERE id = %s",
        (*filtered.values(), user_id),
    )
    return {"success": True, "data": filtered}


# ---------------------------------------------------------------------------
# Order tracking
# ---------------------------------------------------------------------------

def get_pending_orders(user_id, db=None):
    """
    Return orders that are in-flight (status: pending or shipped).
    These are shown to the user as "active" / trackable orders.
    """
    if db is None:
        orders = [
            o for o in _MOCK_USER_ORDERS
            if o["user_id"] == user_id and o["status"] in _ACTIVE_ORDER_STATUSES
        ]
        return {"success": True, "data": orders}

    db.execute(
        "SELECT * FROM orders"
        " WHERE user_id = %s AND status IN ('pending', 'shipped')"
        " ORDER BY order_date DESC",
        (user_id,),
    )
    return {"success": True, "data": db.fetchall()}


def get_past_orders(user_id, db=None):
    """Return completed or cancelled orders (status: delivered or cancelled)."""
    if db is None:
        orders = [
            o for o in _MOCK_USER_ORDERS
            if o["user_id"] == user_id and o["status"] in _COMPLETED_ORDER_STATUSES
        ]
        return {"success": True, "data": orders}

    db.execute(
        "SELECT * FROM orders"
        " WHERE user_id = %s AND status IN ('delivered', 'cancelled')"
        " ORDER BY order_date DESC",
        (user_id,),
    )
    return {"success": True, "data": db.fetchall()}


def get_order_status(user_id, order_id, db=None):
    """Return the current status of a specific order belonging to the user."""
    if db is None:
        order = next(
            (o for o in _MOCK_USER_ORDERS
             if o["order_id"] == order_id and o["user_id"] == user_id),
            None,
        )
        if order is None:
            return {"success": False, "error": "Order not found"}
        return {"success": True, "data": {"order_id": order_id, "status": order["status"]}}

    db.execute(
        "SELECT status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, user_id),
    )
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": "Order not found"}
    return {"success": True, "data": {"order_id": order_id, "status": row["status"]}}


# ---------------------------------------------------------------------------
# Authenticated checkout
# ---------------------------------------------------------------------------

def user_checkout(user_id, cart_items, db=None):
    """
    Place an order as a logged-in user.

    Parameters
    ----------
    user_id    : int
    cart_items : list — each item: {item_id, name, quantity, unit_price}
    """
    global _next_user_order_id

    if not cart_items:
        return {"success": False, "error": "Cart is empty"}

    profile = get_user_profile(user_id, db=db)
    if not profile["success"]:
        return {"success": False, "error": "Invalid or banned user account"}

    order_date = datetime.utcnow().isoformat()
    records = []

    for cart_item in cart_items:
        records.append({
            "order_id":    _next_user_order_id,
            "user_id":     user_id,
            "item_id":     cart_item["item_id"],
            "item_name":   cart_item["name"],
            "quantity":    int(cart_item["quantity"]),
            "unit_price":  float(cart_item["unit_price"]),
            "total_price": float(cart_item["unit_price"]) * int(cart_item["quantity"]),
            "buyer_type":  "user",
            "order_date":  order_date,
            "status":      "pending",
        })
        _next_user_order_id += 1

    if db is None:
        _MOCK_USER_ORDERS.extend(records)
        return {"success": True, "data": records}

    for r in records:
        db.execute(
            """
            INSERT INTO orders
                (user_id, item_id, item_name, quantity, unit_price,
                 total_price, buyer_type, order_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                r["user_id"], r["item_id"], r["item_name"],
                r["quantity"], r["unit_price"], r["total_price"],
                r["buyer_type"], r["order_date"], r["status"],
            ),
        )

    return {"success": True, "data": records}
