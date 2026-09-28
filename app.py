import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime

import certifi

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')  # Replace with a secure secret in production

# MongoDB setup
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client['resume_builder']
users_col = db['users']

# Seed admin user if not exists
ADMIN_EMAILS = {'admin@resumemaker.com', 'admin@resumate.com'}
try:
    admin_user = users_col.find_one({'email': {'$in': list(ADMIN_EMAILS)}})
    if not admin_user:
        users_col.insert_one({
            'username': 'Admin',
            'email': 'admin@resumemaker.com',
            'password': generate_password_hash('admin123')
        })
except Exception as exc:
    print(f"[warn] Skipping admin seed - database unreachable: {exc}")

# Upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/auth')
def auth():
    form = request.args.get('form', 'signin')
    return render_template('auth.html', form=form)


@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    confirm = request.form['confirm_password']

    if password != confirm:
        return "Passwords do not match"

    existing_user = users_col.find_one({'email': email})
    if existing_user:
        return "Email already exists"

    hashed_pw = generate_password_hash(password)
    users_col.insert_one({'username': username, 'email': email, 'password': hashed_pw})

    session['user'] = {'username': username, 'email': email}
    return redirect(url_for('home'))


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = users_col.find_one({'email': email})
    if user and check_password_hash(user['password'], password):
        session['user'] = {'username': user['username'], 'email': user['email']}
        return redirect(url_for('home'))
    else:
        return "Invalid credentials"


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('auth') + '?form=signin')

    user = users_col.find_one({'email': session['user']['email']})
    if not user:
        return "User not found", 404

    user['_id'] = str(user['_id'])
    
    # Retrieve and pop message from session
    msg = session.pop('profile_msg', None)
    return render_template('profile.html', user=user, msg=msg)


@app.route('/profile/update', methods=['POST'])
def profile_update():
    if 'user' not in session:
        return redirect(url_for('auth') + '?form=signin')

    current_email = session['user']['email']
    user = users_col.find_one({'email': current_email})
    if not user:
        return "User not found", 404

    new_username = request.form.get('username', '').strip()
    new_email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not new_username or not new_email:
        session['profile_msg'] = {'type': 'error', 'text': 'Username and email are required.'}
        return redirect(url_for('profile'))

    # Check if new email is in use by someone else
    if new_email != current_email:
        existing = users_col.find_one({'email': new_email})
        if existing:
            session['profile_msg'] = {'type': 'error', 'text': 'Email address is already in use.'}
            return redirect(url_for('profile'))

    update_data = {
        'username': new_username,
        'email': new_email
    }

    if password:
        if password != confirm_password:
            session['profile_msg'] = {'type': 'error', 'text': 'Passwords do not match.'}
            return redirect(url_for('profile'))
        update_data['password'] = generate_password_hash(password)

    # Update DB
    users_col.update_one({'_id': user['_id']}, {'$set': update_data})

    # Update drafts & resumes user_email if email changed
    if new_email != current_email:
        db.drafts.update_many({'user_email': current_email}, {'$set': {'user_email': new_email}})
        db.resumes.update_many({'user_email': current_email}, {'$set': {'user_email': new_email}})

    # Update session
    session['user'] = {'username': new_username, 'email': new_email}
    session['profile_msg'] = {'type': 'success', 'text': 'Profile updated successfully!'}

    return redirect(url_for('profile'))


