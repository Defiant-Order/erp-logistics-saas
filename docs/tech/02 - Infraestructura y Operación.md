# 02 - Infraestructura y Operación
## Entorno Local de Desarrollo (Homelab)
* **Orquestación:** Se utilizará Docker y `docker-compose.yml` para levantar la triada base: Django (App), Redis (Broker/Caché), y un PostgreSQL local rápido para pruebas efímeras.
* **Exposición Segura de Webhooks:** Para desarrollar y probar la integración con WhatsApp localmente sin exponer puertos del servidor a la internet pública, el tráfico se enrutará a través de túneles de **Cloudflare Zero Trust** apuntando directamente al contenedor de Django.

## Entorno de Pruebas Actual (Homelab — implementado)
* **Servidor:** mini-servidor Ubuntu 24 en la red local, administrado vía **Portainer** (Stacks). Alcanzable de forma privada desde el equipo de desarrollo vía **Tailscale**.
* **Dominio:** `defiant-order.xyz` (Hostinger), DNS gestionado por **Cloudflare**.
* **Exposición pública:** un único **Cloudflare Tunnel** (modo gestionado por token, `cloudflared-tunnel`) ya corre en el servidor sobre la red Docker `backend-net`. El contenedor de Django (`erp-django`) se conecta a esa misma red — **no se publica ningún puerto del host**. La ruta pública (`webhooks.defiant-order.xyz` → `http://erp-django:8000`) se configura desde el dashboard de Cloudflare Zero Trust (Networks → Tunnels → Public Hostname), no desde un archivo de configuración local.
* **Imagen y despliegue:** `Dockerfile` en la raíz del repo (Python 3.13-slim + gunicorn). El workflow `.github/workflows/deploy.yml` construye y publica la imagen a GitHub Container Registry (`ghcr.io`) en cada push a `main`, y dispara el **Webhook del Stack de Portainer** para que el servidor vuelva a descargar la imagen y recree el contenedor. No hay paso manual de despliegue.
* **CI adicional:** el job `docker-build` en `.github/workflows/ci.yml` valida que la imagen construya (sin publicarla) en cada Pull Request, para no descubrir un `Dockerfile` roto recién después de mergear a `main`.
* **Variables de entorno reales** (distintas a las de desarrollo local) viven en el `.env` del Stack de Portainer en el servidor, nunca en el repo: `SECRET_KEY` real, `DATABASE_URL` (Neon), `ALLOWED_HOSTS=webhooks.defiant-order.xyz`, `DEBUG=False`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`.

## Entorno de Producción / Staging (futuro)
* **Base de Datos:** PostgreSQL serverless alojado en **Neon**. Garantiza escalabilidad para cargas B2B pesadas y permite *branching* de la base de datos para probar migraciones complejas.
* **Gestión de Migraciones:** Inmutabilidad estricta. Queda prohibido alterar esquemas directamente en la consola de la base de datos. Todo cambio estructural debe nacer de un archivo `migrations` de Django.
* **Cómputo:** Google Cloud Run (pendiente, ver discusión en docs/tech/05) — el "Entorno de Pruebas Actual" de arriba es el homelab, no este entorno final.