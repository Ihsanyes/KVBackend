from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Brand(models.Model):
    workshop    = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'workshop']

    def __str__(self):
        return self.name


class Category(models.Model):
    workshop    = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'workshop']

    def __str__(self):
        return self.name


class VehicleBrand(models.Model):
    workshop = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    name     = models.CharField(max_length=255)

    class Meta:
        unique_together = ['name', 'workshop']

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('2W', 'Two Wheeler'),
        ('3W', 'Three Wheeler'),
        ('4W', 'Four Wheeler'),
        ('HV', 'Heavy Vehicle'),
    ]
    workshop     = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    brand        = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='models')
    model_name   = models.CharField(max_length=255)
    vehicle_type = models.CharField(max_length=2, choices=VEHICLE_TYPE_CHOICES, default='2W')

    class Meta:
        unique_together = ['brand', 'model_name', 'workshop']

    def __str__(self):
        return f"{self.brand.name} {self.model_name}"


class Product(models.Model):
    workshop    = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    name        = models.CharField(max_length=255)
    category    = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    description = models.TextField(blank=True, null=True)
    unit        = models.CharField(max_length=50, default='piece')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'category', 'workshop']
        indexes         = [models.Index(fields=['workshop'])]

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    workshop            = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True)
    product             = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    brand               = models.ForeignKey(Brand, on_delete=models.PROTECT)
    variant_name        = models.CharField(max_length=255, blank=True, null=True)
    sku                 = models.CharField(max_length=100)
    barcode             = models.CharField(max_length=100, blank=True, null=True)
    cost_price          = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price       = models.DecimalField(max_digits=10, decimal_places=2)
    compatible_vehicles = models.ManyToManyField(VehicleModel, blank=True)
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['sku', 'workshop']
        indexes         = [
            models.Index(fields=['workshop']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.product.name} – {self.brand.name} – {self.variant_name or 'Standard'}"


class Stock(models.Model):
    workshop        = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock')
    quantity        = models.IntegerField(default=0)
    updated_at      = models.DateTimeField(auto_now=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product_variant', 'workshop']

    def __str__(self):
        return f"{self.product_variant} | qty={self.quantity}"


class StockAlert(models.Model):
    workshop        = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True, related_name='stock_alerts')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='alert_setting')
    min_stock       = models.PositiveIntegerField(default=5, verbose_name='Reorder Level')
    max_stock       = models.PositiveIntegerField(default=100)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product_variant', 'workshop']

    def __str__(self):
        return f"{self.product_variant} | reorder @ {self.min_stock}"

    def is_low(self, current_qty: int) -> bool:
        return current_qty <= self.min_stock


class Supplier(models.Model):
    workshop     = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True, related_name='suppliers')
    name         = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=100, blank=True)
    phone        = models.CharField(max_length=15)
    email        = models.EmailField(blank=True)
    address      = models.TextField(blank=True)
    gstin        = models.CharField(max_length=20, blank=True)
    credit_days  = models.PositiveSmallIntegerField(default=0)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'workshop']
        ordering        = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT     = 'DRAFT',     'Draft'
        ORDERED   = 'ORDERED',   'Ordered'
        PARTIAL   = 'PARTIAL',   'Partially Received'
        RECEIVED  = 'RECEIVED',  'Fully Received'
        CANCELLED = 'CANCELLED', 'Cancelled'

    workshop      = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True, related_name='purchase_orders')
    supplier      = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    po_number     = models.CharField(max_length=30, unique=True)
    status        = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    order_date    = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    subtotal      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes         = models.TextField(blank=True)
    created_by    = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['workshop', 'status'])]

    def __str__(self):
        return f"PO#{self.po_number}"


class PurchaseOrderItem(models.Model):
    purchase_order  = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='po_items')
    ordered_qty     = models.PositiveIntegerField()
    received_qty    = models.PositiveIntegerField(default=0)
    unit_cost       = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate        = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    line_total      = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def pending_qty(self):
        return self.ordered_qty - self.received_qty

    def __str__(self):
        return f"{self.product_variant} | {self.ordered_qty} ordered"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        PURCHASE   = 'PURCHASE',   'Purchase / GRN'
        JOB_ISSUE  = 'JOB_ISSUE',  'Issued to Job'
        JOB_RETURN = 'JOB_RETURN', 'Returned from Job'
        SUP_RETURN = 'SUP_RETURN', 'Returned to Supplier'
        ADJUSTMENT = 'ADJUSTMENT', 'Manual Adjustment'
        SCRAP      = 'SCRAP',      'Scrap / Write-off'

    workshop        = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True, related_name='stock_movements')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='movements')
    movement_type   = models.CharField(max_length=20, choices=MovementType.choices)
    quantity        = models.IntegerField()
    unit_cost       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchase_order  = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    job_card_id     = models.PositiveIntegerField(null=True, blank=True)
    reference_note  = models.CharField(max_length=255, blank=True)
    moved_by        = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    moved_at        = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-moved_at']
        indexes  = [
            models.Index(fields=['workshop', 'product_variant']),
            models.Index(fields=['workshop', 'movement_type']),
        ]

    def __str__(self):
        d = '▲ IN' if self.quantity > 0 else '▼ OUT'
        return f"{d} {abs(self.quantity)} × {self.product_variant} [{self.movement_type}]"


class PriceHistory(models.Model):
    workshop          = models.ForeignKey('users.Workshop', on_delete=models.CASCADE, db_index=True)
    product_variant   = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='price_history')
    old_cost_price    = models.DecimalField(max_digits=10, decimal_places=2)
    new_cost_price    = models.DecimalField(max_digits=10, decimal_places=2)
    old_selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    changed_by        = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    changed_at        = models.DateTimeField(auto_now_add=True)
    reason            = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.product_variant} | ₹{self.old_selling_price} → ₹{self.new_selling_price}"
