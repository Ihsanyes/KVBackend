from rest_framework import serializers
from users.models import *
from django.db import transaction


class RegisterSerializer(serializers.Serializer):
    # Workshop fields
    workshop_name    = serializers.CharField(max_length=255)
    workshop_phone   = serializers.CharField(max_length=15)
    workshop_email   = serializers.EmailField()
    workshop_address = serializers.CharField()

    # Vehicle type capabilities
    serves_two_wheeler   = serializers.BooleanField(default=False)
    serves_three_wheeler = serializers.BooleanField(default=False)
    serves_four_wheeler  = serializers.BooleanField(default=False)
    serves_heavy_vehicle = serializers.BooleanField(default=False)

    # Owner fields
    first_name = serializers.CharField(max_length=30)
    last_name  = serializers.CharField(max_length=30)
    phone      = serializers.CharField(max_length=15)
    pin        = serializers.CharField(write_only=True)

    def validate_pin(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("PIN must be 6 digits")
        return value

    def validate(self, validated_data):
        if Workshop.objects.filter(phone=validated_data['workshop_phone']).exists():
            raise serializers.ValidationError("Workshop phone already exists")
        if User.objects.filter(phone=validated_data['phone']).exists():
            raise serializers.ValidationError("Phone number already exists")

        # At least one vehicle type must be true
        serves_any = any([
            validated_data.get('serves_two_wheeler'),
            validated_data.get('serves_three_wheeler'),
            validated_data.get('serves_four_wheeler'),
            validated_data.get('serves_heavy_vehicle'),
        ])
        if not serves_any:
            raise serializers.ValidationError(
                "At least one vehicle type must be selected"
            )

        return validated_data

    def create(self, validated_data):
        with transaction.atomic():

            # 1. Create workshop (with vehicle types)
            workshop = Workshop.objects.create(
                name                 = validated_data['workshop_name'],
                phone                = validated_data['workshop_phone'],
                email                = validated_data['workshop_email'],
                address              = validated_data['workshop_address'],
                serves_two_wheeler   = validated_data.get('serves_two_wheeler', False),
                serves_three_wheeler = validated_data.get('serves_three_wheeler', False),
                serves_four_wheeler  = validated_data.get('serves_four_wheeler', False),
                serves_heavy_vehicle = validated_data.get('serves_heavy_vehicle', False),
            )

            # 2. Create owner
            user = User.objects.create_user(
                workshop   = workshop,
                pin        = validated_data['pin'],
                role       = 'owner',
                first_name = validated_data['first_name'],
                last_name  = validated_data['last_name'],
                phone      = validated_data['phone'],
            )

            # 3. Assign owner to workshop
            workshop.owner = user
            workshop.save()

        return user


class LoginSerializer(serializers.Serializer):
    employee_id = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=6, min_length=6, write_only=True)


class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        fields = ['module_name']

class EmployeeSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True)

    employee_id = serializers.CharField(read_only=True)
    module_permissions = ModulePermissionSerializer(many=True, read_only=True)


    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'employee_id',  'pin', 'role', 'phone', 'email', 'module_permissions']
    
    def validate(self, data):
        if self.instance is None and not self.context.get('workshop'):
            raise serializers.ValidationError("Workshop is required")

        if not data.get('first_name'):
            raise serializers.ValidationError("First name is required")

        if not data.get('last_name'):
            raise serializers.ValidationError("Last name is required")

        if not data.get('phone'):
            raise serializers.ValidationError("Phone is required")
        
        if data.get('email') and User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists")

        return data
    
    def validate_pin(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("PIN must be exactly 6 digits")
        return value
    
    def validate_role(self, value):
        if value != 'staff':
            raise serializers.ValidationError("Only staff role can be created here")
        return value

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone must be numeric")

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already exists")

        return value

    def create(self, validated_data):
        pin = validated_data.pop('pin')
        role = validated_data.pop('role', 'staff')
        workshop = self.context.get('workshop')

        if not workshop:
            raise serializers.ValidationError("Workshop is required")

        try:
            user = User.objects.create_user(
                workshop=workshop,
                pin=pin,
                role=role,
                **validated_data
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

        return user

class AssignPermissionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    modules = serializers.ListField(child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES))

    def validate_id(self, value):
        workshop = self.context.get('workshop')
        if not User.objects.filter(id=value, workshop=workshop).exists():
            raise serializers.ValidationError("User not found in your workshop")
        return value
    
    def validate_modules(self, value):
        if not value:
            raise serializers.ValidationError("At least one module must be selected")
        return value
    
    def create(self, validated_data):
        user = User.objects.get(id=validated_data['id'])
        modules = validated_data['modules']

        # Remove old permissions
        ModulePermission.objects.filter(user=user).delete()

        permission_objects = [
            ModulePermission(user=user, module_name=module)
            for module in modules
        ]

        ModulePermission.objects.bulk_create(permission_objects)

        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    module_permissions = ModulePermissionSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'employee_id', 'role', 'phone', 'email', 'module_permissions']

class UpdateEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']

    def validate_phone(self, value):
        user = self.instance

        if not value.isdigit():
            raise serializers.ValidationError("Phone must be numeric")

        if User.objects.filter(phone=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Phone already exists")

        return value

    def validate_email(self, value):
        user = self.instance

        if value and User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Email already exists")

        return value


class PinResetSerializer(serializers.Serializer):
    old_pin = serializers.CharField(max_length=6, write_only=True)
    new_pin = serializers.CharField(max_length=6, write_only=True)

    def validate(self, data):
        user = self.context['request'].user

        old_pin = data.get("old_pin")
        new_pin = data.get("new_pin")

        # ✅ Validate old PIN
        if not user.check_password(old_pin):
            raise serializers.ValidationError({
                "old_pin": "Old PIN is incorrect"
            })

        # ✅ Validate new PIN format
        if not new_pin.isdigit() or len(new_pin) != 6:
            raise serializers.ValidationError({
                "new_pin": "PIN must be exactly 6 digits"
            })

        # ✅ Prevent same PIN
        if old_pin == new_pin:
            raise serializers.ValidationError({
                "new_pin": "New PIN cannot be same as old PIN"
            })

        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        new_pin = self.validated_data['new_pin']

        user.set_password(new_pin)
        user.failed_attempts = 0   # reset attempts
        user.locked_until = None   # unlock if locked
        user.save()

        return user

class WorkshopSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Workshop
        fields = [
            'id', 'name', 'owner', 'phone', 'email', 'address',
            'serves_two_wheeler', 'serves_three_wheeler',      # ← missing
            'serves_four_wheeler', 'serves_heavy_vehicle',     # ← missing
            'created_at'
        ]

    def get_owner(self, obj):
        if obj.owner:
            return obj.owner.get_full_name()
        return None
    

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ["theme", "notifications", "default_view"]
