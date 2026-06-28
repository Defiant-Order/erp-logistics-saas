# 04 - Decisiones Arquitectónicas (ADR)
## ADR-001: Framework y Persistencia
* **Decisión:** Django ORM con PostgreSQL (Neon).
* **Contexto:** Soporta el modelado relacional denso y escalar bases de datos B2B sin fricción inicial de infraestructura.

## ADR-002: Separación Producto-Presentación
* **Decisión:** Un Producto Maestro tiene N Presentaciones, unidas por un factor de conversión.
* **Contexto:** Previene duplicidad en el Kardex y permite el "desarme" de cajas para venta por unidad manteniendo la cuadratura.

## ADR-003: Costeo de Inventario
* **Decisión:** Método de Costo Promedio Ponderado.
* **Contexto:** Cada Recepción recalcula el costo del inventario promediando el valor del nuevo lote con el stock existente.

## ADR-004: Desacoplamiento de Estados
* **Decisión:** Separar la vida de un pedido en Condición de Pago, Estado Logístico y Estado Financiero.
* **Contexto:** Un pedido puede estar logísticamente entregado pero financieramente pendiente (Crédito), o financieramente pagado pero logísticamente en preparación (Contado adelantado). Forzar un solo estado colapsa la operación real.

## ADR-005: Multi-Tenant
* **Decisión:** Todas las entidades de negocio deben pertenecer a un Tenant.
* **Contexto:** Se adopta estrategia Shared Database + tenant_id para minimizar complejidad operativa durante la etapa inicial del SaaS.

## ADR-006: Control Transaccional de Concurrencia
* **Decisión:** Uso estricto de bloqueos de base de datos (`select_for_update()`) dentro de bloques transaccionales (`transaction.atomic()`).
* **Contexto:** Previene el cálculo erróneo del Stock Disponible y del Costo Promedio Ponderado cuando dos usuarios o webhooks intentan confirmar pedidos o registrar recepciones exactamente en el mismo milisegundo.

## ADR-007 Aislamiento Estricto por Tenant
* **Decisión:** Implementación de un TenantManager global. Ningún query de dominio puede ejecutarse sin el scope del tenant.
* **Contexto:** Mitiga el riesgo de fuga de datos (que el Cliente A vea los pedidos del Cliente B) forzando el filtrado a nivel del ORM en lugar de depender de la memoria del desarrollador.

## ADR-008: Idempotencia y Desacoplamiento de Canales
* **Decisión:** WhatsApp (y cualquier otra integración) es tratado exclusivamente como un canal de entrada, no como el dueño de la entidad negocio. Todo webhook debe validar idempotencia antes de procesarse.
* **Contexto:** Si Cloudflare o Meta reintentan el envío de un webhook por latencia de red, el sistema debe reconocer el `external_id` y descartar el duplicado en lugar de crear un doble cobro o reserva.

## ADR-009: Auditoría Inmutable
* **Decisión:** Los registros históricos nunca serán modificados ni eliminados.
* **Contexto:** PedidoEstadoHistorico, MovimientoInventario, Pago, CuentaPorCobrar son evidencia operativa y financiera. Las correcciones deben registrarse mediante nuevos eventos y no modificando registros históricos.