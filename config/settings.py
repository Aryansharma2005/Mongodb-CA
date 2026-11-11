"""
Django settings for Personal Expense Tracker project.
Optimized for Serverless Vercel Deployment using Pure MongoDB.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-expense-tracker-mongo-cse494-secret-key-2026-prod")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver,.vercel.app")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
if ".vercel.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".vercel.app")
if "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")
if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

# CSRF Trusted Origins for Vercel
CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
    "https://*.now.sh",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if csrf_env:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in csrf_env.split(",") if origin.strip()])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tracker.apps.TrackerConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Pure MongoDB Architecture:
# Ephemeral SQLite in /tmp handles Django internal requirements (e.g. contenttypes, model checks).
# All user credentials, sessions, and expense data live persistently in MongoDB Atlas.
if os.path.exists("/tmp") and (
    os.getenv("VERCEL")
    or os.getenv("VERCEL_ENV")
    or str(BASE_DIR).startswith("/var/")
    or not os.access(BASE_DIR, os.W_OK)
):
    db_path = Path("/tmp") / "db.sqlite3"
else:
    db_path = BASE_DIR / "db.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": db_path,
    }
}

# Cryptographically signed cookie sessions - eliminates database session writes entirely
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600

# Dual Authentication Backends: checks MongoDB Atlas users collection first
AUTHENTICATION_BACKENDS = [
    "database.mongo_auth.MongoAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

WHITENOISE_USE_FINDERS = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
