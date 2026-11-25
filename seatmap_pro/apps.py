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


class PretixMeta(_Meta):
    # pretix reads one requirement string here. eventyay reads a list, so it gets its own class.
    compatibility = 'pretix>=2026.9.0'
    settings_links = [
        ((_('Seatmap Pro'),), 'plugins:seatmap_pro:settings', {}),
    ]


class SeatmapProApp(AppConfig):
    name = 'seatmap_pro'
    verbose_name = 'Seatmap Pro'
    default = True

    PretixPluginMeta = PretixMeta
    EventyayPluginMeta = _Meta

    def ready(self):
        from . import logs, signals  # noqa: F401