# ─── Admin Dashboard ──────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        return "Access Denied: Admin privileges required.", 403

    # Statistics
    total_users = users_col.count_documents({})
    total_resumes = db.resumes.count_documents({})
    
    # Template breakdown
    templates = ['modern', 'minimal', 'creative', 'developer', 'startup', 'executive', 'academic']
    template_counts = {t: db.resumes.count_documents({'template': t}) for t in templates}

    # Fetch users and their resume counts
    users_raw = list(users_col.find())
    users = []
    for u in users_raw:
        u_id_str = str(u['_id'])
        resume_count = db.resumes.count_documents({'user_email': u['email']})
        users.append({
            '_id': u_id_str,
            'username': u.get('username', 'N/A'),
            'email': u.get('email', 'N/A'),
            'resumes_count': resume_count
        })

    # Fetch all resumes
    resumes_raw = list(db.resumes.find().sort('created_at', -1))
    resumes = []
    for r in resumes_raw:
        resumes.append({
            '_id': str(r['_id']),
            'resume_name': r.get('resume_name', ''),
            'name': r.get('name', 'Untitled'),
            'user_email': r.get('user_email', 'N/A'),
            'template': r.get('template', 'modern'),
            'created_at': r.get('created_at').strftime('%Y-%m-%d %H:%M') if r.get('created_at') else 'N/A',
            'created_at_iso': r.get('created_at').isoformat() if r.get('created_at') else ''
        })

    msg = session.pop('admin_msg', None)
    return render_template('admin.html', 
                           total_users=total_users, 
                           total_resumes=total_resumes,
                           template_counts=template_counts,
                           users=users,
                           resumes=resumes,
                           msg=msg)


@app.route('/admin/user/<user_id>/delete', methods=['POST'])
def admin_delete_user(user_id):
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        return "Access Denied", 403

    user = users_col.find_one({'_id': ObjectId(user_id)})
    if not user:
        session['admin_msg'] = {'type': 'error', 'text': 'User not found.'}
        return redirect(url_for('admin_dashboard'))

    # Delete user, drafts and resumes
    users_col.delete_one({'_id': ObjectId(user_id)})
    db.resumes.delete_many({'user_email': user['email']})
    db.drafts.delete_many({'user_email': user['email']})

    session['admin_msg'] = {'type': 'success', 'text': f"User {user['username']} and all associated resumes/drafts deleted successfully."}
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/resume/<resume_id>/delete', methods=['POST'])
def admin_delete_resume(resume_id):
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        return "Access Denied", 403

    db.resumes.delete_one({'_id': ObjectId(resume_id)})
    session['admin_msg'] = {'type': 'success', 'text': 'Resume deleted successfully.'}
    return redirect(url_for('admin_dashboard'))


@app.route('/resume/new')
def new_resume():
    if 'user' not in session:
        return redirect(url_for('auth') + '?form=signin')
    
    # Clear draft to start fresh
    db.drafts.delete_one({'user_email': session['user']['email']})
    
    # Initialize draft with the given resume name
    resume_name = request.args.get('name', 'My Resume').strip()
    if not resume_name:
        resume_name = 'My Resume'
        
    db.drafts.insert_one({
        'user_email': session['user']['email'],
        'data': {
            'resume_name': resume_name
        },
        'updated_at': datetime.utcnow()
    })
    return redirect(url_for('dashboard'))


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('auth') + '?form=signin')

    # Load draft if exists
    draft = db.drafts.find_one({'user_email': session['user']['email']})
    return render_template('dashboard.html', draft=draft)


# ─── Auto-save Draft ──────────────────────────────────────────────────────────

