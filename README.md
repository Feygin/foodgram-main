# Foodgram — «Продуктовый помощник»

Онлайн-сервис для публикации рецептов. Пользователи могут:
- создавать, редактировать и удалять свои рецепты;
- подписываться на авторов;
- добавлять рецепты в избранное;
- формировать список покупок и выгружать его в виде файла;
- работать с API

## Автор

**ФИО:** Фейгин Александр Сергеевич
**GitHub:** [my-github](https://github.com/Feygin) 

## Технологический стек

**Backend:**
- Python 3.9+
- Django
- Django REST Framework
- Djoser (auth по токенам)
- PostgreSQL
- Gunicorn

**Инфраструктура:**
- Docker, Docker Compose
- Nginx
- GitHub Actions (CI/CD)
- Unix-подобный сервер (Ubuntu и т.п.)

## Полезные ссылки (продакшн)

- Главная страница проекта:  
  [`feygin-foodgram.viewdns.net`](feygin-foodgram.viewdns.net)

## Подготовка окружения

1. **Клонировать репозиторий:**

   ```bash
   git clone https://github.com/Feygin/foodgram-main.git
   cd foodgram-main
   ```

2. Создать файл окружения .env:

   ```
    # === Postgres container (used by the db service) ===
    POSTGRES_DB=foodgram
    POSTGRES_USER=foodgram_user
    POSTGRES_PASSWORD=foodgram_password

    # === Django (backend) connection to Postgres ===
    DB_HOST=db
    DB_PORT=5432

    # === Django app ===
    DJANGO_ENV=local #production
    SECRET_KEY='your_secret_key'
    DEBUG=0
    CLOUD_HOST=feygin-foodgram.viewdns.net
   ```

## Развёртывание в Docker

1. **Сборка и запуск контейнеров**

    ```
    docker compose up -d --build
    ```

2. **Миграции и статика**

    ```
    docker compose exec backend python manage.py migrate
    docker compose exec backend python manage.py collectstatic --noinput
    ```

3. **Импорт данных (ингредиенты, теги, фикстуры)**

    **Ингредиенты**

    ```
    docker compose exec backend python manage.py load_ingredients data/ingredients.json
    ```
    
    **Теги**

    ```
    docker compose exec backend python manage.py load_tags data/tags.json
    ```

## Локальный запуск без Docker

Задаем переменную окружения DJANGO_ENV=local

**Endpoints**

- [Сайт](http://127.0.0.1:8081/)
- [API](http://127.0.0.1:8081/api/)
- [Документация API](http://127.0.0.1:8081/api/docs/)
- [Админка](http://127.0.0.1:8081/admin/)
