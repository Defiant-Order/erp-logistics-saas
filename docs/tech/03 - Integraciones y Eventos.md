# 03 - Integraciones y Eventos
## Arquitectura Asíncrona (Eventos de Dominio)
* **Justificación:** Operaciones como recalcular el costo promedio ponderado de 10,000 productos o enviar notificaciones de cancelación de reservas no deben bloquear la respuesta del servidor web (el hilo principal).
* **Entidad `DomainEvent`:** Patrón Outbox. Toda transacción crítica inserta un registro en esta tabla con un payload JSON.
* **Procesamiento:** Un *worker* (ej. Celery apoyado en Redis) lee esta tabla y procesa los eventos asíncronos en segundo plano (Ej. `ORDER_CONFIRMED`, `STOCK_CRITICAL`).

## API de WhatsApp (Webhooks)
* **Canal Único de Entrada:** Un solo endpoint (`/api/webhooks/whatsapp/`, `apps/whatsapp/views.py::whatsapp_webhook`) procesa los mensajes entrantes de clientes.
* **Desacoplamiento:** El Webhook no procesa la lógica de ventas. Su única función es autenticar el payload, parsear el texto y disparar un `DomainEvent` o encolar la tarea. La lógica del bot conversacional reside en la capa de servicios.
* **Estado actual (implementado):**
  * `GET` — responde el handshake de verificación de Meta (`hub.challenge`) validando `WHATSAPP_VERIFY_TOKEN`.
  * `POST` — valida la firma `X-Hub-Signature-256` (HMAC-SHA256 con `WHATSAPP_APP_SECRET`), resuelve el tenant via `ConfiguracionWhatsApp.phone_number_id`, deduplica reintentos de Meta con `common.ExternalReference` (`source_system="whatsapp"`), y guarda el evento crudo en `EventoWebhookWhatsApp` (inmutable, `ADR-009`). Siempre responde `200` para no acumular reintentos de Meta durante 7 días.
  * **Pendiente:** disparar el `DomainEvent`/Outbox y el flujo conversacional real (`Conversacion`, `MensajeChat`, *handoff* a humano, distinción minoreo/mayoreo) — el webhook hoy solo captura y deduplica, no actúa sobre el mensaje.
* `ConfiguracionWhatsApp` (`apps/whatsapp/models.py`) vincula un `phone_number_id` de WhatsApp Business a un `Tenant` — necesario porque el sistema es multi-tenant y cada distribuidor puede tener su propio número.