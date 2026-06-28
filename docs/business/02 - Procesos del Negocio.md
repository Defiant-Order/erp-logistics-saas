# 02 - Procesos del Negocio
## Objetivo
Mapear el ciclo de vida secuencial de las operaciones principales.

## 1. Ciclo de Abastecimiento (Procure to Pay)
1. Compras emite `OrdenCompra`.
2. Proveedor entrega mercadería física.
3. Almacén registra `RecepcionCompra` (Homologación).
4. Sistema genera `MovimientoInventario` (Kardex).
5. Sistema actualiza el costo promedio ponderado.
6. `OrdenCompra` se cierra.

## 2. Ciclos de Venta (Order to Cash)

**A. Flujo Minorista (WhatsApp / Contado)**
1. Cliente pide vía bot y transfiere por Yape/Plin.
2. Sistema registra el `Pago` y crea el `Pedido` (Estado Financiero: PAGADO).
3. Almacén prepara y despacha.
4. Repartidor entrega (Fin del ciclo. Nunca hubo deuda).

**B. Flujo Mayorista (Crédito)**
1. Vendedor crea `Pedido` a crédito (Estado Financiero: PENDIENTE).
2. Sistema genera `ReservaInventario`.
3. Almacén prepara y despacha.
4. Repartidor entrega mercadería.
5. Sistema genera la `CuentaPorCobrar` (Nace la deuda).

## 3. Liquidación de Ruta (Cierre Operativo)
1. Repartidor retorna a base al final del turno.
2. Sistema totaliza los pedidos contra entrega marcados como ENTREGADOS.
3. Repartidor rinde el efectivo físico y capturas de transferencias.
4. Tesorería cuadra la ruta y cierra el ciclo del día.