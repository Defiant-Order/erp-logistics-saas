from django.contrib import admin

from apps.sales.models import Cliente, DetallePedido, Pedido


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
