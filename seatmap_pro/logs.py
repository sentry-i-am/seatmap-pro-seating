"""Readable texts for the plugin's entries in the event log."""

from importlib.util import find_spec

from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from .compat import HOST, host_attr

SETTINGS_CHANGED = 'seatmap_pro.settings.changed'
PLAN_SAVED = 'seatmap_pro.plan.saved'

LOG_TEXTS = {
    SETTINGS_CHANGED: _('The Seatmap Pro connection settings were changed.'),
    PLAN_SAVED: _('The seating plan was loaded from Seatmap Pro.'),
}

if HOST == 'pretix' and find_spec('pretix.base.logentrytypes'):
    # pretix 2025 and later register log texts in a registry. The signal below is deprecated there.
    from pretix.base.logentrytypes import EventLogEntryType, log_entry_types

    @log_entry_types.new_from_dict(LOG_TEXTS)
    class SeatmapProLogEntryType(EventLogEntryType):
        pass

else:
    logentry_display = host_attr('base.signals', 'logentry_display')

    @receiver(logentry_display, dispatch_uid='seatmap_pro_logentry_display')
    def display_log_entry(sender, logentry, **kwargs):
        return LOG_TEXTS.get(logentry.action_type)