@app.route('/autosave', methods=['POST'])
def autosave():
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data'}), 400

    db.drafts.update_one(
        {'user_email': session['user']['email']},
        {'$set': {
            'data': data,
            'resume_id': data.get('resume_id', ''),
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )
    return jsonify({'status': 'ok', 'saved_at': datetime.utcnow().isoformat()})


# ─── Profile Photo Upload ─────────────────────────────────────────────────────

@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    if 'user' not in session:
        return jsonify({'status': 'error'}), 401

    if 'photo' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file'}), 400

    file = request.files['photo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    photo_url = url_for('static', filename=f'uploads/{filename}')
    return jsonify({'status': 'ok', 'url': photo_url})


# ─── AI Summary ───────────────────────────────────────────────────────────────

@app.route('/ai-summary', methods=['POST'])
def ai_summary():
    if 'user' not in session:
        return jsonify({'status': 'error'}), 401

    data = request.get_json()
    name = data.get('name', '')
    role = data.get('role', '')
    skills = data.get('skills', '')
    experience = data.get('experience', '')

    try:
        from google import genai
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            return jsonify({'status': 'error', 'message': 'GEMINI_API_KEY not set'}), 500

        client = genai.Client(api_key=api_key)

        prompt = f"""Write a concise, powerful professional summary for a resume.
Name: {name}
Role/Title: {role}
Key Skills: {skills}
Experience: {experience}

Write 2-3 sentences. Be specific, impactful, and professional. Do NOT use first-person pronouns.
Return ONLY the summary text, nothing else."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        summary = response.text.strip()
        return jsonify({'status': 'ok', 'summary': summary})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─── ATS Score ────────────────────────────────────────────────────────────────

@app.route('/ats-score', methods=['POST'])
def ats_score():
    if 'user' not in session:
        return jsonify({'status': 'error'}), 401

    data = request.get_json()
    job_description = data.get('job_description', '')
    if not job_description.strip():
        return jsonify({'status': 'error', 'message': 'Job description is required.'}), 400

    resume_text = ' '.join([
        f"Name: {data.get('name', '')}",
        f"Summary: {data.get('summary', '')}",
        f"Skills: {data.get('skills', '')}",
        f"Work Experience: {data.get('experience', '')}",
        f"Education: {data.get('education', '')}"
    ])

    try:
        from google import genai
        from google.genai import types
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            return jsonify({'status': 'error', 'message': 'GEMINI_API_KEY not set on server.'}), 500

        client = genai.Client(api_key=api_key)

        prompt = f"""
        Analyze the following resume details against the target job description.
        
        Resume details:
        {resume_text}
        
        Target Job Description:
        {job_description}
        
        Provide a professional applicant tracking system (ATS) alignment analysis.
        You must return a JSON object with the following keys:
        - "score": integer from 0 to 100 representing how well the resume matches the job description.
        - "grade": a string rating ("Excellent" for score >= 75, "Good" for 50-74, "Fair" for 25-49, "Needs Work" for < 25).
        - "color": a hex code color for the rating ("#10b981" for Excellent, "#f59e0b" for Good, "#f97316" for Fair, "#ef4444" for Needs Work).
        - "found": a list of matched keywords, skills, or experiences found in the resume that align with the job description.
        - "missing": a list of important keywords, skills, or requirements mentioned in the job description but missing from the resume.
        - "feedback": 1-2 sentences of actionable advice to improve the match.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text.strip())
        return jsonify({
            'status': 'ok',
            'score': result.get('score', 0),
            'grade': result.get('grade', 'Needs Work'),
            'color': result.get('color', '#ef4444'),
            'found': result.get('found', []),
            'missing': result.get('missing', []),
            'feedback': result.get('feedback', '')
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─── Save Resume ──────────────────────────────────────────────────────────────

def parse_dynamic_section(form, prefix):
    """Parse indexed form fields like prefix[0][field] into a list of dicts."""
    result = []
    for key in form:
        if key.startswith(prefix + '['):
            parts = key.split('[')
            try:
                index = int(parts[1][:-1])
                field = parts[2][:-1]
                while len(result) <= index:
                    result.append({})
                result[index][field] = form[key][0]
            except (IndexError, ValueError):
                continue
    return result


@app.route('/save_resume', methods=['POST'])
def save_resume():
    if 'user' not in session:
        return redirect(url_for('auth') + '?form=signin')

    form = request.form.to_dict(flat=False)
    resume_id = form.get('resume_id', [''])[0]

    resume_data = {
        'user_email': session['user']['email'],
        'template': form.get('template', ['minimal'])[0],
        'photo': form.get('photo_url', [''])[0],
        'resume_name': form.get('resume_name', ['My Resume'])[0],
        'name': form.get('name', [''])[0],
        'email': form.get('email', [''])[0],
        'phone': form.get('phone', [''])[0],
        'location': form.get('location', [''])[0],
        'summary': form.get('summary', [''])[0],
        # Social
        'website': form.get('website', [''])[0],
        'github': form.get('github', [''])[0],
        'linkedin': form.get('linkedin', [''])[0],
        'twitter': form.get('twitter', [''])[0],
        'behance': form.get('behance', [''])[0],
        'dribbble': form.get('dribbble', [''])[0],
        # Skills
        'skills': [s.strip() for s in form.get('skills', [''])[0].split(',') if s.strip()],
        'skills_technical': form.get('skills_technical', [''])[0],
        'skills_soft': form.get('skills_soft', [''])[0],
        'skills_tools': form.get('skills_tools', [''])[0],
        # Dynamic sections
        'education':       parse_dynamic_section(form, 'education'),
        'experience':      parse_dynamic_section(form, 'experience'),
        'projects':        parse_dynamic_section(form, 'projects'),
        'languages':       parse_dynamic_section(form, 'languages'),
        'awards':          parse_dynamic_section(form, 'awards'),
        'certifications':  parse_dynamic_section(form, 'certifications'),
        'publications':    parse_dynamic_section(form, 'publications'),
        'volunteering':    parse_dynamic_section(form, 'volunteering'),
        'competitions':    parse_dynamic_section(form, 'competitions'),
        'conferences':     parse_dynamic_section(form, 'conferences'),
        'testscores':      parse_dynamic_section(form, 'testscores'),
        'patents':         parse_dynamic_section(form, 'patents'),
        'scholarships':    parse_dynamic_section(form, 'scholarships'),
        'extracurricular': parse_dynamic_section(form, 'extracurricular'),
        'created_at': datetime.utcnow(),
    }

    # Parse custom sections (list of {title, content})
    custom_sections = []
    i = 0
    while f'custom_section[{i}][title]' in request.form:
        custom_sections.append({
            'title': request.form.get(f'custom_section[{i}][title]', ''),
            'content': request.form.get(f'custom_section[{i}][content]', ''),
        })
        i += 1
    resume_data['custom_sections'] = custom_sections

    if resume_id:
        db.resumes.update_one(
            {'_id': ObjectId(resume_id), 'user_email': session['user']['email']},
            {'$set': resume_data}
        )
    else:
        result = db.resumes.insert_one(resume_data)
        resume_id = str(result.inserted_id)

    # Clear draft after saving
    db.drafts.delete_one({'user_email': session['user']['email']})

    return redirect(url_for('view_resume', resume_id=resume_id))


# ─── View Resume ──────────────────────────────────────────────────────────────

@app.route('/resume/<resume_id>')
def view_resume(resume_id):
    try:
        resume = db.resumes.find_one({'_id': ObjectId(resume_id)})
    except Exception:
        return "Invalid resume ID", 400
    if not resume:
        return "Resume not found", 404
    resume['_id'] = str(resume['_id'])
    
    # Allow overriding template via URL parameter for preview
    tpl = request.args.get('tpl')
    if tpl in ['modern', 'minimal', 'creative', 'developer', 'startup', 'executive', 'academic']:
        resume['template'] = tpl
        
    return render_template('resume.html', resume=resume)


# ─── Edit Resume ──────────────────────────────────────────────────────────────

@app.route('/resume/<resume_id>/edit')
def edit_resume(resume_id):
    if 'user' not in session:
        return redirect(url_for('auth') + '?form=signin')

    try:
        resume = db.resumes.find_one({'_id': ObjectId(resume_id), 'user_email': session['user']['email']})
    except Exception:
        return "Invalid resume ID", 400
        
    if not resume:
        return "Resume not found", 404
        
    # Exclude _id to store in draft
    resume.pop('_id', None)
    
    # Save as draft
    db.drafts.update_one(
        {'user_email': session['user']['email']},
        {'$set': {
            'data': resume,
            'resume_id': str(resume_id),
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )
    
    return redirect(url_for('dashboard'))


# ─── My Resumes ───────────────────────────────────────────────────────────────

@app.route('/my-resumes')
def my_resumes():
    if not session.get('user'):
        return redirect(url_for('auth') + '?form=signin')

    resumes = list(db.resumes.find(
        {'user_email': session['user']['email']},
        {'resume_name': 1, 'name': 1, 'template': 1, 'created_at': 1, 'skills': 1, 'summary': 1}
    ).sort('created_at', -1))

    for r in resumes:
        r['_id'] = str(r['_id'])

    return render_template('my_resumes.html', resumes=resumes)


# ─── Delete Resume ────────────────────────────────────────────────────────────

@app.route('/resume/<resume_id>/delete', methods=['POST'])
def delete_resume(resume_id):
    if 'user' not in session:
        return jsonify({'status': 'error'}), 401
    try:
        db.resumes.delete_one({
            '_id': ObjectId(resume_id),
            'user_email': session['user']['email']
        })
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug)