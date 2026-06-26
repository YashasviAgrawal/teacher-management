from django.urls import path

from .views import SuccessManagerDashboardView, SuccessManagerAtRiskView

urlpatterns = [
    # GET /api/v1/success-manager/dashboard/ — Overview dashboard (Admin + SM)
    path('dashboard/', SuccessManagerDashboardView.as_view(), name='success-manager-dashboard'),

    # GET /api/v1/success-manager/at-risk/ — At-risk student list (Admin + SM)
    path('at-risk/', SuccessManagerAtRiskView.as_view(), name='success-manager-at-risk'),
]
