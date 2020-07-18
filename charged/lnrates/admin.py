from django.contrib import admin

from charged.lnrates.models import FiatRate, Settings


@admin.register(FiatRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    search_fields = ('fiat_symbol', 'coin_symbol', 'source',)
    list_display = ('fiat_symbol', 'coin_symbol', 'source', 'rate', 'is_aggregate', 'created_at')
    list_filter = ('fiat_symbol', 'coin_symbol', 'source', 'is_aggregate', 'created_at')

    readonly_fields = ('fiat_symbol', 'coin_symbol', 'source', 'rate', 'is_aggregate', 'fiat_per_coin', 'created_at')

    def fiat_per_coin(self, obj: FiatRate):
        return obj.fiat_per_coin


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enabled')
    # search_fields = ('name',)
    list_filter = ('is_enabled',)

    readonly_fields = ('id',)
    readonly_fields += ('provider',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
