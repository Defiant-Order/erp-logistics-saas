from django.contrib import admin

from apps.core.models import Tenant, TenantConfig, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "ruc", "slug", "is_active", "created_at")
    search_fields = ("razon_social", "ruc", "slug")


@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    list_display = ("tenant", "allow_negative_stock", "reservation_ttl_hours", "max_credit_limit")
    list_filter = ("allow_negative_stock", "multi_warehouse_enabled")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "tenant", "is_active", "is_staff")
    list_filter = ("tenant", "is_staff", "is_active")
