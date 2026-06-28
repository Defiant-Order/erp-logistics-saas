from django.contrib import admin

from apps.whatsapp.models import ConfiguracionWhatsApp, EventoWebhookWhatsApp


@admin.register(ConfiguracionWhatsApp)
class ConfiguracionWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("tenant", "phone_number_id", "business_account_id")


@admin.register(EventoWebhookWhatsApp)
class EventoWebhookWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("external_id", "tenant", "created_at")
    list_filter = ("tenant",)

    # Inmutable por diseno, igual patron que MovimientoInventario.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
