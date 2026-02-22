from django.urls import path
from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('employee/', CreateEmployeeView.as_view(), name='create_employee'),
    path('preview-employee-id/', PreviewEmployeeIdView.as_view()),

]