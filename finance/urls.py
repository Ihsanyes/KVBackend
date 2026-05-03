from django.urls import path
from finance.views import (
    InvoiceListView,
    GenerateInvoiceView,
    InvoiceDetailView,
    CollectPaymentView,
    ExpenseListCreateView,
    ExpenseDetailView,
)

urlpatterns = [

    # Invoice
    path('invoices/',                          InvoiceListView.as_view(),       name='invoice-list'),
    path('invoices/generate/',                 GenerateInvoiceView.as_view(),   name='invoice-generate'),
    path('invoices/<int:pk>/',                 InvoiceDetailView.as_view(),     name='invoice-detail'),
    path('invoices/<int:pk>/collect-payment/', CollectPaymentView.as_view(),    name='invoice-collect-payment'),

    # Expense
    path('expenses/',          ExpenseListCreateView.as_view(), name='expense-list'),
    path('expenses/<int:pk>/', ExpenseDetailView.as_view(),     name='expense-detail'),
]