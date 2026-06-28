import pytest

from apps.core.models import Tenant


@pytest.mark.django_db
def test_creating_a_tenant_auto_creates_its_config_with_defaults():
    tenant = Tenant.objects.create(
        razon_social="Distribuidora Andina S.A.C.",
        ruc="20123456789",
        slug="distribuidora-andina",
    )

    assert hasattr(tenant, "config")
    assert tenant.config.allow_negative_stock is False
    assert tenant.config.reservation_ttl_hours == 24
    assert tenant.config.max_credit_limit == 0
