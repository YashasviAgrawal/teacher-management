from django.urls import path

from .views import (
    ExamSubjectMarksView,
    ExamSubjectSubmitView,
)

urlpatterns = [
    # POST /api/v1/exam-subjects/{id}/marks/ — Enter/save marks (draft)
    # GET  /api/v1/exam-subjects/{id}/marks/ — Marksheet for a paper
    path('<uuid:exam_subject_pk>/marks/', ExamSubjectMarksView.as_view(), name='exam-subject-marks'),

    # POST /api/v1/exam-subjects/{id}/submit/ — Submit marks
    path('<uuid:exam_subject_pk>/submit/', ExamSubjectSubmitView.as_view(), name='exam-subject-submit'),
]
