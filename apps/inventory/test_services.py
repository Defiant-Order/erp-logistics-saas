from decimal import ROUND_HALF_UP, Decimal

import pytest

from apps.catalog.models import Presentacion, Producto
from apps.core.models import Tenant, User
from apps.inventory.models import Almacen, MovimientoInventario, OrdenCompra, Proveedor
from apps.inventory.services import (
    AlmacenCuarentenaNoConfiguradoError,
    ExcedenteRecepcionError,
    recibir_orden_compra,
)


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.fixture
def usuario(tenant):
    return User.objects.create_user(username="comprador1", password="x", tenant=tenant)


@pytest.fixture
def proveedor(tenant):
    return Proveedor.objects.create(tenant=tenant, razon_social="Backus", ruc="20300000001")


@pytest.fixture
def producto(tenant):
    return Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")


@pytest.fixture
def presentacion(producto):
    return Presentacion.objects.create(producto=producto, nombre="Caja", factor_conversion=Decimal("24"))


@pytest.fixture
def almacen(tenant):
    return Almacen.objects.create(tenant=tenant, nombre="Almacen Central")


@pytest.fixture
def orden_compra_con_detalle(usuario, proveedor, presentacion):
    from apps.inventory.models import DetalleOrdenCompra

    orden = OrdenCompra.objects.create(
        proveedor=proveedor, created_by=usuario, estado=OrdenCompra.Estado.ENVIADA
    )
    detalle = DetalleOrdenCompra.objects.create(
        orden_compra=orden, presentacion=presentacion, cantidad_solicitada=Decimal("10"), costo_unitario=Decimal("70")
    )
    return orden, detalle


@pytest.mark.django_db
def test_recibir_orden_compra_genera_movimiento_y_marca_recibida(usuario, almacen, producto, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle

    recepcion = recibir_orden_compra(
        orden, almacen, [{"detalle": detalle, "cantidad": Decimal("10")}], usuario
    )

    orden.refresh_from_db()
    detalle.refresh_from_db()
    assert orden.estado == OrdenCompra.Estado.RECIBIDA
    assert detalle.cantidad_recibida == Decimal("10")

    movimiento = MovimientoInventario.objects.get(recepcion_compra=recepcion)
    assert movimiento.cantidad == Decimal("240")  # 10 Cajas * factor 24
    assert movimiento.almacen_id == almacen.id
    assert movimiento.costo_unitario == Decimal("70")


@pytest.mark.django_db
def test_recibir_orden_compra_parcial_deja_estado_recibida_parcial(usuario, almacen, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle

    recibir_orden_compra(orden, almacen, [{"detalle": detalle, "cantidad": Decimal("4")}], usuario)

    orden.refresh_from_db()
    detalle.refresh_from_db()
    assert orden.estado == OrdenCompra.Estado.RECIBIDA_PARCIAL
    assert detalle.cantidad_recibida == Decimal("4")


@pytest.mark.django_db
def test_recibir_orden_compra_rechaza_excedente(usuario, almacen, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle

    with pytest.raises(ExcedenteRecepcionError):
        recibir_orden_compra(orden, almacen, [{"detalle": detalle, "cantidad": Decimal("11")}], usuario)


@pytest.mark.django_db
def test_recalcula_costo_promedio_ponderado(usuario, almacen, producto, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle
    # stock inicial: 100 unidades a costo 3.00
    MovimientoInventario.objects.create(
        producto=producto, almacen=almacen, tipo=MovimientoInventario.Tipo.ENTRADA,
        cantidad=Decimal("100"), costo_unitario=Decimal("3.00"),
    )
    producto.costo_promedio = Decimal("3.00")
    producto.save()

    # recibe 4 cajas (96 unidades) a costo 70 cada caja -> costo unitario en unidad base
    recibir_orden_compra(orden, almacen, [{"detalle": detalle, "cantidad": Decimal("4")}], usuario)

    producto.refresh_from_db()
    # (100*3.00 + 96*70) / (100+96) = (300 + 6720) / 196 = 35.8163...
    esperado = (Decimal("100") * Decimal("3.00") + Decimal("96") * Decimal("70")) / Decimal("196")
    esperado = esperado.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert producto.costo_promedio == esperado


@pytest.mark.django_db
def test_merma_va_a_cuarentena_y_no_afecta_costo(usuario, almacen, producto, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle
    cuarentena = Almacen.objects.create(tenant=orden.tenant, nombre="Cuarentena", es_cuarentena=True)

    recibir_orden_compra(
        orden, almacen, [{"detalle": detalle, "cantidad": Decimal("2"), "es_merma": True}], usuario
    )

    movimiento = MovimientoInventario.objects.get(recepcion_compra__orden_compra=orden)
    assert movimiento.almacen_id == cuarentena.id

    producto.refresh_from_db()
    assert producto.costo_promedio == Decimal("0")  # no se recalculo


@pytest.mark.django_db
def test_merma_sin_almacen_cuarentena_configurado_falla(usuario, almacen, orden_compra_con_detalle):
    orden, detalle = orden_compra_con_detalle

    with pytest.raises(AlmacenCuarentenaNoConfiguradoError):
        recibir_orden_compra(
            orden, almacen, [{"detalle": detalle, "cantidad": Decimal("2"), "es_merma": True}], usuario
        )
