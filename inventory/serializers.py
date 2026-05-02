from rest_framework import serializers
from inventory.models import (
    Brand, Category,
    Product, ProductVariant,
    Stock, StockAlert,
    Supplier, PurchaseOrder, PurchaseOrderItem,
    PriceHistory,
)
from jobs.models import StockMovement
from vehicles.models import VehicleBrand, VehicleModel


# ── Brand ─────────────────────────────────────────────────────

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Brand
        fields = ['id', 'name', 'description', 'created_at']

    def validate_name(self, value):
        workshop = self.context.get('workshop')
        qs = Brand.objects.filter(name__iexact=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Brand with this name already exists")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── Category ──────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'description', 'created_at']

    def validate_name(self, value):
        workshop = self.context.get('workshop')
        qs = Category.objects.filter(name__iexact=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Category with this name already exists")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── VehicleBrand ──────────────────────────────────────────────

class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VehicleBrand
        fields = ['id', 'name']

    def validate_name(self, value):
        workshop = self.context.get('workshop')
        qs = VehicleBrand.objects.filter(name__iexact=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Vehicle brand already exists")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── VehicleModel ──────────────────────────────────────────────

class VehicleModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta:
        model  = VehicleModel
        fields = ['id', 'brand', 'brand_name', 'model_name', 'vehicle_type']

    def validate(self, data):
        workshop   = self.context.get('workshop')
        brand      = data.get('brand', getattr(self.instance, 'brand', None))
        model_name = data.get('model_name', getattr(self.instance, 'model_name', None))

        if brand and brand.workshop != workshop:
            raise serializers.ValidationError("Vehicle brand not found in your workshop")

        qs = VehicleModel.objects.filter(brand=brand, model_name__iexact=model_name, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Vehicle model already exists for this brand")
        return data

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── Product ───────────────────────────────────────────────────

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model  = Product
        fields = ['id', 'name', 'category', 'category_name', 'description', 'unit', 'is_active', 'created_at']

    def validate(self, data):
        workshop = self.context.get('workshop')
        category = data.get('category', getattr(self.instance, 'category', None))
        name     = data.get('name', getattr(self.instance, 'name', None))
        qs = Product.objects.filter(name__iexact=name, category=category, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Product already exists in this category")
        return data

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── ProductVariant ────────────────────────────────────────────

class ProductVariantSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product.name', read_only=True)
    brand_name    = serializers.CharField(source='brand.name', read_only=True)
    current_stock = serializers.SerializerMethodField()

    class Meta:
        model  = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'brand', 'brand_name',
            'variant_name', 'sku', 'barcode',
            'cost_price', 'selling_price',
            'compatible_vehicles', 'is_active',
            'current_stock', 'created_at',
        ]

    def get_current_stock(self, obj):
        workshop = self.context.get('workshop')
        stock = obj.stock.filter(workshop=workshop).first()
        return stock.quantity if stock else 0

    def validate_sku(self, value):
        workshop = self.context.get('workshop')
        qs = ProductVariant.objects.filter(sku=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("SKU already exists")
        return value

    def validate(self, data):
        workshop = self.context.get('workshop')
        brand    = data.get('brand')
        product  = data.get('product')
        if brand and brand.workshop != workshop:
            raise serializers.ValidationError("Brand does not belong to your workshop")
        if product and product.workshop != workshop:
            raise serializers.ValidationError("Product does not belong to your workshop")
        return data

    def create(self, validated_data):
        workshop = self.context['workshop']
        validated_data['workshop'] = workshop
        variant = super().create(validated_data)
        Stock.objects.get_or_create(workshop=workshop, product_variant=variant)
        return variant


# ── Stock ─────────────────────────────────────────────────────

class StockSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name  = serializers.CharField(source='product_variant.variant_name', read_only=True)
    sku           = serializers.CharField(source='product_variant.sku', read_only=True)
    brand_name    = serializers.CharField(source='product_variant.brand.name', read_only=True)
    selling_price = serializers.DecimalField(source='product_variant.selling_price', max_digits=10, decimal_places=2, read_only=True)
    is_low        = serializers.SerializerMethodField()

    class Meta:
        model  = Stock
        fields = [
            'id', 'product_variant', 'product_name', 'variant_name',
            'sku', 'brand_name', 'selling_price', 'quantity', 'is_low', 'updated_at',
        ]

    def get_is_low(self, obj):
        alert = obj.product_variant.alert_setting.filter(workshop=obj.workshop).first()
        return alert.is_low(obj.quantity) if alert else False


class StockAdjustSerializer(serializers.Serializer):
    product_variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity        = serializers.IntegerField(help_text='Positive = add, Negative = remove')
    reason          = serializers.CharField(max_length=255)

    def validate_product_variant(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError("Product variant not found in your workshop")
        return value


# ── StockAlert ────────────────────────────────────────────────

class StockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    sku          = serializers.CharField(source='product_variant.sku', read_only=True)

    class Meta:
        model  = StockAlert
        fields = ['id', 'product_variant', 'product_name', 'sku', 'min_stock', 'max_stock', 'is_active']

    def validate_product_variant(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError("Product variant not found in your workshop")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        instance, _ = StockAlert.objects.update_or_create(
            workshop=validated_data['workshop'],
            product_variant=validated_data['product_variant'],
            defaults=validated_data
        )
        return instance


# ── StockMovement ─────────────────────────────────────────────

class StockMovementSerializer(serializers.ModelSerializer):
    product_name  = serializers.CharField(source='product_variant.product.name', read_only=True)
    sku           = serializers.CharField(source='product_variant.sku', read_only=True)
    moved_by_name = serializers.CharField(source='moved_by.get_full_name', read_only=True)

    class Meta:
        model  = StockMovement
        fields = [
            'id', 'product_variant', 'product_name', 'sku',
            'movement_type', 'quantity', 'unit_cost',
            'reference_note', 'moved_by_name', 'moved_at',
        ]


# ── Supplier ──────────────────────────────────────────────────

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Supplier
        fields = ['id', 'name', 'contact_name', 'phone', 'email', 'address', 'gstin', 'credit_days', 'is_active', 'created_at']

    def validate_name(self, value):
        workshop = self.context.get('workshop')
        qs = Supplier.objects.filter(name__iexact=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Supplier already exists")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── PurchaseOrder ─────────────────────────────────────────────

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    sku          = serializers.CharField(source='product_variant.sku', read_only=True)
    pending_qty  = serializers.IntegerField(read_only=True)

    class Meta:
        model  = PurchaseOrderItem
        fields = [
            'id', 'product_variant', 'product_name', 'sku',
            'ordered_qty', 'received_qty', 'pending_qty',
            'unit_cost', 'tax_rate', 'line_total',
        ]
        read_only_fields = ['received_qty', 'line_total']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items         = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model  = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'status',
            'order_date', 'expected_date', 'received_date',
            'subtotal', 'tax_amount', 'total_amount',
            'notes', 'items', 'created_at',
        ]
        read_only_fields = ['po_number', 'status', 'subtotal', 'tax_amount', 'total_amount']

    def validate_supplier(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError("Supplier not found in your workshop")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required")
        return value

    def create(self, validated_data):
        from inventory.services import generate_po_number
        items_data = validated_data.pop('items')
        workshop   = self.context['workshop']
        user       = self.context['request'].user

        validated_data['workshop']   = workshop
        validated_data['created_by'] = user
        validated_data['po_number']  = generate_po_number(workshop)

        po = PurchaseOrder.objects.create(**validated_data)

        subtotal = tax_total = 0
        for item_data in items_data:
            qty        = item_data['ordered_qty']
            unit_cost  = item_data['unit_cost']
            tax_rate   = item_data.get('tax_rate', 18)
            tax_amt    = round(unit_cost * qty * tax_rate / 100, 2)
            line_total = round(unit_cost * qty + tax_amt, 2)

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                line_total=line_total,
                **item_data
            )
            subtotal  += unit_cost * qty
            tax_total += tax_amt

        po.subtotal     = round(subtotal, 2)
        po.tax_amount   = round(tax_total, 2)
        po.total_amount = round(subtotal + tax_total, 2)
        po.save()
        return po


class GRNSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{"item_id": 1, "received_qty": 10}, ...]'
    )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Items are required")
        for item in value:
            if 'item_id' not in item or 'received_qty' not in item:
                raise serializers.ValidationError("Each item needs item_id and received_qty")
            if int(item['received_qty']) <= 0:
                raise serializers.ValidationError("received_qty must be greater than 0")
        return value


# ── PriceHistory ──────────────────────────────────────────────

class PriceHistorySerializer(serializers.ModelSerializer):
    product_name    = serializers.CharField(source='product_variant.product.name', read_only=True)
    sku             = serializers.CharField(source='product_variant.sku', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model  = PriceHistory
        fields = [
            'id', 'product_variant', 'product_name', 'sku',
            'old_cost_price', 'new_cost_price',
            'old_selling_price', 'new_selling_price',
            'changed_by_name', 'reason', 'changed_at',
        ]
