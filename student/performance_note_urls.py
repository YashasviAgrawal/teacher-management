from django.urls import path

from .views import StudentPerformanceNoteDetailView

urlpatterns = [
    # PATCH  /api/v1/performance-notes/{id}/ — Edit a note (Admin + Teacher: author only)
    # DELETE /api/v1/performance-notes/{id}/ — Delete a note (Admin + Teacher: author only)
    path('<uuid:pk>/', StudentPerformanceNoteDetailView.as_view(), name='performance-note-detail'),
]
