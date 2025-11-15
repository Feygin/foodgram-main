from django.urls import path
from .views import ShortLinkRedirectView

urlpatterns = [
    path("s/<slug:code>/", ShortLinkRedirectView.as_view(), name="short-link"),
]