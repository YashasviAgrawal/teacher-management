from django.urls import path
from . import views

urlpatterns = [
    path("teacher-dashboard/my-overview/", views.TeacherDashboardOverviewView.as_view(), name="teacher-dashboard-overview"),
    path("teacher-dashboard/syllabus-status/", views.TeacherDashboardSyllabusStatusView.as_view(), name="teacher-dashboard-syllabus-status"),
    path("teacher-dashboard/pending-topics/", views.TeacherDashboardPendingTopicsView.as_view(), name="teacher-dashboard-pending-topics"),
    path("teacher-dashboard/today-schedule/", views.TeacherDashboardTodayScheduleView.as_view(), name="teacher-dashboard-today-schedule"),
]
