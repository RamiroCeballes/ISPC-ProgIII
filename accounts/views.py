import random
import string
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UserSerializer
from .models import UserProfile

# Create your views here.

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            # Generate OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={'encrypted_info': 'Initial state'})
            profile.otp_code = otp_code
            profile.otp_created_at = timezone.now()
            profile.save()
            
            # Print to console as requested
            print(f"=====================================")
            print(f"LOGIN OTP FOR {user.username}: {otp_code}")
            print(f"=====================================")
            
            return Response({
                'otp_required': True,
                'username': user.username
            }, status=status.HTTP_200_OK)
            
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class VerifyOTPView(APIView):
    permission_classes = (AllowAny,)
    
    def post(self, request):
        username = request.data.get('username')
        otp_code = request.data.get('otp_code')
        
        try:
            user = User.objects.get(username=username)
            profile = UserProfile.objects.get(user=user)
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if profile.otp_code != otp_code:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check expiration (e.g., 5 minutes)
        if timezone.now() > profile.otp_created_at + timedelta(minutes=5):
            return Response({'error': 'OTP Expired'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Clear OTP and return tokens
        profile.otp_code = None
        profile.otp_created_at = None
        profile.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)
    
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={'encrypted_info': 'Initial state'})
            
            # Generate reset token
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            profile.reset_token = reset_token
            profile.reset_token_created_at = timezone.now()
            profile.save()
            
            # Print to console
            print(f"=====================================")
            print(f"PASSWORD RESET TOKEN FOR {email}: {reset_token}")
            print(f"=====================================")
            
            return Response({'message': 'Reset instructions generated (check console).'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # Return success even if we didn't find the user for security reasons (don't leak emails)
            return Response({'message': 'Reset instructions generated (check console).'}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = (AllowAny,)
    
    def post(self, request):
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            
            if not profile.reset_token or profile.reset_token != token:
                return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Check expiration (e.g., 30 minutes)
            if timezone.now() > profile.reset_token_created_at + timedelta(minutes=30):
                return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Change password
            user.set_password(new_password)
            user.save()
            
            # Clear reset token
            profile.reset_token = None
            profile.reset_token_created_at = None
            profile.save()
            
            return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
            
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return Response({'error': 'Invalid metadata'}, status=status.HTTP_400_BAD_REQUEST)
