"""Create any missing QuickHire database tables.

Uses DATABASE_URL when configured, otherwise the application's local SQLite
fallback. Safe to run multiple times because SQLAlchemy create_all is idempotent.
"""
from main import app
from user_model import db

with app.app_context():
    db.create_all()
    print('All QuickHire tables are ready.')
