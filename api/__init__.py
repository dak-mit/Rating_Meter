# This file can be empty 

from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_login import LoginManager

app = Flask(__name__, template_folder='../templates')
CORS(app)
mongo = PyMongo()
login_manager = LoginManager()

from . import models  # Import models after app initialization
from . import index   # Import views after app initialization 