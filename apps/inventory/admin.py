from django.contrib import admin

from apps.inventory.models import (
    Almacen,
    DetalleOrdenCompra,
    MovimientoInventario,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "ruc", "tenant", "is_active")
    search_fields = ("razon_social", "ruc")
    list_filter = ("tenant",)


class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 1
    fields = ("presentacion", "cantidad_solicitada", "costo_unitario")


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "estado", "created_by", "tenant", "created_at")
    list_filter = ("estado", "tenant")
    inlines = [DetalleOrdenCompraInline]


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tenant", "is_active")
    list_filter = ("tenant",)


@admin.register(RecepcionCompra)
class RecepcionCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "orden_compra", "almacen", "created_by", "created_at")
    list_filter = ("tenant", "almacen")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("id", "producto", "almacen", "tipo", "cantidad", "created_at")
    list_filter = ("tipo", "almacen", "tenant")
    # Inmutable por diseno: sin altas/ediciones desde el admin, solo lectura.
    # La creacion real vendra de un service (apps.inventory.services) cuando
    # se construya el flujo de recepcion de compra.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
