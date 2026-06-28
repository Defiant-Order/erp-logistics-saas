from decimal import Decimal

import pytest

from apps.catalog.models import Presentacion, Producto
from apps.core.models import Tenant, User
from apps.finance.models import Pago
from apps.finance.services import registrar_pago
from apps.inventory.models import Almacen, MovimientoInventario
from apps.sales.models import Cliente, DetallePedido, Pedido, PedidoEstadoHistorico, ReservaInventario
from apps.sales.services import (
    LimiteCreditoExcedidoError,
    PagoRequeridoError,
    StockInsuficienteError,
    avanzar_a_preparacion,
    confirmar_entrega,
    confirmar_pedido,
    despachar_pedido,
)


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
def producto(tenant):
    return Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")


@pytest.fixture
def presentacion(producto):
    return Presentacion.objects.create(producto=producto, nombre="Caja", factor_conversion=Decimal("24"))


@pytest.fixture
def almacen(tenant):
    return Almacen.objects.create(tenant=tenant, nombre="Almacen Central")


def _ingresar_stock(producto, almacen, cantidad):
    return MovimientoInventario.objects.create(
        producto=producto,
        almacen=almacen,
        tipo=MovimientoInventario.Tipo.ENTRADA,
        cantidad=cantidad,
        costo_unitario=Decimal("3.50"),
    )


def _crear_pedido_con_detalle(cliente, usuario, presentacion, cantidad_presentaciones):
    pedido = Pedido.objects.create(cliente=cliente, condicion_pago=Pedido.CondicionPago.CONTADO, created_by=usuario)
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=cantidad_presentaciones, precio_unitario=Decimal("75")
    )
    return pedido


@pytest.mark.django_db
def test_confirmar_pedido_crea_reserva_en_unidad_base(usuario, cliente, presentacion, almacen, producto):
    _ingresar_stock(producto, almacen, Decimal("100"))
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))

    confirmar_pedido(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.CONFIRMADO

    reserva = ReservaInventario.objects.get(pedido=pedido)
    assert reserva.cantidad == Decimal("48")  # 2 Cajas * factor 24
    assert reserva.estado == ReservaInventario.Estado.RESERVADA

    assert PedidoEstadoHistorico.objects.filter(
        pedido=pedido, estado_logistico=Pedido.EstadoLogistico.CONFIRMADO
    ).exists()


@pytest.mark.django_db
def test_confirmar_pedido_rechaza_si_stock_insuficiente(usuario, cliente, presentacion, almacen, producto):
    _ingresar_stock(producto, almacen, Decimal("10"))
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))

    with pytest.raises(StockInsuficienteError):
        confirmar_pedido(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.BORRADOR
    assert not ReservaInventario.objects.filter(pedido=pedido).exists()


@pytest.mark.django_db
def test_confirmar_pedido_permite_stock_negativo_si_tenant_lo_permite(
    usuario, cliente, presentacion, almacen, producto, tenant
):
    tenant.config.allow_negative_stock = True
    tenant.config.save()
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))

    confirmar_pedido(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.CONFIRMADO
    assert ReservaInventario.objects.get(pedido=pedido).cantidad == Decimal("48")


@pytest.mark.django_db
def test_confirmar_pedido_falla_si_no_esta_en_borrador(usuario, cliente, presentacion, almacen, producto):
    _ingresar_stock(producto, almacen, Decimal("100"))
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))
    confirmar_pedido(pedido, usuario)

    with pytest.raises(ValueError):
        confirmar_pedido(pedido, usuario)


@pytest.mark.django_db
def test_confirmar_pedido_a_credito_rechaza_si_supera_limite(
    usuario, cliente, presentacion, almacen, producto, tenant
):
    tenant.config.max_credit_limit = Decimal("100")
    tenant.config.save()
    _ingresar_stock(producto, almacen, Decimal("100"))
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario, total=Decimal("500")
    )
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )

    with pytest.raises(LimiteCreditoExcedidoError):
        confirmar_pedido(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.BORRADOR


@pytest.mark.django_db
def test_confirmar_pedido_a_credito_permite_si_autorizado_por_superior(
    usuario, cliente, presentacion, almacen, producto, tenant
):
    tenant.config.max_credit_limit = Decimal("100")
    tenant.config.save()
    _ingresar_stock(producto, almacen, Decimal("100"))
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario, total=Decimal("500")
    )
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )

    confirmar_pedido(pedido, usuario, autorizado_por_superior=True)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.CONFIRMADO


