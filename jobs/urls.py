from django.urls import path
from jobs.views import (
    JobCardListCreateView,
    JobCardDetailView,
    IssuePartView,
    ReturnPartView,
    AddServiceView,
    DeleteServiceView,
)

urlpatterns = [

    # Job Card
    path('', JobCardListCreateView.as_view(), name='jobcard-list'),
    path('<int:pk>/', JobCardDetailView.as_view(), name='jobcard-detail'),

    # Parts
    path('<int:pk>/issue-part/', IssuePartView.as_view(), name='jobcard-issue-part'),
    path('<int:pk>/parts/<int:part_pk>/return/', ReturnPartView.as_view(), name='jobcard-return-part'),

    # Services
    path('<int:pk>/add-service/', AddServiceView.as_view(), name='jobcard-add-service'),
    path('<int:pk>/services/<int:service_pk>/', DeleteServiceView.as_view(), name='jobcard-delete-service'),
]