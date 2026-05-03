from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.permission import IsOwnerOrSuperUser
from vehicles.models import Customer, Vehicle
from vehicles.serializers import CustomerSerializer, VehicleSerializer


def ws(request):
    return request.user.workshop


# ── Customer ──────────────────────────────────────────────────

class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop  = ws(request)
        customers = Customer.objects.filter(workshop=workshop)

        search = request.query_params.get('search')
        if search:
            customers = customers.filter(
                name__icontains=search
            ) | customers.filter(
                phone__icontains=search
            )

        return Response(
            CustomerSerializer(customers, many=True).data
        )

    def post(self, request):
        s = CustomerSerializer(
            data=request.data,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            customer = s.save()
            return Response({
                "status": "1",
                "message": "Customer created successfully",
                "customer": CustomerSerializer(customer).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Customer.objects.get(pk=pk, workshop=ws(request))
        except Customer.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Customer not found"}, status=404
            )
        return Response(CustomerSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Customer not found"}, status=404
            )
        s = CustomerSerializer(
            obj, data=request.data, partial=True,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            s.save()
            return Response({"status": "1", "customer": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Customer not found"}, status=404
            )
        obj.delete()
        return Response({"status": "1", "message": "Customer deleted"})


# ── Vehicle ───────────────────────────────────────────────────

class VehicleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        vehicles = Vehicle.objects.filter(
            workshop=workshop
        ).select_related('customer', 'vehicle_model__brand')

        # Filter by customer
        customer_id = request.query_params.get('customer')
        if customer_id:
            vehicles = vehicles.filter(customer_id=customer_id)

        # Search by reg number
        search = request.query_params.get('search')
        if search:
            vehicles = vehicles.filter(
                registration_no__icontains=search
            )

        return Response(
            VehicleSerializer(
                vehicles, many=True,
                context={'workshop': workshop}
            ).data
        )

    def post(self, request):
        workshop = ws(request)
        s = VehicleSerializer(
            data=request.data,
            context={'workshop': workshop}
        )
        if s.is_valid():
            vehicle = s.save()
            return Response({
                "status": "1",
                "message": "Vehicle registered successfully",
                "vehicle": VehicleSerializer(
                    vehicle, context={'workshop': workshop}
                ).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class VehicleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Vehicle.objects.select_related(
                'customer', 'vehicle_model__brand'
            ).get(pk=pk, workshop=ws(request))
        except Vehicle.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Vehicle not found"}, status=404
            )
        return Response(
            VehicleSerializer(obj, context={'workshop': ws(request)}).data
        )

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Vehicle not found"}, status=404
            )
        s = VehicleSerializer(
            obj, data=request.data, partial=True,
            context={'workshop': ws(request)}
        )
        if s.is_valid():
            vehicle = s.save()
            return Response({
                "status": "1",
                "vehicle": VehicleSerializer(
                    vehicle, context={'workshop': ws(request)}
                ).data
            })
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response(
                {"status": "0", "message": "Vehicle not found"}, status=404
            )
        obj.delete()
        return Response({"status": "1", "message": "Vehicle deleted"})