"""
URL configuration for TeacherManagement project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication endpoints — /api/v1/auth/
    path('api/v1/auth/', include('app1.urls')),

    # User Management endpoints — /api/v1/users/
    path('api/v1/users/', include('app1.user_urls')),

    # School Structure endpoints — /api/v1/classes/ | /sections/ | /subjects/
    path('api/v1/', include('app1.school_urls')),

    # Teacher Assignments endpoints — /api/v1/assignments/
    path('api/v1/assignments/', include('app1.assignment_urls')),

    # Timetable endpoints — /api/v1/timetable/
    path('api/v1/timetable/', include('app1.timetable_urls')),

    # Syllabus endpoints — /api/v1/chapters/ | /api/v1/subtopics/ | /api/v1/subjects/{id}/full-syllabus/
    path('api/v1/', include('app1.syllabus_urls')),

    # Academic Year & Calendar endpoints — /api/v1/academic-years/ | /api/v1/calendar/
    path('api/v1/', include('app1.calendar_urls')),

    # Pacing Engine endpoints — /api/v1/pacing/
    path('api/v1/', include('app1.pacing_urls')),

    # Session Tracking endpoints — /api/v1/sessions/
    path('api/v1/', include('app1.session_urls')),

    # Teacher Attendance endpoints — /api/v1/attendance/
    path('api/v1/', include('app1.attendance_urls')),

    # Audit Trail endpoints — /api/v1/audit-logs/
    path('api/v1/', include('app1.audit_urls')),

    # Admin Dashboard endpoints — /api/v1/dashboard/
    path('api/v1/', include('app1.dashboard_urls')),

    # Teacher Dashboard endpoints — /api/v1/teacher-dashboard/
    path('api/v1/', include('app1.teacher_dashboard_urls')),
]
