from flask import Flask, render_template, abort
import os
from dotenv import load_dotenv
from user_model import db, login_manager
from routes.auth import auth_bp
from routes.landing import landing_bp
from routes.dashboard import dashboard_bp
from routes.api.jobs import jobs_api_bp
from routes.api.candidates import candidates_api_bp

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ANTHROPIC_API_KEY'] = os.getenv("ANTHROPIC_API_KEY")
app.config['GMAIL_ADDRESS'] = os.getenv("GMAIL_ADDRESS")
app.config['GMAIL_APP_PASSWORD'] = os.getenv("GMAIL_APP_PASSWORD")
db.init_app(app)
login_manager.init_app(app)
login_manager.unauthorized_callback = lambda: abort(404)

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

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    from user_model import User, Job, Candidate
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=8080)
