from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Use in-memory SQLite for Vercel
if 'VERCEL' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rating_game.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

PLAYMAKER_PASSWORD = 'qwertypoiu'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_playmaker = db.Column(db.Boolean, default=False)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    points = db.Column(db.Integer, default=0)

class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    playmaker_rating = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.relationship('Rating', backref='sample', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), nullable=False)
    rating_value = db.Column(db.Float, nullable=False)
    points_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Copy ALL your routes from new_project.py here
@app.route('/')
def index():
    logger.debug('Accessing index page')
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f'Error in index route: {str(e)}')
        return f"Error in application: {str(e)}", 500

# Copy ALL other routes from new_project.py here
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

# ... (copy ALL other routes from new_project.py) ...

# Test API endpoint
@app.route('/api/test')
def test_api():
    return jsonify({
        'status': 'success',
        'message': 'Backend is active',
        'timestamp': datetime.utcnow().isoformat()
    })

# Initialize database for each request in Vercel environment
@app.before_request
def before_request():
    if 'VERCEL' in os.environ:
        try:
            initialize_database()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")

def initialize_database():
    try:
        with app.app_context():
            db.create_all()
            
            # Only add demo data if no users exist
            if not User.query.first():
                try:
                    # Create a demo playmaker
                    playmaker = User(
                        username="demo_playmaker",
                        password_hash=generate_password_hash("demo123"),
                        is_playmaker=True
                    )
                    db.session.add(playmaker)
                    
                    # Create some demo samples
                    sample1 = Sample(
                        name="Demo Sample 1",
                        description="This is a demo sample",
                        playmaker_rating=8.5
                    )
                    db.session.add(sample1)
                    
                    db.session.commit()
                    logger.info("Demo data initialized successfully")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error initializing demo data: {str(e)}")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    app.run(debug=True)

# The WSGI application
application = app 