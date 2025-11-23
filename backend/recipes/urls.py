from django.urls import path

from recipes.shortlinks import shortlink_redirect

urlpatterns = [
    path("s/<str:code>/", shortlink_redirect, name="short-link"),
]
