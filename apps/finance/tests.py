from decimal import Decimal

import pytest

from apps.core.models import Tenant, User
from apps.finance.models import CuentaPorCobrar, Pago
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
def pedido(usuario, cliente):
    return Pedido.objects.create(cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario)


@pytest.mark.django_db
def test_cuenta_por_cobrar_hereda_tenant_de_pedido(pedido):
    cxc = CuentaPorCobrar.objects.create(pedido=pedido, monto_total=Decimal("500"))

    assert cxc.tenant_id == pedido.tenant_id
    assert cxc.saldo == Decimal("500")


@pytest.mark.django_db
def test_cuenta_por_cobrar_saldo_se_calcula_de_sus_pagos(pedido, usuario):
    cxc = CuentaPorCobrar.objects.create(pedido=pedido, monto_total=Decimal("500"))
    Pago.objects.create(
        pedido=pedido,
        cuenta_por_cobrar=cxc,
        monto=Decimal("200"),
        metodo_pago=Pago.MetodoPago.YAPE,
        created_by=usuario,
    )

    assert cxc.monto_pagado == Decimal("200")
    assert cxc.saldo == Decimal("300")


@pytest.mark.django_db
def test_cuenta_por_cobrar_es_inmutable(pedido):
    cxc = CuentaPorCobrar.objects.create(pedido=pedido, monto_total=Decimal("500"))

    cxc.monto_total = Decimal("999")
    with pytest.raises(ValueError):
        cxc.save()

    with pytest.raises(ValueError):
        cxc.delete()


@pytest.mark.django_db
def test_pago_es_inmutable(pedido, usuario):
    pago = Pago.objects.create(
        pedido=pedido, monto=Decimal("100"), metodo_pago=Pago.MetodoPago.EFECTIVO, created_by=usuario
    )

    pago.monto = Decimal("9999")
    with pytest.raises(ValueError):
        pago.save()

    with pytest.raises(ValueError):
        pago.delete()


@pytest.mark.django_db
def test_pago_sin_deuda_previa_no_requiere_cuenta_por_cobrar(pedido, usuario):
    pago = Pago.objects.create(
        pedido=pedido, monto=Decimal("100"), metodo_pago=Pago.MetodoPago.EFECTIVO, created_by=usuario
    )

    assert pago.cuenta_por_cobrar is None
    assert pago.tenant_id == pedido.tenant_id


@pytest.mark.django_db
def test_pago_rechaza_cuenta_por_cobrar_de_otro_pedido(usuario, cliente, pedido):
    otro_pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario
    )
    cxc_de_otro_pedido = CuentaPorCobrar.objects.create(pedido=otro_pedido, monto_total=Decimal("500"))

    with pytest.raises(ValueError):
        Pago.objects.create(
            pedido=pedido,
            cuenta_por_cobrar=cxc_de_otro_pedido,
            monto=Decimal("100"),
            metodo_pago=Pago.MetodoPago.EFECTIVO,
            created_by=usuario,
        )
