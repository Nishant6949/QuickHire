"""One-time migration: add settings and notification columns to user table."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("DATABASE_URL"):
    sys.exit("FATAL: DATABASE_URL environment variable is not set.")

from main import app
from user_model import db

ALTER_STATEMENTS = [
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS auto_screen BOOLEAN DEFAULT TRUE",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS match_threshold INTEGER DEFAULT 70",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS bias_detection BOOLEAN DEFAULT TRUE",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS notif_matches BOOLEAN DEFAULT TRUE",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS notif_weekly BOOLEAN DEFAULT TRUE",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS notif_expire BOOLEAN DEFAULT TRUE",
    "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS notif_updates BOOLEAN DEFAULT FALSE",
]

with app.app_context():
    for stmt in ALTER_STATEMENTS:
        db.session.execute(db.text(stmt))
    db.session.commit()
    print("Settings columns added successfully.")
