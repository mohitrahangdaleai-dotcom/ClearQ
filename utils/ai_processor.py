import google.generativeai as genai
import json
from models import db, User, Job, JobMatch
from config import Config

def extract_resume_data(resume_text):
    """Extract structured data from resume text using Gemini"""
    
    prompt = f"""
    Extract the following information from this resume text and return as JSON:
    - name (string)
    - email (string)
    - phone (string)
    - skills (array of strings)
    - experience (array of objects with: role, company, duration, description)
    - education (array of objects with: degree, institution, year)
    - summary (string)
    
    Resume Text:
    {resume_text[:4000]}
    
    Return only valid JSON. Format:
    {{
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "skills": ["Python", "JavaScript", "SQL"],
        "experience": [
            {{
                "role": "Software Engineer",
                "company": "Tech Corp",
                "duration": "2020-2023",
                "description": "Developed web applications"
            }}
        ],
        "education": [
            {{
                "degree": "BS Computer Science",
                "institution": "University",
                "year": "2020"
            }}
        ],
        "summary": "Experienced software developer..."
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        data = json.loads(response_text)
        return data
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return {
            "name": "",
            "email": "",
            "phone": "",
            "skills": [],
            "experience": [],
            "education": [],
            "summary": ""
        }

def calculate_job_match(user_data, job_data):
    """Calculate match percentage between user and job"""
    
    prompt = f"""
    Calculate the job match percentage between this candidate and job posting.
    Consider skills match, experience relevance, and overall fit.
    
    Candidate Profile:
    Skills: {user_data.get('skills', [])}
    Experience: {user_data.get('experience', [])}
    Summary: {user_data.get('summary', '')}
    
    Job Requirements:
    Title: {job_data['title']}
    Required Skills: {job_data['required_skills']}
    Experience Required: {job_data['experience_required']}
    Description: {job_data['description']}
    
    Return a JSON with:
    - match_percentage (number between 0-100)
    - matched_skills (array of matched skills)
    - missing_skills (array of missing skills)
    - fit_summary (2-3 sentence explanation of the match)
    
    Return only valid JSON. Format:
    {{
        "match_percentage": 85,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["React"],
        "fit_summary": "Strong match based on Python and SQL experience..."
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        match_data = json.loads(response_text)
        return match_data
    except Exception as e:
        print(f"Error calculating job match: {e}")
        return {
            "match_percentage": 0, 
            "matched_skills": [], 
            "missing_skills": [], 
            "fit_summary": "Error calculating match"
        }

def calculate_all_matches(user_id):
    """Calculate matches for a user against all jobs using SQLAlchemy"""
    
    # Get user data
    user = db.session.get(User, user_id)
    if not user:
        return
    
    # Get all jobs
    jobs = db.session.query(Job).all()
    
    user_data = {
        'skills': json.loads(user.skills) if user.skills else [],
        'experience': json.loads(user.experience) if user.experience else [],
        'summary': user.resume_text[:1000] if user.resume_text else ''
    }
    
    for job in jobs:
        job_data = {
            'title': job.title,
            'required_skills': json.loads(job.required_skills) if job.required_skills else [],
            'experience_required': job.experience_required,
            'description': job.description
        }
        
        match_result = calculate_job_match(user_data, job_data)
        
        # Check if match already exists
        existing_match = db.session.query(JobMatch).filter_by(
            user_id=user_id, job_id=job.id
        ).first()
        
        if existing_match:
            # Update existing match
            existing_match.match_percentage = match_result['match_percentage']
            existing_match.matched_skills = json.dumps(match_result['matched_skills'])
            existing_match.missing_skills = json.dumps(match_result['missing_skills'])
            existing_match.fit_summary = match_result['fit_summary']
        else:
            # Create new match
            new_match = JobMatch(
                user_id=user_id,
                job_id=job.id,
                match_percentage=match_result['match_percentage'],
                matched_skills=json.dumps(match_result['matched_skills']),
                missing_skills=json.dumps(match_result['missing_skills']),
                fit_summary=match_result['fit_summary']
            )
            db.session.add(new_match)
    

    db.session.commit()
