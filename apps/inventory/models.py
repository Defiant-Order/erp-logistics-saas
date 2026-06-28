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


class DetalleOrdenCompra(BaseModel):
    """Linea de una OrdenCompra: que presentacion, cuanta cantidad y a que costo
    se solicita. Se compra por Presentacion (ej. "10 Cajas"), no por Producto
    suelto -- el producto se obtiene via presentacion.producto cuando se
    necesite (ej. al generar el MovimientoInventario en unidad base, usando
    presentacion.factor_conversion). Ver ADR-002 y ADR-003 en docs/business/04."""

    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name="detalles")
    presentacion = models.ForeignKey(
        "catalog.Presentacion", on_delete=models.PROTECT, related_name="detalles_orden_compra"
    )
    cantidad_solicitada = models.DecimalField(max_digits=12, decimal_places=4)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    cantidad_recibida = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Acumulado recibido hasta ahora (BR-ABAST-02/03). Actualizado por el service de recepcion.",
    )

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.orden_compra_id:
            self.tenant_id = self.orden_compra.tenant_id
        if self.orden_compra_id and self.tenant_id != self.orden_compra.tenant_id:
            raise ValueError("El DetalleOrdenCompra debe pertenecer al mismo tenant que su OrdenCompra.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad_solicitada} de {self.presentacion_id} (OC {self.orden_compra_id})"


class Almacen(BaseModel):
    """Ubicacion fisica de custodia. Ver docs/business/01."""

    nombre = models.CharField(max_length=255)
    es_cuarentena = models.BooleanField(
        default=False,
        help_text="Almacen virtual para mercaderia danada (BR-ABAST-01). No suma a stock vendible.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "nombre"], name="unique_almacen_nombre_por_tenant"),
        ]

    def __str__(self):
        return self.nombre


class RecepcionCompra(BaseModel):
    """Certifica que la mercaderia de una OrdenCompra cruzo la puerta del almacen.
    Ver docs/business/01 y BR-ABAST-02 en docs/business/03."""

    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name="recepciones")
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="recepciones")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.orden_compra_id:
            self.tenant_id = self.orden_compra.tenant_id
        if self.orden_compra_id and self.tenant_id != self.orden_compra.tenant_id:
            raise ValueError("La RecepcionCompra debe pertenecer al mismo tenant que su OrdenCompra.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Recepcion {self.id} de OC {self.orden_compra_id}"


class MovimientoInventario(BaseModel):
    """Kardex: registro INMUTABLE de entradas y salidas, unica fuente de verdad
    del stock. Ver docs/business/01 y BR-INV-01 en docs/business/03.

    El stock de un producto en un almacen no es una columna que se actualiza:
    es la suma de cantidad de todos sus movimientos (ENTRADA suma, SALIDA resta).
    """

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"

    producto = models.ForeignKey("catalog.Producto", on_delete=models.PROTECT, related_name="movimientos")
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4)
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Costo al momento del movimiento. Obligatorio para ENTRADA; "
        "el recalculo de costo promedio ponderado vive en un service futuro.",
    )
    recepcion_compra = models.ForeignKey(
        RecepcionCompra, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos"
    )
    reserva_inventario = models.ForeignKey(
        "sales.ReservaInventario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos",
        help_text="Origen de una SALIDA real al despachar (BR-VENTA-04). "
        "Permite revertir el stock con precision si la entrega falla (BR-COB-03).",
    )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("MovimientoInventario es inmutable: no se puede modificar un movimiento ya creado.")
        if not self.tenant_id and self.almacen_id:
            self.tenant_id = self.almacen.tenant_id
        if self.almacen_id and self.tenant_id != self.almacen.tenant_id:
            raise ValueError("El MovimientoInventario debe pertenecer al mismo tenant que su Almacen.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("MovimientoInventario es inmutable: no se puede eliminar un movimiento.")

    def __str__(self):
        return f"{self.tipo} {self.cantidad} de producto {self.producto_id} en {self.almacen_id}"
