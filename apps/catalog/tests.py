from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.catalog.models import Presentacion, Producto
from apps.core.models import Tenant
from common.tenant_context import tenant_context


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.mark.django_db
def test_presentacion_hereda_tenant_del_producto(tenant):
    producto = Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")
    presentacion = Presentacion.objects.create(producto=producto, nombre="Botella", factor_conversion=Decimal("1"))

    assert presentacion.tenant_id == tenant.id


@pytest.mark.django_db
def test_factor_conversion_refleja_la_unidad_base(tenant):
    producto = Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")
    botella = Presentacion.objects.create(producto=producto, nombre="Botella", factor_conversion=Decimal("1"))
    sixpack = Presentacion.objects.create(producto=producto, nombre="Sixpack", factor_conversion=Decimal("6"))
    caja = Presentacion.objects.create(producto=producto, nombre="Caja", factor_conversion=Decimal("24"))

    assert botella.factor_conversion == Decimal("1")
    assert sixpack.factor_conversion == Decimal("6")
    assert caja.factor_conversion == Decimal("24")


@pytest.mark.django_db
def test_presentacion_no_puede_tener_tenant_distinto_al_producto(tenant):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")
    producto = Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")

    with pytest.raises(ValueError):
        Presentacion.objects.create(
            producto=producto, tenant=otro_tenant, nombre="Botella", factor_conversion=Decimal("1")
        )


@pytest.mark.django_db
def test_sku_es_unico_por_tenant_no_globalmente(tenant):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")
    Producto.objects.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")

    # mismo SKU en otro tenant: permitido
    Producto.objects.create(tenant=otro_tenant, nombre="Cerveza Cristal", sku="CRIS-001")

    # mismo SKU repetido dentro del mismo tenant: prohibido
    with pytest.raises(IntegrityError):
        Producto.objects.create(tenant=tenant, nombre="Otro producto", sku="CRIS-001")


@pytest.mark.django_db
def test_tenant_manager_aisla_productos_entre_tenants(tenant):
    otro_tenant = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")
    Producto.unscoped.create(tenant=tenant, nombre="Cerveza Cristal", sku="CRIS-001")
    Producto.unscoped.create(tenant=otro_tenant, nombre="Cerveza Pilsen", sku="PILS-001")

    with tenant_context(tenant.id):
        assert Producto.objects.count() == 1
        assert Producto.objects.get().sku == "CRIS-001"
