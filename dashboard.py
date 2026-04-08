from flask import Flask, jsonify, request, render_template
import sqlite3
import json
import os
import logging
import datetime
from database import Database

app = Flask(__name__)
DB_PATH = "distractions.db"

# Ensure the database schemas are up to date
db = Database(DB_PATH)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/thoughts', methods=['GET'])
def get_thoughts():
    try:
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # default to last 7 days if not provided
        if not start_date:
            seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            start_date = seven_days_ago.strftime('%Y-%m-%d')
            
        conn = get_db_connection()
        query = "SELECT * FROM thoughts WHERE 1=1"
        params = []
        
        if status != 'all':
            query += " AND status = ?"
            params.append(status)
            
        if search:
            query += " AND (summary LIKE ? OR source LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
            
        if start_date:
            query += " AND date(timestamp) >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND date(timestamp) <= ?"
            params.append(end_date)
            
        query += " ORDER BY timestamp DESC"
        
        thoughts = conn.execute(query, params).fetchall()
        conn.close()
        
        # Convert to list of dicts
        thoughts_list = [dict(ix) for ix in thoughts]
        return jsonify(thoughts_list), 200
    except Exception as e:
        logging.error(f"Error fetching thoughts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/thoughts/<int:id>/status', methods=['PUT'])
def update_status(id):
    try:
        data = request.json
        new_status = data.get('status')
        if new_status not in ['open', 'rejected', 'cleared']:
            return jsonify({"error": "Invalid status"}), 400
            
        conn = get_db_connection()
        conn.execute('UPDATE thoughts SET status = ? WHERE id = ?', (new_status, id))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "status": new_status}), 200
    except Exception as e:
        logging.error(f"Error updating status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/thoughts/<int:id>/assign', methods=['POST'])
def assign_actionable(id):
    try:
        data = request.json
        list_type = data.get('list_type', 'Uncategorized')
        subtype = data.get('subtype', '')
        details = data.get('details', '')
        deadline = data.get('deadline', None)

        conn = get_db_connection()
        thought = conn.execute('SELECT * FROM thoughts WHERE id = ?', (id, )).fetchone()
        
        if not thought:
            conn.close()
            return jsonify({"error": "Thought not found"}), 404
            
        thought_dict = dict(thought)
        
        # Insert into actionables
        conn.execute('''
            INSERT INTO actionables (thought_id, list_type, subtype, details, deadline, original_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            thought_dict['id'],
            list_type,
            subtype,
            details,
            deadline,
            thought_dict['timestamp']
        ))
        
        # Mark thought as cleared
        conn.execute("UPDATE thoughts SET status = 'cleared' WHERE id = ?", (id,))
        
        conn.commit()
        conn.close()
            
        return jsonify({"success": True, "message": "Assigned successfully"}), 200
    except Exception as e:
        logging.error(f"Error assigning thought: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/actionables')
def actionables_dashboard():
    return render_template('actionables.html')

@app.route('/api/actionables', methods=['GET'])
def get_actionables():
    try:
        list_type = request.args.get('list_type', '')
        subtype = request.args.get('subtype', '')
        search = request.args.get('search', '')
        
        conn = get_db_connection()
        query = """
            SELECT a.*, t.summary, t.source 
            FROM actionables a
            LEFT JOIN thoughts t ON a.thought_id = t.id
            WHERE 1=1
        """
        params = []
        
        if list_type:
            query += " AND a.list_type = ?"
            params.append(list_type)
            
        if subtype:
            query += " AND a.subtype = ?"
            params.append(subtype)
            
        if search:
            query += " AND (a.details LIKE ? OR a.list_type LIKE ? OR a.subtype LIKE ? OR t.summary LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
            
        query += " ORDER BY a.created_at DESC"
        
        actionables = conn.execute(query, params).fetchall()
        
        # Also get all unique list_types and subtypes for filtering
        types = conn.execute("SELECT DISTINCT list_type FROM actionables ORDER BY list_type").fetchall()
        list_types = [t[0] for t in types if t[0]]
        
        subtypes_query = conn.execute("SELECT DISTINCT subtype FROM actionables WHERE subtype != '' ORDER BY subtype").fetchall()
        subtypes = [s[0] for s in subtypes_query]
        
        conn.close()
        
        return jsonify({
            "actionables": [dict(ix) for ix in actionables],
            "list_types": list_types,
            "subtypes": subtypes
        }), 200
    except Exception as e:
        logging.error(f"Error fetching actionables: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/list_types', methods=['GET'])
def get_list_types():
    try:
        conn = get_db_connection()
        types = conn.execute("SELECT DISTINCT list_type FROM actionables ORDER BY list_type").fetchall()
        list_types = [t[0] for t in types if t[0]]
        conn.close()
        return jsonify(list_types), 200
    except Exception as e:
        logging.error(f"Error fetching list types: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
