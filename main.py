import logging
import sys

logging.basicConfig(level=logging.INFO)

from flask import Flask, render_template, abort
import os
from dotenv import load_dotenv
from sqlalchemy import event
from user_model import db, login_manager
from routes.auth import auth_bp
from routes.landing import landing_bp
from routes.dashboard import dashboard_bp
from routes.api.jobs import jobs_api_bp
from routes.api.candidates import candidates_api_bp
from routes.password_reset import password_reset_bp

load_dotenv()

# --- Fail fast if critical env vars are missing ---
_required_env = ["SECRET_KEY", "DATABASE_URL"]
_missing = [v for v in _required_env if not os.getenv(v)]
if _missing:
    sys.exit(f"FATAL: Missing required environment variables: {', '.join(_missing)}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ANTHROPIC_API_KEY'] = os.getenv("ANTHROPIC_API_KEY")
app.config['GMAIL_ADDRESS'] = os.getenv("GMAIL_ADDRESS")
app.config['GMAIL_APP_PASSWORD'] = os.getenv("GMAIL_APP_PASSWORD")

# --- Connection pool settings for Supabase / pgbouncer ---
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db.init_app(app)
login_manager.init_app(app)
login_manager.unauthorized_callback = lambda: abort(404)

# Disable RESET ALL on connection return (pgbouncer doesn't support it)
with app.app_context():
    @event.listens_for(db.engine, "connect")
    def _on_connect(dbapi_conn, connection_record):
        dbapi_conn.autocommit = True
        cursor = dbapi_conn.cursor()
        cursor.execute("SET statement_timeout = '30s'")
        cursor.close()
        dbapi_conn.autocommit = False

    @event.listens_for(db.engine, "checkout")
    def _on_checkout(dbapi_conn, connection_record, connection_proxy):
        pass  # skip RESET ALL — pgbouncer compat

ERROR_PAGES = {
    400: ("Bad Request", "We couldn't understand that request. Try again?", "alert-circle"),
    403: ("Access Denied", "You don't have permission to view this page.", "lock"),
    404: ("Page Not Found", "The page you're looking for doesn't exist or has been moved.", "map-pin"),
    405: ("Method Not Allowed", "That action isn't supported here.", "slash"),
    500: ("Something Went Wrong", "We hit a snag on our end. Please try again later.", "alert-triangle"),
}

def render_error(e):
    code = e.code
    title, description, icon = ERROR_PAGES[code]
    return render_template("error.html", error_code=code, error_title=title, error_description=description, error_icon=icon), code

for code in ERROR_PAGES:
    app.register_error_handler(code, render_error)

app.register_blueprint(landing_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(jobs_api_bp)
app.register_blueprint(candidates_api_bp)
app.register_blueprint(password_reset_bp)


# --- Security headers ---
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(debug=debug, port=8080)
