import hashlib
import hmac
import json

import pytest
from django.test import Client
from django.urls import reverse

from apps.core.models import Tenant
from apps.whatsapp.models import ConfiguracionWhatsApp, EventoWebhookWhatsApp
from common.models import ExternalReference

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


@pytest.fixture
def settings_whatsapp(settings):
    settings.WHATSAPP_APP_SECRET = APP_SECRET
    settings.WHATSAPP_VERIFY_TOKEN = VERIFY_TOKEN
    return settings


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(razon_social="Distribuidora A", ruc="20100000001", slug="distribuidora-a")


@pytest.fixture
def configuracion(tenant):
    return ConfiguracionWhatsApp.objects.create(
        tenant=tenant, phone_number_id="106540352242922", business_account_id="102290129340398", access_token="x"
    )


def _firmar(body: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _payload_mensaje(phone_number_id, wamid="wamid.ABC123"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "102290129340398",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "15550783881", "phone_number_id": phone_number_id},
                            "contacts": [{"profile": {"name": "Sheena Nelson"}, "wa_id": "16505551234"}],
                            "messages": [
                                {
                                    "from": "16505551234",
                                    "id": wamid,
                                    "timestamp": "1749416383",
                                    "type": "text",
                                    "text": {"body": "Does it come in another color?"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.mark.django_db
def test_verificacion_handshake_exitoso(settings_whatsapp):
    client = Client()
    response = client.get(
        reverse("whatsapp-webhook"),
        {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )

    assert response.status_code == 200
    assert response.content == b"12345"


@pytest.mark.django_db
def test_verificacion_handshake_rechaza_token_incorrecto(settings_whatsapp):
    client = Client()
    response = client.get(
        reverse("whatsapp-webhook"),
        {"hub.mode": "subscribe", "hub.verify_token": "token-invalido", "hub.challenge": "12345"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_webhook_rechaza_firma_invalida(settings_whatsapp, configuracion):
    client = Client()
    body = json.dumps(_payload_mensaje(configuracion.phone_number_id)).encode()

    response = client.post(
        reverse("whatsapp-webhook"), data=body, content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256="sha256=firma-invalida",
    )

    assert response.status_code == 403
    assert EventoWebhookWhatsApp.unscoped.count() == 0


@pytest.mark.django_db
def test_webhook_con_firma_valida_guarda_el_evento(settings_whatsapp, configuracion):
    client = Client()
    body = json.dumps(_payload_mensaje(configuracion.phone_number_id, wamid="wamid.NUEVO")).encode()

    response = client.post(
        reverse("whatsapp-webhook"), data=body, content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_firmar(body),
    )

    assert response.status_code == 200
    evento = EventoWebhookWhatsApp.unscoped.get(external_id="wamid.NUEVO")
    assert evento.tenant_id == configuracion.tenant_id
    assert ExternalReference.unscoped.filter(source_system="whatsapp", external_id="wamid.NUEVO").exists()


@pytest.mark.django_db
def test_webhook_ignora_reintento_duplicado(settings_whatsapp, configuracion):
    client = Client()
    body = json.dumps(_payload_mensaje(configuracion.phone_number_id, wamid="wamid.REPETIDO")).encode()
    firma = _firmar(body)

    url = reverse("whatsapp-webhook")
    client.post(url, data=body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=firma)
    client.post(url, data=body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=firma)

    assert EventoWebhookWhatsApp.unscoped.filter(external_id="wamid.REPETIDO").count() == 1


@pytest.mark.django_db
def test_webhook_ignora_numero_no_configurado(settings_whatsapp):
    client = Client()
    body = json.dumps(_payload_mensaje("000000000000000")).encode()

    response = client.post(
        reverse("whatsapp-webhook"), data=body, content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_firmar(body),
    )

    assert response.status_code == 200
    assert EventoWebhookWhatsApp.unscoped.count() == 0
