# 01c - ERD Ventas y Finanzas

Entidades de `apps.sales` y `apps.finance`. `PRODUCTO`/`PRESENTACION` se
definen en [01a](01a%20-%20ERD%20Core%20y%20Catalogo.md), `MOVIMIENTO_INVENTARIO`
en [01b](01b%20-%20ERD%20Compras%20e%20Inventario.md).

```mermaid
erDiagram
    CLIENTE ||--o{ PEDIDO : "realiza"
    PEDIDO ||--|{ DETALLE_PEDIDO : "contiene"
    PRESENTACION ||--o{ DETALLE_PEDIDO : "se vende como"
    PEDIDO ||--o{ RESERVA_INVENTARIO : "genera (BR-VENTA-01)"
    PRODUCTO ||--o{ RESERVA_INVENTARIO : "bloquea disponibilidad"
    PEDIDO ||--o{ PEDIDO_ESTADO_HISTORICO : "audita cambios en"
    PEDIDO ||--o| CUENTA_POR_COBRAR : "origina deuda (solo CREDITO + ENTREGADO)"
    PEDIDO ||--o{ PAGO : "recibe dinero via"
    CUENTA_POR_COBRAR ||--o{ PAGO : "se amortiza con"

    CLIENTE {
        string nombre
        string documento "unique por tenant, no global"
    }
    PEDIDO {
        uuid cliente_id FK
        string condicion_pago "CONTADO, CONTRA_ENTREGA, CREDITO (TextChoices)"
        string estado_logistico "BORRADOR..RESERVA_EXPIRADA, 9 valores (TextChoices)"
        string estado_financiero "PENDIENTE, PAGADO_PARCIAL, PAGADO, CON_DEUDA (TextChoices)"
        decimal total "default 0"
        uuid created_by FK
    }
    DETALLE_PEDIDO {
        uuid pedido_id FK
        uuid presentacion_id FK "se vende por Presentacion, no por Producto directo"
        decimal cantidad
        decimal precio_unitario
    }
    RESERVA_INVENTARIO {
        uuid pedido_id FK
        uuid producto_id FK "no Presentacion: el bloqueo es en unidad base"
        decimal cantidad
        string estado "RESERVADA, LIBERADA, CONSUMIDA (TextChoices)"
    }
    PEDIDO_ESTADO_HISTORICO {
        uuid pedido_id FK
        string estado_logistico "snapshot al momento del cambio"
        uuid changed_by FK
    }
    CUENTA_POR_COBRAR {
        uuid pedido_id FK "OneToOne"
        decimal monto_total
    }
    PAGO {
        uuid pedido_id FK
        uuid cuenta_por_cobrar_id FK "nullable: no todo Pago amortiza una deuda previa"
        decimal monto
        string metodo_pago "YAPE, PLIN, EFECTIVO (TextChoices)"
        string referencia
        uuid created_by FK
    }
```

## Notas
* `PEDIDO_ESTADO_HISTORICO` y `CUENTA_POR_COBRAR`/`PAGO` son **INMUTABLES** (`ADR-009`).
* `CUENTA_POR_COBRAR` no almacena `monto_pagado` ni `saldo` — son `@property` calculados agregando los `PAGO` asociados, para no violar la inmutabilidad.
* El ciclo de `estado_logistico` lo orquesta `apps/sales/services.py`: `confirmar_pedido` → `avanzar_a_preparacion` → `despachar_pedido` → `confirmar_entrega`.

## Pendiente de implementar
* **`EntregaPedido`** (mencionada en `docs/business/01` como "registro de la visita del repartidor al cliente") **todavia no existe en codigo**. Hoy `confirmar_entrega` resuelve el resultado final (ENTREGADO/FALLIDO) pero no registra el detalle de la visita en si (hora, firma, fotos, etc.). Se agrega cuando haya un requerimiento real de ese detalle operativo.
