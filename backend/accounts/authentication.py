from rest_framework.authentication import BaseAuthentication
from django.contrib.auth import get_user_model
from accounts.utils import decode_token

User = get_user_model()

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2:
            return None
        prefix, token = parts
        if prefix.lower() != 'bearer':
            return None
        try:
            payload = decode_token(token)
            user = User.objects.get(id=payload['user_id'])
        except Exception:
            return None
        return (user, None)
