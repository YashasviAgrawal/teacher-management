from django.urls import path

from . import views

urlpatterns = [
    # GET  /api/v1/audit-logs/ — View all system action logs (Admin Only)
    path("audit-logs/", views.AuditLogListView.as_view(), name="audit-log-list"),

    # GET  /api/v1/audit-logs/{id}/ — Retrieve full details of specific log (Admin Only)
    path("audit-logs/<uuid:pk>/", views.AuditLogDetailView.as_view(), name="audit-log-detail"),

    # GET  /api/v1/audit-logs/user/{user_id}/ — View logs by a specific user (Admin Only)
    path("audit-logs/user/<uuid:user_id>/", views.AuditLogByUserView.as_view(), name="audit-log-by-user"),

    # GET  /api/v1/audit-logs/entity/{entity_id}/ — View logs for a specific entity (Admin Only)
    path("audit-logs/entity/<uuid:entity_id>/", views.AuditLogByEntityView.as_view(), name="audit-log-by-entity"),
]
