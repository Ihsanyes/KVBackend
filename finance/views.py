from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.permission import IsOwnerOrSuperUser
from finance.models import Invoice, Expense
from finance.serializers import (
    InvoiceSerializer,
    GenerateInvoiceSerializer,
    CollectPaymentSerializer,
    ExpenseSerializer,
)


def ws(request):
    return request.user.workshop


# ── Invoice ───────────────────────────────────────────────────

class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        invoices = Invoice.objects.filter(
            workshop=workshop
        ).select_related(
            'customer', 'job_card'
        ).prefetch_related('payments')

        # Filter by payment status
        status = request.query_params.get('status')
        if status:
            invoices = invoices.filter(payment_status=status.upper())

        # Search by invoice number or customer name
        search = request.query_params.get('search')
        if search:
            invoices = invoices.filter(
                invoice_number__icontains=search
            ) | invoices.filter(
                customer__name__icontains=search
            )

        return Response(
            InvoiceSerializer(invoices, many=True).data
        )


class GenerateInvoiceView(APIView):
    """Generate invoice from a completed job card."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        workshop = ws(request)
        s = GenerateInvoiceSerializer(
            data=request.data,
            context={'workshop': workshop, 'request': request}
        )
        if s.is_valid():
            invoice = s.save()
            return Response({
                "status": "1",
                "message": "Invoice generated",
                "invoice_number": invoice.invoice_number,
                "total_amount": str(invoice.total_amount),
                "invoice": InvoiceSerializer(invoice).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Invoice.objects.prefetch_related(
                'payments'
            ).select_related(
                'customer', 'job_card'
            ).get(pk=pk, workshop=ws(request))
        except Invoice.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Invoice not found"}, status=404
            )
        return Response(InvoiceSerializer(obj).data)


class CollectPaymentView(APIView):
    """Collect payment against an invoice."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        workshop = ws(request)
        try:
            invoice = Invoice.objects.prefetch_related('payments').get(
                pk=pk, workshop=workshop
            )
        except Invoice.DoesNotExist:
            return Response(
                {"status": "0", "message": "Invoice not found"}, status=404
            )

        if invoice.payment_status == 'PAID':
            return Response(
                {"status": "0", "message": "Invoice already fully paid"}, status=400
            )

        s = CollectPaymentSerializer(
            data=request.data,
            context={'invoice': invoice}
        )
        if s.is_valid():
            payment = s.save(invoice=invoice, received_by=request.user)
            return Response({
                "status": "1",
                "message": "Payment recorded",
                "payment_id": payment.id,
                "payment_status": invoice.payment_status,
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Expense ───────────────────────────────────────────────────

class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        expenses = Expense.objects.filter(workshop=workshop)

        # Filter by category
        category = request.query_params.get('category')
        if category:
            expenses = expenses.filter(category=category.upper())

        # Filter by date range
        from_date = request.query_params.get('from')
        to_date   = request.query_params.get('to')
        if from_date:
            expenses = expenses.filter(expense_date__gte=from_date)
        if to_date:
            expenses = expenses.filter(expense_date__lte=to_date)

        return Response(
            ExpenseSerializer(expenses, many=True).data
        )

    def post(self, request):
        s = ExpenseSerializer(
            data=request.data,
            context={'workshop': ws(request), 'request': request}
        )
        if s.is_valid():
            expense = s.save()
            return Response({
                "status": "1",
                "message": "Expense recorded",
                "expense": ExpenseSerializer(expense).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Expense.objects.get(pk=pk, workshop=ws(request))
        except Expense.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Expense not found"}, status=404
            )
        return Response(ExpenseSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Expense not found"}, status=404
            )
        s = ExpenseSerializer(
            obj, data=request.data, partial=True,
            context={'workshop': ws(request), 'request': request}
        )
        if s.is_valid():
            s.save()
            return Response({"status": "1", "expense": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Expense not found"}, status=404
            )
        obj.delete()
        return Response({"status": "1", "message": "Expense deleted"})