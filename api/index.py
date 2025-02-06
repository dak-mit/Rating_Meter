from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging
from flask_cors import CORS

app = Flask(__name__, template_folder='../templates')  # Note the template_folder change
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

# Add this route to test the API
@app.route('/api/test')
def test_api():
    return jsonify({
        'status': 'success',
        'message': 'Backend is active',
        'timestamp': datetime.utcnow().isoformat()
    })

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
                    raise
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise 

# The WSGI application
application = app 