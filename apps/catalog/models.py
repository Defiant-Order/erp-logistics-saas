from django.db import models

from common.models import BaseModel


class Producto(BaseModel):
    """Articulo generico (ej. Cerveza Cristal). Ver docs/business/01."""

    nombre = models.CharField(max_length=255)
    sku = models.CharField(max_length=50)
    unidad_base = models.CharField(max_length=20, default="UND")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "sku"], name="unique_producto_sku_por_tenant"),
        ]

    def __str__(self):
        return self.nombre


class Presentacion(BaseModel):
    """Forma fisica en que se transacciona un Producto, ligada a un factor de
    conversion invariable hacia la unidad base (ej. Botella=1, Sixpack=6, Caja=24).
    Ver docs/business/01 y BR-INV-01 en docs/business/03."""

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="presentaciones")
    nombre = models.CharField(max_length=50)
    factor_conversion = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["producto", "nombre"], name="unique_presentacion_por_producto"),
        ]

    def save(self, *args, **kwargs):
        if not self.tenant_id and self.producto_id:
            self.tenant_id = self.producto.tenant_id
        if self.producto_id and self.tenant_id != self.producto.tenant_id:
            raise ValueError("La Presentacion debe pertenecer al mismo tenant que su Producto.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"
