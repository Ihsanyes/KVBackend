from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

from .services.number_sequence import generate_employee_id


class UserManager(BaseUserManager):
    def create_user(self, employee_id=None, pin=None, role='staff', **extra_fields):

        if not pin:
            raise ValueError("PIN is required")

        if not pin.isdigit() or len(pin) != 6:
            raise ValueError("PIN must be exactly 6 digits")

        if not employee_id:
            employee_id = generate_employee_id()

        employee_id = employee_id.upper()

        user = self.model(employee_id=employee_id, role=role, **extra_fields)
        user.set_password(pin)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, employee_id, password=None, **extra_fields):
        pin = password # password is used as PIN

        if not pin:
            raise ValueError("Superuser must have a PIN")

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(employee_id=employee_id, pin=pin, role='admin', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    ]

    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True, unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Optional security (basic brute-force protection)
    failed_attempts = models.IntegerField(default=0)

    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

    def save(self, *args, **kwargs):
        # Ensure admin has staff access
        if self.role == 'admin':
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.employee_id
    

class EmployeeIdSequence(models.Model):
    last_number = models.IntegerField(default=0)

    def __str__(self):
        return str(self.last_number)
    
