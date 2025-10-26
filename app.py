from flask import Flask, jsonify, request
from flask_cors import CORS # Import CORS
import mysql.connector
from mysql.connector import Error
import datetime
from decimal import Decimal # Import Decimal

# Create the Flask application instance
app = Flask(__name__)
CORS(app) # Initialize CORS for the entire app

# --- Database Configuration ---
# Replace 'your_mysql_root_password' with your actual MySQL root password
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '@Abdullah537', # <-- IMPORTANT: CHANGE THIS
    'database': 'budgie_db'
}

# --- Database Helper Functions ---
# Function to connect to the database
def create_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
    except Error as e:
        print(f"!!! DB Connection Error: {e}")
    return connection

# Format row helper (converts Decimal/Date)
def format_row(row):
    if row is None: return None
    formatted = {}
    for key, value in row.items():
        if isinstance(value, Decimal): formatted[key] = float(value)
        elif isinstance(value, datetime.date): formatted[key] = value.isoformat()
        else: formatted[key] = value
    return formatted

# Read query helper
def execute_read_query(query, params=None):
    connection = create_db_connection()
    cursor = None
    results = None
    if not connection: return None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        raw_results = cursor.fetchall()
        results = [format_row(row) for row in raw_results] # Format results
    except Error as e:
        print(f"!!! Read Query Error: {e}")
    finally:
        if cursor: cursor.close()
        if connection and connection.is_connected(): connection.close()
    return results

# Write query helper
def execute_write_query(query, params=None):
    connection = create_db_connection()
    cursor = None
    success = False
    last_row_id = None
    if not connection: return success, last_row_id
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        connection.commit()
        last_row_id = cursor.lastrowid
        success = True
    except Error as e:
        print(f"!!! Write Query Error: {e}")
        if connection and connection.is_connected(): connection.rollback()
    finally:
        if cursor: cursor.close()
        if connection and connection.is_connected(): connection.close()
    return success, last_row_id
# --- End Database Helpers ---


# --- API Endpoints ---
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    query = "SELECT id, type, category, amount, note, transaction_date FROM transactions ORDER BY transaction_date DESC, created_at DESC"
    transactions = execute_read_query(query)
    if transactions is not None:
        return jsonify(transactions)
    else:
        return jsonify(error="Failed to fetch transactions"), 500

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    if not data or not all(k in data for k in ('type', 'category', 'amount', 'date')): return jsonify(error="Missing required fields"), 400
    try:
        transaction_date_str = data['date'].split('T')[0]
        datetime.datetime.strptime(transaction_date_str, '%Y-%m-%d')
        amount = float(data['amount'])
        params = (data['type'], data['category'], amount, data.get('note'), transaction_date_str)
        query = "INSERT INTO transactions (type, category, amount, note, transaction_date) VALUES (%s, %s, %s, %s, %s)"
        success, last_id = execute_write_query(query, params)
        if success and last_id is not None:
            new_transaction_query = "SELECT id, type, category, amount, note, transaction_date FROM transactions WHERE id = %s"
            new_transaction = execute_read_query(new_transaction_query, (last_id,))
            if new_transaction and len(new_transaction) == 1:
                 return jsonify(new_transaction[0]), 201
            else: return jsonify(message="Transaction added but couldn't retrieve details"), 201
        else: return jsonify(error="Failed to add transaction"), 500
    except ValueError: return jsonify(error="Invalid amount or date format"), 400
    except Exception as e: print(f"Error processing add transaction: {e}"); return jsonify(error=f"Server error: {e}"), 500

# NEW: Endpoint to delete a transaction
@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    print(f"--- Request received for DELETE /api/transactions/{transaction_id} ---")
    query = "DELETE FROM transactions WHERE id = %s"
    # Ensure transaction_id is passed correctly as a tuple
    success, _ = execute_write_query(query, (transaction_id,))

    if success:
        print(f"Transaction ID {transaction_id} deleted successfully.")
        # Return 204 No Content for successful deletion
        return '', 204
    else:
        print(f"!!! Failed to delete transaction ID {transaction_id}.")
        return jsonify(error="Failed to delete transaction"), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    query = "SELECT username, currency_symbol, monthly_budget FROM settings WHERE setting_id = 1"
    settings = execute_read_query(query)
    if settings is not None and len(settings) == 1:
        return jsonify(settings[0])
    elif settings is not None and len(settings) == 0: return jsonify(error="Settings not found"), 404
    else: return jsonify(error="Failed to fetch settings"), 500

@app.route('/api/settings', methods=['PUT'])
def update_settings():
    data = request.get_json();
    if not data: return jsonify(error="Missing data"), 400
    updates = []; params = []
    if 'username' in data: updates.append("username = %s"); params.append(data['username'])
    if 'currency_symbol' in data: updates.append("currency_symbol = %s"); params.append(data['currency_symbol'])
    if 'monthly_budget' in data:
        try: budget = float(data['monthly_budget']); updates.append("monthly_budget = %s"); params.append(budget)
        except ValueError: return jsonify(error="Invalid budget amount"), 400
    if not updates: return jsonify(error="No valid fields to update"), 400
    query = f"UPDATE settings SET {', '.join(updates)} WHERE setting_id = 1"
    success, _ = execute_write_query(query, tuple(params))
    if success:
        updated_settings_q = "SELECT username, currency_symbol, monthly_budget FROM settings WHERE setting_id = 1"
        updated_settings = execute_read_query(updated_settings_q)
        if updated_settings and len(updated_settings) == 1: return jsonify(updated_settings[0])
        else: return jsonify(message="Settings updated but couldn't retrieve details")
    else: return jsonify(error="Failed to update settings"), 500


# Test Route (optional)
@app.route('/api/hello', methods=['GET'])
def hello_world():
    conn = create_db_connection()
    message = "Hello from Budgie Backend!"
    if conn: message += " DB Connected!"; conn.close()
    else: message += " DB FAILED!"
    return jsonify(message=message)
# --- End API Endpoints ---


# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)