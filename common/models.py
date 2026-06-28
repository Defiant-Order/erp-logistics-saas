import uuid

from django.db import models

from common.tenant_context import get_current_tenant_id


class UUIDTimeStampedModel(models.Model):
    """Abstract con PK UUID y auditoria temporal base. Sin tenant: lo usan modelos
    que no pertenecen a un tenant especifico (ej. Tenant mismo)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class TenantAwareQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id):
        return self.filter(tenant_id=tenant_id)


class TenantManager(models.Manager):
    """Filtra automaticamente por el tenant en contexto (ver tenant_context).

    Si no hay tenant en contexto, no filtra: esto es deliberado para permitir
    scripts de management/migraciones de datos que operan sin request HTTP.
    El uso en codigo de negocio siempre debe ocurrir dentro de un `tenant_context`
    activo (seteado por el middleware o explicitamente en tests/management commands).
    """

    def get_queryset(self):
        queryset = TenantAwareQuerySet(self.model, using=self._db)
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return queryset
        return queryset.for_tenant(tenant_id)


class BaseModel(UUIDTimeStampedModel):
    """Abstract para toda tabla de negocio: PK UUID + tenant_id obligatorio +
    auditoria temporal. Ver docs/tech/01 - ERD y Modelos de Datos."""

    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="+")

    objects = TenantManager()
    unscoped = models.Manager()

    class Meta:
        abstract = True


class ExternalReference(BaseModel):
    """Idempotencia de eventos/webhooks externos (ver docs/tech/01).

    Escopeado por tenant porque cada tenant tiene su propio canal de WhatsApp/
    pasarela de pago: un mismo external_id de sistemas distintos no debe colisionar
    entre tenants.
    """

    source_system = models.CharField(max_length=50)
    external_id = models.CharField(max_length=255)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "source_system", "external_id"],
                name="unique_external_reference_per_tenant",
            )
        ]

    def __str__(self):
        return f"{self.source_system}:{self.external_id}"
