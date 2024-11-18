# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'typing_verification'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}


def get_db_connection():
    """Create a database connection"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    return conn


def validate_uuid(uuid_string):
    """Validate UUID format"""
    try:
        return str(uuid.UUID(uuid_string))
    except ValueError:
        return None



@app.route('/api/keypress', methods=['POST'])
def record_keypress():
    conn = None
    cur = None
    try:
        data = request.json
        document_id = data.get('document_id')
        character = data.get('character')

        app.logger.info(f"Received keypress: {data}")  # Debug log

        if not document_id:
            return jsonify({'error': 'document_id is required'}), 400

        if not character:
            return jsonify({'error': 'character is required'}), 400

        if not validate_uuid(document_id):
            return jsonify({'error': 'Invalid document ID format'}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT record_keypress(%s, %s)",
            (document_id, character)
        )
        keypress_id = cur.fetchone()['record_keypress']

        conn.commit()
        return jsonify({
            'id': keypress_id,
            'message': 'Keypress recorded successfully'
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error recording keypress: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/verify/<document_id>', methods=['GET'])
def get_verification_data(document_id):
    conn = None
    cur = None
    try:
        if not validate_uuid(document_id):
            return jsonify({'error': 'Invalid document ID'}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get document data
        cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cur.fetchone()
        if not document:
            return jsonify({'error': 'Document not found'}), 404

        # Get keypress data
        cur.execute(
            "SELECT created_at, key_char, typing_speed::integer as typing_speed, total_characters FROM get_verification_data(%s)",
            (document_id,)
        )
        keypresses = cur.fetchall()

        # Calculate time taken in seconds
        time_taken = 0
        if keypresses:
            time_delta = keypresses[-1]['created_at'] - keypresses[0]['created_at']
            time_taken = round(time_delta.total_seconds())

        # Get the last keypress for final typing speed
        final_typing_speed = keypresses[-1]['typing_speed'] if keypresses else 0

        return jsonify({
            'document': {
                'id': document['id'],
                'content': document['content'],
                'title': document['title'],
                'created_at': document['created_at'].isoformat(),
                'total_characters': document['total_characters'],
                'time_taken_seconds': time_taken,
                'final_typing_speed': final_typing_speed
            },
            'keypresses': [{
                'timestamp': kp['created_at'].isoformat(),
                'character': kp['key_char'],
                'typing_speed': kp['typing_speed'],
                'total_characters': kp['total_characters']
            } for kp in keypresses]
        }), 200

    except Exception as e:
        app.logger.error(f"Error getting verification data: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# Add this to your existing Flask backend

@app.route('/api/submit', methods=['POST'])
def submit_document():
    conn = None
    cur = None
    try:
        data = request.json
        document_id = data.get('document_id')
        content = data.get('content')
        keypresses = data.get('keyPresses', [])

        if not document_id:
            return jsonify({'error': 'document_id is required'}), 400

        if not validate_uuid(document_id):
            return jsonify({'error': 'Invalid document ID format'}), 400

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Update the document content
        cur.execute("""
            UPDATE documents 
            SET content = %s,
                total_characters = %s
            WHERE id = %s
            RETURNING id, created_at
        """, (content, len(content), document_id))

        result = cur.fetchone()

        if not result:
            return jsonify({'error': 'Document not found'}), 404

        # Calculate some final statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_keypresses,
                AVG(typing_speed) as avg_speed,
                MAX(typing_speed) as max_speed,
                MIN(created_at) as start_time,
                MAX(created_at) as end_time
            FROM key_presses
            WHERE document_id = %s
        """, (document_id,))

        stats = cur.fetchone()

        # Generate a verification URL
        verification_url = f"/verify/{document_id}"

        response_data = {
            'id': document_id,
            'verification_url': verification_url,
            'statistics': {
                'total_characters': len(content),
                'total_keypresses': stats['total_keypresses'],
                'average_speed': round(float(stats['avg_speed'] or 0), 2),
                'max_speed': round(float(stats['max_speed'] or 0), 2),
                'start_time': stats['start_time'].isoformat() if stats['start_time'] else None,
                'end_time': stats['end_time'].isoformat() if stats['end_time'] else None,
                'duration_seconds': (stats['end_time'] - stats['start_time']).total_seconds() if stats['start_time'] and
                                                                                                 stats[
                                                                                                     'end_time'] else 0
            }
        }

        conn.commit()
        return jsonify(response_data), 200

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error submitting document: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/documents', methods=['POST'])
def create_document():
    conn = None
    cur = None
    try:
        data = request.json
        content = data.get('content', '')
        title = data.get('title', 'Untitled Document')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Create new document
        cur.execute("""
            INSERT INTO documents (content, title, total_characters)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (content, title, len(content)))

        document_id = cur.fetchone()['id']

        conn.commit()
        return jsonify({
            'id': document_id,
            'message': 'Document created successfully'
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Error creating document: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)