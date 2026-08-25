import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load project-local environment variables before importing application modules.
load_dotenv(Path(__file__).with_name('.env'))

from flask import Flask, abort, jsonify, render_template
from sqlalchemy import event, text

from user_model import db, login_manager
from routes.auth import auth_bp
from routes.landing import landing_bp
from routes.dashboard import dashboard_bp
from routes.api.jobs import jobs_api_bp
from routes.api.candidates import candidates_api_bp
from routes.password_reset import password_reset_bp

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def _truthy(value):
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _is_production():
    return (
        os.getenv('FLASK_ENV') == 'production'
        or _truthy(os.getenv('RENDER'))
        or _truthy(os.getenv('VERCEL'))
    )


PRODUCTION = _is_production()

secret_key = os.getenv('SECRET_KEY')
database_url = os.getenv('DATABASE_URL')

# Production must always use explicit secrets/database configuration. For local
# development, SQLite and a development-only secret make the project runnable
# immediately on a new laptop.
if PRODUCTION and (not secret_key or not database_url):
    missing = [name for name, value in [('SECRET_KEY', secret_key), ('DATABASE_URL', database_url)] if not value]
    sys.exit(f"FATAL: Missing required environment variables: {', '.join(missing)}")

if not secret_key:
    secret_key = 'quickhire-development-only-change-me'
    logger.warning('SECRET_KEY not set; using development-only fallback.')

if not database_url:
    database_url = 'sqlite:///quickhire.db'
    logger.warning('DATABASE_URL not set; using local SQLite database quickhire.db.')

# SQLAlchemy accepts postgresql:// while some providers still expose postgres://.
if database_url.startswith('postgres://'):
    database_url = 'postgresql://' + database_url[len('postgres://'):]

app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key,
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    ANTHROPIC_API_KEY=os.getenv('ANTHROPIC_API_KEY'),
    GMAIL_ADDRESS=os.getenv('GMAIL_ADDRESS'),
    GMAIL_APP_PASSWORD=os.getenv('GMAIL_APP_PASSWORD'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=PRODUCTION,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE='Lax',
    REMEMBER_COOKIE_SECURE=PRODUCTION,
)

if database_url.startswith('postgresql'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }


db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please sign in to continue.'

# Supabase/pgbouncer-specific connection settings must only run on PostgreSQL.
if database_url.startswith('postgresql'):
    with app.app_context():
        @event.listens_for(db.engine, 'connect')
        def _on_connect(dbapi_conn, connection_record):
            try:
                old_autocommit = getattr(dbapi_conn, 'autocommit', False)
                dbapi_conn.autocommit = True
                cursor = dbapi_conn.cursor()
                cursor.execute("SET statement_timeout = '30s'")
                cursor.close()
                dbapi_conn.autocommit = old_autocommit
            except Exception as exc:
                logger.warning('Could not apply PostgreSQL statement timeout: %s', exc)

# Local SQLite should be zero-setup.
if database_url.startswith('sqlite:'):
    with app.app_context():
        db.create_all()


ERROR_PAGES = {
    400: ('Bad Request', "We couldn't understand that request. Try again?", 'alert-circle'),
    403: ('Access Denied', "You don't have permission to view this page.", 'lock'),
    404: ('Page Not Found', "The page you're looking for doesn't exist or has been moved.", 'map-pin'),
    405: ('Method Not Allowed', "That action isn't supported here.", 'slash'),
    413: ('File Too Large', 'The uploaded file exceeds the 16 MB limit.', 'upload-cloud'),
    500: ('Something Went Wrong', 'We hit a snag on our end. Please try again later.', 'alert-triangle'),
}


def render_error(error):
    code = getattr(error, 'code', 500)
    title, description, icon = ERROR_PAGES.get(code, ERROR_PAGES[500])
    return render_template(
        'error.html', error_code=code, error_title=title,
        error_description=description, error_icon=icon,
    ), code


for code in ERROR_PAGES:
    app.register_error_handler(code, render_error)

app.register_blueprint(landing_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(jobs_api_bp)
app.register_blueprint(candidates_api_bp)
app.register_blueprint(password_reset_bp)


@app.get('/health')
def health():
    """Lightweight deployment/readiness endpoint."""
    try:
        db.session.execute(text('SELECT 1'))
        database = 'ok'
        status_code = 200
    except Exception as exc:
        logger.error('Health check database failure: %s', exc)
        database = 'error'
        status_code = 503

    return jsonify({
        'status': 'ok' if status_code == 200 else 'degraded',
        'database': database,
        'ai_configured': bool(app.config.get('ANTHROPIC_API_KEY')),
        'email_configured': bool(app.config.get('GMAIL_ADDRESS') and app.config.get('GMAIL_APP_PASSWORD')),
    }), status_code


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https:; "
        "script-src 'self' 'unsafe-inline' https:; font-src 'self' data: https:; connect-src 'self' https:;"
    )
    if PRODUCTION:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV') == 'development'
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', debug=debug, port=port)
