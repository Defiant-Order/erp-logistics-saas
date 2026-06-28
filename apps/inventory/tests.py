from decimal import Decimal

import pytest

from apps.catalog.models import Producto
from apps.core.models import Tenant, User
from apps.inventory.models import (
    Almacen,
    DetalleOrdenCompra,
    MovimientoInventario,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.fixture
def usuario(tenant):
    return User.objects.create_user(username="vendedor1", password="x", tenant=tenant)


@pytest.fixture
def proveedor(tenant):
    return Proveedor.objects.create(tenant=tenant, razon_social="Backus", ruc="20300000001")


@pytest.fixture
def producto(tenant):
    return Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")


@pytest.fixture
def almacen(tenant):
    return Almacen.objects.create(tenant=tenant, nombre="Almacen Central")


@pytest.mark.django_db
def test_orden_compra_inicia_en_borrador(tenant, usuario, proveedor):
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)

    assert orden.estado == OrdenCompra.Estado.BORRADOR
    assert orden.tenant_id == tenant.id


@pytest.mark.django_db
def test_orden_compra_hereda_tenant_del_proveedor(usuario, proveedor):
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)

    assert orden.tenant_id == proveedor.tenant_id


@pytest.mark.django_db
def test_orden_compra_no_puede_tener_tenant_distinto_al_proveedor(tenant, usuario, proveedor):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")

    with pytest.raises(ValueError):
        OrdenCompra.objects.create(proveedor=proveedor, tenant=otro_tenant, created_by=usuario)


@pytest.mark.django_db
def test_detalle_orden_compra_guarda_cantidad_y_costo(usuario, proveedor, producto):
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)
    detalle = DetalleOrdenCompra.objects.create(
        orden_compra=orden, producto=producto, cantidad_solicitada=Decimal("50"), costo_unitario=Decimal("3.50")
    )

    assert detalle.tenant_id == orden.tenant_id
    assert detalle.cantidad_solicitada == Decimal("50")
    assert detalle.costo_unitario == Decimal("3.50")


@pytest.mark.django_db
def test_recepcion_compra_hereda_tenant_de_orden_compra(usuario, proveedor, almacen):
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)
    recepcion = RecepcionCompra.objects.create(orden_compra=orden, almacen=almacen, created_by=usuario)

    assert recepcion.tenant_id == orden.tenant_id


@pytest.mark.django_db
def test_movimiento_inventario_registra_entrada_con_costo(producto, almacen, usuario, proveedor):
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)
    recepcion = RecepcionCompra.objects.create(orden_compra=orden, almacen=almacen, created_by=usuario)

    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        almacen=almacen,
        tipo=MovimientoInventario.Tipo.ENTRADA,
        cantidad=Decimal("50"),
        costo_unitario=Decimal("3.50"),
        recepcion_compra=recepcion,
    )

    assert movimiento.tenant_id == almacen.tenant_id
    assert movimiento.costo_unitario == Decimal("3.50")


@pytest.mark.django_db
def test_movimiento_inventario_es_inmutable(producto, almacen):
    movimiento = MovimientoInventario.objects.create(
        producto=producto, almacen=almacen, tipo=MovimientoInventario.Tipo.ENTRADA, cantidad=Decimal("10")
    )

    movimiento.cantidad = Decimal("999")
    with pytest.raises(ValueError):
        movimiento.save()

    with pytest.raises(ValueError):
        movimiento.delete()
