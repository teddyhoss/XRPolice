from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from xrpl.clients import JsonRpcClient
from xrpl.models import AccountTx, Tx
import networkx as nx
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = 'la_tua_chiave_segreta'

# XRP Ledger client setup
client = JsonRpcClient("https://s1.ripple.com:51234/")

class ForensicAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def get_transaction_by_hash(self, tx_hash):
        """Retrieve transaction by hash"""
        try:
            print(f"Fetching transaction: {tx_hash}")
            tx_request = Tx(transaction=tx_hash)
            response = client.request(tx_request)
            
            if not response.is_successful():
                print(f"Transaction lookup failed: {response.result.get('error_message', 'Unknown error')}")
                return None

            # Estrai i dati dalla risposta
            tx_data = response.result.get('tx_json', {})
            meta_data = response.result.get('meta', {})
            
            processed_tx = {
                'hash': response.result.get('hash', ''),
                'date': datetime.fromtimestamp(tx_data.get('date', 0) + 946684800),
                'type': tx_data.get('TransactionType', ''),
                'sender': tx_data.get('Account', ''),
                'destination': tx_data.get('Destination', ''),
                'amount': tx_data.get('Amount', ''),
                'fee': tx_data.get('Fee', ''),
                'result': meta_data.get('TransactionResult', '')
            }
            
            print(f"Processed transaction: {processed_tx}")
            return processed_tx
                
        except Exception as e:
            print(f"Error fetching transaction: {str(e)}")
            return None

@app.route('/api/analyze', methods=['POST'])
def analyze_address():
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    tx_hash = data.get('address')  # manteniamo 'address' per compatibilità
    if not tx_hash:
        return jsonify({"error": "Transaction hash required"}), 400
    
    try:
        analyzer = ForensicAnalyzer()
        transaction = analyzer.get_transaction_by_hash(tx_hash)
        
        if not transaction:
            return jsonify({
                "error": "Transaction not found or invalid",
                "transactions": [],
                "flows": {"incoming": [], "outgoing": []},
                "risk_assessment": {"risk_score": 0, "factors": []}
            }), 404
        
        return jsonify({
            "transaction_type": "hash",
            "transactions": [transaction],  # Mettiamo la transazione in un array per mantenere la compatibilità
            "flows": {
                "incoming": [],
                "outgoing": []
            },
            "risk_assessment": {
                "risk_score": 0,
                "factors": []
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error analyzing transaction {tx_hash}: {str(e)}")
        return jsonify({
            "error": str(e),
            "transactions": [],
            "flows": {"incoming": [], "outgoing": []},
            "risk_assessment": {"risk_score": 0, "factors": []}
        }), 500

# Original routes remain the same
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    print(f"Login attempt - Email: {email}")  # Debug print
    
    if email == 'admin@admin.com' and password == 'password':
        session['logged_in'] = True
        print("Login successful")  # Debug print
        return redirect(url_for('dashboard'))
    else:
        flash('Credenziali non valide')
        print("Login failed")  # Debug print
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)