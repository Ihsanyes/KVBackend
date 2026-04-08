from django.urls import path
from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('employee/', CreateListEmployeeView.as_view(), name='create_employee'),
    path('employee/<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('preview-employee-id/', PreviewEmployeeIdView.as_view()),
    path('assign-permission/', AssignPermissionView.as_view(), name='assign_permission'),

    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('pin-reset/', PinResetView.as_view(), name='pin_reset'),
    path('workshop/', WorkshopView.as_view(), name='workshop'),
    path("preferences/", UserPreferenceView.as_view(), name="user_preferences"),
]                       