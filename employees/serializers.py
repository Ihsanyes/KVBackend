from rest_framework import serializers
from django.utils import timezone

from employees.models import Attendance, LeaveRequest, SalaryRecord, PerformanceNote
from users.models import User


# ── Attendance ────────────────────────────────────────────────

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    employee_id_code = serializers.CharField(
        source='employee.employee_id', read_only=True
    )

    class Meta:
        model  = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code',
            'date', 'status', 'check_in', 'check_out',
            'notes', 'created_at',
        ]

    def validate_employee(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError(
                "Employee not found in your workshop"
            )
        return value

    def validate(self, data):
        workshop = self.context.get('workshop')
        employee = data.get('employee', getattr(self.instance, 'employee', None))
        date     = data.get('date', getattr(self.instance, 'date', None))

        qs = Attendance.objects.filter(employee=employee, date=date)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Attendance already marked for this employee on this date"
            )
        return data

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


class BulkAttendanceSerializer(serializers.Serializer):
    """Mark attendance for multiple employees at once."""
    date    = serializers.DateField()
    records = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{"employee": 1, "status": "PRESENT", "check_in": "09:00"}, ...]'
    )

    def validate_records(self, value):
        if not value:
            raise serializers.ValidationError("At least one record required")
        for r in value:
            if 'employee' not in r or 'status' not in r:
                raise serializers.ValidationError(
                    "Each record needs employee id and status"
                )
        return value


# ── Leave Request ─────────────────────────────────────────────

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name   = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name', read_only=True
    )

    class Meta:
        model  = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name',
            'leave_type', 'from_date', 'to_date', 'reason',
            'status', 'approved_by', 'approved_by_name',
            'approved_at', 'created_at',
        ]
        read_only_fields = ['status', 'approved_by', 'approved_at']

    def validate_employee(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError(
                "Employee not found in your workshop"
            )
        return value

    def validate(self, data):
        from_date = data.get('from_date')
        to_date   = data.get('to_date')
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                "from_date cannot be after to_date"
            )
        return data

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


class LeaveApprovalSerializer(serializers.Serializer):
    """Owner approves or rejects a leave request."""
    action = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])

    def save(self, leave_request, approved_by):
        leave_request.status      = self.validated_data['action']
        leave_request.approved_by = approved_by
        leave_request.approved_at = timezone.now()
        leave_request.save()
        return leave_request


# ── Salary Record ─────────────────────────────────────────────

class SalaryRecordSerializer(serializers.ModelSerializer):
    employee_name    = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    employee_id_code = serializers.CharField(
        source='employee.employee_id', read_only=True
    )

    class Meta:
        model  = SalaryRecord
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code',
            'month', 'year',
            'base_salary', 'allowances', 'deductions', 'net_salary',
            'is_paid', 'paid_on', 'payment_mode',
            'notes', 'created_at',
        ]
        read_only_fields = ['net_salary']

    def validate_employee(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError(
                "Employee not found in your workshop"
            )
        return value

    def validate(self, data):
        workshop = self.context.get('workshop')
        employee = data.get('employee', getattr(self.instance, 'employee', None))
        month    = data.get('month', getattr(self.instance, 'month', None))
        year     = data.get('year', getattr(self.instance, 'year', None))

        qs = SalaryRecord.objects.filter(
            employee=employee, month=month, year=year
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Salary record already exists for this employee for this month/year"
            )
        return data

    def create(self, validated_data):
        # Auto-calculate net salary
        base       = validated_data.get('base_salary', 0)
        allowances = validated_data.get('allowances', 0)
        deductions = validated_data.get('deductions', 0)
        validated_data['net_salary'] = base + allowances - deductions
        validated_data['workshop']   = self.context['workshop']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Recalculate net on update
        base       = validated_data.get('base_salary', instance.base_salary)
        allowances = validated_data.get('allowances', instance.allowances)
        deductions = validated_data.get('deductions', instance.deductions)
        validated_data['net_salary'] = base + allowances - deductions
        return super().update(instance, validated_data)


# ── Performance Note ──────────────────────────────────────────

class PerformanceNoteSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.get_full_name', read_only=True
    )
    noted_by_name = serializers.CharField(
        source='noted_by.get_full_name', read_only=True
    )

    class Meta:
        model  = PerformanceNote
        fields = [
            'id', 'employee', 'employee_name',
            'noted_by', 'noted_by_name',
            'note', 'rating', 'created_at',
        ]
        read_only_fields = ['noted_by']

    def validate_employee(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError(
                "Employee not found in your workshop"
            )
        return value

    def validate_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def create(self, validated_data):
        validated_data['workshop']  = self.context['workshop']
        validated_data['noted_by']  = self.context['request'].user
        return super().create(validated_data)