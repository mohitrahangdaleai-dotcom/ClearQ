from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
import bcrypt
import json
import os
from config import Config

from utils.ai_processor import extract_resume_data, calculate_job_match, calculate_all_matches
from utils.resume_parser import parse_resume, allowed_file
from utils.matcher import get_user_matches, get_user_match_stats, get_missing_skills_analysis, update_all_user_matches

app = Flask(__name__)
app.config.from_object(Config)

# Database configuration - SQLite for development, MySQL for production
if os.environ.get('HOSTINGER_ENV') == 'production':
    # Production - Use Hostinger MySQL with mysql-connector-python
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{os.environ.get('MYSQL_USER')}:{os.environ.get('MYSQL_PASSWORD')}@{os.environ.get('MYSQL_HOST')}/{os.environ.get('MYSQL_DB')}"
    print("✅ Using MySQL database (Production)")
else:
    # Development - Use SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'job_matching.db')
    print("✅ Using SQLite database (Development)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)
    preferred_location = db.Column(db.String(255))
    expected_salary = db.Column(db.String(100))
    resume_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    required_skills = db.Column(db.Text)
    experience_required = db.Column(db.String(100))
    location = db.Column(db.String(255))
    salary_range = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class JobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    match_percentage = db.Column(db.Float)
    matched_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    fit_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create tables
with app.app_context():
    try:
        db.create_all()
        
        # Add sample jobs if none exist
        if db.session.query(Job).count() == 0:
            sample_jobs = [
                Job(
                    title='Python Developer',
                    company='Tech Solutions Inc.',
                    description='We are looking for a skilled Python developer with experience in web development and AI applications.',
                    required_skills='["Python", "Flask", "SQL", "REST API", "Git"]',
                    experience_required='2-4 years',
                    location='Remote',
                    salary_range='$60,000 - $90,000'
                ),
                Job(
                    title='Frontend Developer',
                    company='Web Innovations LLC',
                    description='Join our frontend team to build modern, responsive web applications using React and TypeScript.',
                    required_skills='["JavaScript", "React", "TypeScript", "CSS", "HTML5"]',
                    experience_required='1-3 years',
                    location='New York, NY',
                    salary_range='$70,000 - $100,000'
                ),
                Job(
                    title='Data Scientist',
                    company='Data Analytics Corp',
                    description='Seeking data scientist with machine learning experience to analyze large datasets and build predictive models.',
                    required_skills='["Python", "Machine Learning", "SQL", "Pandas", "Statistics"]',
                    experience_required='3-5 years',
                    location='San Francisco, CA',
                    salary_range='$90,000 - $120,000'
                )
            ]
            db.session.bulk_save_objects(sample_jobs)
            db.session.commit()
            print("✅ Database tables created and sample jobs added!")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Configure Gemini
if app.config.get('GEMINI_API_KEY'):
    try:
        genai.configure(api_key=app.config['GEMINI_API_KEY'])
        print("✅ Gemini AI configured successfully!")
    except Exception as e:
        print(f"❌ Gemini AI configuration error: {e}")

# Custom template filter for JSON parsing
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            name = request.form['name']
            
            # Check if user exists
            existing_user = db.session.query(User).filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please login.', 'error')
                return redirect(url_for('register'))
            
            # Hash password and create user
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            new_user = User(
                email=email, 
                password_hash=hashed_password.decode('utf-8'), 
                name=name
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = db.session.query(User).filter_by(email=email).first()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get job matches
    matches = db.session.query(JobMatch).filter_by(user_id=user_id).order_by(JobMatch.match_percentage.desc()).limit(10).all()
    
    # Convert to list of dicts for template
    matches_list = []
    for match in matches:
        job = db.session.get(Job, match.job_id)
        if job:
            # Parse JSON strings safely
            matched_skills = []
            missing_skills = []
            
            try:
                if match.matched_skills:
                    matched_skills = json.loads(match.matched_skills)
            except (json.JSONDecodeError, TypeError):
                matched_skills = []
            
            try:
                if match.missing_skills:
                    missing_skills = json.loads(match.missing_skills)
            except (json.JSONDecodeError, TypeError):
                missing_skills = []
            
            matches_list.append({
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'location': job.location,
                'salary_range': job.salary_range,
                'match_percentage': match.match_percentage or 0,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'fit_summary': match.fit_summary or "No summary available"
            })
    
    return render_template('dashboard.html', user=user, matches=matches_list)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            user.name = request.form.get('name', '')
            user.phone = request.form.get('phone', '')
            user.skills = request.form.get('skills', '')
            user.experience = request.form.get('experience', '')
            user.education = request.form.get('education', '')
            user.preferred_location = request.form.get('preferred_location', '')
            user.expected_salary = request.form.get('expected_salary', '')
            
            db.session.commit()
            
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
        
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')
            print(f"Profile update error: {e}")
    
    return render_template('profile.html', user=user)

@app.route('/upload-resume', methods=['GET', 'POST'])
def upload_resume():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            if 'resume' not in request.files:
                flash('No file selected.', 'error')
                return redirect(request.url)
            
            file = request.files['resume']
            if file.filename == '':
                flash('No file selected.', 'error')
                return redirect(request.url)
            
            # Check file extension
            if not allowed_file(file.filename):
                flash('Invalid file type. Please upload PDF or DOCX files only.', 'error')
                return redirect(request.url)
            
            # Parse resume text
            resume_text = parse_resume(file)
            
            # Extract data using AI
            extracted_data = extract_resume_data(resume_text)
            
            # Update user profile with extracted data
            user.name = extracted_data.get('name', user.name)
            user.phone = extracted_data.get('phone', user.phone)
            user.skills = json.dumps(extracted_data.get('skills', []))
            user.experience = json.dumps(extracted_data.get('experience', []))
            user.education = json.dumps(extracted_data.get('education', []))
            user.resume_text = resume_text
            
            db.session.commit()
            
            # Calculate matches for all jobs
            calculate_all_matches(user_id)
            
            flash('Resume uploaded and processed successfully! AI has analyzed your skills and found job matches.', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading resume: {str(e)}', 'error')
            print(f"Resume upload error: {e}")
    
    return render_template('upload_resume.html')

@app.route('/jobs')
def jobs():
    try:
        jobs = db.session.query(Job).order_by(Job.created_at.desc()).all()
        
        # Parse required_skills for each job
        jobs_data = []
        for job in jobs:
            try:
                skills = json.loads(job.required_skills) if job.required_skills else []
            except (json.JSONDecodeError, TypeError):
                skills = []
            
            job_dict = {
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'required_skills': skills,
                'experience_required': job.experience_required,
                'location': job.location,
                'salary_range': job.salary_range,
                'created_at': job.created_at
            }
            jobs_data.append(job_dict)
        
        return render_template('jobs.html', jobs=jobs_data)
    
    except Exception as e:
        flash('Error loading jobs.', 'error')
        print(f"Jobs error: {e}")
        return render_template('jobs.html', jobs=[])

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    try:
        job = db.session.get(Job, job_id)
        if not job:
            flash('Job not found.', 'error')
            return redirect(url_for('jobs'))
        
        # Parse required_skills
        try:
            skills = json.loads(job.required_skills) if job.required_skills else []
        except (json.JSONDecodeError, TypeError):
            skills = []
        
        job_data = {
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'required_skills': skills,
            'experience_required': job.experience_required,
            'location': job.location,
            'salary_range': job.salary_range,
            'created_at': job.created_at
        }
        
        return render_template('job_detail.html', job=job_data)
    
    except Exception as e:
        flash('Error loading job details.', 'error')
        print(f"Job detail error: {e}")
        return redirect(url_for('jobs'))

@app.route('/admin')
def admin():
    try:
        jobs = db.session.query(Job).all()
        users = db.session.query(User).all()
        return render_template('admin.html', jobs=jobs, users=users)
    except Exception as e:
        flash('Error loading admin panel.', 'error')
        print(f"Admin error: {e}")
        return render_template('admin.html', jobs=[], users=[])

@app.route('/admin/add-job', methods=['POST'])
def add_job():
    if request.method == 'POST':
        try:
            title = request.form['title']
            company = request.form['company']
            description = request.form['description']
            required_skills = request.form.get('required_skills', '')
            experience_required = request.form['experience_required']
            location = request.form['location']
            salary_range = request.form['salary_range']
            
            # Clean and format skills
            skills_list = [skill.strip() for skill in required_skills.split(',') if skill.strip()]
            
            new_job = Job(
                title=title,
                company=company,
                description=description,
                required_skills=json.dumps(skills_list),
                experience_required=experience_required,
                location=location,
                salary_range=salary_range
            )
            
            db.session.add(new_job)
            db.session.commit()
            
            flash('Job added successfully!', 'success')
            return redirect(url_for('admin'))
        
        except Exception as e:
            db.session.rollback()
            flash('Error adding job. Please try again.', 'error')
            print(f"Add job error: {e}")
            return redirect(url_for('admin'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    # For production, use the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('HOSTINGER_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)