from decimal import Decimal

import pytest

from apps.catalog.models import Presentacion, Producto
from apps.core.models import Tenant, User
from apps.inventory.models import Almacen, MovimientoInventario
from apps.sales.models import Cliente, DetallePedido, Pedido, PedidoEstadoHistorico, ReservaInventario
from apps.sales.services import LimiteCreditoExcedidoError, StockInsuficienteError, confirmar_pedido


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
