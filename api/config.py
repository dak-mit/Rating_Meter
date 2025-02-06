import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    
    # Get MongoDB URI from environment or construct local URI
    MONGODB_URI = os.environ.get('MONGODB_URI')
    if not MONGODB_URI:
        # Local development fallback
        MONGODB_URI = 'mongodb://localhost:27017/rating_meter'
    
    # Ensure URI is properly formatted
    if MONGODB_URI.startswith('mongodb+srv://'):
        # Atlas connection string is already properly formatted
        pass
    elif not MONGODB_URI.startswith('mongodb://'):
        MONGODB_URI = f'mongodb://{MONGODB_URI}'
    
    PLAYMAKER_PASSWORD = os.environ.get('PLAYMAKER_PASSWORD', 'qwertypoiu') 