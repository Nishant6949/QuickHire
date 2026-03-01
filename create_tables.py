"""One-time script to create database tables in Supabase."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("DATABASE_URL"):
    sys.exit("FATAL: DATABASE_URL environment variable is not set.")

from main import app
from user_model import db, User, Job, Candidate, ResetToken

with app.app_context():
    db.create_all()
    print("All tables created successfully.")
