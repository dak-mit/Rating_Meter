from pymongo import MongoClient
import os

def test_connection():
    uri = os.environ.get('MONGODB_URI')
    try:
        client = MongoClient(uri)
        db = client.get_database()
        db.command('ping')
        print("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        print(f"Failed to connect to MongoDB: {str(e)}")
        return False

if __name__ == '__main__':
    test_connection() 