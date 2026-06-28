import pytest

from apps.core.models import Tenant
from common.models import ExternalReference
from common.tenant_context import tenant_context


@pytest.mark.django_db
def test_tenant_manager_isolates_records_by_tenant():
    tenant_a = Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")
    tenant_b = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")

    ExternalReference.unscoped.create(tenant=tenant_a, source_system="whatsapp", external_id="msg-1")
    ExternalReference.unscoped.create(tenant=tenant_b, source_system="whatsapp", external_id="msg-1")

    with tenant_context(tenant_a.id):
        assert ExternalReference.objects.count() == 1
        assert ExternalReference.objects.get().tenant_id == tenant_a.id

    with tenant_context(tenant_b.id):
        assert ExternalReference.objects.count() == 1
        assert ExternalReference.objects.get().tenant_id == tenant_b.id

    assert ExternalReference.unscoped.count() == 2


@pytest.mark.django_db
def test_tenant_manager_without_context_does_not_filter():
    tenant_a = Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")
    tenant_b = Tenant.objects.create(razon_social="Distribuidora B", ruc="20100000002", slug="distribuidora-b")

    ExternalReference.unscoped.create(tenant=tenant_a, source_system="whatsapp", external_id="msg-1")
    ExternalReference.unscoped.create(tenant=tenant_b, source_system="whatsapp", external_id="msg-1")

    assert ExternalReference.objects.count() == 2
