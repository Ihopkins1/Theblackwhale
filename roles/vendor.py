"""
vendor.py — Functions for vendor accounts.

Extends user capabilities with:
  - Listing new items on the storefront
  - Editing and removing their own listings
  - Viewing incoming orders for their items
  - Declaring when an order has been shipped
  - Viewing their own sales history

DB compatibility
----------------
Pass a PEP 249-compliant cursor as `db` when the database branch is merged.
When db=None the module runs on in-memory mock data.

All functions return:
    {"success": True,  "data": <payload>}
    {"success": False, "error": <message>}
"""

from datetime import datetime

# Re-export all user + guest capabilities.
from .user import (  # noqa: F401
    get_all_items,
    get_item,
    search_items,
    get_vendor_listings,
    get_user_profile,
    update_user_profile,
    get_pending_orders,
    get_past_orders,
    get_order_status,
    user_checkout,
)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_VENDOR_ITEMS = [
    {
        "id": 201, "vendor_id": 2, "seller": "vendor_store",
        "name": "Smart Watch", "price": 149.99, "quantity": 6,
        "category": "Electronics",
        "description": "Feature-rich smartwatch with health tracking",
        "rating": 4.6, "active": True, "created_at": "2025-02-01",
    },
]

# Orders directed at this vendor's items
_MOCK_VENDOR_ORDERS = [
    {
        "order_id": 50, "vendor_id": 2, "item_id": 201,
        "item_name": "Smart Watch", "buyer_id": 1, "buyer_type": "user",
        "quantity": 1, "unit_price": 149.99, "total_price": 149.99,
        "order_date": "2025-04-28", "status": "pending",
    },
]

_next_vendor_item_id = 300

# ---------------------------------------------------------------------------
# Item management
# ---------------------------------------------------------------------------

