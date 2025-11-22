from django.urls import path
from recipes.shortlinks import ShortLinkRedirectView

urlpatterns = [
    path("s/<str:code>/", ShortLinkRedirectView.as_view(), name="short-link"),
]
