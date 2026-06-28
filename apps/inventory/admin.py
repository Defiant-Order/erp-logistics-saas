from django.contrib import admin

from apps.inventory.models import OrdenCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "ruc", "tenant", "is_active")
    search_fields = ("razon_social", "ruc")
    list_filter = ("tenant",)


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "estado", "created_by", "tenant", "created_at")
    list_filter = ("estado", "tenant")
