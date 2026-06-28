# 06 - Políticas del Tenant
## Objetivo
Tabla de configuración (1 a 1 con Tenant) para gobernar el comportamiento del negocio sin hardcodear lógica en el código fuente.

## Políticas Operativas
* **allow_negative_stock (Boolean):** Permite confirmar pedidos aunque el stock disponible sea cero o menor. (Default: False)
* **reservation_ttl_hours (Integer):** Horas de vida de una reserva de inventario antes de ser liberada por inactividad del pedido. (Default: 24)
* **multi_warehouse_enabled (Boolean):** Activa el módulo de transferencias internas entre almacenes. (Default: False)

## Políticas Comerciales y de Riesgo
* **max_credit_limit (Decimal):** Tope máximo de deuda permitida para clientes corporativos. El sistema bloquea nuevos despachos a crédito si se supera.
* **require_approval_discount_pct (Decimal):** Límite porcentual de descuento que un usuario de ventas puede aplicar. Si se supera, el pedido exige firma electrónica de gerencia.