from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from xrpl.clients import JsonRpcClient
from xrpl.models import AccountTx
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
        
    def get_account_transactions(self, address, limit=100):
        """Retrieve and analyze account transactions"""
        try:
            acct_tx = AccountTx(
                account=address,
                limit=limit
            )
            response = client.request(acct_tx)
            if 'result' not in response or 'transactions' not in response.result:
                return []
            return self._process_transactions(response.result['transactions'])
        except Exception as e:
            app.logger.error(f"Error getting transactions for {address}: {str(e)}")
            return []
    
    def _process_transactions(self, transactions):
        """Process and categorize transactions"""
        processed_data = []
        try:
            for tx in transactions:
                tx_data = tx['tx']
                processed_tx = {
                    'hash': tx_data.get('hash', ''),
                    'date': datetime.fromtimestamp(tx_data.get('date', 0) + 946684800),
                    'type': tx_data.get('TransactionType', ''),
                    'sender': tx_data.get('Account', ''),
                    'amount': tx_data.get('Amount', ''),
                    'destination': tx_data.get('Destination', ''),
                    'fee': tx_data.get('Fee', ''),
                    'result': tx['meta'].get('TransactionResult', '')
                }
                processed_data.append(processed_tx)
                self._update_graph(processed_tx)
        except Exception as e:
            app.logger.error(f"Error processing transactions: {str(e)}")
        return processed_data
    
    def _update_graph(self, tx):
        """Update transaction graph"""
        if tx.get('destination'):
            self.graph.add_edge(tx['sender'], tx['destination'], 
                              amount=tx['amount'],
                              hash=tx['hash'],
                              date=tx['date'])
    
    def analyze_flow(self, address, depth=2):
        """Analyze fund flow from an address"""
        try:
            flows = {
                'incoming': self._get_incoming_flows(address, depth),
                'outgoing': self._get_outgoing_flows(address, depth)
            }
            return flows
        except Exception as e:
            app.logger.error(f"Error analyzing flows: {str(e)}")
            return {'incoming': [], 'outgoing': []}
    
    def _get_incoming_flows(self, address, depth):
        """Analyze incoming transactions"""
        incoming = []
        if depth > 0 and address in self.graph:
            for predecessor in self.graph.predecessors(address):
                edge_data = self.graph.get_edge_data(predecessor, address)
                incoming.append({
                    'from': predecessor,
                    'amount': edge_data.get('amount', ''),
                    'date': edge_data.get('date', ''),
                    'hash': edge_data.get('hash', ''),
                    'sub_flows': self._get_incoming_flows(predecessor, depth-1)
                })
        return incoming
    
    def _get_outgoing_flows(self, address, depth):
        """Analyze outgoing transactions"""
        outgoing = []
        if depth > 0 and address in self.graph:
            for successor in self.graph.successors(address):
                edge_data = self.graph.get_edge_data(address, successor)
                outgoing.append({
                    'to': successor,
                    'amount': edge_data.get('amount', ''),
                    'date': edge_data.get('date', ''),
                    'hash': edge_data.get('hash', ''),
                    'sub_flows': self._get_outgoing_flows(successor, depth-1)
                })
        return outgoing
    
    def get_risk_score(self, address):
        """Calculate basic risk score based on transaction patterns"""
        if address not in self.graph:
            return {"risk_score": 0, "factors": []}
        
        try:
            risk_factors = []
            risk_score = 0
            
            # Check transaction volume
            out_degree = self.graph.out_degree(address)
            if out_degree > 100:
                risk_factors.append("High number of outgoing transactions")
                risk_score += 25
            
            # Check for mixing patterns
            if self._detect_mixing_pattern(address):
                risk_factors.append("Potential mixing pattern detected")
                risk_score += 35
            
            return {
                "risk_score": min(risk_score, 100),
                "factors": risk_factors
            }
        except Exception as e:
            app.logger.error(f"Error calculating risk score: {str(e)}")
            return {"risk_score": 0, "factors": []}
    
    def _detect_mixing_pattern(self, address):
        """Detect potential mixing patterns"""
        if address not in self.graph:
            return False
            
        try:
            outgoing = list(self.graph.successors(address))
            if len(outgoing) < 3:
                return False
                
            small_tx_count = 0
            for successor in outgoing:
                edge_data = self.graph.get_edge_data(address, successor)
                if float(edge_data.get('amount', 0)) < 1000:
                    small_tx_count += 1
            
            return small_tx_count >= 3
        except Exception as e:
            app.logger.error(f"Error detecting mixing pattern: {str(e)}")
            return False

# Routes originali
@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    if email == 'admin@admin.com' and password == 'password':
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    else:
        flash('Credenziali non valide')
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

# API Routes
@app.route('/api/analyze', methods=['POST'])
def analyze_address():
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    address = data.get('address')
    if not address:
        return jsonify({"error": "Address required"}), 400
    
    try:
        analyzer = ForensicAnalyzer()
        
        # Get transaction history
        transactions = analyzer.get_account_transactions(address)
        
        # Analyze transaction flows
        flows = analyzer.analyze_flow(address)
        
        # Get risk assessment
        risk_assessment = analyzer.get_risk_score(address)
        
        return jsonify({
            "transactions": transactions if isinstance(transactions, list) else [],
            "flows": flows if isinstance(flows, dict) else {"incoming": [], "outgoing": []},
            "risk_assessment": risk_assessment if isinstance(risk_assessment, dict) else {"risk_score": 0, "factors": []}
        })
        
    except Exception as e:
        app.logger.error(f"Error analyzing address {address}: {str(e)}")
        return jsonify({
            "transactions": [],
            "flows": {
                "incoming": [],
                "outgoing": []
            },
            "risk_assessment": {
                "risk_score": 0,
                "factors": []
            },
            "error": f"Error analyzing address: {str(e)}"
        })

@app.route('/api/export/<address>', methods=['GET'])
def export_data(address):
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        analyzer = ForensicAnalyzer()
        transactions = analyzer.get_account_transactions(address)
        
        df = pd.DataFrame(transactions)
        return Response(
            df.to_csv(index=False),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={address}_transactions.csv"}
        )
    except Exception as e:
        app.logger.error(f"Error exporting data: {str(e)}")
        return jsonify({"error": "Export failed"}), 500

if __name__ == '__main__':
    app.run(debug=True)