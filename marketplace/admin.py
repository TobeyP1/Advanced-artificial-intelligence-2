from django.contrib import admin
from .models import (
    AIModel,
    Category,
    CustomerProfile,
    Order,
    OrderItem,
    ProducerProfile,
    Product,
    UserActivityLog,
)

admin.site.register(CustomerProfile)
admin.site.register(ProducerProfile)
admin.site.register(Category)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "producer", "price", "stock_quantity", "availability_status")
    list_filter = ("category", "availability_status", "producer")
    search_fields = ("name", "producer__producer_name")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("producer",)
        return ()


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "status", "accuracy_score", "uploaded_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "version")


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "product", "search_query", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("search_query", "user__username", "product__name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "total_amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("customer__username",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price")
    search_fields = ("order__id", "product__name")
