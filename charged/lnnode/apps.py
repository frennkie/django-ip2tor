from django.apps import AppConfig
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LnNodeConfig(AppConfig):
    name = 'charged.lnnode'
    label = 'lnnode'
    verbose_name = _('Charged Lightning Node')

    def ready(self):
        key = f'{self.__class__.__qualname__}.ready'
        now_iso = timezone.now().isoformat()
        try:
            cache.set(key, now_iso, timeout=None)
        except Exception as err:
            print(f'Error [{self.verbose_name}]: '
                  'Cache backend not reachable (check settings/service).')
            raise err
