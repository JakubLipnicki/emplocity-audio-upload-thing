import datetime

import jwt
from decouple import config
from django.conf import settings

SECRET_KEY = config("SECRET_KEY")


def generate_confirmation_token(user_id, token_type="activation"):
    payload = {
        "user_id": user_id,
        "type": token_type, 
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(hours=settings.TOKEN_EXPIRATION_TIME_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def confirm_token(token, expected_type="activation"):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            return None
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

