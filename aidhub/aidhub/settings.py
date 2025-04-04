from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*,.railway.app,aidhub-community-production.up.railway.app,localhost,127.0.0.1').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'donations.apps.DonationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # Commented for development
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aidhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aidhub.wsgi.application'

# Database Configuration
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        ssl_require=True,  # Add this for Railway PostgreSQL
        conn_health_checks=True,
    )
}

# Remove the existing SSL check since we're enforcing it above
# if 'postgres' in DATABASES['default'].get('ENGINE', ''):
#     DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# Static files settings
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []  # Remove the non-existent directory

if os.path.exists(os.path.join(BASE_DIR, 'static')):
    STATICFILES_DIRS.append(os.path.join(BASE_DIR, 'static'))

# Add whitenoise settings
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ML Models settings
ML_MODELS_DIR = os.path.join(BASE_DIR, 'donations', 'ml', 'models')
os.makedirs(ML_MODELS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'aidhub': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Add Gunicorn settings
LOGGING['loggers']['gunicorn'] = {
    'handlers': ['console'],
    'level': 'INFO',
    'propagate': False,
}

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000', 
    'http://127.0.0.1:8000',
    'https://*.onrender.com',
    'https://*.railway.app'  # Add Railway domain
]

CSRF_COOKIE_SECURE = False

# Admin Site Configuration
ADMIN_SITE_HEADER = "AidHub Administration"
ADMIN_SITE_TITLE = "AidHub Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to AidHub Administration"

# Remove EmailJS config
# EMAILJS_CONFIG = {
#     'PUBLIC_KEY': os.getenv('EMAILJS_PUBLIC_KEY'),
#     'SERVICE_ID': os.getenv('EMAILJS_SERVICE_ID'), 
#     'TEMPLATE_ID': os.getenv('EMAILJS_TEMPLATE_ID'),
# }

# Add SMTP Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'emailsender880@gmail.com'
EMAIL_HOST_PASSWORD = 'jzio inzq lhqg azeg'
DEFAULT_FROM_EMAIL = 'AidHub Team - Hexacoders'

# Media files settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Enable file uploads
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]

# Maximum upload size (5MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# Add this setting to handle trailing slashes
APPEND_SLASH = True
