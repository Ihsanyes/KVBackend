from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.permission import IsOwnerOrSuperUser
from jobs.models import JobCard, JobCardPart, JobCardService
from jobs.serializers import (
    JobCardListSerializer, JobCardDetailSerializer,
    JobCardCreateSerializer, JobCardUpdateSerializer,
    IssuePartSerializer, AddServiceSerializer,
)
from jobs.services import return_part_from_job


def ws(request):
    return request.user.workshop


# ── JobCard ───────────────────────────────────────────────────

class JobCardListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop  = ws(request)
        job_cards = JobCard.objects.filter(
            workshop=workshop
        ).select_related('customer', 'vehicle__vehicle_model', 'technician')

        # Filter by status
        status = request.query_params.get('status')
        if status:
            job_cards = job_cards.filter(status=status.upper())

        # Search by job number or reg number
        search = request.query_params.get('search')
        if search:
            job_cards = job_cards.filter(
                job_number__icontains=search
            ) | job_cards.filter(
                vehicle__registration_no__icontains=search
            )

        return Response(
            JobCardListSerializer(job_cards, many=True).data
        )

    def post(self, request):
        workshop = ws(request)

        # Validate workshop serves this vehicle type
        s = JobCardCreateSerializer(
            data=request.data,
            context={'workshop': workshop, 'request': request}
        )
        if s.is_valid():
            job_card = s.save()
            return Response({
                "status": "1",
                "message": "Job card created",
                "job_number": job_card.job_number,
                "job_card": JobCardDetailSerializer(job_card).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class JobCardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return JobCard.objects.select_related(
                'customer', 'vehicle__vehicle_model__brand', 'technician'
            ).prefetch_related(
                'services', 'parts_used__product_variant__product'
            ).get(pk=pk, workshop=ws(request))
        except JobCard.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Job card not found"}, status=404
            )
        return Response(JobCardDetailSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Job card not found"}, status=404
            )
        s = JobCardUpdateSerializer(obj, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response({
                "status": "1",
                "message": "Job card updated",
                "job_card": JobCardDetailSerializer(obj).data
            })
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Issue Part to Job ─────────────────────────────────────────

class IssuePartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        workshop = ws(request)
        try:
            job_card = JobCard.objects.get(pk=pk, workshop=workshop)
        except JobCard.DoesNotExist:
            return Response(
                {"status": "0", "message": "Job card not found"}, status=404
            )

        if job_card.status in ['COMPLETED', 'DELIVERED', 'CANCELLED']:
            return Response({
                "status": "0",
                "message": f"Cannot issue parts to a {job_card.status} job"
            }, status=400)

        s = IssuePartSerializer(
            data=request.data,
            context={'workshop': workshop}
        )
        if s.is_valid():
            part = s.save(job_card=job_card, issued_by=request.user)
            return Response({
                "status": "1",
                "message": "Part issued successfully",
                "part_id": part.id,
                "line_total": str(part.line_total),
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Return Part ───────────────────────────────────────────────

class ReturnPartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, part_pk):
        workshop = ws(request)
        try:
            job_card = JobCard.objects.get(pk=pk, workshop=workshop)
            part     = JobCardPart.objects.get(pk=part_pk, job_card=job_card)
        except (JobCard.DoesNotExist, JobCardPart.DoesNotExist):
            return Response(
                {"status": "0", "message": "Not found"}, status=404
            )

        try:
            return_part_from_job(part, returned_by=request.user)
            return Response({
                "status": "1",
                "message": "Part returned to stock"
            })
        except ValueError as e:
            return Response({"status": "0", "message": str(e)}, status=400)


# ── Add Service ───────────────────────────────────────────────

class AddServiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        workshop = ws(request)
        try:
            job_card = JobCard.objects.get(pk=pk, workshop=workshop)
        except JobCard.DoesNotExist:
            return Response(
                {"status": "0", "message": "Job card not found"}, status=404
            )

        if job_card.status in ['DELIVERED', 'CANCELLED']:
            return Response({
                "status": "0",
                "message": f"Cannot add services to a {job_card.status} job"
            }, status=400)

        s = AddServiceSerializer(data=request.data)
        if s.is_valid():
            service = s.save(job_card=job_card)
            return Response({
                "status": "1",
                "message": "Service added",
                "service_id": service.id,
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class DeleteServiceView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, service_pk):
        workshop = ws(request)
        try:
            job_card = JobCard.objects.get(pk=pk, workshop=workshop)
            service  = JobCardService.objects.get(pk=service_pk, job_card=job_card)
        except (JobCard.DoesNotExist, JobCardService.DoesNotExist):
            return Response(
                {"status": "0", "message": "Not found"}, status=404
            )
        service.delete()
        return Response({"status": "1", "message": "Service removed"})