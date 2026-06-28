from decimal import Decimal

import pytest

from apps.catalog.models import Presentacion, Producto
from apps.core.models import Tenant, User
from apps.sales.models import Cliente, DetallePedido, Pedido


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
def presentacion(tenant):
    producto = Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")
    return Presentacion.objects.create(producto=producto, nombre="Caja", factor_conversion=Decimal("24"))


@pytest.mark.django_db
def test_pedido_inicia_en_borrador_pendiente(usuario, cliente):
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CONTADO, created_by=usuario
    )

    assert pedido.estado_logistico == Pedido.EstadoLogistico.BORRADOR
    assert pedido.estado_financiero == Pedido.EstadoFinanciero.PENDIENTE
    assert pedido.tenant_id == cliente.tenant_id


@pytest.mark.django_db
def test_pedido_no_puede_tener_tenant_distinto_al_cliente(usuario, cliente):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")

    with pytest.raises(ValueError):
        Pedido.objects.create(
            cliente=cliente,
            tenant=otro_tenant,
            condicion_pago=Pedido.CondicionPago.CONTADO,
            created_by=usuario,
        )


@pytest.mark.django_db
def test_detalle_pedido_se_vende_por_presentacion(usuario, cliente, presentacion):
    pedido = Pedido.objects.create(
        cliente=cliente, condicion_pago=Pedido.CondicionPago.CREDITO, created_by=usuario
    )
    detalle = DetallePedido.objects.create(
        pedido=pedido, presentacion=presentacion, cantidad=Decimal("2"), precio_unitario=Decimal("75")
    )

    assert detalle.tenant_id == pedido.tenant_id
    assert detalle.presentacion.producto.sku == "CRIS-001"


@pytest.mark.django_db
def test_cliente_documento_es_unico_por_tenant_no_globalmente(tenant):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")
    Cliente.objects.create(tenant=tenant, nombre="Bodega Don Jose", documento="10123456789")

    # mismo documento en otro tenant: permitido
    Cliente.objects.create(tenant=otro_tenant, nombre="Bodega Maria", documento="10123456789")
