from django.conf import settings
from django.db import models

from common.models import BaseModel


class CuentaPorCobrar(BaseModel):
    """Deuda exigible generada por una entrega a credito (BR-COB-02, ver
    docs/business/03). INMUTABLE por ADR-009 (docs/business/04): no tiene un
    campo "monto_pagado" que se actualice -- el saldo se calcula sumando los
    Pago asociados, igual patron que el stock derivado del Kardex."""

    pedido = models.OneToOneField("sales.Pedido", on_delete=models.PROTECT, related_name="cuenta_por_cobrar")
    monto_total = models.DecimalField(max_digits=12, decimal_places=4)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("CuentaPorCobrar es inmutable: no se puede modificar un registro ya creado.")
        if not self.tenant_id and self.pedido_id:
            self.tenant_id = self.pedido.tenant_id
        if self.pedido_id and self.tenant_id != self.pedido.tenant_id:
            raise ValueError("La CuentaPorCobrar debe pertenecer al mismo tenant que su Pedido.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("CuentaPorCobrar es inmutable: no se puede eliminar un registro.")

    @property
    def monto_pagado(self):
        return self.pagos.aggregate(total=models.Sum("monto"))["total"] or 0

    @property
    def saldo(self):
        return self.monto_total - self.monto_pagado

    def __str__(self):
        return f"CxC Pedido {self.pedido_id} - saldo {self.saldo}"


class Pago(BaseModel):
    """Entidad central de transaccion financiera: registra el ingreso de
    dinero, independiente de si existe o no una deuda previa. INMUTABLE por
    ADR-009. Ver docs/business/01 y el ERD en docs/tech/01."""

    class MetodoPago(models.TextChoices):
        YAPE = "YAPE", "Yape"
        PLIN = "PLIN", "Plin"
        EFECTIVO = "EFECTIVO", "Efectivo"

    pedido = models.ForeignKey("sales.Pedido", on_delete=models.PROTECT, related_name="pagos")
    cuenta_por_cobrar = models.ForeignKey(
        CuentaPorCobrar, on_delete=models.PROTECT, null=True, blank=True, related_name="pagos"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=4)
    metodo_pago = models.CharField(max_length=10, choices=MetodoPago.choices)
    referencia = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Pago es inmutable: no se puede modificar un registro ya creado.")
        if not self.tenant_id and self.pedido_id:
            self.tenant_id = self.pedido.tenant_id
        if self.pedido_id and self.tenant_id != self.pedido.tenant_id:
            raise ValueError("El Pago debe pertenecer al mismo tenant que su Pedido.")
        if self.cuenta_por_cobrar_id and self.cuenta_por_cobrar.pedido_id != self.pedido_id:
            raise ValueError("La CuentaPorCobrar del Pago debe corresponder al mismo Pedido.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Pago es inmutable: no se puede eliminar un registro.")

    def __str__(self):
        return f"Pago {self.monto} ({self.metodo_pago}) - Pedido {self.pedido_id}"
