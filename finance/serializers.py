from rest_framework import serializers
from django.db import transaction

from finance.models import Invoice, Payment, Expense
from jobs.models import JobCard, JobCardPart, JobCardService


# ── Payment ───────────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True
    )

    class Meta:
        model  = Payment
        fields = [
            'id', 'amount', 'payment_date', 'payment_mode',
            'transaction_ref', 'received_by_name', 'notes', 'created_at',
        ]


# ── Invoice ───────────────────────────────────────────────────

class InvoiceSerializer(serializers.ModelSerializer):
    customer_name  = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    job_number     = serializers.CharField(source='job_card.job_number', read_only=True)
    payments       = PaymentSerializer(many=True, read_only=True)
    amount_paid    = serializers.SerializerMethodField()
    amount_due     = serializers.SerializerMethodField()

    class Meta:
        model  = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_date',
            'job_card', 'job_number',
            'customer', 'customer_name', 'customer_phone',
            'parts_total', 'labour_total',
            'discount_amount', 'tax_amount', 'total_amount',
            'payment_status', 'payment_mode',
            'amount_paid', 'amount_due',
            'notes', 'payments', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'invoice_number', 'parts_total', 'labour_total',
            'total_amount', 'payment_status',
        ]

    def get_amount_paid(self, obj):
        return sum(p.amount for p in obj.payments.all())

    def get_amount_due(self, obj):
        paid = sum(p.amount for p in obj.payments.all())
        return obj.total_amount - paid


class GenerateInvoiceSerializer(serializers.Serializer):
    """
    Generate invoice from a completed job card.
    Calculates totals from JobCardPart + JobCardService automatically.
    """
    job_card      = serializers.PrimaryKeyRelatedField(queryset=JobCard.objects.all())
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    tax_rate      = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Tax % on labour (parts tax already in PO)'
    )
    notes         = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_job_card(self, value):
        workshop = self.context.get('workshop')

        # Must belong to this workshop
        if value.workshop != workshop:
            raise serializers.ValidationError("Job card not found in your workshop")

        # Must be completed
        if value.status not in ['COMPLETED', 'DELIVERED']:
            raise serializers.ValidationError(
                "Invoice can only be generated for COMPLETED or DELIVERED jobs"
            )

        # No duplicate invoice
        if hasattr(value, 'invoice'):
            raise serializers.ValidationError(
                "Invoice already exists for this job card"
            )

        return value

    def create(self, validated_data):
        from finance.services import generate_invoice_number

        job_card        = validated_data['job_card']
        discount_amount = validated_data.get('discount_amount', 0)
        tax_rate        = validated_data.get('tax_rate', 0)
        notes           = validated_data.get('notes', '')
        workshop        = self.context['workshop']
        user            = self.context['request'].user

        # Calculate parts total from JobCardPart
        parts_total = sum(
            p.line_total for p in job_card.parts_used.filter(is_returned=False)
        )

        # Calculate labour total from JobCardService
        labour_total = sum(
            s.labour_charge for s in job_card.services.all()
        )

        subtotal   = parts_total + labour_total - discount_amount
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total      = round(subtotal + tax_amount, 2)

        with transaction.atomic():
            invoice = Invoice.objects.create(
                workshop        = workshop,
                job_card        = job_card,
                customer        = job_card.customer,
                invoice_number  = generate_invoice_number(workshop),
                parts_total     = parts_total,
                labour_total    = labour_total,
                discount_amount = discount_amount,
                tax_amount      = tax_amount,
                total_amount    = max(total, 0),
                payment_status  = 'UNPAID',
                notes           = notes,
                created_by      = user,
            )

        return invoice


# ── Collect Payment ───────────────────────────────────────────

class CollectPaymentSerializer(serializers.Serializer):
    amount          = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    payment_mode    = serializers.ChoiceField(choices=Invoice.PaymentMode.choices)
    transaction_ref = serializers.CharField(required=False, allow_blank=True, default='')
    notes           = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_amount(self, value):
        invoice = self.context.get('invoice')
        if not invoice:
            return value

        paid = sum(p.amount for p in invoice.payments.all())
        due  = invoice.total_amount - paid

        if value > due:
            raise serializers.ValidationError(
                f"Amount ₹{value} exceeds due amount ₹{due}"
            )
        return value

    def save(self, invoice, received_by):
        from finance.services import collect_payment
        return collect_payment(
            invoice      = invoice,
            amount       = self.validated_data['amount'],
            payment_mode = self.validated_data['payment_mode'],
            transaction_ref = self.validated_data.get('transaction_ref', ''),
            notes        = self.validated_data.get('notes', ''),
            received_by  = received_by,
        )


# ── Expense ───────────────────────────────────────────────────

class ExpenseSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )

    class Meta:
        model  = Expense
        fields = [
            'id', 'category', 'title', 'amount',
            'expense_date', 'paid_to', 'payment_mode',
            'receipt_ref', 'notes',
            'created_by_name', 'created_at',
        ]

    def create(self, validated_data):
        validated_data['workshop']   = self.context['workshop']
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)