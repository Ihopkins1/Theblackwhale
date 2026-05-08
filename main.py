from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import uuid

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce_db.db'
app.secret_key = 'your_secret_key_here'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB max upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ADMIN_SIGNUP_KEY = 'blackwhale'
ROLE_MAP = {
    'user': 'customer',
    'seller': 'vendor',
    'admin': 'admin'
}

# Users table
class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20))
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


class ProductNutrition(db.Model):
    __tablename__ = 'product_nutrition'

    nutrition_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False, unique=True, index=True)
    nutritional_value = db.Column(db.Text, nullable=False)

    product = db.relationship('Product', backref=db.backref('nutrition', uselist=False))

    def __repr__(self):
        return f'<ProductNutrition {self.product_id}>'

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
def require_role(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            is_api = request.path.startswith('/api/')
            if 'user_id' not in session:
                if is_api:
                    return jsonify({'success': False, 'message': 'Please sign in to continue', 'redirect': '/sign-in'}), 401
                return redirect(url_for('sign_in'))

            current_role = session.get('role')
            if current_role not in allowed_roles:
                if is_api:
                    return jsonify({'success': False, 'message': 'Access denied'}), 403
                return redirect(url_for('index'))

            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def product_price_value(product):
    active_price = ProductPrice.query.filter_by(product_id=product.product_id, is_active=True)\
        .order_by(ProductPrice.updated_at.desc())\
        .first()
    if active_price:
        return float(active_price.current_price)

    latest_price = ProductPrice.query.filter_by(product_id=product.product_id)\
        .order_by(ProductPrice.updated_at.desc())\
        .first()
    if latest_price:
        return float(latest_price.current_price)

    return 0.0


def serialize_product(product):
    primary_image = ProductImage.query.filter_by(product_id=product.product_id)\
        .order_by(ProductImage.display_order.asc(), ProductImage.image_id.asc())\
        .first()

    return {
        'product_id': product.product_id,
        'title': product.title,
        'description': product.description,
        'price': product_price_value(product),
        'inventory': product.inventory,
        'image_url': primary_image.image_url if primary_image else 'https://images.unsplash.com/photo-1535591273668-578e31182c4f?auto=format&fit=crop&w=1200&q=80',
        'seller_name': product.vendor.name if product.vendor else 'Unknown Seller',
        'estimated_delivery': '3-7 days',
        'nutritional_value': product.nutrition.nutritional_value if product.nutrition else 'Nutritional information unavailable'
    }


def seed_sample_products():
    vendor_user = User.query.filter_by(email='demo.vendor@blackwhale.com').first()
    if not vendor_user:
        vendor_user = User(
            name='Black Whale Vendor',
            email='demo.vendor@blackwhale.com',
            username='demo_vendor',
            password=generate_password_hash('blackwhale-demo'),
            role='vendor'
        )
        db.session.add(vendor_user)
        db.session.flush()

    sample_products = [
        {
            'title': 'Atlantic Salmon Fillet',
            'description': 'Fresh-cut salmon fillet with rich flavor and smooth texture. Great for grilling, baking, or meal prep.',
            'inventory': 25,
            'price': 18.99,
            'nutritional_value': 'Per 100g: Protein 20g, Fat 13g, Omega-3 2.3g, Calories 208',
            'image_url': 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=1200&q=80'
        },
        {
            'title': 'Yellowfin Tuna Steak',
            'description': 'Lean premium tuna steak with a firm bite. Perfect for searing or serving rare.',
            'inventory': 18,
            'price': 21.5,
            'nutritional_value': 'Per 100g: Protein 24g, Fat 5g, Omega-3 0.6g, Calories 144',
            'image_url': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=1200&q=80'
        },
        {
            'title': 'Whole Red Snapper',
            'description': 'Whole cleaned red snapper, ideal for roasting or steaming with herbs and citrus.',
            'inventory': 12,
            'price': 26.0,
            'nutritional_value': 'Per 100g: Protein 20g, Fat 1.3g, Potassium 444mg, Calories 100',
            'image_url': 'https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=1200&q=80'
        },
        {
            'title': 'Arctic Char Portions',
            'description': 'Delicate char portions with buttery texture and mild taste, perfect for pan searing.',
            'inventory': 16,
            'price': 19.75,
            'nutritional_value': 'Per 100g: Protein 19g, Fat 11g, Vitamin D 12mcg, Calories 190',
            'image_url': 'https://images.unsplash.com/photo-1559737558-2f5a35f4523b?auto=format&fit=crop&w=1200&q=80'
        },
        {
            'title': 'Mahi Mahi Cutlets',
            'description': 'Firm, lean mahi mahi cutlets for tacos, grilling, and fast weeknight dinners.',
            'inventory': 20,
            'price': 17.4,
            'nutritional_value': 'Per 100g: Protein 20g, Fat 1g, Selenium 37mcg, Calories 85',
            'image_url': 'https://images.unsplash.com/photo-1543332164-6e82f355bad5?auto=format&fit=crop&w=1200&q=80'
        }
    ]

    for item in sample_products:
        product = Product.query.filter_by(title=item['title']).first()
        if not product:
            product = Product(
                vendor_id=vendor_user.user_id,
                title=item['title'],
                description=item['description'],
                warranty_period_months=0,
                inventory=item['inventory']
            )
            db.session.add(product)
            db.session.flush()
        else:
            product.description = item['description']
            product.inventory = item['inventory']

        active_price = ProductPrice.query.filter_by(product_id=product.product_id, is_active=True).first()
        if not active_price:
            db.session.add(ProductPrice(
                product_id=product.product_id,
                current_price=item['price'],
                original_price=item['price'],
                discount_type='none',
                is_active=True
            ))

        nutrition = ProductNutrition.query.filter_by(product_id=product.product_id).first()
        if not nutrition:
            db.session.add(ProductNutrition(
                product_id=product.product_id,
                nutritional_value=item['nutritional_value']
            ))

        image = ProductImage.query.filter_by(product_id=product.product_id).first()
        if not image:
            db.session.add(ProductImage(
                product_id=product.product_id,
                image_url=item['image_url'],
                display_order=1
            ))

    db.session.commit()


@app.route('/')
def index():
    return render_template('storepage.html')


@app.route('/api/store-products')
def store_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify({'success': True, 'products': [serialize_product(product) for product in products]}), 200


@app.route('/product/<int:product_id>')
def product_page(product_id):
    product = Product.query.filter_by(product_id=product_id).first_or_404()
    return render_template('product.html', product=serialize_product(product))


@app.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    review_rows = []
    for review in reviews:
        display_name = review.customer.name if review.customer and review.customer.name else (review.customer.username if review.customer else 'Anonymous')
        review_rows.append({
            'review_id': review.review_id,
            'rating': review.rating,
            'description': review.description or '',
            'username': review.customer.username if review.customer else None,
            'name': display_name,
            'created_at': review.created_at.isoformat() if review.created_at else None
        })

    average_rating = round(sum(review.rating for review in reviews) / len(reviews), 1) if reviews else 0
    return jsonify({
        'success': True,
        'reviews': review_rows,
        'count': len(reviews),
        'average_rating': average_rating
    }), 200


@app.route('/api/products/<int:product_id>/reviews', methods=['POST'])
@require_role('customer', 'vendor', 'admin')
def post_product_review(product_id):
    data = request.get_json() or {}
    rating = data.get('rating')
    description = str(data.get('description', '')).strip()

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    user_id = session.get('user_id')
    existing_review = Review.query.filter_by(product_id=product_id, customer_id=user_id).first()

    if existing_review:
        existing_review.rating = rating
        existing_review.description = description
        existing_review.created_at = datetime.utcnow()
    else:
        db.session.add(Review(
            product_id=product_id,
            customer_id=user_id,
            rating=rating,
            description=description
        ))

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Review saved'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to save review: {str(e)}'}), 500

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/checkout')
@require_role('customer', 'vendor', 'admin')
def checkout():
    return render_template('checkout.html')

