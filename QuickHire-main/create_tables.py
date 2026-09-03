"""Create QuickHire tables and apply lightweight local schema upgrades."""
from sqlalchemy import inspect, text
from main import app
from user_model import db


def ensure_candidate_profile_columns():
    inspector = inspect(db.engine)
    if "candidate_accounts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("candidate_accounts")}
    for name, sql_type in (("phone", "VARCHAR(50)"), ("location", "VARCHAR(160)"), ("headline", "VARCHAR(200)"), ("skills", "TEXT")):
        if name not in columns:
            with db.engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE candidate_accounts ADD COLUMN {name} {sql_type}"))
            print(f"Added candidate_accounts.{name} column.")


def ensure_job_deadline_column():
    """Add application_deadline to older QuickHire databases without deleting data."""
    inspector = inspect(db.engine)
    if "jobs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "application_deadline" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN application_deadline DATETIME"))
        print("Added jobs.application_deadline column.")


def ensure_employer_phone_column():
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("user")}
    if "phone" not in columns:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE user ADD COLUMN phone VARCHAR(50)"))
        print("Added user.phone column.")


with app.app_context():
    db.create_all()
    ensure_job_deadline_column()
    ensure_candidate_profile_columns()
    ensure_employer_phone_column()
    print("All QuickHire tables are ready.")
