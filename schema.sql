-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TEXT
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    warranty_period_months INTEGER,
    inventory INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- Product variants (colors, sizes)
CREATE TABLE IF NOT EXISTS product_variants (
    variant_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color VARCHAR(50) NOT NULL,
    size VARCHAR(20) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    UNIQUE(product_id, color, size)
);

-- Product images
CREATE TABLE IF NOT EXISTS product_images (
    image_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    display_order INTEGER
);

-- Product prices with discount history
CREATE TABLE IF NOT EXISTS product_prices (
    price_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    current_price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    discount_type VARCHAR(20) DEFAULT 'none',
    discount_value DECIMAL(10, 2),
    discount_start_date TEXT,
    discount_end_date TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

-- Cart
CREATE TABLE IF NOT EXISTS cart (
    cart_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    created_at TEXT,
    updated_at TEXT
);

-- Cart items
CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id INTEGER PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    price_at_time DECIMAL(10, 2),
    added_at TEXT
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT,
    status VARCHAR(30) DEFAULT 'pending',
    total_price DECIMAL(12, 2),
    created_at TEXT,
    updated_at TEXT
);

-- Order items (linking multiple products to orders)
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    vendor_id INTEGER NOT NULL,
    variant_id INTEGER,
    quantity INTEGER NOT NULL,
    price_at_order DECIMAL(10, 2) NOT NULL,
    vendor_confirmation_status VARCHAR(20) DEFAULT 'pending',
    item_status VARCHAR(30) DEFAULT 'pending'
);

-- Reviews
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    order_item_id INTEGER,
    rating INTEGER NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    created_at TEXT
);

-- Complaints (returns, refunds, warranty claims)
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INTEGER PRIMARY KEY,
    order_item_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    complaint_type VARCHAR(30) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    customer_demand VARCHAR(30) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TEXT,
    updated_at TEXT
);

-- Complaint images
CREATE TABLE IF NOT EXISTS complaint_images (
    complaint_image_id INTEGER PRIMARY KEY,
    complaint_id INTEGER NOT NULL,
    image_url VARCHAR(500) NOT NULL
);

-- Chat messages
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    complaint_id INTEGER,
    message_text TEXT,
    message_type VARCHAR(20) DEFAULT 'text',
    image_url VARCHAR(500),
    created_at TEXT
);

-- Wishlist
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT,
    UNIQUE(customer_id, product_id)
);
