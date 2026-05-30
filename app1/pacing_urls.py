from django.urls import path

from . import views

urlpatterns = [
    # GET /api/v1/pacing/ — View all pacing status (Admin)
    path("pacing/", views.PacingListView.as_view(), name="pacing-list"),

    # GET /api/v1/pacing/my-pacing/ — Teacher views own pacing
    path("pacing/my-pacing/", views.MyPacingView.as_view(), name="pacing-my-pacing"),

    # GET /api/v1/pacing/behind-alerts/ — List behind schedule (Admin)
    path("pacing/behind-alerts/", views.BehindAlertsView.as_view(), name="pacing-behind-alerts"),

    # POST /api/v1/pacing/recalculate/ — Manually trigger recalculation (Admin)
    path("pacing/recalculate/", views.RecalculatePacingView.as_view(), name="pacing-recalculate"),

    # GET /api/v1/pacing/{assignment_id}/chapter/{chapter_id}/ — View specific chapter pacing
    path("pacing/<uuid:assignment_id>/chapter/<uuid:chapter_id>/", views.PacingDetailView.as_view(), name="pacing-detail"),
]
