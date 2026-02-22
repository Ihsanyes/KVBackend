from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, employee_id, pin=None, role='staff', **extra_fields):
        if not employee_id:
            raise ValueError("Employee ID is required")

        user = self.model(employee_id=employee_id, role=role, **extra_fields)
        user.set_password(pin)  # PIN stored as hashed password
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, pin=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(employee_id, pin, role='admin', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    ]

    employee_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.employee_id

    def is_admin(self):
        return self.role == 'admin'
