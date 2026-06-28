# 05 - Estados del Sistema (State Machines)
## Máquina de Estados: Pedido (Logística)
* **BORRADOR:** Creación inicial. Sin impacto en inventario.
* **CONFIRMADO:** Validado. Dispara ReservaInventario.
* **PREPARACION:** Almacén armando picking.
* **DESPACHADO:** Asignado a ruta.
* **ENTREGADO:** Conformidad total del cliente en puerta.
* **ENTREGADO_PARCIAL:** Rechazo parcial en puerta. Genera devolución al almacén.
* **FALLIDO:** Entrega fallida en ruta o falta de pago en puerta.
* **CANCELADO:** Anulado post-confirmación. Libera reservas.
* **RESERVA_EXPIRADA:** Pedido perdió prioridad sobre stock físico por inactividad. Espera decisión manual.
* *Nota: Un pedido no puede retroceder de DESPACHADO a PREPARACION.*

## Máquina de Estados: Pedido (Finanzas)
* **PENDIENTE:** No hay pagos registrados.
* **PAGADO_PARCIAL:** Existen abonos pero no cubren el total.
* **PAGADO:** El monto pagado iguala el total del pedido.
* **CON_DEUDA:** Exclusivo post-entrega para clientes a crédito.

## Condiciones de Pago (Pedido)
* **CONTADO:** Exige pago total previo al despacho.
* **CONTRA_ENTREGA:** Exige pago total simultáneo a la entrega física.
* **CREDITO:** Exige liquidación en una fecha posterior a la entrega.

## Máquina de Estados: Orden de Compra
* **BORRADOR:** En redacción.
* **ENVIADA:** Transmitida a proveedor.
* **RECIBIDA_PARCIAL:** Ingreso incompleto.
* **RECIBIDA:** Ingreso conforme. Estado final inmutable.
* **CERRADA_INCOMPLETA:** Liquidada manualmente sin recibir el saldo.