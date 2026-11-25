import json

from django.db import transaction

from .booking_api import BookingApi
from .compat import host_attr
from .layout import build_layout

SETTING_KEYS = ('api_url', 'organization_token', 'public_key', 'event_id')


def setting(event, key):
    return event.settings.get(f'seatmap_pro_{key}', default='') or ''


def save_settings(event, data):
    for key in SETTING_KEYS:
        if key == 'organization_token' and not data.get(key):
            continue
        event.settings.set(f'seatmap_pro_{key}', data.get(key) or '')


def api_for(event):
    return BookingApi(setting(event, 'api_url'), setting(event, 'organization_token'), setting(event, 'public_key'))


def fetch_layout(event):
    venue = api_for(event).venue(setting(event, 'event_id'))
    layout = build_layout(venue.name, venue.public_layout, venue.zone_by_seat, venue.zone_names)
    event.settings.set('seatmap_pro_pending_layout', json.dumps(layout))
    return layout


def pending_layout(event):
    raw = event.settings.get('seatmap_pro_pending_layout', default='')
    return json.loads(raw) if raw else None


def current_mapping(event):
    return {m.layout_category: m.product for m in event.seat_category_mappings.filter(subevent=None)}


@transaction.atomic
def apply_layout(event, organizer, layout, mapping):
    SeatingPlan = host_attr('base.models', 'SeatingPlan')
    generate_seats = host_attr('base.services.seating', 'generate_seats')
    validate_plan_change = host_attr('base.services.seating', 'validate_plan_change')
    plan = SeatingPlan(
        organizer=organizer,
        name=f'Seatmap Pro: {layout["name"]}'[:190],
        layout=json.dumps(layout),
    )
    validate_plan_change(event, None, plan)
    plan.save()
    event.seat_category_mappings.filter(subevent=None).delete()
    for category, product in mapping.items():
        if product is not None:
            event.seat_category_mappings.create(layout_category=category, product=product)
    event.seating_plan = plan
    event.save(update_fields=['seating_plan'])
    generate_seats(event, None, plan, {k: v for k, v in mapping.items() if v is not None})
    event.settings.delete('seatmap_pro_pending_layout')
    return plan
