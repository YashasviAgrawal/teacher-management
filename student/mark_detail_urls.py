from django.urls import path

from .views import MarkDetailView

urlpatterns = [
    # PATCH /api/v1/marks/{id}/ — Edit a mark
    path('<uuid:pk>/', MarkDetailView.as_view(), name='mark-detail'),
]
