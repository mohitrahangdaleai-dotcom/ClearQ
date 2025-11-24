import json
from app import db, Job, JobMatch

def get_user_matches(user_id, limit=10):
    """Get job matches for a specific user using SQLAlchemy"""
    
    matches = db.session.query(JobMatch).filter_by(user_id=user_id).order_by(
        JobMatch.match_percentage.desc()
    ).limit(limit).all()
    
    matches_list = []
    for match in matches:
        job = db.session.get(Job, match.job_id)
        if job:
            matches_list.append({
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'location': job.location,
                'salary_range': job.salary_range,
                'match_percentage': match.match_percentage or 0,
                'matched_skills': json.loads(match.matched_skills) if match.matched_skills else [],
                'missing_skills': json.loads(match.missing_skills) if match.missing_skills else [],
                'fit_summary': match.fit_summary or "No summary available"
            })
    
    return matches_list

def get_user_match_stats(user_id):
    """Get matching statistics for a user using SQLAlchemy"""
    
    from sqlalchemy import func
    
    stats = db.session.query(
        func.count(JobMatch.id),
        func.avg(JobMatch.match_percentage),
        func.max(JobMatch.match_percentage)
    ).filter_by(user_id=user_id).first()
    
    return {
        'total_matches': stats[0] if stats[0] else 0,
        'average_match': round(stats[1], 1) if stats[1] else 0,
        'best_match': round(stats[2], 1) if stats[2] else 0
    }

def get_missing_skills_analysis(user_id):
    """Analyze most common missing skills across job matches using SQLAlchemy"""
    
    matches = db.session.query(JobMatch).filter_by(
        user_id=user_id
    ).filter(JobMatch.match_percentage < 80).all()
    
    # Count frequency of missing skills
    skill_count = {}
    for match in matches:
        if match.missing_skills:
            try:
                skills = json.loads(match.missing_skills)
                for skill in skills:
                    skill_count[skill] = skill_count.get(skill, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Return top 5 most frequently missing skills
    sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:5]
    return [skill for skill, count in sorted_skills]

def update_all_user_matches():
    """Recalculate matches for all users (admin function) using SQLAlchemy"""
    
    from app import User
    from utils.ai_processor import calculate_all_matches
    
    users = db.session.query(User).all()
    
    for user in users:
        calculate_all_matches(user.id)
    
    return len(users)