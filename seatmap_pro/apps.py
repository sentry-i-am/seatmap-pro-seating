from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from . import __version__


class _Meta:
    name = _('Seatmap Pro')
    author = 'Seatmap Pro'
    version = __version__
    category = 'FEATURE'
    description = _('Seat selection on Seatmap Pro venue maps.')
    visible = True


class SeatmapProApp(AppConfig):
    name = 'seatmap_pro'
    verbose_name = 'Seatmap Pro'
    default = True

    PretixPluginMeta = _Meta
    EventyayPluginMeta = _Meta

    def ready(self):
        from . import signals  # noqa: F401
