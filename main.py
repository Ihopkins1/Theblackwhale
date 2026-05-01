from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce_db.db'
app.secret_key = 'your_secret_key_here'
db = SQLAlchemy(app)

# Users table
class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # 'admin', 'vendor', 'customer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Products table
class Product(db.Model):
    __tablename__ = 'products'
    
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    warranty_period_months = db.Column(db.Integer)
    inventory = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    vendor = db.relationship('User', backref='products')
    
    def __repr__(self):
        return f'<Product {self.title}>'

# Product variants (colors, sizes)
class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    
    variant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False, index=True)
    color = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(20), nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    
    product = db.relationship('Product', backref='variants')
    
    def __repr__(self):
        return f'<Variant {self.color}-{self.size}>'

# Product images
class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    image_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer)
    
    product = db.relationship('Product', backref='images')
    
    def __repr__(self):
        return f'<Image {self.image_id}>'

# Product prices with discount history
class ProductPrice(db.Model):
    __tablename__ = 'product_prices'
    
    price_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False, index=True)
    current_price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_type = db.Column(db.String(20), default='none')  # 'none', 'fixed', 'percentage'
    discount_value = db.Column(db.Numeric(10, 2))
    discount_start_date = db.Column(db.DateTime)
    discount_end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = db.relationship('Product', backref='prices')
    
    def __repr__(self):
        return f'<Price {self.current_price}>'

# Cart
class Cart(db.Model):
    __tablename__ = 'cart'
    
    cart_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = db.relationship('User', backref='cart')
    
    def __repr__(self):
        return f'<Cart {self.cart_id}>'

# Cart items
class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    cart_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.cart_id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.variant_id'))
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Numeric(10, 2))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    cart = db.relationship('Cart', backref='items')
    product = db.relationship('Product')
    variant = db.relationship('ProductVariant')
    
    def __repr__(self):
        return f'<CartItem {self.cart_item_id}>'

# Orders
class Order(db.Model):
    __tablename__ = 'orders'
    
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default='pending', index=True)  # 'pending', 'confirmed', 'handed_to_delivery', 'shipped'
    total_price = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = db.relationship('User', backref='orders')
    
    def __repr__(self):
        return f'<Order {self.order_id}>'

# Order items (linking multiple products to orders)
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    order_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.variant_id'))
    quantity = db.Column(db.Integer, nullable=False)
    price_at_order = db.Column(db.Numeric(10, 2), nullable=False)
    vendor_confirmation_status = db.Column(db.String(20), default='pending')  # 'pending', 'confirmed'
    item_status = db.Column(db.String(30), default='pending')  # 'pending', 'confirmed', 'handed_to_delivery', 'shipped'
    
    order = db.relationship('Order', backref='items')
    product = db.relationship('Product')
    vendor = db.relationship('User', foreign_keys=[vendor_id])
    variant = db.relationship('ProductVariant')
    
    def __repr__(self):
        return f'<OrderItem {self.order_item_id}>'

# Reviews
class Review(db.Model):
    __tablename__ = 'reviews'
    
    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.order_item_id'))
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    product = db.relationship('Product', backref='reviews')
    customer = db.relationship('User', backref='reviews')
    order_item = db.relationship('OrderItem')
    
    def __repr__(self):
        return f'<Review {self.review_id}>'

# Complaints (returns, refunds, warranty claims)
class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    complaint_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.order_item_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    complaint_type = db.Column(db.String(30), nullable=False)  # 'return', 'refund', 'warranty_claim'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    customer_demand = db.Column(db.String(30), nullable=False)  # 'return', 'refund', 'warranty_claim'
    status = db.Column(db.String(30), default='pending', index=True)  # 'pending', 'rejected', 'confirmed', 'processing', 'complete'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order_item = db.relationship('OrderItem', backref='complaints')
    customer = db.relationship('User', backref='complaints')
    
    def __repr__(self):
        return f'<Complaint {self.complaint_id}>'

# Complaint images
class ComplaintImage(db.Model):
    __tablename__ = 'complaint_images'
    
    complaint_image_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.complaint_id'), nullable=False, index=True)
    image_url = db.Column(db.String(500), nullable=False)
    
    complaint = db.relationship('Complaint', backref='images')
    
    def __repr__(self):
        return f'<ComplaintImage {self.complaint_image_id}>'

# Chat messages
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.complaint_id'))
    message_text = db.Column(db.Text)
    message_type = db.Column(db.String(20), default='text')  # 'text', 'image'
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    complaint = db.relationship('Complaint', backref='messages')
    
    def __repr__(self):
        return f'<ChatMessage {self.message_id}>'

# Wishlist
class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    
    wishlist_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('User', backref='wishlist')
    product = db.relationship('Product', backref='wishlist_items')
    
    def __repr__(self):
        return f'<Wishlist {self.wishlist_id}>'

# Routes
@app.route('/')
def index():
    return render_template('storepage.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/seller')
def seller():
    return render_template('seller.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
