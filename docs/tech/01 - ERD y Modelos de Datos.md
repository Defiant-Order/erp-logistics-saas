# 01 - ERD y Modelos de Datos (v1.0)
## Reglas del ORM (Django)
* **Llaves Primarias:** Toda tabla usará `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
* **Auditoría Base:** Toda tabla transaccional debe heredar de un modelo abstracto `TimeStampedModel` que incluya `created_at`, `updated_at` y `is_active`.
* **Aislamiento Multi-Tenant:** Toda tabla del negocio hereda de `TenantModel` para inyectar obligatoriamente `tenant_id` y usar un `TenantManager`/`TenantAwareQuerySet` que filtra automáticamente por el tenant en contexto.
* **Composición de abstracts:** En la práctica, `TenantModel` y `TimeStampedModel` se combinan en un único `BaseModel` (UUID PK + `tenant_id` + `created_at`/`updated_at`/`is_active`) del que heredan todos los modelos de negocio. Esto evita que cada app reimplemente el PK o el manager de tenant de forma distinta.
* **Dinero y Cantidades Fijas:** Uso exclusivo de `DecimalField(max_digits=12, decimal_places=4)`. Prohibido el uso de Float.
* **Estados Inmutables (TextChoices):** Prohibido el uso de *strings* libres para estados. Campos como `estado_logistico`, `estado_financiero` y `condicion_pago` deben programarse obligatoriamente usando `models.TextChoices` en Django para prevenir errores tipográficos.
* **Trazabilidad de Autoría:** Toda entidad transaccional crítica (`OrdenCompra`, `RecepcionCompra`, `Pedido`, `Pago`) debe incluir un campo `created_by` (FK a User) para auditar quién ejecutó la acción. **Importante:** `created_by` no forma parte de `TimeStampedModel`/`BaseModel` — se agrega explícitamente solo en esas entidades transaccionales, no en catálogos ni tablas de configuración (ej. `Producto`, `TenantConfig` no lo necesitan).
* **Control de Idempotencia:** Implementar una tabla o modelo abstracto `ExternalReference` (`source_system`, `external_id`, `processed_at`) para garantizar que un webhook duplicado de WhatsApp o pasarela de pago no genere dos pedidos o dos pagos.

## Diagramas Entidad-Relación

El ERD se divide por dominio para que cada archivo quede corto y se mantenga
junto al codigo que describe (un PR que toca `apps.sales` solo edita el
archivo de ventas, no un diagrama monolitico compartido):

* [01a - ERD Core y Catalogo](01a%20-%20ERD%20Core%20y%20Catalogo.md) — Tenant, TenantConfig, Usuario, Producto, Presentacion.
* [01b - ERD Compras e Inventario](01b%20-%20ERD%20Compras%20e%20Inventario.md) — Proveedor, OrdenCompra, DetalleOrdenCompra, Almacen, RecepcionCompra, MovimientoInventario.
* [01c - ERD Ventas y Finanzas](01c%20-%20ERD%20Ventas%20y%20Finanzas.md) — Cliente, Pedido, DetallePedido, ReservaInventario, PedidoEstadoHistorico, CuentaPorCobrar, Pago.

Las reglas del ORM de arriba aplican a las tres por igual (UUID PK, `BaseModel`,
Decimal, TextChoices, etc.) — no se repiten en cada archivo.