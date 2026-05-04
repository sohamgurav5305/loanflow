from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify, render_template
from sqlalchemy.exc import IntegrityError
from prometheus_client import start_http_server, Counter
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ------------------ CONFIG ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loanflow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------ METRICS ------------------
REQUEST_COUNT = Counter('request_count', 'Total Requests')

# ------------------ MODELS ------------------
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Submitted")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, index=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(50))  # user/admin/manager
    is_verified = db.Column(db.Boolean, default=False)


# ------------------ ROUTES ------------------

@app.route('/')
def home():
    REQUEST_COUNT.inc()
    return render_template('index.html')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    if not data.get('username') or not data.get('password'):
        return jsonify({"message": "Username and password are required"}), 400

    if data.get('role') not in ['user', 'admin', 'manager']:
        return jsonify({"message": "Select a valid role"}), 400

    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        role=data.get('role', 'user'),
        is_verified=False
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Username already exists"}), 409

    return jsonify({"message": "Account created. Wait for admin verification before login."})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    if not data.get('username') or not data.get('password'):
        return jsonify({"message": "Username and password are required"}), 400

    if data.get('role') not in ['user', 'admin', 'manager']:
        return jsonify({"message": "Select a valid role"}), 400

    user = User.query.filter_by(
        username=data['username'],
        role=data['role']
    ).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.is_verified:
        return jsonify({"message": "Account is waiting for admin verification"}), 403

    return jsonify({
        "message": "Login success",
        "username": user.username,
        "role": user.role,
        "is_verified": user.is_verified
    })


@app.route('/apply', methods=['POST'])
def apply():
    data = request.get_json(silent=True) or {}

    if not data.get('name') or not data.get('amount'):
        return jsonify({"message": "Name and amount are required"}), 400

    try:
        amount = int(data['amount'])
        if amount <= 0:
            return jsonify({"message": "Amount must be positive"}), 400
    except ValueError:
        return jsonify({"message": "Amount must be a number"}), 400

    loan = Loan(name=data['name'], amount=amount)
    db.session.add(loan)
    db.session.commit()

    return jsonify({"message": "Loan Submitted"})


@app.route('/loans', methods=['GET'])
def get_loans():
    loans = Loan.query.all()
    return jsonify([
        {
            "id": l.id,
            "name": l.name,
            "amount": l.amount,
            "status": l.status
        }
        for l in loans
    ])


@app.route('/users', methods=['GET'])
def get_users():
    role = request.args.get('role')

    if role != 'admin':
        return jsonify({"message": "Unauthorized"}), 403

    users = User.query.order_by(User.is_verified.asc(), User.id.desc()).all()

    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_verified": user.is_verified
        }
        for user in users
    ])


@app.route('/users/<int:id>/verify', methods=['POST'])
def verify_user(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    user = db.session.get(User, id)

    if user is None:
        return jsonify({"message": "User not found"}), 404

    user.is_verified = True
    db.session.commit()

    return jsonify({"message": "User verified"})


@app.route('/verify/<int:id>', methods=['POST'])
def verify_loan(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    loan = db.session.get(Loan, id)

    if loan is None:
        return jsonify({"message": "Loan not found"}), 404

    loan.status = "Verified"
    db.session.commit()

    return jsonify({"message": "Verified"})


@app.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "manager":
        return jsonify({"message": "Unauthorized"}), 403

    loan = db.session.get(Loan, id)

    if loan is None:
        return jsonify({"message": "Loan not found"}), 404

    loan.status = "Approved"
    db.session.commit()

    return jsonify({"message": "Approved"})


@app.route('/reject/<int:id>', methods=['POST'])
def reject(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "manager":
        return jsonify({"message": "Unauthorized"}), 403

    loan = db.session.get(Loan, id)

    if loan is None:
        return jsonify({"message": "Loan not found"}), 404

    loan.status = "Rejected"
    db.session.commit()

    return jsonify({"message": "Rejected"})


# ------------------ DB INIT ------------------

def seed_admin():
    admin = User.query.filter_by(username='admin').first()

    if admin is None:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin',
            is_verified=True
        )
        db.session.add(admin)
    else:
        admin.password = generate_password_hash('admin123')
        admin.role = 'admin'
        admin.is_verified = True

    db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        seed_admin()


# ------------------ RUN ------------------

if __name__ == '__main__':
    start_http_server(8000)
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)