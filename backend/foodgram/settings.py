import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Определяем окружение
DJANGO_ENV = os.getenv("DJANGO_ENV", "production").lower()

# === БАЗОВЫЕ НАСТРОЙКИ ===

SECRET_KEY = os.getenv("SECRET_KEY", "dev-unsafe")

DEBUG = os.getenv("DEBUG", "0") == "1" if DJANGO_ENV == "production" else True

cloud_host = os.getenv("CLOUD_HOST")
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

if cloud_host:
    ALLOWED_HOSTS.append(cloud_host)

if DJANGO_ENV == "local":
    ALLOWED_HOSTS = ["*"]


# === INSTALLED_APPS ===

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "django_filters",
    # local
    "recipes",
    "api",
]

# Локальные расширения
if DJANGO_ENV == "local":
    INSTALLED_APPS += ["debug_toolbar"]


# === MIDDLEWARE ===

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DJANGO_ENV == "local":
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]


# === DATABASES ===

if DJANGO_ENV == "local":
    # SQLite для разработки
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # PostgreSQL из Docker
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT", 5432),
        }
    }


# Остальная конфигурация — как в твоём settings.py

AUTH_USER_MODEL = "recipes.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 6,
}

DJOSER = {
    "LOGIN_FIELD": "email",
    "SERIALIZERS": {
        "user": "api.serializers.UserSerializer",
        "current_user": "api.serializers.UserSerializer",
        "user_create": "api.serializers.UserCreateSerializer",
    },
    "PERMISSIONS": {
        "user": ["rest_framework.permissions.AllowAny"],
        "user_list": ["rest_framework.permissions.AllowAny"],
        "current_user": ["rest_framework.permissions.IsAuthenticated"],
    },
}

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"

LANGUAGES = [("ru", "Русский"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "collected_static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if DJANGO_ENV == "local":
    INTERNAL_IPS = ["127.0.0.1"]
