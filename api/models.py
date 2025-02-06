from datetime import datetime
from bson import ObjectId
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
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
        return str(self.user_data['_id'])

    @property
    def id(self):
        return str(self.user_data['_id'])

    @property
    def username(self):
        return self.user_data['username']

    @property
    def password_hash(self):
        return self.user_data['password_hash']

    @property
    def is_playmaker(self):
        return self.user_data.get('is_playmaker', False)

    @property
    def points(self):
        return self.user_data.get('points', 0)

    @points.setter
    def points(self, value):
        self.user_data['points'] = value 