from django.urls import path

from . import views

urlpatterns = [
    # GET  /api/v1/assignments/        — List all assignments (Admin)
    # POST /api/v1/assignments/        — Create a new assignment (Admin)
    path("", views.AssignmentListCreateView.as_view(), name="assignment-list-create"),

    # GET  /api/v1/assignments/my/     — Get own assignments (Teacher/Authenticated)
    path("my/", views.MyAssignmentsView.as_view(), name="assignment-my"),

    # GET  /api/v1/assignments/{id}/   — Get assignment details (Admin)
    path("<uuid:pk>/", views.AssignmentDetailView.as_view(), name="assignment-detail"),

    # PATCH /api/v1/assignments/{id}/deactivate/ — Soft-delete assignment (Admin)
    path("<uuid:pk>/deactivate/", views.AssignmentDeactivateView.as_view(), name="assignment-deactivate"),
]
