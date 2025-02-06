import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/rating_meter')
    PLAYMAKER_PASSWORD = 'qwertypoiu' 