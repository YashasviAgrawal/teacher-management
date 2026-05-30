from django.urls import path

from . import views

urlpatterns = [
    # GET  /api/v1/attendance/ — List all attendance records (Admin Only)
    # POST /api/v1/attendance/ — Record a teacher's attendance (Admin Only)
    path("attendance/", views.AttendanceListCreateView.as_view(), name="attendance-list-create"),

    # GET  /api/v1/attendance/my-attendance/ — Teacher views own attendance history (Teacher Only)
    # Note: Must be before `<uuid:pk>/` to avoid UUID format matching conflict.
    path("attendance/my-attendance/", views.MyAttendanceView.as_view(), name="attendance-my-attendance"),

    # PATCH /api/v1/attendance/{id}/ — Correct an existing entry (Admin Only)
    path("attendance/<uuid:pk>/", views.AttendanceDetailView.as_view(), name="attendance-detail"),
]
