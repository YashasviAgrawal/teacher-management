from django.urls import path

from . import views

urlpatterns = [
    # GET  /api/v1/dashboard/overview/ — High-level school statistics (Admin Only)
    path("dashboard/overview/", views.AdminDashboardOverviewView.as_view(), name="dashboard-overview"),

    # GET  /api/v1/dashboard/syllabus-progress/ — Progress percentages by assignment (Admin Only)
    path("dashboard/syllabus-progress/", views.AdminDashboardSyllabusProgressView.as_view(), name="dashboard-syllabus-progress"),

    # GET  /api/v1/dashboard/unmarked-topics/ — Uncovered subtopics (Admin Only)
    path("dashboard/unmarked-topics/", views.AdminDashboardUnmarkedTopicsView.as_view(), name="dashboard-unmarked-topics"),

    # GET  /api/v1/dashboard/teacher-activity/ — Teacher consistency & inactivity flags (Admin Only)
    path("dashboard/teacher-activity/", views.AdminDashboardTeacherActivityView.as_view(), name="dashboard-teacher-activity"),

    # GET  /api/v1/dashboard/behind-schedule/ — Pacing-behind alerts (Admin Only)
    path("dashboard/behind-schedule/", views.AdminDashboardBehindScheduleView.as_view(), name="dashboard-behind-schedule"),

    # GET  /api/v1/dashboard/test-frequency/ — Subject-wise test counts (Admin Only)
    path("dashboard/test-frequency/", views.AdminDashboardTestFrequencyView.as_view(), name="dashboard-test-frequency"),

    # GET  /api/v1/dashboard/revision-coverage/ — Chapter-wise revision counts (Admin Only)
    path("dashboard/revision-coverage/", views.AdminDashboardRevisionCoverageView.as_view(), name="dashboard-revision-coverage"),
]
