import mysql.connector
from config import Config

def create_tables():
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )
    
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            google_id VARCHAR(255),
            name VARCHAR(255),
            phone VARCHAR(50),
            skills JSON,
            experience JSON,
            education JSON,
            preferred_location VARCHAR(255),
            expected_salary VARCHAR(100),
            resume_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)
    
    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            description TEXT,
            required_skills JSON,
            experience_required VARCHAR(100),
            location VARCHAR(255),
            salary_range VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Job matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_matches (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT,
            job_id INT,
            match_percentage FLOAT,
            matched_skills JSON,
            missing_skills JSON,
            fit_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_job (user_id, job_id)
        )
    """)
    
    # Insert sample jobs
    sample_jobs = [
        {
            'title': 'Python Developer',
            'company': 'Tech Solutions Inc.',
            'description': 'We are looking for a skilled Python developer with experience in web development and AI applications.',
            'required_skills': ['Python', 'Flask', 'SQL', 'REST API', 'Git'],
            'experience_required': '2-4 years',
            'location': 'Remote',
            'salary_range': '$60,000 - $90,000'
        },
        {
            'title': 'Frontend Developer',
            'company': 'Web Innovations LLC',
            'description': 'Join our frontend team to build modern, responsive web applications using React and TypeScript.',
            'required_skills': ['JavaScript', 'React', 'TypeScript', 'CSS', 'HTML5'],
            'experience_required': '1-3 years',
            'location': 'New York, NY',
            'salary_range': '$70,000 - $100,000'
        },
        {
            'title': 'Data Scientist',
            'company': 'Data Analytics Corp',
            'description': 'Seeking data scientist with machine learning experience to analyze large datasets and build predictive models.',
            'required_skills': ['Python', 'Machine Learning', 'SQL', 'Pandas', 'Statistics'],
            'experience_required': '3-5 years',
            'location': 'San Francisco, CA',
            'salary_range': '$90,000 - $120,000'
        }
    ]
    
    for job in sample_jobs:
        cursor.execute("""
            INSERT IGNORE INTO jobs (title, company, description, required_skills, experience_required, location, salary_range)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            job['title'],
            job['company'],
            job['description'],
            '["' + '","'.join(job['required_skills']) + '"]',
            job['experience_required'],
            job['location'],
            job['salary_range']
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Database tables created successfully!")

if __name__ == '__main__':
    create_tables()