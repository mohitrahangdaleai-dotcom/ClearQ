import sys
import os

# Add your app's directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import your Flask app
from app import app as application

# Initialize database on startup
with application.app_context():
    from app import db
    try:
        db.create_all()
        print("✅ Database initialized successfully on Hostinger")
    except Exception as e:
        print(f"❌ Database initialization error on Hostinger: {e}")