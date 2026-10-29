
"""
Django settings for sabin_balan_finance_project project.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

try:
    import certifi
    os.environ.setdefault('SSL_CERT_FILE', certifi.where())
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
import shutil
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')


# Project Image Fallbacks & Auto-Sync inside photos/ folder
_photos_dir = BASE_DIR / "photos"

_target_img = _photos_dir / "financial_advisors_team.png"
_about_img = _photos_dir / "about_showcase_team.png"
if os.path.exists(_target_img) and not os.path.exists(_about_img):
    try:
        shutil.copy(_target_img, _about_img)
    except Exception:
        pass

_home_hero = _photos_dir / "home_hero.png"
_contact_hero = _photos_dir / "contact_hero.png"
_about_hero = _photos_dir / "about_us_hero.png"
if os.path.exists(_home_hero):
    if not os.path.exists(_contact_hero):
        try:
            shutil.copy(_home_hero, _contact_hero)
        except Exception:
            pass
    if not os.path.exists(_about_hero):
        try:
            shutil.copy(_home_hero, _about_hero)
        except Exception:
            pass


# Publisher Logos Auto-Sync (KP RegTech & VintushTech)
_kp_logo_target = BASE_DIR / "photos" / "kplogo.png"
_vintush_logo_target = BASE_DIR / "photos" / "vintushtech_logo.png"

try:
    import urllib.request
    if not os.path.exists(_kp_logo_target):
        req = urllib.request.Request("https://kpregtech.com/static/images/kplogo.png", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response, open(_kp_logo_target, 'wb') as out_file:
            out_file.write(response.read())
except Exception:
    pass

try:
    import urllib.request
    if not os.path.exists(_vintush_logo_target):
        req = urllib.request.Request("https://vintushtech.cloud/static/website/images/favicon.png", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response, open(_vintush_logo_target, 'wb') as out_file:
            out_file.write(response.read())
except Exception:
    pass

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-@wlg*897qb*$lo1_ek^5&5c#bldttck@9$9iah37-)qcf!zd)7')

DEBUG = True

# ALLOWED_HOSTS - Allow all hosts for testing on Render
ALLOWED_HOSTS = ['*']

# CSRF Trusted Origins - Allow all for testing
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.render.com',
    'http://*.onrender.com',
    'http://*.render.com',
    'https://*.railway.app',
    'http://*.railway.app',
    'https://*.herokuapp.com',
    'http://*.herokuapp.com',
    'https://*.fly.dev',
    'http://*.fly.dev',
    'https://*.vercel.app',
    'http://*.vercel.app',
    'https://*.netlify.app',
    'http://*.netlify.app',
    'https://*.cloud',
    'http://*.cloud',
    'https://*.app',
    'http://*.app',
    'https://localhost',
    'http://localhost',
    'http://127.0.0.1',
    'https://*.ngrok.io',
    'http://*.ngrok.io',
]

# Also parse from environment variable if provided
csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_env:
    extra_origins = [c.strip() for c in csrf_trusted_env.split(',') if c.strip()]
    CSRF_TRUSTED_ORIGINS.extend(extra_origins)

# SSL Proxy Header Setup
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'http')
USE_X_FORWARDED_HOST = True


# ================================================================
# PRODUCTION SECURITY HARDENING & HTTP HEADERS
# ================================================================
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS SSL Redirect & HSTS Headers (Configurable via environment)
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1', 't')
if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('true', '1', 't')
    SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'True').lower() in ('true', '1', 't')


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'contactform',
    'navfooter',
    'theme_config',
    'login',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'login.middleware.AdminSaaSGuardMiddleware',
]

ROOT_URLCONF = 'sabin_balan_finance_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'theme_config.context_processors.theme_colors',
            ],
        },
    },
]

WSGI_APPLICATION = 'sabin_balan_finance_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.environ.get('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ================================================================
# STATIC FILES CONFIGURATION - For Render with collectstatic
# ================================================================
# URL prefix for static files
STATIC_URL = '/static/'

# The absolute path to the directory where collectstatic will collect static files for deployment
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional locations of static files
STATICFILES_DIRS = [
    BASE_DIR / 'photos',
    BASE_DIR / 'videos',
]

# Storage backend for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ================================================================
# MEDIA FILES (User Uploads)
# ================================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ================================================================
# SECRET UNGUESSABLE SLUG FOR ADMINISTRATOR PORTAL
# ================================================================
ADMIN_SECRET_PATH = os.environ.get('ADMIN_SECRET_PATH', 'x7K9mQp2LrT4').strip('/')

# Custom User Model & Authentication Redirects
AUTH_USER_MODEL = 'login.CustomUser'
LOGIN_URL = f'/{ADMIN_SECRET_PATH}/login/'
LOGIN_REDIRECT_URL = f'/{ADMIN_SECRET_PATH}/'
LOGOUT_REDIRECT_URL = 'login:home'

# ================================================================
# EMAIL DISPATCH CONFIGURATION (Adaptive Gmail & GoDaddy SMTP Engine)
# ================================================================
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()

# If user configured a Gmail address for sending, auto-route through smtp.gmail.com:587
if 'gmail.com' in EMAIL_HOST_USER.lower() or os.environ.get('EMAIL_HOST', '').lower() == 'smtp.gmail.com':
    EMAIL_HOST_PASSWORD = EMAIL_HOST_PASSWORD.replace(' ', '')
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
else:
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtpout.secureserver.net')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False').lower() in ('true', '1', 't')
    EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True').lower() in ('true', '1', 't')

EMAIL_TIMEOUT = 30

# WhiteNoise static asset caching performance configuration
WHITENOISE_MAX_AGE = 31536000
CONN_MAX_AGE = 60

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'GuardianTree FP <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'GuardianTree FP <advisory@guardiantreefp.com>'
)
ADMIN_NOTIFICATION_EMAIL = os.environ.get('ADMIN_NOTIFICATION_EMAIL', 'tusharsilotia1@gmail.com')
CONTACT_FORM_EMAIL_RECIPIENT = ADMIN_NOTIFICATION_EMAIL
SABIN_CLIENT_EMAIL = os.environ.get('SABIN_CLIENT_EMAIL', 'vintushtech@gmail.com')
PROVIDER_EMAIL = os.environ.get('PROVIDER_EMAIL', 'tusharsilotia1@gmail.com')
SITE_NAME = os.environ.get('SITE_NAME', 'GuardianTree FP')
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')

# ================================================================
# 2-Factor Authentication (2FA) & SaaS Settings
# ================================================================
ADMIN_2FA_ENABLED = os.environ.get('ADMIN_2FA_ENABLED', 'True').lower() in ('true', '1', 't')
ADMIN_2FA_EMAIL = os.environ.get('ADMIN_2FA_EMAIL', 'tusharsilotia1@gmail.com')
ADMIN_2FA_CODE_EXPIRY_SECONDS = int(os.environ.get('ADMIN_2FA_CODE_EXPIRY_SECONDS', '300'))
SAAS_SECRET_KEY = os.environ.get('SAAS_SECRET_KEY', 'vintushtech-kpregtech-saas-master-key')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