@pytest.mark.django_db
def test_ciclo_completo_contado_paga_antes_de_preparacion(usuario, cliente, presentacion, almacen, producto):
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))
    pedido.total = Decimal("150")
    pedido.save()
    _ingresar_stock(producto, almacen, Decimal("100"))
    confirmar_pedido(pedido, usuario)

    registrar_pago(pedido, Decimal("150"), Pago.MetodoPago.EFECTIVO, usuario)
    avanzar_a_preparacion(pedido, usuario)
    despachar_pedido(pedido, usuario)
    confirmar_entrega(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.ENTREGADO

    reserva = ReservaInventario.objects.get(pedido=pedido)
    assert reserva.estado == ReservaInventario.Estado.CONSUMIDA

    salida = MovimientoInventario.objects.get(reserva_inventario=reserva)
    assert salida.tipo == MovimientoInventario.Tipo.SALIDA
    assert salida.cantidad == Decimal("48")


@pytest.mark.django_db
def test_contado_no_puede_avanzar_a_preparacion_sin_pagar(usuario, cliente, presentacion, almacen, producto):
    pedido = _crear_pedido_con_detalle(cliente, usuario, presentacion, Decimal("2"))
    pedido.total = Decimal("150")
    pedido.save()
    _ingresar_stock(producto, almacen, Decimal("100"))
    confirmar_pedido(pedido, usuario)

    with pytest.raises(PagoRequeridoError):
        avanzar_a_preparacion(pedido, usuario)


@pytest.mark.django_db
def test_contra_entrega_sin_pagar_marca_fallido_y_revierte_stock(usuario, cliente, presentacion, almacen, producto):
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CONTRA_ENTREGA, created_by=usuario, total=Decimal("150")
    )
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )
    _ingresar_stock(producto, almacen, Decimal("100"))
    confirmar_pedido(pedido, usuario)
    avanzar_a_preparacion(pedido, usuario)
    despachar_pedido(pedido, usuario)

    confirmar_entrega(pedido, usuario, pago=None)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.FALLIDO

    entradas_compensatorias = MovimientoInventario.objects.filter(
        producto=producto, tipo=MovimientoInventario.Tipo.ENTRADA
    ).count()
    assert entradas_compensatorias == 2  # el ingreso inicial + la reversion


@pytest.mark.django_db
def test_contra_entrega_pagando_completo_llega_a_entregado(usuario, cliente, presentacion, almacen, producto):
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CONTRA_ENTREGA, created_by=usuario, total=Decimal("150")
    )
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )
    _ingresar_stock(producto, almacen, Decimal("100"))
    confirmar_pedido(pedido, usuario)
    avanzar_a_preparacion(pedido, usuario)
    despachar_pedido(pedido, usuario)

    confirmar_entrega(pedido, usuario, pago={"monto": Decimal("150"), "metodo_pago": Pago.MetodoPago.YAPE})

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.ENTREGADO
    assert Pago.objects.filter(pedido=pedido).exists()


@pytest.mark.django_db
def test_credito_entregado_genera_cuenta_por_cobrar_automaticamente(
    usuario, cliente, presentacion, almacen, producto, tenant
):
    tenant.config.max_credit_limit = Decimal("1000")
    tenant.config.save()
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario, total=Decimal("150")
    )
    DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )
    _ingresar_stock(producto, almacen, Decimal("100"))
    confirmar_pedido(pedido, usuario)
    avanzar_a_preparacion(pedido, usuario)
    despachar_pedido(pedido, usuario)
    confirmar_entrega(pedido, usuario)

    pedido.refresh_from_db()
    assert pedido.estado_logistico == Pedido.EstadoLogistico.ENTREGADO
    assert pedido.estado_financiero == Pedido.EstadoFinanciero.CON_DEUDA

    from apps.finance.models import CuentaPorCobrar

    cuenta = CuentaPorCobrar.objects.get(pedido=pedido)
    assert cuenta.monto_total == Decimal("150")
