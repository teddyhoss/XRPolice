from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Cambia questo con una chiave segreta vera
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xrpolice.db'  # Usa SQLite come database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inizializza SQLAlchemy
db = SQLAlchemy(app)

# Modelli del database
class Investigation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    investigations = db.relationship('Investigation', backref='user', lazy=True)

# Crea le tabelle del database
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@admin.com').first():
        default_user = User(
            email='admin@admin.com',
            password='password'  # In produzione, usa password hashate!
        )
        db.session.add(default_user)
        db.session.commit()

# Le tue route esistenti
@app.route('/')
def index():
    if 'logged_in' not in session:
        return render_template('login.html')
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == 'admin@admin.com' and password == 'password':
            session['logged_in'] = True
            session['user_id'] = 1  # Per ora usiamo un ID utente fisso
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

# API Routes per le investigazioni
@app.route('/api/investigations', methods=['GET'])
def get_investigations():
    investigations = Investigation.query.order_by(Investigation.created_at.desc()).all()
    return jsonify([{
        'id': inv.id,
        'name': inv.name,
        'description': inv.description,
        'created_at': inv.created_at.isoformat()
    } for inv in investigations])

@app.route('/api/investigations', methods=['POST'])
def create_investigation():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    investigation = Investigation(
        name=data['name'],
        description=data.get('description', ''),
        user_id=session['user_id']
    )
    db.session.add(investigation)
    db.session.commit()
    return jsonify({
        'id': investigation.id,
        'name': investigation.name,
        'description': investigation.description,
        'created_at': investigation.created_at.isoformat()
    })

@app.route('/api/investigations/<int:id>', methods=['GET'])
def get_investigation(id):
    investigation = Investigation.query.get_or_404(id)
    return jsonify({
        'id': investigation.id,
        'name': investigation.name,
        'description': investigation.description,
        'created_at': investigation.created_at.isoformat()
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/analyze', methods=['POST'])
def analyze_address():
    data = request.json
    address = data.get('address')
    investigation_id = data.get('investigation_id')
    
    # Qui implementa la logica per analizzare l'indirizzo XRP
    # Per esempio, puoi usare una libreria per interagire con la XRP Ledger API
    
    # Per ora, restituiamo dati di esempio
    return jsonify({
        'address': address,
        'transactions': [
            {
                'from': address,
                'to': 'rRandomAddress1',
                'amount': '100',
                'timestamp': '2024-01-01T12:00:00Z'
            },
            {
                'from': 'rRandomAddress2',
                'to': address,
                'amount': '50',
                'timestamp': '2024-01-02T12:00:00Z'
            }
        ]
    })

if __name__ == '__main__':
    app.run(debug=True)