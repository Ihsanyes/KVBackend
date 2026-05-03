from django.urls import path
from employees.views import (
    AttendanceListCreateView,
    AttendanceDetailView,
    BulkAttendanceView,
    LeaveRequestListCreateView,
    LeaveApprovalView,
    SalaryListCreateView,
    SalaryDetailView,
    PerformanceNoteListCreateView,
)

urlpatterns = [

    # Attendance
    path('attendance/',             AttendanceListCreateView.as_view(), name='attendance-list'),
    path('attendance/<int:pk>/',    AttendanceDetailView.as_view(),     name='attendance-detail'),
    path('attendance/bulk/',        BulkAttendanceView.as_view(),       name='attendance-bulk'),

    # Leave
    path('leaves/',                        LeaveRequestListCreateView.as_view(), name='leave-list'),
    path('leaves/<int:pk>/approval/',      LeaveApprovalView.as_view(),          name='leave-approval'),

    # Salary
    path('salary/',          SalaryListCreateView.as_view(), name='salary-list'),
    path('salary/<int:pk>/', SalaryDetailView.as_view(),     name='salary-detail'),

    # Performance
    path('performance/', PerformanceNoteListCreateView.as_view(), name='performance-list'),
]