from rest_framework.views import APIView
from .serializers import UserSerializer
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from .models import User
from django.core.mail import send_mail

from .utils import generate_confirmation_token, confirm_token
import jwt
import datetime
from decouple import config
from rest_framework.permissions import AllowAny

SECRET_KEY = config('SECRET_KEY')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')

class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        token = generate_confirmation_token(user.id)
        verify_link = f"http://127.0.0.1:8000/api/verify-email/?token={token}"

        send_mail(
            'Account Verification',
            f'Click the link to activate your account: {verify_link}',
            EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        return Response({'message': 'Registration successful. Check your email to activate your account.'})


class VerifyEmailView(APIView):
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            return Response({'error': 'Missing token'}, status=400)

        user_id = confirm_token(token)
        if not user_id:
            return Response({'error': 'Invalid or expired token'}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if user.is_active:
            return Response({'message': 'Account is already active'}, status=400)


        user.is_active = True
        user.save(update_fields=['is_active'])

        return Response({'message': 'Account has been activated!'})



class LoginView(APIView):
    def post(self, request):
        email = request.data['email']
        password = request.data['password']

        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed('User not found!')
        
        if not user.check_password(password):
            raise AuthenticationFailed('Incorrect password!')

        if not user.is_active:
            raise AuthenticationFailed('Account not activated. Please check your email.')

        payload = {
            'id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            'iat': datetime.datetime.utcnow()
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        response = Response()
        response.set_cookie(key='jwt', value=token, httponly=True)

        response.data = {
            'jwt': token
        }

        return response


class UserView(APIView):
    def get(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            raise AuthenticationFailed('Unauthenticated')
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Unauthenticated')
        
        user = User.objects.filter(id=payload['id']).first()
        serializer = UserSerializer(user)

        return Response(serializer.data)
    
class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {
            'message': 'Success'
        }
        return response
    

