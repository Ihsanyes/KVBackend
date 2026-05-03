from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from users.permission import IsOwnerOrSuperUser
from employees.models import Attendance, LeaveRequest, SalaryRecord, PerformanceNote
from employees.serializers import (
    AttendanceSerializer, BulkAttendanceSerializer,
    LeaveRequestSerializer, LeaveApprovalSerializer,
    SalaryRecordSerializer,
    PerformanceNoteSerializer,
)


def ws(request):
    return request.user.workshop


# ── Attendance ────────────────────────────────────────────────

class AttendanceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop    = ws(request)
        attendances = Attendance.objects.filter(
            workshop=workshop
        ).select_related('employee')

        # Filter by date
        date = request.query_params.get('date')
        if date:
            attendances = attendances.filter(date=date)

        # Filter by employee
        employee_id = request.query_params.get('employee')
        if employee_id:
            attendances = attendances.filter(employee_id=employee_id)

        # Filter by month/year
        month = request.query_params.get('month')
        year  = request.query_params.get('year')
        if month and year:
            attendances = attendances.filter(
                date__month=month, date__year=year
            )

        return Response(
            AttendanceSerializer(attendances, many=True).data
        )

    def post(self, request):
        s = AttendanceSerializer(
            data=request.data,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            attendance = s.save()
            return Response({
                "status": "1",
                "message": "Attendance marked",
                "attendance": AttendanceSerializer(attendance).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class AttendanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Attendance.objects.get(pk=pk, workshop=ws(request))
        except Attendance.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Attendance not found"}, status=404
            )
        s = AttendanceSerializer(
            obj, data=request.data, partial=True,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            s.save()
            return Response({"status": "1", "attendance": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Attendance not found"}, status=404
            )
        obj.delete()
        return Response({"status": "1", "message": "Attendance deleted"})


class BulkAttendanceView(APIView):
    """Mark attendance for all employees in one request."""
    permission_classes = [IsOwnerOrSuperUser]

    def post(self, request):
        workshop = ws(request)
        s = BulkAttendanceSerializer(data=request.data)

        if not s.is_valid():
            return Response({"status": "0", "errors": s.errors}, status=400)

        date    = s.validated_data['date']
        records = s.validated_data['records']
        created = 0
        errors  = []

        for record in records:
            try:
                from users.models import User
                employee = User.objects.get(
                    id=record['employee'], workshop=workshop
                )
                Attendance.objects.update_or_create(
                    employee  = employee,
                    date      = date,
                    defaults  = {
                        'workshop':   workshop,
                        'status':     record.get('status', 'PRESENT'),
                        'check_in':   record.get('check_in'),
                        'check_out':  record.get('check_out'),
                        'notes':      record.get('notes', ''),
                    }
                )
                created += 1
            except User.DoesNotExist:
                errors.append(f"Employee {record['employee']} not found")

        return Response({
            "status": "1",
            "message": f"{created} attendance records saved",
            "errors": errors
        }, status=201)


# ── Leave Request ─────────────────────────────────────────────

class LeaveRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        leaves   = LeaveRequest.objects.filter(
            workshop=workshop
        ).select_related('employee', 'approved_by')

        # Staff sees only their own leaves
        if request.user.role == 'staff':
            leaves = leaves.filter(employee=request.user)

        # Filter by status
        status = request.query_params.get('status')
        if status:
            leaves = leaves.filter(status=status.upper())

        # Filter by employee (owner only)
        employee_id = request.query_params.get('employee')
        if employee_id and request.user.role == 'owner':
            leaves = leaves.filter(employee_id=employee_id)

        return Response(
            LeaveRequestSerializer(leaves, many=True).data
        )

    def post(self, request):
        s = LeaveRequestSerializer(
            data=request.data,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            leave = s.save()
            return Response({
                "status": "1",
                "message": "Leave request submitted",
                "leave": LeaveRequestSerializer(leave).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class LeaveApprovalView(APIView):
    """Owner approves / rejects leave request."""
    permission_classes = [IsOwnerOrSuperUser]

    def post(self, request, pk):
        workshop = ws(request)
        try:
            leave = LeaveRequest.objects.get(pk=pk, workshop=workshop)
        except LeaveRequest.DoesNotExist:
            return Response(
                {"status": "0", "message": "Leave request not found"}, status=404
            )

        if leave.status != 'PENDING':
            return Response({
                "status": "0",
                "message": f"Leave request already {leave.status}"
            }, status=400)

        s = LeaveApprovalSerializer(data=request.data)
        if s.is_valid():
            s.save(leave_request=leave, approved_by=request.user)
            return Response({
                "status": "1",
                "message": f"Leave {leave.status}",
                "leave": LeaveRequestSerializer(leave).data
            })
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Salary Record ─────────────────────────────────────────────

class SalaryListCreateView(APIView):
    permission_classes = [IsOwnerOrSuperUser]

    def get(self, request):
        workshop  = ws(request)
        salaries  = SalaryRecord.objects.filter(
            workshop=workshop
        ).select_related('employee')

        # Filter by month/year
        month = request.query_params.get('month')
        year  = request.query_params.get('year')
        if month:
            salaries = salaries.filter(month=month)
        if year:
            salaries = salaries.filter(year=year)

        # Filter by employee
        employee_id = request.query_params.get('employee')
        if employee_id:
            salaries = salaries.filter(employee_id=employee_id)

        return Response(
            SalaryRecordSerializer(salaries, many=True).data
        )

    def post(self, request):
        s = SalaryRecordSerializer(
            data=request.data,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            salary = s.save()
            return Response({
                "status": "1",
                "message": "Salary record created",
                "salary": SalaryRecordSerializer(salary).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class SalaryDetailView(APIView):
    permission_classes = [IsOwnerOrSuperUser]

    def get_object(self, pk, request):
        try:
            return SalaryRecord.objects.get(pk=pk, workshop=ws(request))
        except SalaryRecord.DoesNotExist:
            return None

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Salary record not found"}, status=404
            )
        s = SalaryRecordSerializer(
            obj, data=request.data, partial=True,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            s.save()
            return Response({"status": "1", "salary": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Performance Note ──────────────────────────────────────────

class PerformanceNoteListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        notes    = PerformanceNote.objects.filter(
            workshop=workshop
        ).select_related('employee', 'noted_by')

        # Staff sees only their own notes
        if request.user.role == 'staff':
            notes = notes.filter(employee=request.user)

        employee_id = request.query_params.get('employee')
        if employee_id and request.user.role == 'owner':
            notes = notes.filter(employee_id=employee_id)

        return Response(
            PerformanceNoteSerializer(notes, many=True).data
        )

    def post(self, request):
        s = PerformanceNoteSerializer(
            data=request.data,
            context={'workshop': ws(request), 'request': request}
        )
        if s.is_valid():
            note = s.save()
            return Response({
                "status": "1",
                "message": "Performance note added",
                "note": PerformanceNoteSerializer(note).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)