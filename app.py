from flask import Flask, render_template, request, jsonify, abort, Response, session, redirect, url_for
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bleach
import os
import datetime
import json
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
import requests
import re
import dermatologist_logic as derma_logic
import ent_logic as ent_logic_module
import psych_logic as psych_logic_module
import general_logic as general_logic_module
import pharmacy_logic as pharmacy_logic_module
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-ai-hospital-dev-key-2026')

# Initialize Security Extensions
csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

DERMA_UPLOAD_FOLDER = 'static/dermatalogist_upload'
ENT_UPLOAD_FOLDER = 'static/ent_upload'
PSYCH_UPLOAD_FOLDER = 'static/psych_upload'
GENERAL_UPLOAD_FOLDER = 'static/general_upload'
PHARMACY_UPLOAD_FOLDER = 'static/pharmacy_upload'

for folder in [DERMA_UPLOAD_FOLDER, ENT_UPLOAD_FOLDER, PSYCH_UPLOAD_FOLDER, GENERAL_UPLOAD_FOLDER, PHARMACY_UPLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff', 'tif', 'heic', 'svg', 'ico', 'jfif', 'avif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# OAuth Configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def get_user_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    # Migration: Add full_name and profile_pic if they don't exist
    try:
        c = conn.cursor()
        c.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        c.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass # Columns already exist
    return conn

# ===== MOCK DATA =====
# ... (DOCTORS dict and QUICK_SUGGESTIONS list remain same) ...
# (skipping for brevity in the tool call but I'll make sure they are preserved in the actual replacement)

DOCTORS = {
    'derma': {
        'id': 'derma',
        'name': 'Dr.Zavian',
        'title': 'AI Dermatologist',
        'subtitle': 'Dermatology AI',
        'specialty': 'Skin & Aesthetic Health',
        'description': 'AI-powered skin analysis for acne, rashes, and suspicious lesions with high-precision imaging.',
        'image': 'static/dr_salman.png',
        'credentials': 'Powered by DermaScan AI Analysis',
        'capabilities': [
            'Skin Condition Mapping',
            'Acne & Rash Diagnosis',
            'Lesion Assessment',
            'Suncare Recommendations'
        ]
    },
    'ent': {
        'id': 'ent',
        'name': 'Dr. Anees',
        'title': 'AI ENT Specialist',
        'subtitle': 'ENT Specialist',
        'specialty': 'Ear, Nose & Throat Care',
        'description': 'Advanced AI for analyzing sinus issues, hearing health, and throat conditions with precision diagnostics.',
        'image': 'static/images/ent2.png',
        'credentials': 'Powered by Advanced Otolaryngology AI',
        'capabilities': [
            'Sinus Analysis',
            'Hearing Health',
            'Throat Assessment',
            'Allergy Management'
        ]
    },
    'psych': {
        'id': 'psych',
        'name': 'Dr. Aria',
        'title': 'AI Psychiatrist',
        'subtitle': 'Mental Health AI',
        'specialty': 'Mental & Behavioral Health',
        'description': 'Compassionate AI for mental health support, behavioral patterns analysis, and cognitive therapy guidance.',
        'image': 'static/images/phys_doctor.jpg',
        'credentials': 'Powered by Cognitive Behavioral AI',
        'capabilities': [
            'Behavioral Analysis',
            'Cognitive Support',
            'Mood Tracking',
            'Stress Management'
        ]
    },
    'general': {
        'id': 'general',
        'name': 'Dr. Alara',
        'title': 'General Physician',
        'subtitle': 'Primary Care & Referrals',
        'specialty': 'Family & General Medicine',
        'description': 'Your first point of contact for health assessments, basic treatments, and guidance to the right specialist.',
        'image': 'static/images/gn.webp',
        'credentials': 'MD, Board Certified in Family Medicine',
        'capabilities': [
            'Health Screening',
            'Basic Treatment',
            'Specialist Referrals',
            'Preventative Care'
        ]
    },
    'pharmacy': {
        'id': 'pharmacy',
        'name': 'Dr. Pharma',
        'title': 'AI Pharmacist',
        'subtitle': 'Medication & Interaction AI',
        'specialty': 'Pharmacology & Toxicology',
        'description': 'Advanced AI for medication verification, dosage optimization, and interaction analysis with multi-layered RAG validation.',
        'image': 'static/images/phrama.png',
        'credentials': 'Powered by Pharmaceutical RAG Intelligence',
        'capabilities': [
            'Drug Interaction Check',
            'Dosage Optimization',
            'Side Effect Profiling',
            'Clinical Validation'
        ]
    }
}



QUICK_SUGGESTIONS = [
    "Evaluate my symptoms",
    "Interpret my test results",
    "Lifestyle recommendations",
    "Explain this condition",
    "Medication interactions"
]

# ===== ROUTES =====

@app.route('/')
def index():
    """Dashboard/Home page"""
    return render_template('index.html', doctors=DOCTORS)

@app.route('/specialists')
def specialists():
    """AI Specialists overview page"""
    return render_template('specialists.html', doctors=DOCTORS)


# --- AUTH ROUTES ---

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def signup():
    if request.method == 'POST':
        # Sanitize and lowercase input
        username = bleach.clean(request.form.get('username', '')).strip().lower()
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('signup.html', error="Missing username or password")
            
        # Validate email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', username):
            return render_template('signup.html', error="Invalid email format.")
            
        # Validate password strength
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password) or not re.search(r'[@$!%*?&]', password):
            return render_template('signup.html', error="Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character (@$!%*?&).")
            
        conn = get_user_db_connection()
        c = conn.cursor()
        
        # Check if user already exists
        user = c.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            conn.close()
            return render_template('signup.html', error="This email/username is already registered. Please Login instead.")

        try:
            hashed_password = generate_password_hash(password)
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error="Registration failed. This account may already exist.")
        finally:
            conn.close()
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        # Sanitize and lowercase input
        username = bleach.clean(request.form.get('username', '')).strip().lower()
        password = request.form.get('password')
        
        # Validate email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', username):
            return render_template('login.html', error="Invalid email format.")
        
        conn = get_user_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name'] or user['username'].split('@')[0]
            session['profile_pic'] = user['profile_pic']
            return redirect(url_for('index'))
            
        return render_template('login.html', error="Invalid username or password")
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri, prompt='select_account')

