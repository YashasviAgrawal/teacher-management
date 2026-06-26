from django.urls import path

from .views import (
    ExamListCreateView,
    ExamDetailView,
    ExamSubjectListCreateView,
    ExamPublishView,
)

urlpatterns = [
    # POST /api/v1/exams/         — Create exam event
    # GET  /api/v1/exams/         — List exams
    path('', ExamListCreateView.as_view(), name='exam-list-create'),

    # GET    /api/v1/exams/{id}/  — Retrieve details
    # PATCH  /api/v1/exams/{id}/  — Edit exam
    # DELETE /api/v1/exams/{id}/  — Delete exam
    path('<uuid:pk>/', ExamDetailView.as_view(), name='exam-detail'),

    # POST /api/v1/exams/{id}/subjects/ — Add class+subject paper
    # GET  /api/v1/exams/{id}/subjects/ — List subjects/papers under an exam
    path('<uuid:pk>/subjects/', ExamSubjectListCreateView.as_view(), name='exam-subject-list-create'),

    # POST /api/v1/exams/{id}/publish/  — Publish results and lock marks
    path('<uuid:pk>/publish/', ExamPublishView.as_view(), name='exam-publish'),
]
