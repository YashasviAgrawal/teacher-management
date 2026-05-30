from django.urls import path

from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Academic Years Endpoints
    # -------------------------------------------------------------------------
    # GET  /api/v1/academic-years/        — List all academic years (Both)
    # POST /api/v1/academic-years/        — Create a new academic year (Admin)
    path("academic-years/", views.AcademicYearListCreateView.as_view(), name="academic-year-list-create"),

    # PATCH /api/v1/academic-years/{id}/set-current/ — Mark year as current (Admin)
    path("academic-years/<uuid:pk>/set-current/", views.AcademicYearCurrentView.as_view(), name="academic-year-set-current"),

    # -------------------------------------------------------------------------
    # Calendar Endpoints
    # -------------------------------------------------------------------------
    # GET  /api/v1/calendar/        — List all events (Both)
    # POST /api/v1/calendar/        — Create a new event (Admin)
    path("calendar/", views.CalendarEventListCreateView.as_view(), name="calendar-list-create"),

    # GET /api/v1/calendar/effective-days/ — Calculate working days (Both)
    path("calendar/effective-days/", views.EffectiveDaysView.as_view(), name="calendar-effective-days"),

    # PUT    /api/v1/calendar/{id}/ — Update an event (Admin)
    # DELETE /api/v1/calendar/{id}/ — Delete an event (Admin)
    path("calendar/<uuid:pk>/", views.CalendarEventDetailView.as_view(), name="calendar-detail"),
]
