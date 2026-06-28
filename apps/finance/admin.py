from django.contrib import admin

from apps.finance.models import CuentaPorCobrar, Pago


class ReadOnlyInmutableAdminMixin:
    """ADR-009: estos registros son evidencia financiera inmutable, sin
    altas/ediciones/borrados desde el admin. La creacion real vendra de un
    service futuro (confirmacion de pago, cierre de entrega a credito)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(ReadOnlyInmutableAdminMixin, admin.ModelAdmin):
    list_display = ("id", "pedido", "monto_total", "monto_pagado", "saldo", "tenant")
    list_filter = ("tenant",)


@admin.register(Pago)
class PagoAdmin(ReadOnlyInmutableAdminMixin, admin.ModelAdmin):
    list_display = ("id", "pedido", "monto", "metodo_pago", "cuenta_por_cobrar", "created_by", "created_at")
    list_filter = ("metodo_pago", "tenant")
