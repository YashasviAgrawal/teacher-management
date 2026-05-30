from django.urls import path

from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Chapters Endpoints
    # -------------------------------------------------------------------------
    # GET  /api/v1/chapters/        — List all chapters (Both)
    # POST /api/v1/chapters/        — Create a new chapter (Admin)
    path("chapters/", views.ChapterListCreateView.as_view(), name="chapter-list-create"),

    # PUT    /api/v1/chapters/{id}/ — Update a chapter (Admin)
    # DELETE /api/v1/chapters/{id}/ — Soft delete a chapter (Admin)
    path("chapters/<uuid:pk>/", views.ChapterDetailView.as_view(), name="chapter-detail"),

    # -------------------------------------------------------------------------
    # SubTopics Endpoints
    # -------------------------------------------------------------------------
    # GET  /api/v1/subtopics/        — List all subtopics (Both)
    # POST /api/v1/subtopics/        — Add a subtopic under a chapter (Admin)
    path("subtopics/", views.SubTopicListCreateView.as_view(), name="subtopic-list-create"),

    # PUT    /api/v1/subtopics/{id}/ — Update a subtopic (Admin)
    # DELETE /api/v1/subtopics/{id}/ — Soft delete a subtopic (Admin)
    path("subtopics/<uuid:pk>/", views.SubTopicDetailView.as_view(), name="subtopic-detail"),

    # -------------------------------------------------------------------------
    # Full Syllabus Endpoint
    # -------------------------------------------------------------------------
    # GET  /api/v1/subjects/{id}/full-syllabus/ — Retrieve full syllabus (Both)
    path("subjects/<uuid:subject_id>/full-syllabus/", views.FullSyllabusView.as_view(), name="subject-full-syllabus"),
]
