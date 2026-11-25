from importlib import import_module
from importlib.util import find_spec

HOST = 'eventyay' if find_spec('eventyay') else 'pretix'


def host_attr(path, name):
    return getattr(import_module(f'{HOST}.{path}'), name)


def event_products(event):
    return event.products if HOST == 'eventyay' else event.items
