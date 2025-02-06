# This file can be empty 

from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_login import LoginManager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')
CORS(app)

# Load configuration
from .config import Config
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MONGO_URI'] = Config.MONGODB_URI

# Initialize extensions
try:
    mongo = PyMongo(app)
    # Test connection
    mongo.db.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    mongo = None

login_manager = LoginManager()
login_manager.init_app(app)

from . import models  # Import models after app initialization
from . import index   # Import views after app initialization 