from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from prometheus_client import start_http_server, Counter

app = Flask(__name__)

# ------------------- DATABASE CONFIG -------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loanflow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------- PROMETHEUS -------------------
REQUEST_COUNT = Counter('request_count', 'Total Requests')

# ------------------- MODELS -------------------
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Submitted")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(50))  # user/admin/manager
    is_verified = db.Column(db.Boolean, default=False)

# ------------------- ROUTES -------------------

@app.route('/')
def home():
    REQUEST_COUNT.inc()
    return render_template('index.html')   # UI works

# ------------------- AUTH -------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    if not data.get('username') or not data.get('password'):
        return jsonify({"message": "Username and password required"}), 400

    if data.get('role') not in ['user', 'admin', 'manager']:
        return jsonify({"message": "Invalid role"}), 400

    user = User(
        username=data['username'],
        password=data['password'],
        role=data['role'],
        is_verified=False
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Username already exists"}), 409

    return jsonify({"message": "Registered. Wait for admin verification."})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    user = User.query.filter_by(
        username=data.get('username'),
        password=data.get('password'),
        role=data.get('role')
    ).first()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    if not user.is_verified:
        return jsonify({"message": "Not verified"}), 403

    return jsonify({
        "message": "Login success",
        "username": user.username,
        "role": user.role
    })

# ------------------- LOANS -------------------

@app.route('/apply', methods=['POST'])
def apply():
    data = request.get_json(silent=True) or {}

    if not data.get('name') or not data.get('amount'):
        return jsonify({"message": "Name & amount required"}), 400

    loan = Loan(
        name=data['name'],
        amount=int(data['amount'])
    )

    db.session.add(loan)
    db.session.commit()

    return jsonify({"message": "Loan submitted"})

@app.route('/loans', methods=['GET'])
def get_loans():
    loans = Loan.query.all()

    return jsonify([
        {
            "id": l.id,
            "name": l.name,
            "amount": l.amount,
            "status": l.status
        } for l in loans
    ])

# ------------------- ADMIN -------------------

@app.route('/users', methods=['GET'])
def get_users():
    role = request.args.get('role')

    if role != 'admin':
        return jsonify({"message": "Unauthorized"}), 403

    users = User.query.all()

    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_verified": u.is_verified
        } for u in users
    ])

@app.route('/users/<int:id>/verify', methods=['POST'])
def verify_user(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    user = db.session.get(User, id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    user.is_verified = True
    db.session.commit()

    return jsonify({"message": "User verified"})

# ------------------- LOAN ACTIONS -------------------

@app.route('/verify/<int:id>', methods=['POST'])
def verify(id):
    data = request.get_json(silent=True) or {}

    if data.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    loan = db.session.get(Loan, id)

    if not loan:
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

    if not loan:
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

    if not loan:
        return jsonify({"message": "Loan not found"}), 404

    loan.status = "Rejected"
    db.session.commit()

    return jsonify({"message": "Rejected"})

# ------------------- INIT -------------------

def init_db():
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password='admin123',
                role='admin',
                is_verified=True
            )
            db.session.add(admin)

        db.session.commit()

# ------------------- RUN -------------------

if __name__ == "__main__":
    init_db()
    start_http_server(8000)   # Prometheus metrics
    app.run(host='0.0.0.0', port=5000)