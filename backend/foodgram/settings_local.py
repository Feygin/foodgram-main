from .settings import *

# ————————————————————————————
# ЛОКАЛЬНАЯ БАЗА ДЛЯ РАЗРАБОТКИ (SQLite)
# ————————————————————————————
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Включаем DEBUG локально
DEBUG = True

# Разрешаем localhost
ALLOWED_HOSTS = ["*"]

# Добавляем django_debug_toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = [
    '127.0.0.1',
] 