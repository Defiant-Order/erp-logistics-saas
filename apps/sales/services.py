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


class LimiteCreditoExcedidoError(Exception):
    """BR-COB-04: la deuda acumulada del Cliente mas el total de este Pedido
    superaria el max_credit_limit del tenant, sin autorizacion explicita."""


def _stock_disponible(producto):
    """Stock Kardex - Reservas activas, en unidad base (BR-INV-01)."""
    movimientos = MovimientoInventario.objects.filter(producto=producto).exclude(
        almacen__es_cuarentena=True
    ).aggregate(
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
def confirmar_pedido(pedido, usuario, autorizado_por_superior=False):
    """Transicion BORRADOR -> CONFIRMADO (BR-VENTA-01/02, BR-COB-04).

    Por cada DetallePedido crea una ReservaInventario en unidad base (via
    factor_conversion de la Presentacion), validando que no se supere el
    stock disponible salvo que TenantConfig.allow_negative_stock lo permita.

    Si la condicion de pago es CREDITO, valida que la deuda acumulada del
    Cliente mas el total de este Pedido no supere max_credit_limit, salvo
    que `autorizado_por_superior=True` (BR-COB-04).

    Usa select_for_update() sobre cada Producto involucrado para serializar
    confirmaciones concurrentes que compitan por el mismo stock (ADR-006).
    """
    if pedido.estado_logistico != Pedido.EstadoLogistico.BORRADOR:
        raise ValueError("Solo se puede confirmar un Pedido en estado BORRADOR.")

    with tenant_context(pedido.tenant_id):
        tenant_config = pedido.tenant.config

        if pedido.condicion_pago == Pedido.CondicionPago.CREDITO and not autorizado_por_superior:
            from apps.finance.services import deuda_acumulada_cliente

            deuda_actual = deuda_acumulada_cliente(pedido.cliente)
            if deuda_actual + pedido.total > tenant_config.max_credit_limit:
                raise LimiteCreditoExcedidoError(
                    f"Deuda acumulada ({deuda_actual}) + total del pedido ({pedido.total}) "
                    f"superaria el limite de credito ({tenant_config.max_credit_limit})."
                )

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
