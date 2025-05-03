from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Use email as the username field
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required")

        # Authenticate using email as the username
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        # Generate tokens
        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,  # Optional: include user ID in response
            'email': user.email  # Optional: include email in response
        }