@app.route('/auth/callback')
def google_auth():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        # Fallback to manual fetch if userinfo isn't in token
        resp = google.get('userinfo')
        user_info = resp.json()
    
    email = user_info['email'].lower()
    # If Google name is missing, use the part before @ as full_name
    full_name = user_info.get('name') or email.split('@')[0]
    profile_pic = user_info.get('picture')
    
    conn = get_user_db_connection()
    c = conn.cursor()
    user = c.execute('SELECT * FROM users WHERE username = ?', (email,)).fetchone()
    
    if not user:
        # Create user if it doesn't exist
        c.execute("INSERT INTO users (username, password_hash, full_name, profile_pic) VALUES (?, ?, ?, ?)", 
                  (email, generate_password_hash(os.urandom(24).hex()), full_name, profile_pic))
        conn.commit()
        user = c.execute('SELECT * FROM users WHERE username = ?', (email,)).fetchone()
    else:
        # Update existing user info from Google
        c.execute("UPDATE users SET full_name = ?, profile_pic = ? WHERE id = ?", (full_name, profile_pic, user['id']))
        conn.commit()
        user = c.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
    
    conn.close()
    
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['full_name'] = user['full_name']
    session['profile_pic'] = user['profile_pic']
    return redirect(url_for('index'))

# --- CONSULTATION ROUTES ---

@app.route('/specialists/derma/consult')
@login_required
def derma_consult():
    """Renders the advanced dermatologist interface."""
    return render_template('dermatalogist.html', 
                          username=session['username'],
                          full_name=session.get('full_name'),
                          profile_pic=session.get('profile_pic'))

