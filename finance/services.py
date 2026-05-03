from django.db import transaction


def generate_invoice_number(workshop):
    """Thread-safe invoice number. Format: W{id}INV{0001}"""
    from finance.models import Invoice
    with transaction.atomic():
        last = Invoice.objects.filter(workshop=workshop).order_by('-id').first()
        number = (last.id + 1) if last else 1
    return f"W{workshop.id}INV{str(number).zfill(4)}"


def collect_payment(invoice, amount, payment_mode, transaction_ref, notes, received_by):
    """
    Record a payment against an invoice.
    Updates invoice payment_status automatically.
    """
    from finance.models import Payment

    with transaction.atomic():
        payment = Payment.objects.create(
            invoice         = invoice,
            amount          = amount,
            payment_mode    = payment_mode,
            transaction_ref = transaction_ref,
            notes           = notes,
            received_by     = received_by,
        )

        # Recalculate payment status
        total_paid = sum(p.amount for p in invoice.payments.all())

        if total_paid >= invoice.total_amount:
            invoice.payment_status = 'PAID'
            invoice.payment_mode   = payment_mode  # last mode used
        elif total_paid > 0:
            invoice.payment_status = 'PARTIAL'
        else:
            invoice.payment_status = 'UNPAID'

        invoice.save()

    return payment