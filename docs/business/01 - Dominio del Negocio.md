# 01 - Dominio del Negocio
## Objetivo
Definir las entidades fundamentales que componen el sistema ERP logístico y su vocabulario unificado.

## Core & Seguridad
* **Tenant:** La empresa distribuidora (SaaS).
* **TenantConfig:** Tabla explícita (1 a 1 con Tenant) que almacena las reglas de negocio específicas de la empresa.
* **Usuario / Rol / Permiso:** Control de acceso basado en roles (RBAC).

## Catálogo de Productos
* **Producto Maestro:** El artículo genérico (Ej. Cerveza Cristal).
* **Presentación:** La forma física en que se transacciona, ligada a un factor de conversión invariable (Ej. Botella=1, Sixpack=6, Caja=24).

## Logística e Inventario
* **Proveedor:** Entidad comercial que abastece mercadería al distribuidor.
* **OrdenCompra:** Solicitud formal emitida al proveedor para adquirir productos.
* **Almacén:** Ubicación física de custodia.
* **RecepcionCompra:** Documento que certifica que la mercadería física cruzó la puerta del almacén.
* **MovimientoInventario (Kardex):** Registro inmutable de entradas y salidas. Única fuente de verdad del stock.
* **ReservaInventario:** Stock bloqueado temporalmente para garantizar el cumplimiento de un pedido confirmado.

## Comercial y Despacho
* **Cliente / ClienteDireccion:** Compradores B2B/B2C y sus coordenadas de entrega.
* **Pedido:** Compromiso comercial entre el cliente y la empresa. Es el documento central que coordina inventario, logística y finanzas. Posee una Condición de Pago y dos estados independientes (Logístico y Financiero).
* **PedidoEstadoHistorico:** Tabla de auditoría que registra cada salto de estado del pedido, quién lo hizo y cuándo.
* **EntregaPedido:** Registro de la visita del repartidor al cliente.

## Finanzas
* **Pago:** Entidad central de transacción financiera. Registra el ingreso de dinero independiente de si existe o no una deuda previa.
* **CuentaPorCobrar:** Deuda exigible generada formalmente por una entrega a crédito.