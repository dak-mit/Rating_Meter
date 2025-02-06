from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# For Vercel, we need to use a different database approach
# SQLite won't work properly in Vercel's serverless environment
if 'VERCEL' in os.environ:
    # For demo purposes, we'll still use SQLite but in the /tmp directory
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/rating_game.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rating_game.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

PLAYMAKER_PASSWORD = 'qwertypoiu'  # Add this near the top of the file

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

# Routes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    logger.debug('Accessing index page')
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f'Error in index route: {str(e)}')
        return str(e), 500

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_playmaker = request.form.get('is_playmaker') == 'on'
        playmaker_password = request.form.get('playmaker_password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Check playmaker password if trying to register as playmaker
        if is_playmaker and playmaker_password != PLAYMAKER_PASSWORD:
            flash('Invalid playmaker password')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_playmaker=is_playmaker
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_playmaker:
        samples = Sample.query.all()
        ratings = Rating.query.all()
        users = User.query.filter_by(is_playmaker=False).all()
        return render_template('playmaker_dashboard.html', samples=samples, ratings=ratings, users=users)
    else:
        samples = Sample.query.all()
        user_ratings = Rating.query.filter_by(user_id=current_user.id).all()
        rated_sample_ids = [r.sample_id for r in user_ratings]
        unrated_samples = [s for s in samples if s.id not in rated_sample_ids]
        return render_template('player_dashboard.html', samples=unrated_samples, ratings=user_ratings)

@app.route('/add_sample', methods=['GET', 'POST'])
@login_required
def add_sample():
    if not current_user.is_playmaker:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        playmaker_rating = float(request.form.get('rating'))
        
        sample = Sample(
            name=name,
            description=description,
            playmaker_rating=playmaker_rating
        )
        db.session.add(sample)
        db.session.commit()
        
        flash('Sample added successfully')
        return redirect(url_for('dashboard'))
    return render_template('add_sample.html')

@app.route('/rate_sample/<int:sample_id>', methods=['POST'])
@login_required
def rate_sample(sample_id):
    if current_user.is_playmaker:
        return redirect(url_for('dashboard'))
    
    sample = Sample.query.get_or_404(sample_id)
    rating_value = float(request.form.get('rating'))
    
    # Calculate points (maximum 10 points for exact match)
    difference = abs(sample.playmaker_rating - rating_value)
    points = max(0, 10 - int(difference * 2))
    
    rating = Rating(
        user_id=current_user.id,
        sample_id=sample_id,
        rating_value=rating_value,
        points_earned=points
    )
    
    current_user.points += points
    db.session.add(rating)
    db.session.commit()
    
    flash(f'Rating submitted! You earned {points} points!')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/confirm_delete_user/<username>')
@login_required
def confirm_delete_user(username):
    if not current_user.is_playmaker:
        flash('Only playmakers can delete users')
        return redirect(url_for('dashboard'))
        
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User not found')
        return redirect(url_for('dashboard'))
        
    return render_template('confirm_delete.html', username=username)

@app.route('/delete_user/<username>', methods=['POST'])
@login_required
def delete_user(username):
    if not current_user.is_playmaker:
        flash('Only playmakers can delete users')
        return redirect(url_for('dashboard'))
        
    user = User.query.filter_by(username=username).first()
    if user:
        Rating.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f'User {username} has been deleted')
    else:
        flash(f'User {username} not found')
    return redirect(url_for('dashboard'))

@app.route('/leaderboard')
def leaderboard():
    # Get top 10 players by points
    top_players = User.query.filter_by(is_playmaker=False).order_by(User.points.desc()).limit(10).all()
    
    # Get current user's rank if logged in
    current_user_rank = None
    if current_user.is_authenticated and not current_user.is_playmaker:
        higher_points = User.query.filter(
            User.points > current_user.points,
            User.is_playmaker == False
        ).count()
        current_user_rank = higher_points + 1
    
    return render_template('leaderboard.html', 
                         top_players=top_players, 
                         current_user_rank=current_user_rank)

@app.errorhandler(500)
def handle_500_error(e):
    return render_template('error.html', error=str(e)), 500

@app.errorhandler(404)
def handle_404_error(e):
    return render_template('error.html', error="Page not found"), 404

# Add this at the end of the file
app = app.wsgi_app

# Database configuration
if 'VERCEL' in os.environ:
    # Initialize with demo data for Vercel
    @app.before_first_request
    def initialize_database():
        db.create_all()
        
        # Check if we need to add demo data
        if not User.query.first():
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
else:
    with app.app_context():
        db.create_all()
