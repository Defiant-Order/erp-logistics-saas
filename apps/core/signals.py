from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import Tenant, TenantConfig


@receiver(post_save, sender=Tenant)
def create_tenant_config(sender, instance, created, **kwargs):
    if created:
        TenantConfig.objects.create(tenant=instance)
