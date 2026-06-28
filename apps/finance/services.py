from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.finance.models import CuentaPorCobrar, Pago
from apps.sales.models import Pedido
from common.tenant_context import tenant_context


def deuda_acumulada_cliente(cliente):
    """Suma el saldo de todas las CuentaPorCobrar del cliente (BR-COB-04)."""
    cuentas = CuentaPorCobrar.objects.filter(pedido__cliente=cliente)
    return sum((cuenta.saldo for cuenta in cuentas), Decimal("0"))


def _recalcular_estado_financiero(pedido):
    total_pagado = pedido.pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    if total_pagado <= 0:
        pedido.estado_financiero = Pedido.EstadoFinanciero.PENDIENTE
    elif total_pagado < pedido.total:
        pedido.estado_financiero = Pedido.EstadoFinanciero.PAGADO_PARCIAL
    else:
        pedido.estado_financiero = Pedido.EstadoFinanciero.PAGADO
    pedido.save()


@transaction.atomic
def registrar_pago(pedido, monto, metodo_pago, usuario, referencia="", cuenta_por_cobrar=None):
    """Registra un ingreso de dinero y recalcula estado_financiero entre
    PENDIENTE/PAGADO_PARCIAL/PAGADO. No establece CON_DEUDA -- ese estado es
    exclusivo del flujo de generar_cuenta_por_cobrar (BR-COB-02, doc 05)."""
    with tenant_context(pedido.tenant_id):
        pago = Pago.objects.create(
            pedido=pedido,
            cuenta_por_cobrar=cuenta_por_cobrar,
            monto=monto,
            metodo_pago=metodo_pago,
            referencia=referencia,
            created_by=usuario,
        )
        _recalcular_estado_financiero(pedido)
    return pago


@transaction.atomic
def generar_cuenta_por_cobrar(pedido):
    """BR-COB-02: la CuentaPorCobrar nace unicamente si la condicion es
    CREDITO y el Pedido ya transiciono a ENTREGADO.

    La transicion DESPACHADO -> ENTREGADO la gestiona el servicio de
    despacho/entrega (fuera de alcance todavia, ver issue de seguimiento) --
    esta funcion solo valida la precondicion y crea el registro.
    """
    if pedido.condicion_pago != Pedido.CondicionPago.CREDITO:
        raise ValueError("Solo los pedidos con condicion_pago=CREDITO generan CuentaPorCobrar.")
    if pedido.estado_logistico != Pedido.EstadoLogistico.ENTREGADO:
        raise ValueError("La CuentaPorCobrar solo nace cuando el Pedido ya esta ENTREGADO.")

    with tenant_context(pedido.tenant_id):
        cuenta = CuentaPorCobrar.objects.create(pedido=pedido, monto_total=pedido.total)
        pedido.estado_financiero = Pedido.EstadoFinanciero.CON_DEUDA
        pedido.save()
    return cuenta
