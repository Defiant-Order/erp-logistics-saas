from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from apps.catalog.models import Producto
from apps.inventory.models import MovimientoInventario
from apps.sales.models import Pedido, PedidoEstadoHistorico, ReservaInventario
from common.tenant_context import tenant_context


class StockInsuficienteError(Exception):
    """BR-VENTA-02: la cantidad solicitada supera el stock disponible y el
    tenant no permite stock negativo."""


def _stock_disponible(producto):
    """Stock Kardex - Reservas activas, en unidad base (BR-INV-01)."""
    movimientos = MovimientoInventario.objects.filter(producto=producto).aggregate(
        entradas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.ENTRADA)),
        salidas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.SALIDA)),
    )
    entradas = movimientos["entradas"] or Decimal("0")
    salidas = movimientos["salidas"] or Decimal("0")
    reservado = (
        ReservaInventario.objects.filter(producto=producto, estado=ReservaInventario.Estado.RESERVADA).aggregate(
            total=Sum("cantidad")
        )["total"]
        or Decimal("0")
    )
    return (entradas - salidas) - reservado


@transaction.atomic
def confirmar_pedido(pedido, usuario):
    """Transicion BORRADOR -> CONFIRMADO (BR-VENTA-01/02).

    Por cada DetallePedido crea una ReservaInventario en unidad base (via
    factor_conversion de la Presentacion), validando que no se supere el
    stock disponible salvo que TenantConfig.allow_negative_stock lo permita.

    Usa select_for_update() sobre cada Producto involucrado para serializar
    confirmaciones concurrentes que compitan por el mismo stock (ADR-006).
    """
    if pedido.estado_logistico != Pedido.EstadoLogistico.BORRADOR:
        raise ValueError("Solo se puede confirmar un Pedido en estado BORRADOR.")

    with tenant_context(pedido.tenant_id):
        tenant_config = pedido.tenant.config
        detalles = pedido.detalles.select_related("presentacion__producto").all()

        for detalle in detalles:
            producto = Producto.objects.select_for_update().get(pk=detalle.presentacion.producto_id)
            cantidad_base = detalle.cantidad * detalle.presentacion.factor_conversion
            disponible = _stock_disponible(producto)

            if cantidad_base > disponible and not tenant_config.allow_negative_stock:
                raise StockInsuficienteError(
                    f"Stock insuficiente para {producto.nombre}: "
                    f"disponible {disponible}, solicitado {cantidad_base}."
                )

            ReservaInventario.objects.create(pedido=pedido, producto=producto, cantidad=cantidad_base)

        pedido.estado_logistico = Pedido.EstadoLogistico.CONFIRMADO
        pedido.save()

        PedidoEstadoHistorico.objects.create(
            pedido=pedido, estado_logistico=Pedido.EstadoLogistico.CONFIRMADO, changed_by=usuario
        )

    return pedido
