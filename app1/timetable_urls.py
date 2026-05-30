from django.urls import path

from . import views

urlpatterns = [
    # GET  /api/v1/timetable/        — List all timetable slots (Admin)
    # POST /api/v1/timetable/        — Create a new period slot (Admin)
    path("", views.TimetableListCreateView.as_view(), name="timetable-list-create"),

    # GET  /api/v1/timetable/my-schedule/ — Teacher views their own weekly timetable (Teacher/Auth)
    path("my-schedule/", views.MyScheduleView.as_view(), name="timetable-my-schedule"),

    # GET  /api/v1/timetable/today/       — Teacher views today's periods (Teacher/Auth)
    path("today/", views.MyTodayScheduleView.as_view(), name="timetable-my-today"),

    # PUT    /api/v1/timetable/{id}/   — Update a period slot (Admin)
    # DELETE /api/v1/timetable/{id}/   — Remove a period slot (Admin)
    path("<uuid:pk>/", views.TimetableDetailView.as_view(), name="timetable-detail"),
]
