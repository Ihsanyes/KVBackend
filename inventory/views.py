from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.permission import IsOwnerOrSuperUser
from inventory.models import (
    Brand, Category,
    Product, ProductVariant,
    Stock, StockAlert,
    Supplier, PurchaseOrder, PriceHistory,
)
from inventory.serializers import (
    BrandSerializer, CategorySerializer,
    VehicleBrandSerializer, VehicleModelSerializer,
    ProductSerializer, ProductVariantSerializer,
    StockSerializer, StockAdjustSerializer, StockAlertSerializer, StockMovementSerializer,
    SupplierSerializer,
    PurchaseOrderSerializer, GRNSerializer,
    PriceHistorySerializer,
)
from inventory.services.services import apply_grn, apply_stock_adjustment
from jobs.models import StockMovement
from vehicles.models import VehicleBrand, VehicleModel


def ws(request):
    """Shortcut — get workshop from request."""
    return request.user.workshop


# ── Brand ─────────────────────────────────────────────────────

class BrandListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        brands = Brand.objects.filter(workshop=ws(request))
        return Response(BrandSerializer(brands, many=True).data)

    def post(self, request):
        s = BrandSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "brand": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class BrandDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Brand.objects.get(pk=pk, workshop=ws(request))
        except Brand.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Brand not found"}, status=404)
        return Response(BrandSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Brand not found"}, status=404)
        s = BrandSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "brand": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Brand not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Brand deleted"})


# ── Category ──────────────────────────────────────────────────

class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cats = Category.objects.filter(workshop=ws(request))
        return Response(CategorySerializer(cats, many=True).data)

    def post(self, request):
        s = CategorySerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "category": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Category.objects.get(pk=pk, workshop=ws(request))
        except Category.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Category not found"}, status=404)
        return Response(CategorySerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Category not found"}, status=404)
        s = CategorySerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "category": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Category not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Category deleted"})


# ── VehicleBrand ──────────────────────────────────────────────

class VehicleBrandListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        brands = VehicleBrand.objects.filter(workshop=ws(request))
        return Response(VehicleBrandSerializer(brands, many=True).data)

    def post(self, request):
        s = VehicleBrandSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "brand": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class VehicleBrandDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return VehicleBrand.objects.get(pk=pk, workshop=ws(request))
        except VehicleBrand.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle brand not found"}, status=404)
        return Response(VehicleBrandSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle brand not found"}, status=404)
        s = VehicleBrandSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "brand": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle brand not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Vehicle brand deleted"})


# ── VehicleModel ──────────────────────────────────────────────

class VehicleModelListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        models = VehicleModel.objects.filter(workshop=ws(request)).select_related('brand')
        if request.query_params.get('brand'):
            models = models.filter(brand_id=request.query_params['brand'])
        if request.query_params.get('vehicle_type'):
            models = models.filter(vehicle_type=request.query_params['vehicle_type'])
        return Response(VehicleModelSerializer(models, many=True).data)

    def post(self, request):
        s = VehicleModelSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "model": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class VehicleModelDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return VehicleModel.objects.get(pk=pk, workshop=ws(request))
        except VehicleModel.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle model not found"}, status=404)
        return Response(VehicleModelSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle model not found"}, status=404)
        s = VehicleModelSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "model": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Vehicle model not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Vehicle model deleted"})


# ── Product ───────────────────────────────────────────────────

class ProductListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product.objects.filter(workshop=ws(request)).select_related('category')
        return Response(ProductSerializer(products, many=True, context={'workshop': ws(request)}).data)

    def post(self, request):
        s = ProductSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "product": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Product.objects.get(pk=pk, workshop=ws(request))
        except Product.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Product not found"}, status=404)
        return Response(ProductSerializer(obj, context={'workshop': ws(request)}).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Product not found"}, status=404)
        s = ProductSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "product": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Product not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Product deleted"})


# ── ProductVariant ────────────────────────────────────────────

class ProductVariantListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        variants = ProductVariant.objects.filter(workshop=workshop).select_related('product', 'brand').prefetch_related('stock')
        if request.query_params.get('product'):
            variants = variants.filter(product_id=request.query_params['product'])
        return Response(ProductVariantSerializer(variants, many=True, context={'workshop': workshop}).data)

    def post(self, request):
        workshop = ws(request)
        s = ProductVariantSerializer(data=request.data, context={'workshop': workshop, 'request': request})
        if s.is_valid():
            variant = s.save()
            return Response({"status": "1", "variant": ProductVariantSerializer(variant, context={'workshop': workshop}).data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class ProductVariantDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return ProductVariant.objects.get(pk=pk, workshop=ws(request))
        except ProductVariant.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Variant not found"}, status=404)
        return Response(ProductVariantSerializer(obj, context={'workshop': ws(request)}).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Variant not found"}, status=404)
        s = ProductVariantSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            variant = s.save()
            return Response({"status": "1", "variant": ProductVariantSerializer(variant, context={'workshop': ws(request)}).data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Variant not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Variant deleted"})


# ── Stock ─────────────────────────────────────────────────────

class StockListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        stocks   = Stock.objects.filter(workshop=workshop).select_related('product_variant__product', 'product_variant__brand')

        if request.query_params.get('low_stock') == 'true':
            low_ids = []
            for s in stocks:
                alert = s.product_variant.alert_setting.filter(workshop=workshop).first()
                if alert and alert.is_low(s.quantity):
                    low_ids.append(s.id)
            stocks = stocks.filter(id__in=low_ids)

        return Response(StockSerializer(stocks, many=True, context={'workshop': workshop}).data)


class StockAdjustView(APIView):
    permission_classes = [IsOwnerOrSuperUser]

    def post(self, request):
        workshop = ws(request)
        s = StockAdjustSerializer(data=request.data, context={'workshop': workshop})
        if s.is_valid():
            try:
                stock = apply_stock_adjustment(
                    workshop        = workshop,
                    product_variant = s.validated_data['product_variant'],
                    quantity        = s.validated_data['quantity'],
                    reason          = s.validated_data['reason'],
                    moved_by        = request.user,
                )
                return Response({"status": "1", "message": "Stock adjusted", "new_quantity": stock.quantity})
            except ValueError as e:
                return Response({"status": "0", "message": str(e)}, status=400)
        return Response({"status": "0", "errors": s.errors}, status=400)


class StockMovementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop  = ws(request)
        movements = StockMovement.objects.filter(workshop=workshop).select_related('product_variant__product', 'moved_by')
        if request.query_params.get('variant'):
            movements = movements.filter(product_variant_id=request.query_params['variant'])
        if request.query_params.get('type'):
            movements = movements.filter(movement_type=request.query_params['type'].upper())
        return Response(StockMovementSerializer(movements, many=True).data)


# ── StockAlert ────────────────────────────────────────────────

class StockAlertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alerts = StockAlert.objects.filter(workshop=ws(request))
        return Response(StockAlertSerializer(alerts, many=True).data)

    def post(self, request):
        s = StockAlertSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "alert": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


# ── Supplier ──────────────────────────────────────────────────

class SupplierListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        suppliers = Supplier.objects.filter(workshop=ws(request))
        return Response(SupplierSerializer(suppliers, many=True).data)

    def post(self, request):
        s = SupplierSerializer(data=request.data, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "supplier": s.data}, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class SupplierDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return Supplier.objects.get(pk=pk, workshop=ws(request))
        except Supplier.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Supplier not found"}, status=404)
        return Response(SupplierSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Supplier not found"}, status=404)
        s = SupplierSerializer(obj, data=request.data, partial=True, context={'workshop': ws(request)})
        if s.is_valid():
            s.save()
            return Response({"status": "1", "supplier": s.data})
        return Response({"status": "0", "errors": s.errors}, status=400)

    def delete(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Supplier not found"}, status=404)
        obj.delete()
        return Response({"status": "1", "message": "Supplier deleted"})


# ── PurchaseOrder ─────────────────────────────────────────────

class PurchaseOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workshop = ws(request)
        pos = PurchaseOrder.objects.filter(workshop=workshop).select_related('supplier').prefetch_related('items')
        if request.query_params.get('status'):
            pos = pos.filter(status=request.query_params['status'].upper())
        return Response(PurchaseOrderSerializer(pos, many=True, context={'workshop': workshop, 'request': request}).data)

    def post(self, request):
        workshop = ws(request)
        s = PurchaseOrderSerializer(data=request.data, context={'workshop': workshop, 'request': request})
        if s.is_valid():
            po = s.save()
            return Response({
                "status": "1",
                "message": "Purchase order created",
                "po_number": po.po_number,
                "po": PurchaseOrderSerializer(po, context={'workshop': workshop, 'request': request}).data
            }, status=201)
        return Response({"status": "0", "errors": s.errors}, status=400)


class PurchaseOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            return PurchaseOrder.objects.get(pk=pk, workshop=ws(request))
        except PurchaseOrder.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk, request)
        if not obj:
            return Response({"status": "0", "message": "Purchase order not found"}, status=404)
        return Response(PurchaseOrderSerializer(obj, context={'workshop': ws(request), 'request': request}).data)


class GRNView(APIView):
    permission_classes = [IsOwnerOrSuperUser]

    def post(self, request, pk):
        try:
            po = PurchaseOrder.objects.get(pk=pk, workshop=ws(request))
        except PurchaseOrder.DoesNotExist:
            return Response({"status": "0", "message": "Purchase order not found"}, status=404)

        if po.status == 'RECEIVED':
            return Response({"status": "0", "message": "Already fully received"}, status=400)
        if po.status == 'CANCELLED':
            return Response({"status": "0", "message": "Cannot receive a cancelled order"}, status=400)

        s = GRNSerializer(data=request.data)
        if s.is_valid():
            po = apply_grn(po, s.validated_data['items'], request.user)
            return Response({"status": "1", "message": "GRN processed", "po_status": po.status})
        return Response({"status": "0", "errors": s.errors}, status=400)


class PurchaseOrderCancelView(APIView):
    permission_classes = [IsOwnerOrSuperUser]

    def post(self, request, pk):
        try:
            po = PurchaseOrder.objects.get(pk=pk, workshop=ws(request))
        except PurchaseOrder.DoesNotExist:
            return Response({"status": "0", "message": "Purchase order not found"}, status=404)

        if po.status == 'RECEIVED':
            return Response({"status": "0", "message": "Cannot cancel a fully received order"}, status=400)
        if po.status == 'CANCELLED':
            return Response({"status": "0", "message": "Already cancelled"}, status=400)
        if po.status == 'PARTIAL':
            return Response({"status": "0", "message": "Cannot cancel a partially received order"}, status=400)

        po.status = 'CANCELLED'
        po.save()
        return Response({"status": "1", "message": f"PO#{po.po_number} cancelled"})


# ── PriceHistory ──────────────────────────────────────────────

class PriceHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, variant_pk):
        workshop = ws(request)
        if not ProductVariant.objects.filter(pk=variant_pk, workshop=workshop).exists():
            return Response({"status": "0", "message": "Variant not found"}, status=404)
        history = PriceHistory.objects.filter(product_variant_id=variant_pk, workshop=workshop)
        return Response(PriceHistorySerializer(history, many=True).data)