@app.route('/account')
@require_role('customer', 'vendor', 'admin')
def account():
    return render_template('account.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/sign-in')
def sign_in():
    return render_template('sign-in.html')

@app.route('/admin')
@require_role('admin')
def admin():
    return render_template('admin.html')

@app.route('/seller')
@require_role('vendor')
def seller():
    return render_template('seller.html')

@app.route('/inventory')
@require_role('admin')
def inventory():
    return render_template('inventory.html')

@app.route('/itemeditor')
@require_role('vendor')
def itemeditor():
    return render_template('itemeditor.html')


@app.route('/api/products', methods=['POST'])
@require_role('vendor')
def create_product():
    # Support both multipart/form-data (with file upload) and JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form
        title = str(data.get('title', '')).strip()
        description = str(data.get('description', '')).strip()
        nutritional_value = str(data.get('nutritional_value', '')).strip()
        price = data.get('price')
        stock = data.get('stock', 0)
        image_file = request.files.get('image')
    else:
        raw = request.get_json() or {}
        title = str(raw.get('title', '')).strip()
        description = str(raw.get('description', '')).strip()
        nutritional_value = str(raw.get('nutritional_value', '')).strip()
        price = raw.get('price')
        stock = raw.get('stock', 0)
        image_file = None

    if not title or not description:
        return jsonify({'success': False, 'message': 'Title and description are required'}), 400

    try:
        numeric_price = float(price)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'A valid price is required'}), 400

    try:
        stock_value = int(stock)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'A valid stock value is required'}), 400

    if numeric_price < 0 or stock_value < 0:
        return jsonify({'success': False, 'message': 'Price and stock cannot be negative'}), 400

    product = Product(
        vendor_id=session['user_id'],
        title=title,
        description=description,
        warranty_period_months=0,
        inventory=stock_value
    )

    try:
        db.session.add(product)
        db.session.flush()

        db.session.add(ProductPrice(
            product_id=product.product_id,
            current_price=numeric_price,
            original_price=numeric_price,
            discount_type='none',
            is_active=True
        ))

        db.session.add(ProductNutrition(
            product_id=product.product_id,
            nutritional_value=nutritional_value or 'Per serving: Protein-rich seafood source'
        ))

        # Save uploaded image if provided
        if image_file and image_file.filename and allowed_file(image_file.filename):
            ext = image_file.filename.rsplit('.', 1)[1].lower()
            safe_name = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, safe_name)
            image_file.save(save_path)
            image_url = f'/static/uploads/{safe_name}'
            db.session.add(ProductImage(
                product_id=product.product_id,
                image_url=image_url,
                display_order=1
            ))

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Product created',
            'redirect': url_for('product_page', product_id=product.product_id)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to create product: {str(e)}'}), 500


