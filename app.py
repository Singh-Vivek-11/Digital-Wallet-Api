from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
import os
import urllib.parse

app = Flask(__name__)
load_dotenv()


MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'Vivek@3938')
MYSQL_DB = os.getenv('MYSQL_DB', 'digital_wallet')

encoded_password = urllib.parse.quote(MYSQL_PASSWORD)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}/{MYSQL_DB}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
db = SQLAlchemy(app)


CURRENCY_API_KEY = os.getenv('CURRENCY_API_KEY', 'your_currency_api_key')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # 'credit' or 'debit'
    amount = db.Column(db.Float, nullable=False)
    updated_balance = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)


def authenticate():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        abort(401, description="Missing or invalid Authorization header")
    
    try:
        auth_token = auth_header.split(" ")[1]
        decoded = base64.b64decode(auth_token).decode('utf-8')
        username, password = decoded.split(':')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return user
        abort(401, description="Invalid credentials")
    except:
        abort(401, description="Invalid Authorization header format")


@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Digital Wallet API"}), 200


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        abort(400, description="Username and password are required")
    
    username = data['username']
    password = data['password']
    
    if User.query.filter_by(username=username).first():
        abort(400, description="Username already exists")
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(username=username, password=hashed_password.decode('utf-8'))
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User created"}), 201


@app.route('/fund', methods=['POST'])
def fund_account():
    user = authenticate()
    data = request.get_json()
    if not data or not data.get('amt') or data['amt'] <= 0:
        abort(400, description="Valid amount is required")
    
    amount = float(data['amt'])
    user.balance += amount
    transaction = Transaction(user_id=user.id, kind='credit', amount=amount, updated_balance=user.balance)
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({"balance": user.balance})


@app.route('/pay', methods=['POST'])
def pay_user():
    user = authenticate()
    data = request.get_json()
    if not data or not data.get('to') or not data.get('amt') or data['amt'] <= 0:
        abort(400, description="Valid recipient and amount are required")
    
    recipient = User.query.filter_by(username=data['to']).first()
    if not recipient:
        abort(400, description="Recipient does not exist")
    
    amount = float(data['amt'])
    if user.balance < amount:
        abort(400, description="Insufficient funds")
    
    user.balance -= amount
    recipient.balance += amount
    
    debit_transaction = Transaction(user_id=user.id, kind='debit', amount=amount, updated_balance=user.balance)
    credit_transaction = Transaction(user_id=recipient.id, kind='credit', amount=amount, updated_balance=recipient.balance)
    db.session.add_all([debit_transaction, credit_transaction])
    db.session.commit()
    
    return jsonify({"balance": user.balance})


@app.route('/bal', methods=['GET'])
def check_balance():
    user = authenticate()
    currency = request.args.get('currency', 'INR')
    
    balance = user.balance
    if currency != 'INR':
        response = requests.get(f"https://api.currencyapi.com/v3/latest?apikey={CURRENCY_API_KEY}&base_currency=INR&currencies={currency}")
        if response.status_code != 200:
            abort(500, description="Currency conversion failed")
        rate = response.json()['data'][currency]['value']
        balance = user.balance * rate
    
    return jsonify({"balance": round(balance, 2), "currency": currency})


@app.route('/stmt', methods=['GET'])
def transaction_history():
    user = authenticate()
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
    return jsonify([
        {
            "kind": t.kind,
            "amt": t.amount,
            "updated_bal": t.updated_balance,
            "timestamp": t.timestamp.isoformat()
        } for t in transactions
    ])


@app.route('/product', methods=['POST'])
def add_product():
    authenticate()  
    data = request.get_json()
    if not data or not data.get('name') or not data.get('price') or not data.get('description'):
        abort(400, description="Name, price, and description are required")
    
    product = Product(name=data['name'], price=float(data['price']), description=data['description'])
    db.session.add(product)
    db.session.commit()
    
    return jsonify({"id": product.id, "message": "Product added"}), 201


@app.route('/product', methods=['GET'])
def list_products():
    products = Product.query.all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "description": p.description
        } for p in products
    ])


@app.route('/buy', methods=['POST'])
def buy_product():
    user = authenticate()
    data = request.get_json()
    if not data or not data.get('product_id'):
        abort(400, description="Product ID is required")
    
    product = Product.query.get(data['product_id'])
    if not product:
        abort(400, description="Invalid product")
    
    if user.balance < product.price:
        abort(400, description="Insufficient balance")
    
    user.balance -= product.price
    transaction = Transaction(user_id=user.id, kind='debit', amount=product.price, updated_balance=user.balance)
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({"message": "Product purchased", "balance": user.balance})


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": error.description}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": error.description}), 401

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": error.description}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
