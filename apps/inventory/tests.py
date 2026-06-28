import pytest

from apps.core.models import Tenant, User
from apps.inventory.models import OrdenCompra, Proveedor


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.fixture
def usuario(tenant):
    return User.objects.create_user(username="vendedor1", password="x", tenant=tenant)


@pytest.mark.django_db
def test_orden_compra_inicia_en_borrador(tenant, usuario):
    proveedor = Proveedor.objects.create(tenant=tenant, razon_social="Backus", ruc="20300000001")
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)

    assert orden.estado == OrdenCompra.Estado.BORRADOR
    assert orden.tenant_id == tenant.id


@pytest.mark.django_db
def test_orden_compra_hereda_tenant_del_proveedor(tenant, usuario):
    proveedor = Proveedor.objects.create(tenant=tenant, razon_social="Backus", ruc="20300000001")
    orden = OrdenCompra.objects.create(proveedor=proveedor, created_by=usuario)

    assert orden.tenant_id == proveedor.tenant_id


@pytest.mark.django_db
def test_orden_compra_no_puede_tener_tenant_distinto_al_proveedor(tenant, usuario):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")
    proveedor = Proveedor.objects.create(tenant=tenant, razon_social="Backus", ruc="20300000001")

    with pytest.raises(ValueError):
        OrdenCompra.objects.create(proveedor=proveedor, tenant=otro_tenant, created_by=usuario)
