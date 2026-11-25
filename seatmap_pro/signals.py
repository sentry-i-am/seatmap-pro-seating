from urllib.parse import urlsplit

from django.dispatch import receiver
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

from .compat import SETTINGS_PERMISSION, host_attr, sales_channel_identifier
from .importer import setting
from .layout import seat_id_from_guid

RENDERER_VERSION = '1.75.0'
RENDERER_URL = f'https://cdn.jsdelivr.net/npm/@seatmap.pro/renderer@{RENDERER_VERSION}/+esm'
RENDERER_ORIGIN = 'https://cdn.jsdelivr.net'
STATISTICS_ORIGIN = 'https://stat.seatmap.pro'

nav_event_settings = host_attr('control.signals', 'nav_event_settings')
render_seating_plan = host_attr('presale.signals', 'render_seating_plan')
process_response = host_attr('presale.signals', 'process_response')


@receiver(nav_event_settings, dispatch_uid='seatmap_pro_nav_settings')
def navigation(sender, request, **kwargs):
    if not request.user.has_event_permission(request.organizer, request.event, SETTINGS_PERMISSION, request=request):
        return []
    url = reverse(
        'plugins:seatmap_pro:settings',
        kwargs={'organizer': request.organizer.slug, 'event': request.event.slug},
    )
    return [{'label': _('Seatmap Pro'), 'url': url, 'active': request.path_info == url}]


def available_seats(event, request, voucher):
    seats = event.free_seats(ignore_voucher=voucher, sales_channel=sales_channel_identifier(request))
    available = {}
    for seat in seats.filter(product__isnull=False).select_related('product'):
        try:
            seatmap_id = seat_id_from_guid(seat.seat_guid)
        except ValueError:
            continue
        available[seatmap_id] = {
            'guid': seat.seat_guid,
            'field': f'seat_{seat.product_id}',
            'productId': seat.product_id,
            'price': float(seat.product.default_price),
        }
    return available


def api_origin(event):
    parts = urlsplit(setting(event, 'api_url') or 'https://booking.seatmap.pro')
    return f'{parts.scheme}://{parts.netloc}'


@receiver(render_seating_plan, dispatch_uid='seatmap_pro_render_seating_plan')
def render(sender, request, subevent=None, voucher=None, **kwargs):
    if subevent is not None or not setting(sender, 'event_id'):
        return ''
    # The host renders this signal on the seating frame, the event front page and the voucher page.
    # The flag tells allow_renderer which responses carry the map.
    request.seatmap_pro_rendered = True
    config = {
        'rendererUrl': RENDERER_URL,
        'apiUrl': f'{api_origin(sender)}/api/public/v1.0/',
        'publicKey': setting(sender, 'public_key'),
        'eventId': setting(sender, 'event_id'),
        'currency': sender.currency,
        'seats': available_seats(sender, request, voucher),
        'labels': {'selected': str(_('Selected seats: {count}, total {total}'))},
    }
    return get_template('seatmap_pro/frame.html').render({'config': config}, request)


SEATING_FRAME_URLS = ('event.seatingplan', 'event.seatingplan.subevent')


def shows_map(request):
    if getattr(request, 'seatmap_pro_rendered', False):
        return True
    try:
        return resolve(request.path_info).url_name in SEATING_FRAME_URLS
    except Exception:
        return False


def merge_csp(header, additions):
    """Merge directives into a policy without repeating a directive. Browsers ignore repeated directives."""
    policy = {}
    for part in header.split(';'):
        words = part.split()
        if words:
            current = policy.setdefault(words[0], [])
            current.extend(value for value in words[1:] if value not in current)
    for name, values in additions.items():
        current = policy.setdefault(name, [])
        current.extend(value for value in values if value not in current)
    return '; '.join(f'{name} {" ".join(values)}' for name, values in policy.items() if values)


@receiver(process_response, dispatch_uid='seatmap_pro_csp')
def allow_renderer(sender, request, response, **kwargs):
    if not setting(sender, 'event_id') or not shows_map(request):
        return response
    api = api_origin(sender)
    response['Content-Security-Policy'] = merge_csp(
        response.get('Content-Security-Policy', ''),
        {
            'script-src': [RENDERER_ORIGIN],
            'connect-src': [api, RENDERER_ORIGIN, STATISTICS_ORIGIN],
            'img-src': ['https:', 'data:', 'blob:'],
            'worker-src': ['blob:'],
        },
    )
    return response
