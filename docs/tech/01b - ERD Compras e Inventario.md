# 01b - ERD Compras e Inventario

Entidades de `apps.inventory`. `RESERVA_INVENTARIO` se define en
[01c - ERD Ventas y Finanzas](01c%20-%20ERD%20Ventas%20y%20Finanzas.md) pero
se referencia aqui porque origina movimientos de Kardex.

```mermaid
erDiagram
    PROVEEDOR ||--o{ ORDEN_COMPRA : "recibe"
    ORDEN_COMPRA ||--|{ DETALLE_ORDEN_COMPRA : "contiene"
    PRESENTACION ||--o{ DETALLE_ORDEN_COMPRA : "se solicita en"
    ORDEN_COMPRA ||--o{ RECEPCION_COMPRA : "se formaliza ingreso en"
    RECEPCION_COMPRA ||--o{ MOVIMIENTO_INVENTARIO : "genera (ENTRADA)"
    ALMACEN ||--o{ MOVIMIENTO_INVENTARIO : "registra"
    PRODUCTO ||--o{ MOVIMIENTO_INVENTARIO : "afecta stock base"
    RESERVA_INVENTARIO ||--o{ MOVIMIENTO_INVENTARIO : "origina (SALIDA)"

    PROVEEDOR {
        string razon_social
        string ruc "unique por tenant"
    }
    ORDEN_COMPRA {
        uuid proveedor_id FK
        string estado "BORRADOR, ENVIADA, RECIBIDA_PARCIAL, RECIBIDA, CERRADA_INCOMPLETA (TextChoices)"
        uuid created_by FK
    }
    DETALLE_ORDEN_COMPRA {
        uuid orden_compra_id FK
        uuid presentacion_id FK "se compra por Presentacion, no por Producto directo"
        decimal cantidad_solicitada
        decimal costo_unitario
        decimal cantidad_recibida "acumulado, default 0, actualizado por el service de recepcion"
    }
    ALMACEN {
        string nombre "unique por tenant"
        boolean es_cuarentena "default False, BR-ABAST-01"
    }
    RECEPCION_COMPRA {
        uuid orden_compra_id FK
        uuid almacen_id FK
        uuid created_by FK
    }
    MOVIMIENTO_INVENTARIO {
        uuid producto_id FK
        uuid almacen_id FK
        string tipo "ENTRADA, SALIDA (TextChoices)"
        decimal cantidad "siempre en unidad base, BR-INV-01"
        decimal costo_unitario "nullable, obligatorio para ENTRADA"
        uuid recepcion_compra_id FK "nullable, origen si viene de una compra"
        uuid reserva_inventario_id FK "nullable, origen si viene de un despacho"
    }
```

## Notas
* `MOVIMIENTO_INVENTARIO` es **INMUTABLE** (`ADR-009`): `save()`/`delete()` se niegan a modificar o borrar un registro ya creado.
* El stock de un producto no es una columna: se calcula sumando `ENTRADA` y restando `SALIDA` de `MOVIMIENTO_INVENTARIO`, **excluyendo siempre** los movimientos cuyo `Almacen.es_cuarentena=True` (ver `BR-ABAST-01`).
* `DETALLE_ORDEN_COMPRA` no es inmutable: `cantidad_recibida` se actualiza en cada recepcion parcial.
