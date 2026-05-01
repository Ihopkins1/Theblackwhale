"""
guest.py — Functions available to all visitors (authenticated or not).

Guests can browse the store, search items, view vendor storefronts,
and place orders via guest checkout (email/phone + card).

DB compatibility
----------------
Pass a PEP 249-compliant cursor as `db` when the database branch is merged.
When db=None the module runs entirely on in-memory mock data that mirrors
the local items defined in inventory.js.

All functions return:
    {"success": True,  "data": <payload>}
    {"success": False, "error": <message>}
"""

from datetime import datetime

# ---------------------------------------------------------------------------
# Mock data — mirrors inventory.js localInventoryItems
# ---------------------------------------------------------------------------
_MOCK_ITEMS = [
    {
        "id": 101, "name": "Wireless Headphones", "price": 79.99, "quantity": 5,
        "category": "Electronics",
        "description": "High-quality wireless headphones with noise cancellation",
        "seller": "TechStore", "rating": 4.5, "active": True,
    },
    {
        "id": 102, "name": "USB-C Cable", "price": 12.99, "quantity": 20,
        "category": "Electronics", "description": "Durable 6ft USB-C charging cable",
        "seller": "CableWorld", "rating": 4.8, "active": True,
    },
    {
        "id": 103, "name": "Laptop Stand", "price": 34.99, "quantity": 8,
        "category": "Office", "description": "Adjustable aluminum laptop stand",
        "seller": "OfficeGear", "rating": 4.3, "active": True,
    },
    {
        "id": 104, "name": "Mechanical Keyboard", "price": 89.99, "quantity": 3,
        "category": "Electronics",
        "description": "RGB mechanical keyboard with mechanical switches",
        "seller": "PeripheralPro", "rating": 4.7, "active": True,
    },
    {
        "id": 105, "name": "Phone Stand", "price": 15.99, "quantity": 12,
        "category": "Accessories", "description": "Adjustable phone stand for desk",
        "seller": "AccessoryHub", "rating": 4.2, "active": True,
    },
]

_MOCK_GUEST_ORDERS = []
_next_guest_order_id = 1000


# ---------------------------------------------------------------------------
# Browse / search
# ---------------------------------------------------------------------------

def get_all_items(db=None):
    """Return all active items on the storefront."""
    if db is None:
        return {"success": True, "data": [i for i in _MOCK_ITEMS if i.get("active")]}

    db.execute("SELECT * FROM items WHERE active = 1 ORDER BY name")
    return {"success": True, "data": db.fetchall()}


def get_item(item_id, db=None):
    """Return a single active item by ID."""
    if db is None:
        item = next(
            (i for i in _MOCK_ITEMS if i["id"] == item_id and i.get("active")), None
        )
        if item is None:
            return {"success": False, "error": f"Item {item_id} not found"}
        return {"success": True, "data": item}

    db.execute("SELECT * FROM items WHERE id = %s AND active = 1", (item_id,))
    row = db.fetchone()
    if row is None:
        return {"success": False, "error": f"Item {item_id} not found"}
    return {"success": True, "data": row}


def search_items(query="", category=None, max_price=None, min_rating=None, db=None):
    """
    Search active items by name or description with optional filters.

    Parameters
    ----------
    query       : str  — text to match against name / description
    category    : str  — filter to a single category ("all" or None = no filter)
    max_price   : float — upper price bound (inclusive)
    min_rating  : float — lower rating bound (inclusive)
    """
    if db is None:
        results = [i for i in _MOCK_ITEMS if i.get("active")]
        if query:
            q = query.lower()
            results = [
                i for i in results
                if q in i["name"].lower() or q in i.get("description", "").lower()
            ]
        if category and category.lower() != "all":
            results = [i for i in results if i["category"].lower() == category.lower()]
        if max_price is not None:
            results = [i for i in results if i["price"] <= max_price]
        if min_rating is not None:
            results = [i for i in results if i.get("rating", 0) >= min_rating]
        return {"success": True, "data": results}

    sql = (
        "SELECT * FROM items WHERE active = 1"
        " AND (name LIKE %s OR description LIKE %s)"
    )
    params = [f"%{query}%", f"%{query}%"]

    if category and category.lower() != "all":
        sql += " AND category = %s"
        params.append(category)
    if max_price is not None:
        sql += " AND price <= %s"
        params.append(max_price)
    if min_rating is not None:
        sql += " AND rating >= %s"
        params.append(min_rating)

    db.execute(sql, params)
    return {"success": True, "data": db.fetchall()}


def get_vendor_listings(vendor_username, db=None):
    """Return all active items listed by a vendor, found by their username."""
    if db is None:
        items = [
            i for i in _MOCK_ITEMS
            if i["seller"] == vendor_username and i.get("active")
        ]
        return {"success": True, "data": items}

    db.execute(
        "SELECT * FROM items WHERE seller_username = %s AND active = 1 ORDER BY name",
        (vendor_username,),
    )
    return {"success": True, "data": db.fetchall()}


# ---------------------------------------------------------------------------
# Guest checkout
# ---------------------------------------------------------------------------

def guest_checkout(contact_info, cart_items, db=None):
    """
    Place an order without a user account.

    Parameters
    ----------
    contact_info : dict  — keys: email (str|None), phone (str|None), card_last4 (str)
    cart_items   : list  — each item: {item_id, name, quantity, unit_price}
    """
    global _next_guest_order_id

    if not cart_items:
        return {"success": False, "error": "Cart is empty"}

    email = (contact_info.get("email") or "").strip() or None
    phone = (contact_info.get("phone") or "").strip() or None
    card_last4 = (contact_info.get("card_last4") or "").strip()

    if not (email or phone):
        return {"success": False, "error": "An email or phone number is required"}
    if not card_last4:
        return {"success": False, "error": "Payment information is required"}

    order_date = datetime.utcnow().isoformat()
    records = []

    for cart_item in cart_items:
        records.append({
            "order_id":   _next_guest_order_id,
            "item_id":    cart_item["item_id"],
            "item_name":  cart_item["name"],
            "quantity":   int(cart_item["quantity"]),
            "unit_price": float(cart_item["unit_price"]),
            "total_price": float(cart_item["unit_price"]) * int(cart_item["quantity"]),
            "buyer_type": "guest",
            "buyer_email": email,
            "buyer_phone": phone,
            "card_last4":  card_last4,
            "order_date":  order_date,
            "status":      "pending",
        })
        _next_guest_order_id += 1

    if db is None:
        _MOCK_GUEST_ORDERS.extend(records)
        return {"success": True, "data": records}

    for r in records:
        db.execute(
            """
            INSERT INTO orders
                (item_id, item_name, quantity, unit_price, total_price,
                 buyer_type, buyer_email, buyer_phone, card_last4, order_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                r["item_id"], r["item_name"], r["quantity"],
                r["unit_price"], r["total_price"], r["buyer_type"],
                r["buyer_email"], r["buyer_phone"], r["card_last4"],
                r["order_date"], r["status"],
            ),
        )

    return {"success": True, "data": records}
