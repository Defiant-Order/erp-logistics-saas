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

## Diagrama Entidad-Relación Definitivo

```mermaid
erDiagram
    %% Core & Configuración
    TENANT ||--|| TENANT_CONFIG : "posee reglas en"
    TENANT ||--o{ USUARIO : "tiene"
    
    TENANT_CONFIG {
        uuid tenant_id PK
        boolean allow_negative_stock
        int reservation_ttl_hours
        decimal max_credit_limit
    }

    %% Catálogo
    PRODUCTO ||--|{ PRESENTACION : "se transacciona como"
    
    %% Inventario & Compras
    PROVEEDOR ||--o{ ORDEN_COMPRA : "recibe"
    ORDEN_COMPRA ||--o{ RECEPCION_COMPRA : "se formaliza ingreso en"
    RECEPCION_COMPRA ||--o{ MOVIMIENTO_INVENTARIO : "genera"
    ALMACEN ||--o{ MOVIMIENTO_INVENTARIO : "registra"
    PRODUCTO ||--o{ MOVIMIENTO_INVENTARIO : "afecta stock base"
    
    %% Comercial (El núcleo)
    CLIENTE ||--o{ PEDIDO : "realiza"
    PEDIDO ||--|{ DETALLE_PEDIDO : "contiene"
    PRESENTACION ||--o{ DETALLE_PEDIDO : "incluye"
    PEDIDO ||--o{ PEDIDO_ESTADO_HISTORICO : "audita cambios en"
    
    PEDIDO {
        uuid id PK
        uuid tenant_id FK
        uuid cliente_id FK
        string condicion_pago "CONTADO, CONTRA_ENTREGA, CREDITO (TextChoices)"
        string estado_logistico "PREPARACION, DESPACHADO, ENTREGADO... (TextChoices)"
        string estado_financiero "PENDIENTE, PAGADO, CON_DEUDA (TextChoices)"
        decimal total
    }

    %% Reservas (Vínculo Ventas-Inventario)
    PEDIDO ||--o{ RESERVA_INVENTARIO : "genera"
    PRODUCTO ||--o{ RESERVA_INVENTARIO : "bloquea disponibilidad"
    
    %% Finanzas & Despacho
    PEDIDO ||--o{ ENTREGA_PEDIDO : "se despacha en"
    PEDIDO ||--o{ PAGO : "recibe dinero vía"
    PEDIDO ||--o| CUENTA_POR_COBRAR : "origina deuda (Solo si es a Crédito)"
    CUENTA_POR_COBRAR ||--o{ PAGO : "se amortiza con"
    
    PAGO {
        uuid id PK
        uuid pedido_id FK
        decimal monto
        string metodo_pago "YAPE, PLIN, EFECTIVO (TextChoices)"
        string referencia
    }