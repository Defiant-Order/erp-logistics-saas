# 03 - Reglas de Negocio
## Reglas de Abastecimiento
* **BR-ABAST-01 (Mermas):** Productos dañados en recepción ingresan al Kardex hacia un almacén virtual de CUARENTENA. No suman al stock vendible. **Regla transversal de implementación:** toda función que calcule stock disponible o stock físico (en cualquier app: ventas, inventario, finanzas) debe excluir explícitamente los movimientos cuyo almacén tenga `es_cuarentena=True`. No basta con que el almacén de cuarentena exista — cada cálculo de stock nuevo debe filtrarlo, no se hereda automáticamente.
* **BR-ABAST-02 (Recepción Parcial):** Si llega menos stock del solicitado, la Orden transiciona a RECIBIDA_PARCIAL y permanece abierta esperando el remanente.
* **BR-ABAST-03 (Excedentes):** El sistema bloquea el ingreso de cantidades superiores al 100% de la OC. Requiere adenda documental.

## Reglas de Venta e Inventario
* **BR-INV-01 (Unidad Base):** Todo movimiento de Kardex y reserva se calcula estrictamente en la Unidad Base del producto.
* **BR-VENTA-01 (Nacimiento de Reserva):** La `ReservaInventario` se crea estrictamente cuando el Pedido pasa a estado logístico CONFIRMADO.
* **BR-VENTA-02 (Prevención de Sobreventa):** Se rechaza la confirmación si la cantidad solicitada supera al Stock Disponible (Stock Kardex - Reservas), salvo que la política del tenant lo permita.
* **BR-VENTA-03 (Expiración Segura):** Si se supera el límite de horas configurado en el tenant, la `ReservaInventario` cambia a estado LIBERADA. El Pedido transiciona al estado logístico RESERVA_EXPIRADA. No se cancela automáticamente. Queda en una cola de atención para decisión manual.
* **BR-VENTA-04 (Consumo al Despacho):** Al transicionar a DESPACHADO, la `ReservaInventario` cambia a CONSUMIDA. Desaparece lógicamente porque se genera el `MovimientoInventario` de salida real.

## Reglas de Cobranza (Finanzas)
* **BR-COB-01 (Pago al Contado):** Si el pedido es CONTADO, se requiere registrar un `Pago` por el total antes de permitir que el estado logístico avance a PREPARACION. No genera CuentaPorCobrar.
* **BR-COB-02 (Nacimiento de Deuda - Crédito):** La `CuentaPorCobrar` nace **únicamente** si la condición es CREDITO y el estado logístico transiciona a ENTREGADO.
* **BR-COB-03 (Pago Contra Entrega):** Al registrar la entrega física, el sistema exige registrar el Pago. Si el cliente no paga, la entrega se anula y el pedido se marca estrictamente como FALLIDO (rechazo logístico), retornando la mercadería al almacén.
* **BR-COB-04 (Límite de Crédito):** Un pedido con condición CREDITO no puede transicionar a CONFIRMADO si la deuda acumulada del cliente supera el `max_credit_limit`, salvo autorización explícita de un usuario superior.