def list_item(vendor_id, item_data, db=None):
    """
    Add a new item to the vendor's storefront.

    Required item_data keys: name, price, quantity, category, description
    """
    global _next_vendor_item_id

    required = {"name", "price", "quantity", "category", "description"}
    missing = required - item_data.keys()
    if missing:
        return {"success": False, "error": f"Missing required fields: {', '.join(sorted(missing))}"}
    if float(item_data["price"]) <= 0:
        return {"success": False, "error": "Price must be greater than 0"}
    if int(item_data["quantity"]) < 0:
        return {"success": False, "error": "Quantity cannot be negative"}

    profile = get_user_profile(vendor_id, db=db)
    seller_name = profile["data"]["username"] if profile["success"] else str(vendor_id)

    new_item = {
        "id":          _next_vendor_item_id,
        "vendor_id":   vendor_id,
        "seller":      seller_name,
        "name":        item_data["name"],
        "price":       float(item_data["price"]),
        "quantity":    int(item_data["quantity"]),
        "category":    item_data["category"],
        "description": item_data.get("description", ""),
        "rating":      0.0,
        "active":      True,
        "created_at":  datetime.utcnow().isoformat(),
    }

    if db is None:
        _MOCK_VENDOR_ITEMS.append(new_item)
        _next_vendor_item_id += 1
        return {"success": True, "data": new_item}

    db.execute(
        """
        INSERT INTO items
            (vendor_id, seller_username, name, price, quantity,
             category, description, rating, active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            vendor_id, seller_name, new_item["name"], new_item["price"],
            new_item["quantity"], new_item["category"], new_item["description"],
            0.0, True, new_item["created_at"],
        ),
    )
    new_item["id"] = db.lastrowid
    return {"success": True, "data": new_item}


def update_item(vendor_id, item_id, updates, db=None):
    """
    Edit a listing the vendor owns.

    Allowed fields: name, price, quantity, category, description
    """
    allowed = {"name", "price", "quantity", "category", "description"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return {"success": False, "error": "No valid fields to update"}

    if db is None:
        item = next(
            (i for i in _MOCK_VENDOR_ITEMS
             if i["id"] == item_id and i["vendor_id"] == vendor_id),
            None,
        )
        if item is None:
            return {"success": False, "error": "Item not found or access denied"}
        item.update(filtered)
        return {"success": True, "data": item}

    db.execute(
        "SELECT id FROM items WHERE id = %s AND vendor_id = %s",
        (item_id, vendor_id),
    )
    if db.fetchone() is None:
        return {"success": False, "error": "Item not found or access denied"}

    set_clause = ", ".join(f"{k} = %s" for k in filtered)
    db.execute(
        f"UPDATE items SET {set_clause} WHERE id = %s AND vendor_id = %s",
        (*filtered.values(), item_id, vendor_id),
    )
    return {"success": True, "data": filtered}


def remove_item(vendor_id, item_id, db=None):
    """Soft-delete (deactivate) a listing the vendor owns."""
    if db is None:
        item = next(
            (i for i in _MOCK_VENDOR_ITEMS
             if i["id"] == item_id and i["vendor_id"] == vendor_id),
            None,
        )
        if item is None:
            return {"success": False, "error": "Item not found or access denied"}
        item["active"] = False
        return {"success": True, "data": {"item_id": item_id, "active": False}}

    db.execute(
        "SELECT id FROM items WHERE id = %s AND vendor_id = %s",
        (item_id, vendor_id),
    )
    if db.fetchone() is None:
        return {"success": False, "error": "Item not found or access denied"}

    db.execute(
        "UPDATE items SET active = 0 WHERE id = %s AND vendor_id = %s",
        (item_id, vendor_id),
    )
    return {"success": True, "data": {"item_id": item_id, "active": False}}


def get_vendor_items(vendor_id, include_inactive=False, db=None):
    """Return all items listed by this vendor (active only by default)."""
    if db is None:
        items = [i for i in _MOCK_VENDOR_ITEMS if i["vendor_id"] == vendor_id]
        if not include_inactive:
            items = [i for i in items if i.get("active")]
        return {"success": True, "data": items}

    sql = "SELECT * FROM items WHERE vendor_id = %s"
    params = [vendor_id]
    if not include_inactive:
        sql += " AND active = 1"
    sql += " ORDER BY created_at DESC"
    db.execute(sql, params)
    return {"success": True, "data": db.fetchall()}


# ---------------------------------------------------------------------------
# Shipment management
# ---------------------------------------------------------------------------

def mark_shipped(vendor_id, order_id, db=None):
    """
    Declare that an order has been shipped.

    Only valid for orders on the vendor's items that are currently 'pending'.
    Transitions status: pending → shipped.
    """
    if db is None:
        order = next(
            (o for o in _MOCK_VENDOR_ORDERS
             if o["order_id"] == order_id and o["vendor_id"] == vendor_id),
            None,
        )
        if order is None:
            return {"success": False, "error": "Order not found or access denied"}
        if order["status"] != "pending":
            return {
                "success": False,
                "error": f"Cannot ship an order with status '{order['status']}'",
            }
        order["status"] = "shipped"
        return {"success": True, "data": {"order_id": order_id, "status": "shipped"}}

    db.execute(
        "SELECT id, status FROM orders WHERE id = %s AND vendor_id = %s",
        (order_id, vendor_id),
    )
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": "Order not found or access denied"}
    if row["status"] != "pending":
        return {
            "success": False,
            "error": f"Cannot ship an order with status '{row['status']}'",
        }

    db.execute("UPDATE orders SET status = 'shipped' WHERE id = %s", (order_id,))
    return {"success": True, "data": {"order_id": order_id, "status": "shipped"}}


# ---------------------------------------------------------------------------
# Order visibility
# ---------------------------------------------------------------------------

def get_vendor_orders(vendor_id, status=None, db=None):
    """
    Return orders for items this vendor has listed.

    Parameters
    ----------
    status : str | None — filter to a specific status if provided
    """
    if db is None:
        orders = [o for o in _MOCK_VENDOR_ORDERS if o["vendor_id"] == vendor_id]
        if status:
            orders = [o for o in orders if o["status"] == status]
        return {"success": True, "data": orders}

    sql = "SELECT * FROM orders WHERE vendor_id = %s"
    params = [vendor_id]
    if status:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY order_date DESC"
    db.execute(sql, params)
    return {"success": True, "data": db.fetchall()}


def get_vendor_sales_history(vendor_id, db=None):
    """Return only delivered (completed) sales for this vendor."""
    return get_vendor_orders(vendor_id, status="delivered", db=db)
