from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from bson import ObjectId
from pymongo.errors import PyMongoError

from . import app, mongo, login_manager
from .models import User
from .config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure app
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MONGO_URI'] = Config.MONGODB_URI

# Initialize extensions
mongo.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

PLAYMAKER_PASSWORD = Config.PLAYMAKER_PASSWORD

@login_manager.user_loader
def load_user(user_id):
    try:
        # Convert string ID to ObjectId
        if ObjectId.is_valid(user_id):
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        return None
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

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
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            logger.debug(f"Login attempt for user: {username}")
            
            user_data = mongo.db.users.find_one({'username': username})
            if user_data:
                if check_password_hash(user_data['password_hash'], password):
                    try:
                        user = User(user_data)
                        login_user(user)
                        logger.debug(f"User {username} logged in successfully")
                        return redirect(url_for('dashboard'))
                    except Exception as e:
                        logger.error(f"Error creating user object: {str(e)}")
                        flash('Error during login. Please try again.')
                else:
                    logger.debug(f"Invalid password for user: {username}")
                    flash('Invalid username or password')
            else:
                logger.debug(f"User not found: {username}")
                flash('Invalid username or password')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Error during login. Please try again.')
            
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        logger.debug(f"User accessing dashboard: {current_user.username}")
        
        if current_user.is_playmaker:
            # Get all samples
            samples = list(mongo.db.samples.find())
            
            # Get ratings with user information
            ratings = []
            ratings_cursor = mongo.db.ratings.find()
            for rating in ratings_cursor:
                try:
                    # Get user information for each rating
                    user = mongo.db.users.find_one({'_id': rating['user_id']})
                    if user:
                        rating['user'] = {
                            'username': user.get('username', 'Unknown User'),
                            'points': user.get('points', 0)
                        }
                    # Get sample information
                    sample = mongo.db.samples.find_one({'_id': rating['sample_id']})
                    if sample:
                        rating['sample'] = {
                            'name': sample.get('name', 'Unknown Sample'),
                            'playmaker_rating': sample.get('playmaker_rating', 0)
                        }
                    rating['formatted_date'] = rating['created_at'].strftime('%Y-%m-%d %H:%M')
                    ratings.append(rating)
                except Exception as e:
                    logger.error(f"Error processing rating: {str(e)}")
                    continue
            
            # Get non-playmaker users
            users = list(mongo.db.users.find({'is_playmaker': False}))
            
            return render_template('playmaker_dashboard.html', 
                                samples=samples, 
                                ratings=ratings, 
                                users=users,
                                user=current_user)
        else:
            # Get all samples
            samples = list(mongo.db.samples.find())
            logger.debug(f"Found {len(samples)} total samples")
            
            try:
                # Get user's ratings
                user_id = ObjectId(current_user.get_id())
                logger.debug(f"Looking for ratings for user_id: {user_id}")
                
                user_ratings = list(mongo.db.ratings.find({'user_id': user_id}))
                logger.debug(f"Found {len(user_ratings)} ratings for user")
                
                ratings = []
                for rating in user_ratings:
                    try:
                        sample = mongo.db.samples.find_one({'_id': rating['sample_id']})
                        if sample:
                            rating['sample'] = {
                                'name': sample.get('name', 'Unknown Sample'),
                                'playmaker_rating': sample.get('playmaker_rating', 0)
                            }
                            rating['formatted_date'] = rating['created_at'].strftime('%Y-%m-%d %H:%M')
                            ratings.append(rating)
                    except Exception as e:
                        logger.error(f"Error processing individual rating: {str(e)}")
                        continue
                
                # Get unrated samples
                rated_sample_ids = [rating.get('sample_id') for rating in ratings if rating.get('sample_id')]
                unrated_samples = [s for s in samples if s['_id'] not in rated_sample_ids]
                
                logger.debug(f"Rendering dashboard with {len(unrated_samples)} unrated samples and {len(ratings)} ratings")
                
                return render_template('player_dashboard.html', 
                                    samples=unrated_samples, 
                                    ratings=ratings,
                                    user=current_user)
                
            except Exception as e:
                logger.error(f"Error processing ratings: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        logger.exception("Full traceback:")
        flash('Error loading dashboard. Please try again.')
        return redirect(url_for('index'))

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

@app.route('/rate_sample/<sample_id>', methods=['POST'])
@login_required
def rate_sample(sample_id):
    if current_user.is_playmaker:
        return redirect(url_for('dashboard'))
    
    try:
        # Convert string ID to ObjectId
        sample_obj_id = ObjectId(sample_id)
        sample = mongo.db.samples.find_one({'_id': sample_obj_id})
        if not sample:
            flash('Sample not found')
            return redirect(url_for('dashboard'))
        
        rating_value = float(request.form.get('rating'))
        
        # Calculate points (maximum 10 points for exact match)
        difference = abs(sample['playmaker_rating'] - rating_value)
        points = max(0, 10 - int(difference * 2))
        
        rating_data = {
            'user_id': ObjectId(current_user.id),
            'sample_id': sample_obj_id,
            'rating_value': rating_value,
            'points_earned': points,
            'created_at': datetime.utcnow()
        }
        
        mongo.db.ratings.insert_one(rating_data)
        current_user.points += points
        mongo.db.users.update_one(
            {'_id': ObjectId(current_user.id)}, 
            {'$set': {'points': current_user.points}}
        )
        
        flash(f'Rating submitted! You earned {points} points!')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error in rate_sample: {str(e)}")
        flash('Error processing rating')
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

@app.route('/api/db-test')
def test_db():
    try:
        # Test MongoDB connection
        mongo.db.command('ping')
        # Try to access a collection
        user_count = mongo.db.users.count_documents({})
        return jsonify({
            'status': 'success',
            'message': 'Database connection successful',
            'user_count': user_count,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

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

@app.route('/delete_sample/<sample_id>')
@login_required
def delete_sample(sample_id):
    if not current_user.is_playmaker:
        flash('Only playmakers can delete samples')
        return redirect(url_for('dashboard'))
    
    try:
        # Convert string ID to ObjectId
        sample_obj_id = ObjectId(sample_id)
        
        # First delete all ratings associated with this sample
        mongo.db.ratings.delete_many({'sample_id': sample_obj_id})
        
        # Then delete the sample
        result = mongo.db.samples.delete_one({'_id': sample_obj_id})
        
        if result.deleted_count > 0:
            flash('Sample deleted successfully')
        else:
            flash('Sample not found')
            
    except Exception as e:
        logger.error(f"Error deleting sample: {str(e)}")
        flash('Error deleting sample')
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

# The WSGI application
application = app 