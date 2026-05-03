from django.db import transaction


def generate_job_number(workshop):
    """Thread-safe job number. Format: W{id}JC{0001}"""
    from jobs.models import JobCard
    with transaction.atomic():
        last = JobCard.objects.filter(workshop=workshop).order_by('-id').first()
        number = (last.id + 1) if last else 1
    return f"W{workshop.id}JC{str(number).zfill(4)}"


def issue_part_to_job(job_card, variant, quantity, unit_price, discount_pct, issued_by):
    """
    Issue a part to a job card:
    - Create JobCardPart
    - Create StockMovement (JOB_ISSUE)
    - Reduce Stock.quantity
    """
    from jobs.models import JobCardPart, StockMovement
    from inventory.models import Stock

    with transaction.atomic():
        # Calculate line total
        discount    = unit_price * quantity * discount_pct / 100
        line_total  = round(unit_price * quantity - discount, 2)

        # Create JobCardPart
        part = JobCardPart.objects.create(
            job_card        = job_card,
            product_variant = variant,
            quantity        = quantity,
            unit_price      = unit_price,
            discount_pct    = discount_pct,
            line_total      = line_total,
            issued_by       = issued_by,
        )

        # Stock Movement (OUT)
        StockMovement.objects.create(
            workshop        = job_card.workshop,
            product_variant = variant,
            movement_type   = 'JOB_ISSUE',
            quantity        = -quantity,  # negative = OUT
            unit_cost       = variant.cost_price,
            job_card        = job_card,
            reference_note  = f"Issued to {job_card.job_number}",
            moved_by        = issued_by,
        )

        # Reduce stock
        stock, _ = Stock.objects.select_for_update().get_or_create(
            workshop        = job_card.workshop,
            product_variant = variant,
        )
        stock.quantity -= quantity
        stock.save()

    return part


def return_part_from_job(job_card_part, returned_by):
    """
    Return a part from a job card back to stock.
    """
    from jobs.models import StockMovement
    from inventory.models import Stock

    if job_card_part.is_returned:
        raise ValueError("Part already returned")

    with transaction.atomic():
        job_card_part.is_returned = True
        job_card_part.save()

        variant = job_card_part.product_variant

        StockMovement.objects.create(
            workshop        = job_card_part.job_card.workshop,
            product_variant = variant,
            movement_type   = 'JOB_RETURN',
            quantity        = job_card_part.quantity,  # positive = IN
            unit_cost       = variant.cost_price,
            job_card        = job_card_part.job_card,
            reference_note  = f"Returned from {job_card_part.job_card.job_number}",
            moved_by        = returned_by,
        )

        stock, _ = Stock.objects.select_for_update().get_or_create(
            workshop        = job_card_part.job_card.workshop,
            product_variant = variant,
        )
        stock.quantity += job_card_part.quantity
        stock.save()

    return job_card_part