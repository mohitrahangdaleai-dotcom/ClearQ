# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... your fields

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... your fields

class JobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... your fields
