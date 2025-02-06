from datetime import datetime
from bson import ObjectId
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        if user_data is None:
            raise ValueError("User data cannot be None")
        self.user_data = user_data

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.user_data.get('_id', ''))

    @property
    def id(self):
        # Convert ObjectId to string
        return str(self.user_data.get('_id'))

    @property
    def username(self):
        return self.user_data.get('username', 'Unknown User')

    @property
    def password_hash(self):
        return self.user_data.get('password_hash')

    @property
    def is_playmaker(self):
        return self.user_data.get('is_playmaker', False)

    @property
    def points(self):
        return self.user_data.get('points', 0)

    @points.setter
    def points(self, value):
        self.user_data['points'] = value 