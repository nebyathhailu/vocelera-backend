import environ
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    # Declare types AND safe defaults for every variable.
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-change-me-in-production"),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1","wiley-argillaceous-magdalene.ngrok-free.dev"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    DATABASE_URL=(str, ""),           
    GEMINI_API_KEY=(str, ""),        
    GEMINI_MODEL=(str, "gemini-2.5-flash"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    TWILIO_ACCOUNT_SID=(str, ""),
    TWILIO_AUTH_TOKEN=(str, ""),
    TWILIO_WHATSAPP_NUMBER=(str, "whatsapp:+14155238886"),
    INSIGHT_TRIGGER_EVERY_N_MESSAGES=(int, 10),
    )

environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY   = env("SECRET_KEY")
DEBUG        = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Installed Apps
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "channels",
]

LOCAL_APPS = [
    "users",
    "projects",
    "messages_app",
    "insights",
    "reports",
    "collaboration",
    "ai_app",
    "twilio_app",
    "document_analysis"
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# URLs & WSGI/ASGI
# ---------------------------------------------------------------------------
ROOT_URLCONF       = "vocelera.urls"
WSGI_APPLICATION   = "vocelera.wsgi.application"
ASGI_APPLICATION   = "vocelera.asgi.application"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ---------------------------------------------------------------------------
# Database
# Tries DATABASE_URL from .env first; falls back to local SQLite.
# ---------------------------------------------------------------------------
_database_url = env("DATABASE_URL")

if _database_url:
    DATABASES = {"default": env.db_url("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_URL  = "/static/"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Gemini AI
# ---------------------------------------------------------------------------
GEMINI_API_KEY   = env("GEMINI_API_KEY")
GEMINI_MODEL     = env("GEMINI_MODEL")
GEMINI_MAX_TOKENS = 8192
GEMINI_TEMPERATURE = 0.4

# ---------------------------------------------------------------------------
# Twilio / WhatsApp
# ---------------------------------------------------------------------------
TWILIO_ACCOUNT_SID      = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN       = env("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER  = env("TWILIO_WHATSAPP_NUMBER")

# How many new WhatsApp messages must arrive before AI insights are regenerated
INSIGHT_TRIGGER_EVERY_N_MESSAGES = env("INSIGHT_TRIGGER_EVERY_N_MESSAGES")

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL      = env("REDIS_URL")
CELERY_RESULT_BACKEND  = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT  = ["json"]
CELERY_TASK_SERIALIZER = "json"

# ---------------------------------------------------------------------------
# Django Channels (WebSocket — real-time dashboard)
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL")],
        },
    }
}

# ---------------------------------------------------------------------------
# drf-spectacular (API Docs)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Vocelera API",
    "DESCRIPTION": "AI-powered citizen feedback analysis platform",
    "VERSION": "2.0.0",
}

# File upload size limit (50MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE  = 52428800