import datetime

import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

SECRET_KEY = settings.SECRET_KEY


def generate_access_token(user_id):
    expiration_time = settings.ACCESS_TOKEN_EXPIRATION_TIME_HOURS
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_time),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user_id):
    expiration_time = settings.REFRESH_TOKEN_EXPIRATION_TIME_DAYS
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=expiration_time),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token, expected_type="access"):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed(f"{expected_type.capitalize()} token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid token")

    if payload.get("type") != expected_type:
        raise AuthenticationFailed("Invalid token type")

    return payload


def generate_verification_token(user_id):
    payload = {
        "user_id": user_id,
        "type": "email_verification",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_verification_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "email_verification":
            raise AuthenticationFailed("Invalid verification token")
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Verification token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid verification token")


def generate_password_reset_token(user_id):
    payload = {
        "user_id": user_id,
        "type": "password_reset",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_password_reset_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "password_reset":
            raise AuthenticationFailed("Invalid password reset token")
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Password reset token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid password reset token")

