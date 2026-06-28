# 01a - ERD Core y Catalogo

Entidades de `apps.core` y `apps.catalog`. Ver reglas generales del ORM en
[01 - ERD y Modelos de Datos](01%20-%20ERD%20y%20Modelos%20de%20Datos.md).

```mermaid
erDiagram
    TENANT ||--|| TENANT_CONFIG : "posee reglas en"
    TENANT ||--o{ USUARIO : "tiene"
    TENANT ||--o{ PRODUCTO : "posee"
    PRODUCTO ||--|{ PRESENTACION : "se transacciona como"

    TENANT {
        string razon_social
        string ruc "unique"
        string slug "unique"
    }
    TENANT_CONFIG {
        boolean allow_negative_stock "default False"
        int reservation_ttl_hours "default 24"
        boolean multi_warehouse_enabled "default False"
        decimal max_credit_limit "default 0"
        decimal require_approval_discount_pct "default 0"
    }
    USUARIO {
        string username
        string email
        uuid tenant_id FK "nullable, solo null para superusers de plataforma"
    }
    PRODUCTO {
        string nombre
        string sku "unique por tenant, no global"
        string unidad_base "default UND"
        decimal costo_promedio "ADR-003, recalculado en cada recepcion de compra"
    }
    PRESENTACION {
        uuid producto_id FK
        string nombre "unique por producto"
        decimal factor_conversion "invariable: ej. Botella=1, Sixpack=6, Caja=24"
    }
```

## Notas
* `TENANT_CONFIG` es 1 a 1 con `TENANT`, se crea automaticamente via signal al crear el Tenant (ver `apps/core/signals.py`).
* `USUARIO` (`apps.core.User`) no hereda `BaseModel` — es un `AbstractUser` de Django con un campo `tenant` agregado.
* `PRESENTACION.producto` es obligatorio (no nullable): la base de datos rechaza una Presentacion sin Producto.
