from django.urls import path
from .views import (
    MeView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    CSRFTokenView,
)

urlpatterns = [
    path("me/auth/login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("me/auth/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("me/auth/logout/", LogoutView.as_view(), name="logout"),
    path("me/auth/csrf/", CSRFTokenView.as_view(), name="csrf"),
    path("me/auth/me/", MeView.as_view(), name="me"),
]
