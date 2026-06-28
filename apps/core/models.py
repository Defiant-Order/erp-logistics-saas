from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import UUIDTimeStampedModel


class Tenant(UUIDTimeStampedModel):
    """La empresa distribuidora (SaaS). No esta tenant-scoped a si misma."""

    razon_social = models.CharField(max_length=255)
    ruc = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=255, unique=True)

    def __str__(self):
        return self.razon_social


class TenantConfig(UUIDTimeStampedModel):
    """Reglas de negocio por tenant. Ver docs/business/06 - Politicas del Tenant."""

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="config")
    allow_negative_stock = models.BooleanField(default=False)
    reservation_ttl_hours = models.PositiveIntegerField(default=24)
    multi_warehouse_enabled = models.BooleanField(default=False)
    max_credit_limit = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    require_approval_discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"Config de {self.tenant.name}"


class User(AbstractUser):
    """Usuario del sistema. Ligado a un tenant (nulo solo para superusers de plataforma)."""

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, null=True, blank=True, related_name="users")
