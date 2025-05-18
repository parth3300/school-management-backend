from djoser.serializers import UserCreateSerializer, TokenCreateSerializer
from school_user.models import User
from rest_framework import serializers
from django.contrib.auth import authenticate

class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model=User
        fields=('id', 'email', 'name', 'password')
        
# school_user/serializers.py


class CustomTokenCreateSerializer(TokenCreateSerializer):
    role = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        role = attrs.get("role")

        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        if not user or user.role != role:
            raise serializers.ValidationError("Invalid credentials.")

        attrs['user'] = user
        return attrs
