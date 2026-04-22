from django.conf import settings
from django.db import models


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    delivery_address = models.TextField()
    postcode = models.CharField(max_length=20)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_name


class ProducerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    producer_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    address = models.TextField()
    postcode = models.CharField(max_length=20)

    def __str__(self):
        return self.producer_name


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    AVAILABLE = "AVAILABLE"
    IN_SEASON = "IN_SEASON"
    UNAVAILABLE = "UNAVAILABLE"
    OUT_OF_SEASON = "OUT_OF_SEASON"

    STATUS_CHOICES = [
        (AVAILABLE, "Available"),
        (IN_SEASON, "In Season"),
        (UNAVAILABLE, "Unavailable"),
        (OUT_OF_SEASON, "Out of Season"),
    ]

    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    producer = models.ForeignKey(ProducerProfile, on_delete=models.CASCADE, related_name="products")
    description = models.TextField(blank=True)
    allergen_info = models.CharField(max_length=200, blank=True)
    organic_certified = models.BooleanField(default=False)
    harvest_date = models.DateField(null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    availability_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=AVAILABLE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AIModel(models.Model):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (ACTIVE, "Active"),
        (ARCHIVED, "Archived"),
    ]

    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    model_file = models.FileField(upload_to="ai_models/")
    accuracy_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_ai_models",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("name", "version")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == self.ACTIVE:
            AIModel.objects.exclude(pk=self.pk).filter(status=self.ACTIVE).update(status=self.ARCHIVED)

    def __str__(self):
        return f"{self.name} v{self.version}"


class UserActivityLog(models.Model):
    SEARCH = "SEARCH"
    PRODUCT_VIEW = "PRODUCT_VIEW"
    CART_ADD = "CART_ADD"
    CART_UPDATE = "CART_UPDATE"
    CART_REMOVE = "CART_REMOVE"
    MODEL_UPLOAD = "MODEL_UPLOAD"

    ACTION_CHOICES = [
        (SEARCH, "Search"),
        (PRODUCT_VIEW, "Product View"),
        (CART_ADD, "Cart Add"),
        (CART_UPDATE, "Cart Update"),
        (CART_REMOVE, "Cart Remove"),
        (MODEL_UPLOAD, "Model Upload"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    search_query = models.CharField(max_length=200, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} at {self.created_at:%Y-%m-%d %H:%M}"
