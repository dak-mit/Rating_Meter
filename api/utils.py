from bson import ObjectId

def validate_object_id(id_str):
    try:
        return ObjectId(id_str)
    except:
        return None

def validate_rating(rating):
    try:
        rating = float(rating)
        return 0 <= rating <= 10
    except:
        return False 