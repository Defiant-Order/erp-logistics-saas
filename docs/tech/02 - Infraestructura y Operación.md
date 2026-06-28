# 02 - Infraestructura y Operación
## Entorno Local de Desarrollo (Homelab)
* **Orquestación:** Se utilizará Docker y `docker-compose.yml` para levantar la triada base: Django (App), Redis (Broker/Caché), y un PostgreSQL local rápido para pruebas efímeras.
* **Exposición Segura de Webhooks:** Para desarrollar y probar la integración con WhatsApp localmente sin exponer puertos del servidor a la internet pública, el tráfico se enrutará a través de túneles de **Cloudflare Zero Trust** apuntando directamente al contenedor de Django.

## Entorno de Producción / Staging
* **Base de Datos:** PostgreSQL serverless alojado en **Neon**. Garantiza escalabilidad para cargas B2B pesadas y permite *branching* de la base de datos para probar migraciones complejas.
* **Gestión de Migraciones:** Inmutabilidad estricta. Queda prohibido alterar esquemas directamente en la consola de la base de datos. Todo cambio estructural debe nacer de un archivo `migrations` de Django.