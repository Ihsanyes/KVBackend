from django.urls import path
from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('employee/', CreateListEmployeeView.as_view(), name='create_employee'),
    path('preview-employee-id/', PreviewEmployeeIdView.as_view()),
    path('assign-permission/', AssignPermissionView.as_view(), name='assign_permission'),

]