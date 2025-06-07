from djoser.serializers import UserCreateSerializer, TokenCreateSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from school_user.models import User


class CustomUserCreateSerializer(UserCreateSerializer):

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = [
            'id',
            'email',
            'name',
            'password',
            'role',
            'school',
            'photo',
            'first_name',
            'last_name',
            'date_of_birth',
            'gender',
            'address',
            'phone',
            'is_active',
            'is_admin',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'is_admin': {'read_only': True},
            'is_active': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
        
    

class CustomTokenCreateSerializer(TokenCreateSerializer):
    role = serializers.CharField(required=True)

    def __init__(self, *args, **kwargs):
        print("✅ CustomTokenCreateSerializer INIT called")
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        print("Received data in CustomTokenCreateSerializer:", attrs)

        email = attrs.get("email")
        password = attrs.get("password")
        role = attrs.get("role")

        user = authenticate(request=self.context.get('request'), email=email, password=password)
        print("Authenticated user in CustomTokenCreateSerializer:", user)

        if user:
            print("User role:", user.role, "| Provided role:", role)

        if not user or user.role != role:
            raise serializers.ValidationError("Invalid credentials or role mismatch.")

        attrs['user'] = user
        return attrs

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.CharField(required=True)
    school = serializers.CharField(required=True)

    def validate(self, attrs):
        print("\n🔐 Login Attempt:")
        print("   📧 Email     :", attrs.get('email'))
        print("   🔑 Password  :", attrs.get('password'))
        print("   🧑‍🏫 Role      :", attrs.get('role'))
        print("   🏫 School ID :", attrs.get('school'))

        email = attrs.get('email')
        role = attrs.get('role')
        school = attrs.get('school')

        try:
            user = User.objects.get(email=email, role=role, school_id=school)
            print("✅ User found:", user)
        except User.DoesNotExist:
            print("❌ User with provided email/role/school not found.")
            raise serializers.ValidationError("Invalid credentials or user not found.")
        except Exception as e:
            print("🔥 Unexpected error:", str(e))
            raise serializers.ValidationError(f"Unexpected error: {str(e)}")

        print("✅ Proceeding with JWT token validation...")
        data = super().validate(attrs)
        print("✅ Token issued.")
        return data
