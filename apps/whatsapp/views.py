import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.whatsapp.models import ConfiguracionWhatsApp, EventoWebhookWhatsApp
from common.models import ExternalReference
from common.tenant_context import tenant_context

logger = logging.getLogger(__name__)


@csrf_exempt
def whatsapp_webhook(request):
    """Canal unico de entrada de WhatsApp (docs/tech/03). Solo autentica,
    parsea y guarda -- no contiene logica de negocio (ADR-008)."""
    if request.method == "GET":
        return _verificar_suscripcion(request)
    if request.method == "POST":
        return _recibir_evento(request)
    return HttpResponse(status=405)


def _verificar_suscripcion(request):
    """Handshake de verificacion que Meta hace una vez al configurar el
    webhook en el dashboard."""
    modo = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge", "")

    if modo == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("whatsapp webhook: handshake de verificacion exitoso")
        return HttpResponse(challenge, content_type="text/plain")

    logger.warning("whatsapp webhook: handshake de verificacion rechazado (modo=%s)", modo)
    return HttpResponse(status=403)


def _firma_valida(request):
    """Valida X-Hub-Signature-256 (HMAC-SHA256 con el App Secret) para
    confirmar que la peticion realmente viene de Meta."""
    firma = request.headers.get("X-Hub-Signature-256", "")
    if not firma.startswith("sha256="):
        return False

    esperada = hmac.new(settings.WHATSAPP_APP_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma.removeprefix("sha256="), esperada)


def _recibir_evento(request):
    if not _firma_valida(request):
        logger.warning("whatsapp webhook: firma invalida, peticion rechazada")
        return HttpResponse(status=403)

    payload = json.loads(request.body)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue
            _procesar_cambio(change.get("value", {}))

    # Siempre 200: Meta reintenta hasta 7 dias si no recibe 200, lo que
    # duplicaria notificaciones. Los duplicados ya se filtran por external_id.
    return JsonResponse({"status": "ok"})


def _procesar_cambio(valor):
    phone_number_id = valor.get("metadata", {}).get("phone_number_id")
    configuracion = ConfiguracionWhatsApp.unscoped.filter(phone_number_id=phone_number_id).first()
    if configuracion is None:
        logger.warning(
            "whatsapp webhook: phone_number_id '%s' no tiene ConfiguracionWhatsApp asociada, evento descartado",
            phone_number_id,
        )
        return

    with tenant_context(configuracion.tenant_id):
        for mensaje in valor.get("messages", []):
            external_id = mensaje["id"]
            if ExternalReference.objects.filter(source_system="whatsapp", external_id=external_id).exists():
                logger.info("whatsapp webhook: external_id %s ya procesado, reintento de Meta ignorado", external_id)
                continue

            ExternalReference.objects.create(
                tenant=configuracion.tenant, source_system="whatsapp", external_id=external_id
            )
            EventoWebhookWhatsApp.objects.create(
                tenant=configuracion.tenant, external_id=external_id, payload=mensaje
            )
            logger.info(
                "whatsapp webhook: evento %s guardado para tenant %s", external_id, configuracion.tenant_id
            )
