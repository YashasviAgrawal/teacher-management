from django.urls import path

from . import views

urlpatterns = [
    # GET /api/v1/sessions/ — View all sessions (Admin)
    # POST /api/v1/sessions/ — Log a new session (Teacher)
    path("sessions/", views.SessionListView.as_view(), name="session-list-create"),

    # GET /api/v1/sessions/my-sessions/ — Teacher views own sessions
    path("sessions/my-sessions/", views.MySessionListView.as_view(), name="session-my-sessions"),

    # GET /api/v1/sessions/{id}/ — View full details
    # PATCH /api/v1/sessions/{id}/ — Update session
    # DELETE /api/v1/sessions/{id}/ — Delete session
    path("sessions/<uuid:pk>/", views.SessionDetailView.as_view(), name="session-detail"),

    # POST /api/v1/sessions/{id}/topics/ — Add topic to session
    path("sessions/<uuid:session_id>/topics/", views.SessionTopicCreateView.as_view(), name="session-topic-create"),

    # PATCH /api/v1/sessions/{id}/topics/{tid}/ — Update topic
    # DELETE /api/v1/sessions/{id}/topics/{tid}/ — Remove topic
    path("sessions/<uuid:session_id>/topics/<uuid:topic_id>/", views.SessionTopicDetailView.as_view(), name="session-topic-detail"),
]
