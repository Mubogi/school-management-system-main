import os
import sys
from pathlib import Path

from core.edition import get_edition, is_offline

# ---------------------------------------------------------------------------
# Edition / runtime mode
# ---------------------------------------------------------------------------
EDITION = get_edition()
IS_OFFLINE_EDITION = is_offline()

_INSTANCE_DIR_ENV = os.environ.get('JDHUB_INSTANCE_DIR', '').strip()

# BASE_DIR points to the project source tree (used for templates/static).
# In a frozen (PyInstaller) bundle this resolves to the read-only bundle dir.
SOURCE_ROOT = Path(__file__).resolve().parent.parent

if _INSTANCE_DIR_ENV:
    # Portable/frozen builds keep every writable file (source code, templates,
    # database, media) inside one folder so the bundle can run from anywhere.
    INSTANCE_DIR = Path(_INSTANCE_DIR_ENV).resolve()
elif getattr(sys, 'frozen', False):
    INSTANCE_DIR = Path(sys.executable).resolve().parent
else:
    INSTANCE_DIR = SOURCE_ROOT

if _INSTANCE_DIR_ENV:
    BASE_DIR = INSTANCE_DIR
else:
    BASE_DIR = SOURCE_ROOT

# DATA_DIR is where writable, user-specific data lives (database, media,
# backups). In a frozen app this is the directory next to the executable so
# data persists across runs; in development it is the project root.
DATA_DIR = INSTANCE_DIR

# A per-installation secret key: generated once and persisted next to the data
# so sessions/CSRF survive restarts. The old hard-coded insecure key is kept as
# a last-resort fallback if the file cannot be written (read-only media).
def _load_or_create_secret_key() -> str:
    key_file = DATA_DIR / 'secret_key.txt'
    try:
        if key_file.exists():
            value = key_file.read_text(encoding='utf-8').strip()
            if value:
                return value
        from django.core.management.utils import get_random_secret_key
        value = get_random_secret_key()
        key_file.write_text(value, encoding='utf-8')
        return value
    except Exception:
        return 'django-insecure-please-change-me'


SECRET_KEY = _load_or_create_secret_key()

# The offline desktop/APK build is meant for real schools, so it runs with
# debug disabled. The online/dev edition keeps DEBUG on for convenience.
DEBUG = not IS_OFFLINE_EDITION

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://work-1-muruuxfrxlthhzis.prod-runtime.all-hands.dev',
    'https://work-2-muruuxfrxlthhzis.prod-runtime.all-hands.dev',
    'http://localhost:12000',
    'http://localhost:12001',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Suppress the "your URLconf does not have a leading slash" warning class of
# noise in the packaged build and keep the console free for real errors.
if IS_OFFLINE_EDITION:
    SILENCED_SYSTEM_CHECKS = ['security.W018']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'school',
    'licensing',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.FlexibleCsrfMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'licensing.middleware.LicenseCheckMiddleware',
]

ROOT_URLCONF = 'django_sms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'school' / 'templates',
            BASE_DIR / 'licensing' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'licensing.templatetags.feature_tags.get_license_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_sms.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}

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

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'school' / 'static',
    BASE_DIR / 'core' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_USE_FINDERS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
