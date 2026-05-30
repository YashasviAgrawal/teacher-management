from django.urls import path

from . import views

urlpatterns = [
    # ── CLASSES ──────────────────────────────────────────────────────────────
    # GET  /api/v1/classes/        — List all classes       (Both)
    # POST /api/v1/classes/        — Create a new class     (Admin)
    path("classes/", views.ClassListCreateView.as_view(), name="class-list-create"),

    # PUT    /api/v1/classes/{id}/ — Update class name/desc (Admin)
    # DELETE /api/v1/classes/{id}/ — Soft-delete class      (Admin)
    path("classes/<uuid:pk>/", views.ClassDetailView.as_view(), name="class-detail"),

    # ── SECTIONS ─────────────────────────────────────────────────────────────
    # GET  /api/v1/sections/       — List all sections, ?class_id= filter (Both)
    # POST /api/v1/sections/       — Create a new section                  (Admin)
    path("sections/", views.SectionListCreateView.as_view(), name="section-list-create"),

    # PUT /api/v1/sections/{id}/   — Update a section                     (Admin)
    path("sections/<uuid:pk>/", views.SectionDetailView.as_view(), name="section-detail"),

    # ── SUBJECTS ─────────────────────────────────────────────────────────────
    # GET  /api/v1/subjects/       — List all subjects      (Both)
    # POST /api/v1/subjects/       — Create a new subject   (Admin)
    path("subjects/", views.SubjectListCreateView.as_view(), name="subject-list-create"),

    # PUT    /api/v1/subjects/{id}/ — Update subject details (Admin)
    # DELETE /api/v1/subjects/{id}/ — Soft-delete subject    (Admin)
    path("subjects/<uuid:pk>/", views.SubjectDetailView.as_view(), name="subject-detail"),
]
