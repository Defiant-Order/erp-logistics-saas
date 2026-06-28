from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from apps.catalog.models import Producto
from apps.inventory.models import Almacen, MovimientoInventario
from apps.sales.models import Pedido, PedidoEstadoHistorico, ReservaInventario
from common.tenant_context import tenant_context


class StockInsuficienteError(Exception):
    """BR-VENTA-02: la cantidad solicitada supera el stock disponible y el
    tenant no permite stock negativo."""


class LimiteCreditoExcedidoError(Exception):
    """BR-COB-04: la deuda acumulada del Cliente mas el total de este Pedido
    superaria el max_credit_limit del tenant, sin autorizacion explicita."""


class PagoRequeridoError(Exception):
    """BR-COB-01: CONTADO exige el pago total antes de pasar a PREPARACION."""


class SinAlmacenConStockError(Exception):
    """No se encontro un unico almacen con stock suficiente para despachar.
    Repartir el despacho entre varios almacenes queda fuera de alcance
    (ver TenantConfig.multi_warehouse_enabled, hoy False por defecto)."""


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


def _registrar_cambio_estado(pedido, usuario):
    PedidoEstadoHistorico.objects.create(
        pedido=pedido, estado_logistico=pedido.estado_logistico, changed_by=usuario
    )


@transaction.atomic
def avanzar_a_preparacion(pedido, usuario):
    """Transicion CONFIRMADO -> PREPARACION (BR-COB-01): si la condicion de
    pago es CONTADO, exige que el Pedido ya este PAGADO en su totalidad."""
    if pedido.estado_logistico != Pedido.EstadoLogistico.CONFIRMADO:
        raise ValueError("Solo se puede pasar a PREPARACION un Pedido CONFIRMADO.")

    with tenant_context(pedido.tenant_id):
        if (
            pedido.condicion_pago == Pedido.CondicionPago.CONTADO
            and pedido.estado_financiero != Pedido.EstadoFinanciero.PAGADO
        ):
            raise PagoRequeridoError("BR-COB-01: se requiere el pago total antes de pasar a PREPARACION.")

        pedido.estado_logistico = Pedido.EstadoLogistico.PREPARACION
        pedido.save()
        _registrar_cambio_estado(pedido, usuario)

    return pedido


def _elegir_almacen_con_stock(producto, cantidad_necesaria):
    """Elige un almacen individual (no cuarentena) con stock fisico
    suficiente para cubrir la cantidad. Repartir entre varios almacenes
    queda fuera de alcance, ver SinAlmacenConStockError."""
    filas = (
        MovimientoInventario.objects.filter(producto=producto)
        .exclude(almacen__es_cuarentena=True)
        .values("almacen")
        .annotate(
            entradas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.ENTRADA)),
            salidas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.SALIDA)),
        )
    )
    for fila in filas:
        stock = (fila["entradas"] or Decimal("0")) - (fila["salidas"] or Decimal("0"))
        if stock >= cantidad_necesaria:
            return Almacen.objects.get(pk=fila["almacen"])

    raise SinAlmacenConStockError(
        f"Ningun almacen individual tiene {cantidad_necesaria} unidades disponibles de {producto.nombre}."
    )


@transaction.atomic
def despachar_pedido(pedido, usuario):
    """Transicion PREPARACION -> DESPACHADO (BR-VENTA-04): consume cada
    ReservaInventario RESERVADA y genera el MovimientoInventario de SALIDA
    real que efectivamente descuenta el Kardex."""
    if pedido.estado_logistico != Pedido.EstadoLogistico.PREPARACION:
        raise ValueError("Solo se puede despachar un Pedido en PREPARACION.")

    with tenant_context(pedido.tenant_id):
        reservas = pedido.reservas.filter(estado=ReservaInventario.Estado.RESERVADA)

        for reserva in reservas:
            producto = Producto.objects.select_for_update().get(pk=reserva.producto_id)
            almacen = _elegir_almacen_con_stock(producto, reserva.cantidad)

            MovimientoInventario.objects.create(
                producto=producto,
                almacen=almacen,
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad=reserva.cantidad,
                reserva_inventario=reserva,
            )
            reserva.estado = ReservaInventario.Estado.CONSUMIDA
            reserva.save()

        pedido.estado_logistico = Pedido.EstadoLogistico.DESPACHADO
        pedido.save()
        _registrar_cambio_estado(pedido, usuario)

    return pedido


def _revertir_stock_y_marcar_fallido(pedido, usuario):
    """BR-COB-03: si no se paga contra entrega, el Pedido pasa a FALLIDO y la
    mercaderia regresa al almacen. El Kardex es inmutable: no se borra la
    SALIDA original, se genera una ENTRADA compensatoria en el mismo
    almacen, identificado via MovimientoInventario.reserva_inventario."""
    for reserva in pedido.reservas.filter(estado=ReservaInventario.Estado.CONSUMIDA):
        salida = MovimientoInventario.objects.get(
            reserva_inventario=reserva, tipo=MovimientoInventario.Tipo.SALIDA
        )
        MovimientoInventario.objects.create(
            producto=salida.producto,
            almacen=salida.almacen,
            tipo=MovimientoInventario.Tipo.ENTRADA,
            cantidad=salida.cantidad,
        )

    pedido.estado_logistico = Pedido.EstadoLogistico.FALLIDO
    pedido.save()
    _registrar_cambio_estado(pedido, usuario)


@transaction.atomic
def confirmar_entrega(pedido, usuario, pago=None):
    """Transicion DESPACHADO -> ENTREGADO o FALLIDO (BR-COB-01/02/03).

    `pago` es un dict opcional {"monto", "metodo_pago", "referencia"},
    usado unicamente cuando condicion_pago=CONTRA_ENTREGA. Si no se paga el
    total, el Pedido pasa a FALLIDO y se revierte el stock despachado.

    Si condicion_pago=CREDITO, al llegar a ENTREGADO se genera la
    CuentaPorCobrar automaticamente (BR-COB-02).
    """
    if pedido.estado_logistico != Pedido.EstadoLogistico.DESPACHADO:
        raise ValueError("Solo se puede confirmar la entrega de un Pedido DESPACHADO.")

    from apps.finance.services import generar_cuenta_por_cobrar, registrar_pago

    with tenant_context(pedido.tenant_id):
        if pedido.condicion_pago == Pedido.CondicionPago.CONTRA_ENTREGA:
            monto_pagado = (pago or {}).get("monto", Decimal("0"))
            if monto_pagado < pedido.total:
                _revertir_stock_y_marcar_fallido(pedido, usuario)
                return pedido

            registrar_pago(
                pedido, monto_pagado, pago["metodo_pago"], usuario, referencia=pago.get("referencia", "")
            )

        pedido.estado_logistico = Pedido.EstadoLogistico.ENTREGADO
        pedido.save()
        _registrar_cambio_estado(pedido, usuario)

        if pedido.condicion_pago == Pedido.CondicionPago.CREDITO:
            generar_cuenta_por_cobrar(pedido)

    return pedido
