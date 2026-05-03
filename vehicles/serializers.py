from rest_framework import serializers
from vehicles.models import Customer, Vehicle, VehicleModel, VehicleBrand


# ── Customer ──────────────────────────────────────────────────

class CustomerSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.SerializerMethodField()

    class Meta:
        model  = Customer
        fields = [
            'id', 'name', 'phone', 'email',
            'address', 'gstin', 'vehicle_count',
            'created_at', 'updated_at',
        ]

    def get_vehicle_count(self, obj):
        return obj.vehicles.count()

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone must be numeric")
        workshop = self.context.get('workshop')
        qs = Customer.objects.filter(phone=value, workshop=workshop)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Customer with this phone already exists")
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)


# ── Vehicle ───────────────────────────────────────────────────

class VehicleSerializer(serializers.ModelSerializer):
    customer_name  = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    model_name     = serializers.CharField(source='vehicle_model.__str__', read_only=True)
    vehicle_type   = serializers.CharField(read_only=True)  # @property from model

    class Meta:
        model  = Vehicle
        fields = [
            'id', 'customer', 'customer_name', 'customer_phone',
            'vehicle_model', 'model_name', 'vehicle_type',
            'registration_no', 'chassis_no', 'engine_no',
            'color', 'year', 'fuel_type', 'odometer_km',
            'insurance_expiry', 'puc_expiry',
            'permit_expiry', 'fitness_expiry',
            'created_at', 'updated_at',
        ]

    def validate_registration_no(self, value):
        workshop = self.context.get('workshop')
        qs = Vehicle.objects.filter(
            registration_no__iexact=value, workshop=workshop
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Vehicle with this registration number already exists"
            )
        return value.upper()

    def validate_customer(self, value):
        workshop = self.context.get('workshop')
        if value.workshop != workshop:
            raise serializers.ValidationError(
                "Customer does not belong to your workshop"
            )
        return value

    def validate_vehicle_model(self, value):
        workshop = self.context.get('workshop')
        # VehicleModel can be workshop-specific or global (workshop=None)
        if value.workshop and value.workshop != workshop:
            raise serializers.ValidationError(
                "Vehicle model not available for your workshop"
            )
        return value

    def create(self, validated_data):
        validated_data['workshop'] = self.context['workshop']
        return super().create(validated_data)