from django.db import models

from common.models import BaseModel


class ConfiguracionWhatsApp(BaseModel):
    """Vincula un numero de WhatsApp Business (phone_number_id) a un Tenant.
    Ver docs/tech/03 - Integraciones y Eventos y ADR-008 en docs/business/04."""

    tenant = models.OneToOneField("core.Tenant", on_delete=models.CASCADE, related_name="whatsapp")
    phone_number_id = models.CharField(max_length=50, unique=True)
    business_account_id = models.CharField(max_length=50)
    access_token = models.CharField(
        max_length=512,
        help_text="Token de usuario del sistema para ENVIAR mensajes. "
        "TODO: mover a un secret manager (GCP Secret Manager) antes de produccion.",
    )

    def __str__(self):
        return f"WhatsApp de {self.tenant.razon_social} ({self.phone_number_id})"


class EventoWebhookWhatsApp(BaseModel):
    """Registro INMUTABLE de cada webhook entrante de WhatsApp ya validado y
    deduplicado (ver common.ExternalReference). El canal solo autentica,
    parsea y guarda -- el procesamiento de negocio real (disparar un
    DomainEvent, avanzar un flujo conversacional) es responsabilidad de un
    service futuro, no de esta vista. Ver ADR-008."""

    external_id = models.CharField(max_length=255, help_text="wamid del mensaje de WhatsApp.")
    payload = models.JSONField()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("EventoWebhookWhatsApp es inmutable: no se puede modificar un registro ya creado.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("EventoWebhookWhatsApp es inmutable: no se puede eliminar un registro.")

    def __str__(self):
        return f"Evento {self.external_id}"