@app.route('/specialists/ent/consult')
@login_required
def ent_consult():
    """Renders the advanced ENT specialist interface."""
    return render_template('ent.html', 
                          username=session['username'],
                          full_name=session.get('full_name'),
                          profile_pic=session.get('profile_pic'))

@app.route('/specialists/psych/consult')
@login_required
def psych_consult():
    """Renders the advanced psychiatric interface."""
    return render_template('psych.html', 
                          username=session['username'],
                          full_name=session.get('full_name'),
                          profile_pic=session.get('profile_pic'))

@app.route('/specialists/general/consult')
@app.route('/consultation')
@login_required
def general_consult():
    """Dr. Alara — Family & General Medicine (Under Development)"""
    return render_template('under_development_general.html')

@app.route('/specialists/pharmacy/consult')
@login_required
def pharmacy_consult():
    """Dr. Pharma AI Pharmacist - Live Consultation."""
    return render_template('pharmacy.html',
                          username=session['username'],
                          full_name=session.get('full_name'),
                          profile_pic=session.get('profile_pic'))
@app.route('/threads', methods=['GET'])
@login_required
def get_threads():
    """Return list of conversations filtered by specialist and user."""
    specialist = request.args.get('specialist', 'derma')
    user_id = session.get('user_id')
    
    if specialist == 'ent':
        current_logic = ent_logic_module
    elif specialist == 'psych':
        current_logic = psych_logic_module
    elif specialist == 'general':
        current_logic = general_logic_module
    elif specialist == 'pharmacy':
        current_logic = pharmacy_logic_module
    else:
        current_logic = derma_logic
    
    db_path = current_logic.DB_NAME
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # 1. Ensure table exists FIRST
        c.execute("""CREATE TABLE IF NOT EXISTS conversations 
                     (thread_id TEXT PRIMARY KEY, title TEXT, created_at DATETIME, specialist TEXT, user_id INTEGER)""")
        
        # 2. Migration: Add missing columns if they don't exist
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN specialist TEXT DEFAULT 'derma'")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        conn.commit()
        
        # 3. Query filtered threads
        c.execute("SELECT thread_id, title, created_at FROM conversations WHERE specialist = ? AND user_id = ? ORDER BY created_at DESC", 
                  (specialist, user_id))
        threads = [{"thread_id": r[0], "title": r[1], "date": r[2]} for r in c.fetchall()]
        conn.close()
        return jsonify(threads)
        
    except Exception as e:
        print(f"Error fetching threads for {specialist}: {e}")
        return jsonify({"error": "Failed to load conversations", "details": str(e)}), 500

