from django.urls import path
from vehicles.views import (
    CustomerListCreateView, CustomerDetailView,
    VehicleListCreateView, VehicleDetailView,
)

urlpatterns = [

    # Customer
    path('customers/',          CustomerListCreateView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', CustomerDetailView.as_view(),     name='customer-detail'),

    # Vehicle
    path('vehicles/',          VehicleListCreateView.as_view(), name='vehicle-list'),
    path('vehicles/<int:pk>/', VehicleDetailView.as_view(),     name='vehicle-detail'),
]