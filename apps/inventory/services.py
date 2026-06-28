from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from apps.catalog.models import Producto
from apps.inventory.models import Almacen, MovimientoInventario, OrdenCompra, RecepcionCompra
from common.tenant_context import tenant_context


class ExcedenteRecepcionError(Exception):
    """BR-ABAST-03: la cantidad recibida acumulada superaria el 100% de lo
    solicitado en el DetalleOrdenCompra."""


class AlmacenCuarentenaNoConfiguradoError(Exception):
    """BR-ABAST-01: se intento registrar una merma sin tener un Almacen
    marcado como es_cuarentena=True para el tenant."""


def _stock_fisico(producto):
    """Stock fisico real (Kardex), sin restar reservas -- usado para el
    recalculo de costo promedio ponderado (ADR-003), no para disponibilidad
    de venta (ver apps.sales.services._stock_disponible para esa otra cosa)."""
    movimientos = MovimientoInventario.objects.filter(producto=producto).exclude(
        almacen__es_cuarentena=True
    ).aggregate(
        entradas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.ENTRADA)),
        salidas=Sum("cantidad", filter=Q(tipo=MovimientoInventario.Tipo.SALIDA)),
    )
    entradas = movimientos["entradas"] or Decimal("0")
    salidas = movimientos["salidas"] or Decimal("0")
    return entradas - salidas


def _recalcular_costo_promedio(producto, cantidad_nueva, costo_unitario_nuevo):
    """ADR-003: promedia el costo del stock existente con el del lote nuevo."""
    stock_actual = _stock_fisico(producto)
    valor_actual = stock_actual * producto.costo_promedio
    valor_nuevo = cantidad_nueva * costo_unitario_nuevo
    stock_resultante = stock_actual + cantidad_nueva

    if stock_resultante == 0:
        return Decimal("0")
    return (valor_actual + valor_nuevo) / stock_resultante


@transaction.atomic
def recibir_orden_compra(orden_compra, almacen_destino, lineas, usuario):
    """Procesa la recepcion fisica de una OrdenCompra (BR-ABAST-01/02/03).

    `lineas` es una lista de dicts: {"detalle": DetalleOrdenCompra,
    "cantidad": Decimal (en unidad de Presentacion), "es_merma": bool}.

    Por cada linea: genera un MovimientoInventario ENTRADA en unidad base,
    recalcula el costo promedio ponderado del Producto (ADR-003), y acumula
    en DetalleOrdenCompra.cantidad_recibida. Las mermas van al almacen de
    cuarentena del tenant en vez de almacen_destino.

    Al final, transiciona la OrdenCompra a RECIBIDA_PARCIAL o RECIBIDA segun
    si todas sus lineas quedaron completas.
    """
    if orden_compra.estado not in (OrdenCompra.Estado.ENVIADA, OrdenCompra.Estado.RECIBIDA_PARCIAL):
        raise ValueError("Solo se puede recibir una OrdenCompra en estado ENVIADA o RECIBIDA_PARCIAL.")

    with tenant_context(orden_compra.tenant_id):
        recepcion = RecepcionCompra.objects.create(
            orden_compra=orden_compra, almacen=almacen_destino, created_by=usuario
        )

        almacen_cuarentena = None
        if any(linea.get("es_merma") for linea in lineas):
            almacen_cuarentena = Almacen.objects.filter(
                tenant_id=orden_compra.tenant_id, es_cuarentena=True
            ).first()
            if almacen_cuarentena is None:
                raise AlmacenCuarentenaNoConfiguradoError(
                    "No existe un Almacen marcado como es_cuarentena=True para este tenant."
                )

        for linea in lineas:
            detalle = linea["detalle"]
            cantidad = linea["cantidad"]
            es_merma = linea.get("es_merma", False)

            total_acumulado = detalle.cantidad_recibida + cantidad
            if total_acumulado > detalle.cantidad_solicitada:
                raise ExcedenteRecepcionError(
                    f"La recepcion de {detalle} superaria el 100% solicitado "
                    f"({total_acumulado} > {detalle.cantidad_solicitada})."
                )

            producto = Producto.objects.select_for_update().get(pk=detalle.presentacion.producto_id)
            cantidad_base = cantidad * detalle.presentacion.factor_conversion

            if not es_merma:
                producto.costo_promedio = _recalcular_costo_promedio(producto, cantidad_base, detalle.costo_unitario)
                producto.save()

            MovimientoInventario.objects.create(
                producto=producto,
                almacen=almacen_cuarentena if es_merma else almacen_destino,
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad=cantidad_base,
                costo_unitario=detalle.costo_unitario,
                recepcion_compra=recepcion,
            )

            detalle.cantidad_recibida = total_acumulado
            detalle.save()

        detalles = orden_compra.detalles.all()
        if all(d.cantidad_recibida >= d.cantidad_solicitada for d in detalles):
            orden_compra.estado = OrdenCompra.Estado.RECIBIDA
        else:
            orden_compra.estado = OrdenCompra.Estado.RECIBIDA_PARCIAL
        orden_compra.save()

    return recepcion
