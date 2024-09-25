from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from utils import save_audio_file
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Set your secret key here
DATABASE = 'transcripts.db'
AUDIO_FOLDER = 'static/audios/'
MYMEMORY_URL = "https://api.mymemory.translated.net/get"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS transcripts
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     transcript TEXT NOT NULL,
                     language TEXT NOT NULL,
                     source TEXT NOT NULL,
                     FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS audio_files
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     file_path TEXT NOT NULL,
                     FOREIGN KEY (user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()

def add_missing_columns():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE transcripts ADD COLUMN language TEXT')
        print("Added 'language' column to 'transcripts' table")
    except sqlite3.OperationalError:
        print("'language' column already exists in 'transcripts' table")
    
    try:
        conn.execute('ALTER TABLE transcripts ADD COLUMN source TEXT')
        print("Added 'source' column to 'transcripts' table")
    except sqlite3.OperationalError:
        print("'source' column already exists in 'transcripts' table")
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        if cursor.fetchone() is not None:
            flash('Username already exists')
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful')
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transcripts WHERE user_id = ?', (session['user_id'],))
    transcripts = cursor.fetchall()
    cursor.execute('SELECT * FROM audio_files WHERE user_id = ?', (session['user_id'],))
    audios = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', transcripts=transcripts, audios=audios)

@app.route('/save_transcript', methods=['POST'])
def save_transcript():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    transcript = request.form['transcript']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transcripts (user_id, transcript, language, source) VALUES (?, ?, ?, ?)', 
                   (session['user_id'], transcript, 'en', 'manual'))  # Assuming English and manual input
    conn.commit()
    conn.close()
    flash('Transcript saved successfully')
    return redirect(url_for('dashboard'))

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    text = request.form['text']
    file_path = save_audio_file(text, session['user_id'])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO audio_files (user_id, file_path) VALUES (?, ?)', 
                   (session['user_id'], file_path))
    conn.commit()
    conn.close()
    flash('Audio generated successfully')
    return redirect(url_for('dashboard'))

@app.route('/serve_audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

@app.route('/download_audio/<path:filename>')
def download_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename, as_attachment=True)

@app.route('/translate', methods=['POST'])
def translate_text():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    data = request.get_json()
    text = data.get('text')
    target_language = data.get('target_language')

    if not text or not target_language:
        return jsonify({'success': False, 'message': 'Missing text or target language'}), 400

    try:
        response = requests.get(MYMEMORY_URL, params={
            "q": text,
            "langpair": f"auto|{target_language}"
        })
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        translated_text = result['responseData']['translatedText']
        
        # Save the translation to the database
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transcripts (user_id, transcript, source, language) VALUES (?, ?, ?, ?)', 
                       (user_id, translated_text, 'translation', target_language))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'translated_text': translated_text})
    except requests.RequestException as e:
        app.logger.error(f"Translation error: {str(e)}")
        return jsonify({'success': False, 'message': f"Translation error: {str(e)}"}), 500

@app.route('/save_speech_transcript', methods=['POST'])
def save_speech_transcript():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    data = request.get_json()
    transcript = data.get('transcript')
    language = data.get('language')

    if not transcript or not language:
        return jsonify({'success': False, 'message': 'Missing transcript or language'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO transcripts (user_id, transcript, source, language) VALUES (?, ?, ?, ?)', 
                       (session['user_id'], transcript, 'speech', language))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Speech transcript saved successfully'})
    except Exception as e:
        app.logger.error(f"Error saving speech transcript: {str(e)}")
        return jsonify({'success': False, 'message': f"Error saving speech transcript: {str(e)}"}), 500

if __name__ == '__main__':
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
    init_db()
    add_missing_columns()
    app.run(debug=True)