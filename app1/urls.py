from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # POST /api/v1/auth/login/ — Login with phone + password → JWT tokens
    path("login/", views.LoginView.as_view(), name="auth-login"),

    # POST /api/v1/auth/logout/ — Blacklist the refresh token
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),

    # POST /api/v1/auth/token/refresh/ — Get new access token using refresh token
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),

    # POST /api/v1/auth/change-password/ — Change password (requires current password)
    path("change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),

    # GET /api/v1/auth/me/ — Get logged-in user's profile
    path("me/", views.MeView.as_view(), name="auth-me"),
]
