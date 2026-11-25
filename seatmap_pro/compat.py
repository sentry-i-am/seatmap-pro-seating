"""Differences between pretix and eventyay, kept in one place."""

from importlib import import_module
from importlib.util import find_spec

HOST = 'eventyay' if find_spec('eventyay') else 'pretix'

# pretix 2026 replaced the can_* team flags with named permissions. It still accepts the old
# names, but they are deprecated, so the plugin asks for the new one where it exists.
NEW_PERMISSIONS = HOST == 'pretix' and find_spec('pretix.helpers.permission_migration') is not None
SETTINGS_PERMISSION = 'event.settings.general:write' if NEW_PERMISSIONS else 'can_change_event_settings'


def host_attr(path, name):
    return getattr(import_module(f'{HOST}.{path}'), name)


def event_products(event):
    return event.products if HOST == 'eventyay' else event.items


def quota_products(quota):
    return quota.products if HOST == 'eventyay' else quota.items


def sales_channel_identifier(request):
    """pretix keeps a SalesChannel model on the request, older code and eventyay may keep a string."""
    channel = getattr(request, 'sales_channel', None)
    return getattr(channel, 'identifier', channel) or 'web'
