from django.conf import settings
from django.db import models

from common.models import BaseModel


class Proveedor(BaseModel):
    """Entidad comercial que abastece mercaderia al distribuidor. Ver docs/business/01."""

    razon_social = models.CharField(max_length=255)
    ruc = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "ruc"], name="unique_proveedor_ruc_por_tenant"),
        ]

    def __str__(self):
        return self.razon_social


class OrdenCompra(BaseModel):
    """Solicitud formal emitida al proveedor. Maquina de estados en docs/business/05."""

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADA = "ENVIADA", "Enviada"
        RECIBIDA_PARCIAL = "RECIBIDA_PARCIAL", "Recibida parcial"
        RECIBIDA = "RECIBIDA", "Recibida"
        CERRADA_INCOMPLETA = "CERRADA_INCOMPLETA", "Cerrada incompleta"

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="ordenes_compra")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.proveedor_id:
            self.tenant_id = self.proveedor.tenant_id
        if self.proveedor_id and self.tenant_id != self.proveedor.tenant_id:
            raise ValueError("La OrdenCompra debe pertenecer al mismo tenant que su Proveedor.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OC {self.id} - {self.proveedor.razon_social} ({self.estado})"
