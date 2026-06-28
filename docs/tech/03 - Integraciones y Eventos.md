# 03 - Integraciones y Eventos
## Arquitectura Asíncrona (Eventos de Dominio)
* **Justificación:** Operaciones como recalcular el costo promedio ponderado de 10,000 productos o enviar notificaciones de cancelación de reservas no deben bloquear la respuesta del servidor web (el hilo principal).
* **Entidad `DomainEvent`:** Patrón Outbox. Toda transacción crítica inserta un registro en esta tabla con un payload JSON.
* **Procesamiento:** Un *worker* (ej. Celery apoyado en Redis) lee esta tabla y procesa los eventos asíncronos en segundo plano (Ej. `ORDER_CONFIRMED`, `STOCK_CRITICAL`).

## API de WhatsApp (Webhooks)
* **Canal Único de Entrada:** Un solo endpoint (`/api/webhooks/whatsapp/`) procesa los mensajes entrantes de clientes.
* **Desacoplamiento:** El Webhook no procesa la lógica de ventas. Su única función es autenticar el payload, parsear el texto y disparar un `DomainEvent` o encolar la tarea. La lógica del bot conversacional reside en la capa de servicios.