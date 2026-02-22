from rest_framework import serializers

from users.models import User



class LoginSerializer(serializers.Serializer):
    employee_id = serializers.CharField(max_length=100)
    pin = serializers.CharField(max_length=6, min_length=6, write_only=True)




class EmployeeCreateSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'pin', 'role', 'phone', 'email']
    
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