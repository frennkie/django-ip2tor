from django.contrib import admin

from charged.lnrates.models import Settings


@admin.register(Settings)
class FakeNodeAdmin(admin.ModelAdmin):

    list_display = ('name', 'is_enabled')
    # search_fields = ('name',)
    # readonly_fields = ('type',)
