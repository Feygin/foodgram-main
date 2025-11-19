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