@app.route('/history/<thread_id>', methods=['GET'])
@login_required
def get_history(thread_id):
    """Reconstruct history for a thread."""
    user_id = session.get('user_id')
    specialist = request.args.get('specialist', 'derma')
    
    # Prefix thread_id for isolation
    thread_id = f"user_{user_id}_{thread_id}"
    
    if specialist == 'ent':
        current_logic = ent_logic_module
        upload_path = "/static/ent_upload/"
    elif specialist == 'psych':
        current_logic = psych_logic_module
        upload_path = "/static/psych_upload/"
    elif specialist == 'general':
        current_logic = general_logic_module
        upload_path = "/static/general_upload/"
    elif specialist == 'pharmacy':
        current_logic = pharmacy_logic_module
        upload_path = "/static/pharmacy_upload/"
    else:
        current_logic = derma_logic
        upload_path = "/static/dermatalogist_upload/"
    
    # Reuse the module-level compiled graph so we read from the same
    # checkpointer that was used during chat (fixes empty history bug).
    app_graph = current_logic.chatbot_compiled
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = app_graph.get_state(config)
        if not snapshot.values:
            return jsonify({"messages": []})
        messages = snapshot.values.get("messages", [])
        history = []
        for idx, msg in enumerate(messages):
            role = "user"
            if isinstance(msg, AIMessage):
                role = "ai"
            elif isinstance(msg, ToolMessage):
                if msg.name in ["generate_medical_report", "generate_pharmacy_report"]:
                    role = "ai"
                else: continue
            elif isinstance(msg, SystemMessage): continue
            content = msg.content
            if isinstance(content, list):
                content = " ".join([c.get('text', '') if isinstance(c, dict) else str(c) for c in content])
            
            # Image Path Extraction
            if role == "user" and "[System Alert: User uploaded an image. Local Path:" in content:
                import re
                match = re.search(r'\[System Alert: User uploaded an image\. Local Path: (.*?)\] (.*)', content)
                if match:
                    filename = os.path.basename(match.group(1))
                    content = {"text": match.group(2), "image": f"{upload_path}{filename}"}

            history.append({"role": role, "content": content, "index": idx})
        return jsonify({"messages": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/edit', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def edit_message():
    """Handle editing of a previous user message."""
    data = request.json
    thread_id = data.get('thread_id')
    message_index = data.get('index')  # Index in the total message history
    raw_text = data.get('new_text', '')
    new_text = bleach.clean(raw_text) if raw_text else None
    specialist = data.get('specialist', 'derma')
    user_id = session.get('user_id')
    
    # Prefix thread_id for isolation
    thread_id = f"user_{user_id}_{thread_id}"
    
    if not thread_id or message_index is None or new_text is None:
        return jsonify({"error": "Missing parameters"}), 400

    if specialist == 'ent':
        current_logic = ent_logic_module
    elif specialist == 'psych':
        current_logic = psych_logic_module
    elif specialist == 'general':
        current_logic = general_logic_module
    else:
        current_logic = derma_logic
    
    # Reuse the module-level compiled graph for the same checkpointer used during chat.
    app_graph = current_logic.chatbot_compiled
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        snapshot = app_graph.get_state(config)
        if not snapshot.values:
            return jsonify({"error": "Thread not found"}), 404
        
        messages = snapshot.values.get("messages", [])
        
        new_history = messages[:message_index] 
        
        # Update state with truncated history
        app_graph.update_state(config, {"messages": new_history}, as_node="chat_node")
        
        # Re-run chat logic with the new message
        def generate():
            try:
                old_msg = messages[message_index]
                image_path_match = None
                if isinstance(old_msg, HumanMessage):
                     import re
                     match = re.search(r'\[System Alert: User uploaded an image\. Local Path: (.*?)\]', old_msg.content)
                     if match:
                         image_path_match = match.group(0)

                final_content = new_text
                if image_path_match:
                    final_content = f"{image_path_match} {new_text}"

                for chunk in app_graph.stream(
                    {"messages": [HumanMessage(content=final_content)]},
                    config=config,
                    stream_mode="messages"
                ):
                    messages_chunk = chunk if isinstance(chunk, (list, tuple)) else [chunk]
                    for message in messages_chunk:
                        if isinstance(message, AIMessage) and message.tool_calls:
                            for tool_call in message.tool_calls:
                                yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': tool_call.get('name'), 'args': tool_call.get('args'), 'tool_call_id': tool_call.get('id')})}\n\n"
                        if isinstance(message, ToolMessage):
                            yield f"data: {json.dumps({'type': 'tool_end', 'tool_name': message.name, 'output': message.content, 'tool_call_id': message.tool_call_id})}\n\n"
                            if message.name in ["generate_medical_report", "generate_pharmacy_report"]:
                                 yield f"data: {json.dumps({'type': 'token', 'content': message.content})}\n\n"
                        if isinstance(message, AIMessage) and message.content:
                            content = message.content
                            if isinstance(content, list):
                                content = " ".join([c.get('text', '') if isinstance(c, dict) else str(c) for c in content])
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def chat():
    user_id = session.get('user_id')
    if request.is_json:
        data = request.json
        user_input = bleach.clean(data.get('message', ''))
        thread_id = data.get('thread_id')
        specialist = data.get('specialist', 'derma')
        image_url = None
    else:
        user_input = bleach.clean(request.form.get('message', ''))
        thread_id = request.form.get('thread_id')
        specialist = request.form.get('specialist', 'derma')
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Use thread_id for filename before prefixing if we want original thread_id in name, 
                # but prefixing it first is safer for isolation.
                temp_thread_id = f"user_{user_id}_{thread_id}"
                filename = secure_filename(f"{temp_thread_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                
                if specialist == 'ent': upload_folder = ENT_UPLOAD_FOLDER
                elif specialist == 'psych': upload_folder = PSYCH_UPLOAD_FOLDER
                elif specialist == 'general': upload_folder = GENERAL_UPLOAD_FOLDER
                elif specialist == 'pharmacy': upload_folder = PHARMACY_UPLOAD_FOLDER
                else: upload_folder = DERMA_UPLOAD_FOLDER
                
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                if specialist == 'ent': image_url = f"/static/ent_upload/{filename}"
                elif specialist == 'psych': image_url = f"/static/psych_upload/{filename}"
                elif specialist == 'general': image_url = f"/static/general_upload/{filename}"
                elif specialist == 'pharmacy': image_url = f"/static/pharmacy_upload/{filename}"
                else: image_url = f"/static/dermatalogist_upload/{filename}"
    
    # Prefix thread_id for absolute isolation
    original_thread_id = thread_id
    thread_id = f"user_{user_id}_{thread_id}"
    
    if not user_input and not image_url:
        return jsonify({"error": "No input provided"}), 400
    
    try:
        if specialist == 'ent':
            current_logic = ent_logic_module
        elif specialist == 'psych':
            current_logic = psych_logic_module
        elif specialist == 'general':
            current_logic = general_logic_module
        elif specialist == 'pharmacy':
            current_logic = pharmacy_logic_module
        else:
            current_logic = derma_logic
        
        db_path = current_logic.DB_NAME
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS conversations 
                     (thread_id TEXT PRIMARY KEY, title TEXT, created_at DATETIME, specialist TEXT, user_id INTEGER)""")
        # Migration
        for col, col_type in [('specialist', 'TEXT DEFAULT "derma"'), ('user_id', 'INTEGER')]:
            try: c.execute(f"ALTER TABLE conversations ADD COLUMN {col} {col_type}")
            except: pass
        conn.commit()
        c.execute("SELECT thread_id FROM conversations WHERE thread_id = ?", (original_thread_id,))
        if not c.fetchone():
            title = " ".join(user_input.split()[:4]) + "..." if user_input else "New Chat"
            c.execute("INSERT INTO conversations (thread_id, title, created_at, specialist, user_id) VALUES (?, ?, ?, ?, ?)", 
                      (original_thread_id, title, datetime.datetime.now(), specialist, user_id))
            conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    def generate():
        try:
            chatbot_compiled = current_logic.chatbot_compiled
            
            message_content = user_input or ""
            if image_url:
                local_path = os.path.abspath(os.path.join(app.root_path, image_url.lstrip('/'))).replace('\\', '/')
                message_content = f"[System Alert: User uploaded an image. Local Path: {local_path}] {message_content}"

            for chunk in chatbot_compiled.stream(
                {"messages": [HumanMessage(content=message_content)]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="messages"
            ):
                messages_chunk = chunk if isinstance(chunk, (list, tuple)) else [chunk]
                for message in messages_chunk:
                    if isinstance(message, AIMessage) and message.tool_calls:
                        for tool_call in message.tool_calls:
                            yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': tool_call.get('name'), 'args': tool_call.get('args'), 'tool_call_id': tool_call.get('id')})}\n\n"
                    if isinstance(message, ToolMessage):
                        yield f"data: {json.dumps({'type': 'tool_end', 'tool_name': message.name, 'output': message.content, 'tool_call_id': message.tool_call_id})}\n\n"
                        if message.name in ["generate_medical_report", "generate_pharmacy_report"]:
                             yield f"data: {json.dumps({'type': 'token', 'content': message.content})}\n\n"
                    if isinstance(message, AIMessage) and message.content:
                        content = message.content
                        if isinstance(content, list):
                            content = " ".join([c.get('text', '') if isinstance(c, dict) else str(c) for c in content])
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# ===== MAIN =====

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