@app.route('/session-info')
def session_info():
    role = session.get('role')
    return jsonify({
        'logged_in': 'user_id' in session,
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': role,
        'is_admin': role == 'admin',
        'is_seller': role == 'vendor'
    }), 200

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        selected_role = str(data.get('account_type', 'user')).strip().lower()
        admin_key = str(data.get('admin_key', '')).strip().lower()
        name = data.get('name', email.split('@')[0])  # Default name from email
        
        # Validation
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

        if selected_role not in ROLE_MAP:
            return jsonify({'success': False, 'message': 'Invalid account type selected'}), 400

        if selected_role == 'admin' and admin_key != ADMIN_SIGNUP_KEY:
            return jsonify({'success': False, 'message': 'Invalid admin credential'}), 403
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Create new user with selected role
        hashed_password = generate_password_hash(password)
        username = email.split('@')[0]  # Use email prefix as username
        db_role = ROLE_MAP[selected_role]
        
        # Ensure unique username
        counter = 1
        original_username = username
        while User.query.filter_by(username=username).first():
            username = f"{original_username}{counter}"
            counter += 1
        
        new_user = User(
            name=name,
            email=email,
            username=username,
            password=hashed_password,
            role=db_role
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Log the user in
            session['user_id'] = new_user.user_id
            session['username'] = new_user.username
            session['role'] = new_user.role

            if new_user.role == 'admin':
                redirect_url = url_for('admin')
            elif new_user.role == 'vendor':
                redirect_url = url_for('seller')
            else:
                redirect_url = url_for('index')

            return jsonify({'success': True, 'message': 'Account created successfully', 'redirect': redirect_url}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error creating account: {str(e)}'}), 500
    
    return render_template('CreateAccount.html')

@app.route('/login_post', methods=['POST'])
def login_post():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password, password):
        # Login successful
        session['user_id'] = user.user_id
        session['username'] = user.username
        session['role'] = user.role
        
        # Redirect based on role
        if user.role == 'admin':
            redirect_url = url_for('admin')
        elif user.role == 'vendor':
            redirect_url = url_for('seller')
        else:
            redirect_url = url_for('index')
        
        return jsonify({'success': True, 'message': 'Login successful', 'redirect': redirect_url}), 200
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

@app.route('/api/cart', methods=['GET'])
@require_role('customer', 'vendor', 'admin')
def get_cart():
    user_id = session.get('user_id')
    cart = Cart.query.filter_by(customer_id=user_id).first()
    
    if not cart:
        return jsonify({'items': [], 'total': 0}), 200
    
    items = []
    total = 0
    for ci in cart.items:
        price = float(ci.price_at_time) if ci.price_at_time else float(ci.product.prices[0].current_price if ci.product.prices else 0)
        item_total = price * ci.quantity
        total += item_total
        items.append({
            'cart_item_id': ci.cart_item_id,
            'product_id': ci.product_id,
            'title': ci.product.title,
            'quantity': ci.quantity,
            'price': price,
            'item_total': item_total,
            'image_url': ci.product.images[0].image_url if ci.product.images else 'https://images.unsplash.com/photo-1535591273668-578e31182c4f?auto=format&fit=crop&w=1200&q=80'
        })
    
    return jsonify({'items': items, 'total': total}), 200

@app.route('/api/cart', methods=['POST'])
@require_role('customer', 'vendor', 'admin')
def add_to_cart():
    user_id = session.get('user_id')
    data = request.get_json() or {}
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            return jsonify({'success': False, 'message': 'Quantity must be at least 1'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid quantity'}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    # Get or create cart
    cart = Cart.query.filter_by(customer_id=user_id).first()
    if not cart:
        cart = Cart(customer_id=user_id)
        db.session.add(cart)
        db.session.flush()
    
    # Check if item already in cart
    existing = CartItem.query.filter_by(cart_id=cart.cart_id, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        price = float(product.prices[0].current_price) if product.prices else 0
        cart_item = CartItem(cart_id=cart.cart_id, product_id=product_id, quantity=quantity, price_at_time=price)
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Added to cart'}), 201

@app.route('/api/cart/<int:cart_item_id>', methods=['PUT'])
@require_role('customer', 'vendor', 'admin')
def update_cart_item(cart_item_id):
    user_id = session.get('user_id')
    data = request.get_json() or {}
    quantity = data.get('quantity')
    
    if quantity is None:
        return jsonify({'success': False, 'message': 'Quantity required'}), 400
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            return jsonify({'success': False, 'message': 'Quantity must be at least 1'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid quantity'}), 400
    
    ci = CartItem.query.get(cart_item_id)
    if not ci or ci.cart.customer_id != user_id:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404
    
    ci.quantity = quantity
    db.session.commit()
    return jsonify({'success': True, 'message': 'Updated'}), 200

@app.route('/api/cart/<int:cart_item_id>', methods=['DELETE'])
@require_role('customer', 'vendor', 'admin')
def remove_from_cart(cart_item_id):
    user_id = session.get('user_id')
    
    ci = CartItem.query.get(cart_item_id)
    if not ci or ci.cart.customer_id != user_id:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404
    
    db.session.delete(ci)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Removed from cart'}), 200

@app.route('/api/checkout', methods=['POST'])
@require_role('customer', 'vendor', 'admin')
def api_checkout():
    user_id = session.get('user_id')
    data = request.get_json() or {}
    
    cart = Cart.query.filter_by(customer_id=user_id).first()
    if not cart or not cart.items:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400
    
    # Calculate total
    total = 0
    for ci in cart.items:
        price = float(ci.price_at_time) if ci.price_at_time else float(ci.product.prices[0].current_price if ci.product.prices else 0)
        total += price * ci.quantity
    
    try:
        # Create order
        order = Order(customer_id=user_id, total_price=total, status='pending')
        db.session.add(order)
        db.session.flush()
        
        # Create order items (one per vendor/product combination)
        for ci in cart.items:
            price = float(ci.price_at_time) if ci.price_at_time else float(ci.product.prices[0].current_price if ci.product.prices else 0)
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=ci.product_id,
                vendor_id=ci.product.vendor_id,
                quantity=ci.quantity,
                price_at_order=price,
                vendor_confirmation_status='pending',
                item_status='pending'
            )
            db.session.add(order_item)
        
        # Clear cart
        CartItem.query.filter_by(cart_id=cart.cart_id).delete()
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Order placed',
            'order_id': order.order_id,
            'redirect': url_for('order_detail_page', order_id=order.order_id)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Checkout failed: {str(e)}'}), 500

@app.route('/api/orders', methods=['GET'])
@require_role('customer', 'vendor', 'admin')
def get_user_orders():
    user_id = session.get('user_id')
    role = session.get('role')
    
    if role == 'customer':
        orders = Order.query.filter_by(customer_id=user_id).order_by(Order.order_date.desc()).all()
    elif role == 'vendor':
        # Show orders containing this vendor's products
        order_ids = db.session.query(OrderItem.order_id).filter_by(vendor_id=user_id).distinct()
        orders = Order.query.filter(Order.order_id.in_(order_ids)).order_by(Order.order_date.desc()).all()
    else:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    result = []
    for order in orders:
        result.append({
            'order_id': order.order_id,
            'order_date': order.order_date.isoformat(),
            'status': order.status,
            'total_price': float(order.total_price),
            'item_count': len(order.items)
        })
    
    return jsonify({'orders': result}), 200

@app.route('/api/vendor/orders', methods=['GET'])
@require_role('vendor')
def get_vendor_orders():
    user_id = session.get('user_id')
    
    # Get all order items from this vendor
    order_items = OrderItem.query.filter_by(vendor_id=user_id).all()
    order_ids = [oi.order_id for oi in order_items]
    
    if not order_ids:
        return jsonify({'orders': []}), 200
    
    orders = Order.query.filter(Order.order_id.in_(order_ids)).order_by(Order.order_date.desc()).all()
    
    result = []
    for order in orders:
        # Get this vendor's items in this order
        vendor_items = [oi for oi in order.items if oi.vendor_id == user_id]
        result.append({
            'order_id': order.order_id,
            'customer_name': order.customer.name,
            'customer_email': order.customer.email,
            'order_date': order.order_date.isoformat(),
            'status': order.status,
            'total_price': float(order.total_price),
            'items': [{
                'order_item_id': oi.order_item_id,
                'product_title': oi.product.title,
                'quantity': oi.quantity,
                'price_at_order': float(oi.price_at_order),
                'vendor_confirmation_status': oi.vendor_confirmation_status,
                'item_status': oi.item_status
            } for oi in vendor_items]
        })
    
    return jsonify({'orders': result}), 200

@app.route('/api/vendor/orders/<int:order_item_id>', methods=['PUT'])
@require_role('vendor')
def update_vendor_order(order_item_id):
    user_id = session.get('user_id')
    data = request.get_json() or {}
    
    oi = OrderItem.query.get(order_item_id)
    if not oi or oi.vendor_id != user_id:
        return jsonify({'success': False, 'message': 'Order item not found'}), 404
    
    action = data.get('action')  # 'confirm', 'deny', 'ship', 'deliver'
    
    if action == 'confirm':
        oi.vendor_confirmation_status = 'confirmed'
        oi.item_status = 'confirmed'
    elif action == 'deny':
        oi.vendor_confirmation_status = 'denied'
        oi.item_status = 'denied'
    elif action == 'ship':
        oi.item_status = 'handed_to_delivery'
    elif action == 'deliver':
        oi.item_status = 'shipped'
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'Order updated: {action}'}), 200

@app.route('/api/admin/orders', methods=['GET'])
@require_role('admin')
def get_all_orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    
    result = []
    for order in orders:
        result.append({
            'order_id': order.order_id,
            'customer_name': order.customer.name,
            'customer_email': order.customer.email,
            'order_date': order.order_date.isoformat(),
            'status': order.status,
            'total_price': float(order.total_price),
            'item_count': len(order.items),
            'vendors': list(set([oi.vendor.username for oi in order.items]))
        })
    
    return jsonify({'orders': result}), 200

@app.route('/api/admin/users', methods=['GET'])
@require_role('admin')
def get_all_users():
    users = User.query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        result.append({
            'user_id': u.user_id,
            'name': u.name,
            'email': u.email,
            'username': u.username,
            'role': u.role,
            'created_at': u.created_at.isoformat()
        })
    return jsonify({'users': result}), 200

@app.route('/api/admin/stats', methods=['GET'])
@require_role('admin')
def get_admin_stats():
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_products = Product.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    total_revenue = db.session.query(db.func.sum(Order.total_price)).scalar() or 0
    return jsonify({
        'total_users': total_users,
        'total_orders': total_orders,
        'total_products': total_products,
        'pending_orders': pending_orders,
        'total_revenue': float(total_revenue)
    }), 200

@app.route('/api/user/profile', methods=['GET'])
@require_role('customer', 'vendor', 'admin')
def get_user_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.user_id,
        'name': user.name,
        'email': user.email,
        'username': user.username,
        'phone_number': user.phone_number,
        'role': user.role,
        'created_at': user.created_at.isoformat()
    }), 200

@app.route('/api/user/profile', methods=['PUT'])
@require_role('customer', 'vendor', 'admin')
def update_user_profile():
    user_id = session.get('user_id')
    data = request.get_json() or {}
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    if 'name' in data:
        user.name = str(data['name']).strip()
    if 'phone_number' in data:
        user.phone_number = str(data['phone_number']).strip()
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 500

@app.route('/order/<int:order_id>')
def order_detail_page(order_id):
    order = Order.query.get(order_id)
    if not order:
        return render_template('error.html', message='Order not found'), 404
    
    # Check authorization
    if session.get('user_id') != order.customer_id and session.get('role') not in ['admin', 'vendor']:
        return redirect(url_for('index'))
    
    return render_template('order-detail.html', order=order)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_sample_products()
    app.run(debug=True)
