from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

from .services.number_sequence import generate_employee_id


class Workshop(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_workshops"
    )
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, workshop, employee_id=None, pin=None, role='staff', **extra_fields):

        if not workshop:
            raise ValueError("Workshop is required")

        if not pin:
            raise ValueError("PIN is required")

        if not pin.isdigit() or len(pin) != 6:
            raise ValueError("PIN must be exactly 6 digits")
        
        if role == 'owner' and self.filter(workshop=workshop, role='owner').exists():
            raise ValueError("This workshop already has an owner")

        if not employee_id:
            employee_id = generate_employee_id(workshop=workshop)

        user = self.model(
            employee_id=employee_id.upper(),
            role=role,
            workshop=workshop,
            **extra_fields
        )

        user.set_password(pin)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, employee_id, password=None, **extra_fields):

        if not password:
            raise ValueError("Superuser must have a PIN")

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        user = self.model(
            employee_id=employee_id.upper(),
            role='owner',
            workshop=None,  # 👈 IMPORTANT
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        null=True,
        db_index=True,
        related_name="users"
    )

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('staff', 'Staff'),
    ]
    employee_id = models.CharField(max_length=30, unique=True, db_index=True)
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

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['workshop']),
            models.Index(fields=['employee_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['workshop'],
                condition=models.Q(role='owner', workshop__isnull=False),
                name='unique_owner_per_workshop',
            ),
        ]

    def save(self, *args, **kwargs):
        # Ensure owners can access admin screens.
        if self.role == 'owner' or self.is_superuser:
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id}-{self.employee_id}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    

class EmployeeIdSequence(models.Model):
    workshop = models.OneToOneField(Workshop, on_delete=models.CASCADE, db_index=True)
    last_number = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.workshop.name} - {self.last_number}"
    
class ModulePermission(models.Model):
    MODULE_CHOICES = [
        ('employee_management', 'Employee Management'),
        ('reporting', 'Reporting'),
        ('settings', 'Settings'),
        ('inventory', 'Inventory Management'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_permissions')
    module_name = models.CharField(max_length=50, choices=MODULE_CHOICES)

    class Meta:
        unique_together = ('user', 'module_name')

    def __str__(self):
        return f"{self.user.employee_id} - {self.module_name}"


class UserPreference(models.Model):
    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
    ]

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="preferences"
    )

    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="dark")
    notifications = models.BooleanField(default=True)
    default_view = models.CharField(max_length=50, default="dashboard")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} Preferences"