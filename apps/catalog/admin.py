from django.contrib import admin

from apps.catalog.models import Presentacion, Producto


class PresentacionInline(admin.TabularInline):
    model = Presentacion
    extra = 1
    fields = ("nombre", "factor_conversion", "is_active")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "sku", "unidad_base", "costo_promedio", "tenant", "is_active")
    search_fields = ("nombre", "sku")
    list_filter = ("tenant",)
    inlines = [PresentacionInline]


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ("producto", "nombre", "factor_conversion", "tenant", "is_active")
    list_filter = ("tenant",)
