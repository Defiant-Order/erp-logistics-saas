from decimal import Decimal

import pytest

from apps.core.models import Tenant, User
from apps.finance.models import CuentaPorCobrar, Pago
from apps.finance.services import deuda_acumulada_cliente, generar_cuenta_por_cobrar, registrar_pago
from apps.sales.models import Cliente, Pedido


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.fixture
def usuario(tenant):
    return User.objects.create_user(username="vendedor1", password="x", tenant=tenant)


@pytest.fixture
def cliente(tenant):
    return Cliente.objects.create(tenant=tenant, nombre="Bodega Don Jose", documento="10123456789")


@pytest.fixture
def pedido_contado(usuario, cliente):
    return Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CONTADO, created_by=usuario, total=Decimal("500")
    )


@pytest.mark.django_db
def test_registrar_pago_actualiza_estado_financiero_a_pagado_parcial(usuario, pedido_contado):
    registrar_pago(pedido_contado, Decimal("200"), Pago.MetodoPago.YAPE, usuario)

    pedido_contado.refresh_from_db()
    assert pedido_contado.estado_financiero == Pedido.EstadoFinanciero.PAGADO_PARCIAL


@pytest.mark.django_db
def test_registrar_pago_completo_marca_pagado(usuario, pedido_contado):
    registrar_pago(pedido_contado, Decimal("500"), Pago.MetodoPago.EFECTIVO, usuario)

    pedido_contado.refresh_from_db()
    assert pedido_contado.estado_financiero == Pedido.EstadoFinanciero.PAGADO


@pytest.mark.django_db
def test_generar_cuenta_por_cobrar_solo_si_credito(usuario, cliente):
    pedido = Pedido.objects.create(
        cliente=cliente,
        condicion_pago=Pedido.CondicionPago.CONTADO,
        created_by=usuario,
        estado_logistico=Pedido.EstadoLogistico.ENTREGADO,
    )

    with pytest.raises(ValueError):
        generar_cuenta_por_cobrar(pedido)


@pytest.mark.django_db
def test_generar_cuenta_por_cobrar_solo_si_entregado(usuario, cliente):
    pedido = Pedido.objects.create(cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario)

    with pytest.raises(ValueError):
        generar_cuenta_por_cobrar(pedido)


@pytest.mark.django_db
def test_generar_cuenta_por_cobrar_marca_con_deuda(usuario, cliente):
    pedido = Pedido.objects.create(
        cliente=cliente,
        condicion_pago=Pedido.CondicionPago.CREDITO,
        created_by=usuario,
        estado_logistico=Pedido.EstadoLogistico.ENTREGADO,
        total=Decimal("800"),
    )

    cuenta = generar_cuenta_por_cobrar(pedido)

    pedido.refresh_from_db()
    assert pedido.estado_financiero == Pedido.EstadoFinanciero.CON_DEUDA
    assert cuenta.monto_total == Decimal("800")
    assert cuenta.saldo == Decimal("800")


@pytest.mark.django_db
def test_deuda_acumulada_cliente_suma_saldos_de_varias_cuentas(usuario, cliente):
    pedido1 = Pedido.objects.create(
        cliente=cliente,
        condicion_pago=Pedido.CondicionPago.CREDITO,
        created_by=usuario,
        estado_logistico=Pedido.EstadoLogistico.ENTREGADO,
        total=Decimal("300"),
    )
    pedido2 = Pedido.objects.create(
        cliente=cliente,
        condicion_pago=Pedido.CondicionPago.CREDITO,
        created_by=usuario,
        estado_logistico=Pedido.EstadoLogistico.ENTREGADO,
        total=Decimal("200"),
    )
    cuenta1 = CuentaPorCobrar.objects.create(pedido=pedido1, monto_total=Decimal("300"))
    CuentaPorCobrar.objects.create(pedido=pedido2, monto_total=Decimal("200"))
    Pago.objects.create(
        pedido=pedido1, cuenta_por_cobrar=cuenta1, monto=Decimal("100"), metodo_pago=Pago.MetodoPago.YAPE,
        created_by=usuario,
    )

    assert deuda_acumulada_cliente(cliente) == Decimal("400")  # (300-100) + 200
