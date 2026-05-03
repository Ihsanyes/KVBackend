from rest_framework import serializers
from django.utils import timezone

from jobs.models import JobCard, JobCardService, JobCardPart, StockMovement
from inventory.models import ProductVariant, Stock


# ── JobCardService ────────────────────────────────────────────

class JobCardServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = JobCardService
        fields = ['id', 'service_name', 'description', 'labour_charge', 'is_completed']


# ── JobCardPart ───────────────────────────────────────────────

class JobCardPartSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    sku          = serializers.CharField(source='product_variant.sku', read_only=True)

    class Meta:
        model  = JobCardPart
        fields = [
            'id', 'product_variant', 'product_name', 'sku',
            'quantity', 'unit_price', 'discount_pct',
            'line_total', 'is_returned', 'issued_at',
        ]
        read_only_fields = ['line_total', 'issued_at']


# ── JobCard List ──────────────────────────────────────────────

class JobCardListSerializer(serializers.ModelSerializer):
    customer_name      = serializers.CharField(source='customer.name', read_only=True)
    customer_phone     = serializers.CharField(source='customer.phone', read_only=True)
    registration_no    = serializers.CharField(source='vehicle.registration_no', read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle.vehicle_model.__str__', read_only=True)
    technician_name    = serializers.SerializerMethodField()

    class Meta:
        model  = JobCard
        fields = [
            'id', 'job_number', 'status',
            'customer_name', 'customer_phone',
            'registration_no', 'vehicle_model_name',
            'technician_name', 'odometer_in',
            'complaint', 'received_at', 'promised_at', 'created_at',
        ]

    def get_technician_name(self, obj):
        return obj.technician.get_full_name() if obj.technician else None


# ── JobCard Detail ────────────────────────────────────────────

class JobCardDetailSerializer(serializers.ModelSerializer):
    customer_name      = serializers.CharField(source='customer.name', read_only=True)
    customer_phone     = serializers.CharField(source='customer.phone', read_only=True)
    registration_no    = serializers.CharField(source='vehicle.registration_no', read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle.vehicle_model.__str__', read_only=True)
    vehicle_type       = serializers.CharField(source='vehicle.vehicle_type', read_only=True)
    technician_name    = serializers.SerializerMethodField()
    services           = JobCardServiceSerializer(many=True, read_only=True)
    parts_used         = JobCardPartSerializer(many=True, read_only=True)
    has_invoice        = serializers.SerializerMethodField()

    class Meta:
        model  = JobCard
        fields = [
            'id', 'job_number', 'status',
            'customer', 'customer_name', 'customer_phone',
            'vehicle', 'registration_no', 'vehicle_model_name', 'vehicle_type',
            'technician', 'technician_name',
            'odometer_in', 'odometer_out',
            'complaint', 'diagnosis', 'work_done',
            'received_at', 'promised_at', 'completed_at', 'delivered_at',
            'services', 'parts_used', 'has_invoice',
            'created_at', 'updated_at',
        ]

    def get_technician_name(self, obj):
        return obj.technician.get_full_name() if obj.technician else None

    def get_has_invoice(self, obj):
        return hasattr(obj, 'invoice')


# ── JobCard Create ────────────────────────────────────────────

class JobCardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = JobCard
        fields = ['vehicle', 'customer', 'technician', 'odometer_in', 'complaint', 'promised_at']

    def validate_vehicle(self, value):
        if value.workshop != self.context['workshop']:
            raise serializers.ValidationError("Vehicle not found in your workshop")
        return value

    def validate_customer(self, value):
        if value.workshop != self.context['workshop']:
            raise serializers.ValidationError("Customer not found in your workshop")
        return value

    def validate_technician(self, value):
        if value and value.workshop != self.context['workshop']:
            raise serializers.ValidationError("Technician not found in your workshop")
        return value

    def validate(self, data):
        vehicle  = data.get('vehicle')
        customer = data.get('customer')
        if vehicle and customer and vehicle.customer != customer:
            raise serializers.ValidationError(
                "This vehicle does not belong to the selected customer"
            )
        return data

    def create(self, validated_data):
        from jobs.services import generate_job_number
        workshop = self.context['workshop']
        validated_data['workshop']   = workshop
        validated_data['created_by'] = self.context['request'].user
        validated_data['job_number'] = generate_job_number(workshop)
        return JobCard.objects.create(**validated_data)


# ── JobCard Update ────────────────────────────────────────────

class JobCardUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = JobCard
        fields = [
            'status', 'technician', 'diagnosis', 'work_done',
            'odometer_out', 'promised_at', 'completed_at', 'delivered_at',
        ]

    def validate_status(self, value):
        instance = self.instance
        if not instance:
            return value
        transitions = {
            'PENDING':     ['IN_PROGRESS', 'CANCELLED'],
            'IN_PROGRESS': ['ON_HOLD', 'COMPLETED', 'CANCELLED'],
            'ON_HOLD':     ['IN_PROGRESS', 'CANCELLED'],
            'COMPLETED':   ['DELIVERED'],
            'DELIVERED':   [],
            'CANCELLED':   [],
        }
        allowed = transitions.get(instance.status, [])
        if value != instance.status and value not in allowed:
            raise serializers.ValidationError(
                f"Cannot change status from {instance.status} to {value}"
            )
        return value

    def update(self, instance, validated_data):
        status = validated_data.get('status', instance.status)
        if status == 'COMPLETED' and not instance.completed_at:
            validated_data['completed_at'] = timezone.now()
        if status == 'DELIVERED' and not instance.delivered_at:
            validated_data['delivered_at'] = timezone.now()
        return super().update(instance, validated_data)


# ── Issue Part ────────────────────────────────────────────────

class IssuePartSerializer(serializers.Serializer):
    product_variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity        = serializers.IntegerField(min_value=1)
    unit_price      = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_pct    = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)

    def validate_product_variant(self, value):
        if value.workshop != self.context['workshop']:
            raise serializers.ValidationError("Product variant not found in your workshop")
        return value

    def validate(self, data):
        stock = Stock.objects.filter(
            workshop=self.context['workshop'],
            product_variant=data['product_variant']
        ).first()
        available = stock.quantity if stock else 0
        if data['quantity'] > available:
            raise serializers.ValidationError(
                f"Insufficient stock. Available: {available}"
            )
        return data

    def save(self, job_card, issued_by):
        from jobs.services import issue_part_to_job
        return issue_part_to_job(
            job_card     = job_card,
            variant      = self.validated_data['product_variant'],
            quantity     = self.validated_data['quantity'],
            unit_price   = self.validated_data['unit_price'],
            discount_pct = self.validated_data['discount_pct'],
            issued_by    = issued_by,
        )


# ── Add Service ───────────────────────────────────────────────

class AddServiceSerializer(serializers.Serializer):
    service_name  = serializers.CharField(max_length=200)
    description   = serializers.CharField(required=False, allow_blank=True, default='')
    labour_charge = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)

    def save(self, job_card):
        return JobCardService.objects.create(
            job_card      = job_card,
            service_name  = self.validated_data['service_name'],
            description   = self.validated_data.get('description', ''),
            labour_charge = self.validated_data['labour_charge'],
        )