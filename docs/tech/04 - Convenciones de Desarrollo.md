# 04 - Convenciones de Desarrollo
## 1. Arquitectura del Monolito Modular
Django debe estructurarse por "dominios de negocio", no agrupando todas las vistas o modelos juntos.
* `apps/core/` (Tenant, Usuarios, Autenticación)
* `apps/catalog/` (Productos, Presentaciones)
* `apps/inventory/` (Almacenes, Kardex, Reservas)
* `apps/purchases/` (Proveedores, Órdenes, Recepciones)
* `apps/sales/` (Clientes, Pedidos)
* `apps/finance/` (Pagos, Cuentas por Cobrar)

## 2. Fat Services, Thin Views
* **Prohibido:** Escribir reglas de negocio, validaciones de stock, o lógica transaccional dentro de `views.py` o los Serializers.
* **Obligatorio:** Toda acción de negocio vive en un archivo `services.py` dentro de su respectiva aplicación (Ej. `sales/services/order_creation.py`). Las vistas solo parsean la petición HTTP y llaman al servicio.

## 3. Atomicidad en Base de Datos
* Toda operación que afecte a más de una tabla (ej. Crear un Pedido y crear una ReservaInventario) debe ejecutarse obligatoriamente dentro de un bloque `transaction.atomic()` de Django. Si el paso final falla, ningún registro debe guardarse en la base de datos.

## 4. Convenciones de Lógica
* **Prohibición de Strings Mágicos:** Queda estrictamente prohibido comparar estados utilizando cadenas de texto en crudo (Ej. `if pedido.estado == "ENTREGADO"`). Todo el código debe referenciar la clase `TextChoices` (Ej. `if pedido.estado == OrderStatus.ENTREGADO`).
* **Tenant Scoping Obligatorio:** Queda prohibido usar `Model.objects.all()` en consultas de negocio. Se debe implementar un `TenantAwareManager` y un `TenantAwareQuerySet` personalizado para que los queries se filtren automáticamente por el tenant en contexto.