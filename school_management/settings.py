"""
Django settings for school_management project.

Generated by 'django-admin startproject' using Django 5.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os
import cloudinary
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'school',
    'school_user',
    'rest_framework',
    'djoser',
    "corsheaders",
    "bot"
]

DATABASE_URL = os.environ.get('DATABASE_URL')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DATABASE_URL.rsplit('/', 1)[-1],
        'USER': DATABASE_URL.split('//')[1].split(':')[0],
        'PASSWORD': DATABASE_URL.split(':')[2].split('@')[0],
        'HOST': DATABASE_URL.split('@')[1].split(':')[0],
        'PORT': DATABASE_URL.rsplit(':', 1)[-1].split('/')[0],
        'CONN_MAX_AGE': 600,
    }
}
# BASE_DIR = Path(__file__).resolve().parent.parent
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# Email Configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS')
EMAIL_USE_TLS = True

# Google Meet Bot Credentials
MEET_BOT_EMAIL = os.environ.get('MEET_BOT_EMAIL')
MEET_BOT_PASSWORD = os.environ.get('MEET_BOT_PASSWORD')

# Recording settings
RECORDINGS_DIR = "/tmp/recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_management.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'school_user' / 'templates',
            BASE_DIR / 'bot' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]



# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True



# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CLOUD_NAME = os.environ.get('CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

cloudinary.config( 
  cloud_name = CLOUD_NAME,
  api_key = CLOUDINARY_API_KEY,
  api_secret = CLOUDINARY_API_SECRET
)

# ✅ STATIC & MEDIA
STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# ✅ Cloudinary media storage
DEFAULT_FILE_STORAGE = os.environ.get('DEFAULT_FILE_STORAGE')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME':  CLOUD_NAME,
    'API_KEY':  CLOUDINARY_API_KEY,
    'API_SECRET':  CLOUDINARY_API_SECRET
}


AUTH_USER_MODEL = 'school_user.User'

TIME_ZONE = 'Asia/Kolkata'
USE_TZ = True


CORS_ALLOW_ALL_ORIGINS = True

# JWT Configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# JWT Settings
SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=355),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    'TOKEN_OBTAIN_SERIALIZER': 'school_user.serializers.CustomTokenObtainPairSerializer',

}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Change to INFO in prod
        },
    }
}


# Djoser Settings
DJOSER = {
    'LOGIN_FIELD': 'email',
    # 'USER_CREATE_PASSWORD_RETYPE':True,
    'ACTIVATION_URL':'/activate/{uid}/{token}',
    'SEND_ACTIVATION_EMAIL':True,
    'SEND_CONFIRMATION_EMAIL':True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION':True,
    'PASSWORD_RESET_CONFIRM_URL': 'password-reset/{uid}/{token}',
    'SET_PASSWORD_RETYPE': True,
    'PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND': True,
    'TOKEN_MODEL': None,       # To Delete User Must Set it to None
    'SERIALIZERS':{
        'user': 'school_user.serializers.CustomUserDetailSerializer',  # 👈 here
        'user_create': 'school_user.serializers.CustomUserCreateSerializer',
        'user_delete': 'djoser.serializers.UserDeleteSerializer',
        'token_create': 'school_user.serializers.CustomTokenCreateSerializer',

    },
    'EMAIL': {
        'activation': 'school_user.email.ActivationEmail',
        'confirmation': 'school_user.email.ConfirmationEmail',
        'password_reset': 'school_user.email.PasswordResetEmail',
        'password_changed_confirmation': 'school_user.email.PasswordChangedConfirmationEmail',
    },
}


CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]