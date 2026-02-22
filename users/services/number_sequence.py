from django.db import transaction

def generate_employee_id():
    from ..models import EmployeeIdSequence, User

    with transaction.atomic():
        seq, _ = EmployeeIdSequence.objects.select_for_update().get_or_create(id=1)

        next_number = seq.last_number + 1

        while True:
            emp_id = f"EMP{str(next_number).zfill(4)}"

            if not User.objects.filter(employee_id=emp_id).exists():
                break

            next_number += 1

        seq.last_number = next_number
        seq.save()

        return emp_id