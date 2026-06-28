from django.contrib import admin

from apps.sales.models import Cliente, DetallePedido, Pedido, PedidoEstadoHistorico, ReservaInventario


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "tenant", "is_active")
    search_fields = ("nombre", "documento")
    list_filter = ("tenant",)


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    fields = ("presentacion", "cantidad", "precio_unitario")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "condicion_pago",
        "estado_logistico",
        "estado_financiero",
        "total",
        "created_by",
    )
    list_filter = ("estado_logistico", "estado_financiero", "condicion_pago", "tenant")
    inlines = [DetallePedidoInline]


@admin.register(ReservaInventario)
class ReservaInventarioAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "producto", "cantidad", "estado", "tenant")
    list_filter = ("estado", "tenant")


@admin.register(PedidoEstadoHistorico)
class PedidoEstadoHistoricoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "estado_logistico", "changed_by", "created_at")
    list_filter = ("estado_logistico", "tenant")

    # Inmutable por diseno: solo lectura, igual que MovimientoInventario.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
