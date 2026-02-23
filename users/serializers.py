from rest_framework import serializers

from users.models import User, ModulePermission



class LoginSerializer(serializers.Serializer):
    employee_id = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=6, min_length=6, write_only=True)


class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        fields = ['module_name']

class EmployeeSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True)
    module_permissions = ModulePermissionSerializer(many=True, read_only=True)


    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'pin', 'role', 'phone', 'email', 'module_permissions']
    
    def validate(self, data):
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

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone must be numeric")

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already exists")

        return value

    def create(self, validated_data):
        pin = validated_data.pop('pin')

        user = User.objects.create_user(
            pin=pin,
            **validated_data
        )

        return user

class AssignPermissionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    modules = serializers.ListField(child=serializers.ChoiceField(choices=ModulePermission.MODULE_CHOICES))

    def validate_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User with this ID does not exist")
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