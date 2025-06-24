from djoser.serializers import UserCreateSerializer, TokenCreateSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = [
            'id', 'email', 'name', 'password', 'role', 'school', 'photo',
            'first_name', 'last_name', 'date_of_birth', 'gender', 'address',
            'phone', 'is_active', 'is_admin', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'is_admin': {'read_only': True},
            'is_active': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

class CustomUserDetailSerializer(serializers.ModelSerializer):
    profile_id = serializers.SerializerMethodField(read_only = True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'role',
            'school',
            'is_admin',
            'is_active',
            'created_at',
            'updated_at',
            'profile_id'
        ]
    
    def get_profile_id(self, obj):
        try:
            if obj.role == 'teacher':
                return obj.teacher.id if hasattr(obj, 'teacher') else None
            elif obj.role == 'student':
                return obj.student.id if hasattr(obj, 'student') else None
            return obj.id  # For admin and other roles
        except Exception as e:
            return None
        
        
# ✅ Djoser Email/Password + Role Login
class CustomTokenCreateSerializer(TokenCreateSerializer):
    role = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        role = attrs.get("role")

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user or user.role != role:
            raise serializers.ValidationError("Invalid credentials or role mismatch.")

        attrs['user'] = user
        return attrs


# ✅ JWT Login with TokenObtainPairSerializer
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.CharField(required=True)
    school = serializers.CharField(required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        role = attrs.get('role')
        school = attrs.get('school')

        try:
            user = User.objects.get(email=email, role=role, school_id=school)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials or user not found.")
        except Exception as e:
            raise serializers.ValidationError(f"Unexpected error: {str(e)}")

        self.user = user
        data = super().validate(attrs)

        return data


