from django.conf import settings
from django.db import models

from common.models import BaseModel


class Cliente(BaseModel):
    """Comprador B2B/B2C. Ver docs/business/01."""

    nombre = models.CharField(max_length=255)
    documento = models.CharField(max_length=20)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "documento"], name="unique_cliente_documento_por_tenant"),
        ]

    def __str__(self):
        return self.nombre


class Pedido(BaseModel):
    """Compromiso comercial central que coordina inventario, logistica y
    finanzas. Tres estados desacoplados, ver ADR-004 en docs/business/04."""

    class CondicionPago(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        CONTRA_ENTREGA = "CONTRA_ENTREGA", "Contra entrega"
        CREDITO = "CREDITO", "Credito"

    class EstadoLogistico(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        PREPARACION = "PREPARACION", "Preparacion"
        DESPACHADO = "DESPACHADO", "Despachado"
        ENTREGADO = "ENTREGADO", "Entregado"
        ENTREGADO_PARCIAL = "ENTREGADO_PARCIAL", "Entregado parcial"
        FALLIDO = "FALLIDO", "Fallido"
        CANCELADO = "CANCELADO", "Cancelado"
        RESERVA_EXPIRADA = "RESERVA_EXPIRADA", "Reserva expirada"

    class EstadoFinanciero(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO_PARCIAL = "PAGADO_PARCIAL", "Pagado parcial"
        PAGADO = "PAGADO", "Pagado"
        CON_DEUDA = "CON_DEUDA", "Con deuda"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    condicion_pago = models.CharField(max_length=20, choices=CondicionPago.choices)
    estado_logistico = models.CharField(
        max_length=20, choices=EstadoLogistico.choices, default=EstadoLogistico.BORRADOR
    )
    estado_financiero = models.CharField(
        max_length=20, choices=EstadoFinanciero.choices, default=EstadoFinanciero.PENDIENTE
    )
    total = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.cliente_id:
            self.tenant_id = self.cliente.tenant_id
        if self.cliente_id and self.tenant_id != self.cliente.tenant_id:
            raise ValueError("El Pedido debe pertenecer al mismo tenant que su Cliente.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.nombre} ({self.estado_logistico})"


class DetallePedido(BaseModel):
    """Linea de un Pedido: se vende por Presentacion (ej. "2 Cajas"), no por
    Producto suelto. Mismo patron que DetalleOrdenCompra en apps.inventory."""

    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="detalles")
    presentacion = models.ForeignKey(
        "catalog.Presentacion", on_delete=models.PROTECT, related_name="detalles_pedido"
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4)

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.pedido_id:
            self.tenant_id = self.pedido.tenant_id
        if self.pedido_id and self.tenant_id != self.pedido.tenant_id:
            raise ValueError("El DetallePedido debe pertenecer al mismo tenant que su Pedido.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} de {self.presentacion} (Pedido {self.pedido_id})"
