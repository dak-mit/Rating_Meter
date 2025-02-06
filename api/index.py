from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash

app = Flask(__name__)
CORS(app)

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