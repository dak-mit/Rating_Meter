from datetime import datetime
import json
from bson import ObjectId
from flask import current_app

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

def backup_database():
    try:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup = {
            'users': list(current_app.mongo.db.users.find()),
            'samples': list(current_app.mongo.db.samples.find()),
            'ratings': list(current_app.mongo.db.ratings.find())
        }
        
        with open(f'backup_{timestamp}.json', 'w') as f:
            json.dump(backup, f, cls=JSONEncoder)
            
        return True
    except Exception as e:
        current_app.logger.error(f"Backup error: {str(e)}")
        return False 