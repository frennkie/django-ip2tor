from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class ShopConfig(AppConfig):
    name = 'shop'
    verbose_name = _("Shop")

    def ready(self):
        from shop import signals
        # _ = signals  # avoid unused import warning in IDE (not needed with post_create below)

        # make sure to create default 'operators' group and assign permissions
        post_migrate.connect(signals.create_default_operator_group, sender=self)
