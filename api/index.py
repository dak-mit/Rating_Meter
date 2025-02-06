from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from flask_cors import CORS
from flask_pymongo import PyMongo
from bson import ObjectId
from models import User
from pymongo.errors import PyMongoError

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='../templates')
CORS(app)

# MongoDB Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MONGO_URI'] = os.environ.get('MONGODB_URI', 'your-mongodb-uri-here')
mongo = PyMongo(app)

# Login manager setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

PLAYMAKER_PASSWORD = 'qwertypoiu'

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# Routes
@app.route('/')
def index():
    logger.debug('Accessing index page')
    try:
        if not check_db_connection():
            return "Database connection error", 500
        return render_template('index.html')
    except Exception as e:
        logger.error(f'Error in index route: {str(e)}')
        return f"Error in application: {str(e)}", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_playmaker = request.form.get('is_playmaker') == 'on'
        playmaker_password = request.form.get('playmaker_password')
        
        if mongo.db.users.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if is_playmaker and playmaker_password != PLAYMAKER_PASSWORD:
            flash('Invalid playmaker password')
            return redirect(url_for('register'))
        
        user_data = {
            'username': username,
            'password_hash': generate_password_hash(password),
            'is_playmaker': is_playmaker,
            'points': 0,
            'created_at': datetime.utcnow()
        }
        
        mongo.db.users.insert_one(user_data)
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = mongo.db.users.find_one({'username': username})
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_playmaker:
        samples = mongo.db.samples.find()
        ratings = mongo.db.ratings.find()
        users = mongo.db.users.find({'is_playmaker': False})
        return render_template('playmaker_dashboard.html', samples=samples, ratings=ratings, users=users)
    else:
        samples = mongo.db.samples.find()
        user_ratings = mongo.db.ratings.find({'user_id': current_user.id})
        rated_sample_ids = [r['sample_id'] for r in user_ratings]
        unrated_samples = [s for s in samples if s['_id'] not in rated_sample_ids]
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
        
        sample_data = {
            'name': name,
            'description': description,
            'playmaker_rating': playmaker_rating,
            'created_at': datetime.utcnow()
        }
        
        mongo.db.samples.insert_one(sample_data)
        flash('Sample added successfully')
        return redirect(url_for('dashboard'))
    return render_template('add_sample.html')

@app.route('/rate_sample/<int:sample_id>', methods=['POST'])
@login_required
def rate_sample(sample_id):
    if current_user.is_playmaker:
        return redirect(url_for('dashboard'))
    
    sample = mongo.db.samples.find_one({'_id': ObjectId(sample_id)})
    if not sample:
        flash('Sample not found')
        return redirect(url_for('dashboard'))
    
    rating_value = float(request.form.get('rating'))
    
    # Calculate points (maximum 10 points for exact match)
    difference = abs(sample['playmaker_rating'] - rating_value)
    points = max(0, 10 - int(difference * 2))
    
    rating_data = {
        'user_id': current_user.id,
        'sample_id': sample_id,
        'rating_value': rating_value,
        'points_earned': points,
        'created_at': datetime.utcnow()
    }
    
    mongo.db.ratings.insert_one(rating_data)
    current_user.points += points
    mongo.db.users.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'points': current_user.points}})
    
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
        
    user = mongo.db.users.find_one({'username': username})
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
        
    user = mongo.db.users.find_one({'username': username})
    if user:
        mongo.db.ratings.delete_many({'user_id': user['_id']})
        mongo.db.users.delete_one({'username': username})
        flash(f'User {username} has been deleted')
    else:
        flash(f'User {username} not found')
    return redirect(url_for('dashboard'))

@app.route('/leaderboard')
def leaderboard():
    # Get top 10 players by points
    top_players = mongo.db.users.find({'is_playmaker': False}).sort('points', -1).limit(10)
    
    # Get current user's rank if logged in
    current_user_rank = None
    if current_user.is_authenticated and not current_user.is_playmaker:
        higher_points = mongo.db.users.count_documents({'points': {'$gt': current_user.points}, 'is_playmaker': False})
        current_user_rank = higher_points + 1
    
    return render_template('leaderboard.html', 
                         top_players=top_players, 
                         current_user_rank=current_user_rank)

# Test API endpoint
@app.route('/api/test')
def test_api():
    return jsonify({
        'status': 'success',
        'message': 'Backend is active',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.errorhandler(PyMongoError)
def handle_mongo_error(error):
    logger.error(f"MongoDB Error: {str(error)}")
    return "Database error occurred", 500

def check_db_connection():
    try:
        # The ping command is lightweight and checks if the database is responding
        mongo.db.command('ping')
        logger.info("Successfully connected to MongoDB")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection error: {str(e)}")
        return False

def setup_mongodb_indexes():
    try:
        # Create indexes for faster queries
        mongo.db.users.create_index('username', unique=True)
        mongo.db.ratings.create_index([('user_id', 1), ('sample_id', 1)])
        mongo.db.users.create_index([('points', -1)])
        logger.info("MongoDB indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating MongoDB indexes: {str(e)}")

# Call this when the app starts
setup_mongodb_indexes()

if __name__ == '__main__':
    app.run(debug=True)

# The WSGI application
application = app 