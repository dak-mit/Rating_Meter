from pymongo import MongoClient
import os

def test_mongodb():
    uri = "your_mongodb_uri_here"  # Replace with your connection string
    try:
        client = MongoClient(uri)
        db = client.get_database()
        db.command('ping')
        print("MongoDB connection successful!")
        # Try to access a collection
        users = db.users.count_documents({})
        print(f"Number of users: {users}")
    except Exception as e:
        print(f"MongoDB connection failed: {str(e)}")

if __name__ == "__main__":
    test_mongodb() 