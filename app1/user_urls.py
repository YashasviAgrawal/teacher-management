from django.urls import path

from . import views

urlpatterns = [
    # GET   /api/v1/users/    — List all teachers (Admin)
    # POST  /api/v1/users/    — Create teacher    (Admin)
    path("", views.TeacherListCreateView.as_view(), name="user-list-create"),

    # GET   /api/v1/users/me/ — Own profile  (Both)
    # PATCH /api/v1/users/me/ — Update own phone + photo (Both)
    # ⚠️  Must be before {pk}/ so Django matches 'me' before trying it as a UUID
    path("me/", views.MyProfileView.as_view(), name="user-me"),

    # GET   /api/v1/users/{id}/ — Teacher detail (Admin)
    # PUT   /api/v1/users/{id}/ — Update teacher  (Admin)
    path("<uuid:pk>/", views.TeacherDetailView.as_view(), name="user-detail"),

    # PATCH /api/v1/users/{id}/activate/      — Activate account   (Admin)
    path("<uuid:pk>/activate/", views.TeacherActivateView.as_view(), name="user-activate"),

    # PATCH /api/v1/users/{id}/deactivate/    — Deactivate account  (Admin)
    path("<uuid:pk>/deactivate/", views.TeacherDeactivateView.as_view(), name="user-deactivate"),

    # PATCH /api/v1/users/{id}/reset-password/ — Force reset password (Admin)
    path("<uuid:pk>/reset-password/", views.TeacherResetPasswordView.as_view(), name="user-reset-password"),
]
