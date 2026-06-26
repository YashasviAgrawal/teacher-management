from django.urls import path

from .views import SuccessNoteDetailView

urlpatterns = [
    # PATCH /api/v1/success-notes/{id}/ — Update a success note (Admin + SM: author only)
    path('<uuid:pk>/', SuccessNoteDetailView.as_view(), name='success-note-detail'),
]
