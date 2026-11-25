"""End-to-end check inside a host's test environment.

pretix: install the plugin into the pretix environment and run from this repository with
``pytest tests/host --ds=pretix.testutils.settings``.
eventyay: copy this file into the eventyay tests directory and run it there with its settings.
"""

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.test import Client
from django.utils.timezone import now
from django_scopes import scopes_disabled

from seatmap_pro.booking_api import Venue
from seatmap_pro.compat import HOST, NEW_PERMISSIONS, event_products, host_attr, quota_products
from seatmap_pro.layout import seat_guid

Event = host_attr('base.models', 'Event')
Organizer = host_attr('base.models', 'Organizer')
Quota = host_attr('base.models', 'Quota')
Team = host_attr('base.models', 'Team')
User = host_attr('base.models', 'User')
CartPosition = host_attr('base.models', 'CartPosition')
LogEntry = host_attr('base.models', 'LogEntry')

VENUE = Venue(
    name='Small Hall',
    public_layout={
        'rows': [{'id': 500, 'rowNumber': 'A', 'sectorId': 10}, {'id': 1, 'rowNumber': 'B', 'sectorId': 10}],
        'sectors': [{'id': 10, 'name': 'Stalls', 'isGa': False}],
        'plainSeats': {
            'names': ['1', '2', '1', '2'],
            'ids': [1000, 1, 1, 1],
            'x': [100, 30, -30, 30],
            'y': [100, 0, 30, 0],
            'rowIds': [500, 0, 1, 0],
            'sectorIds': [10, 0, 0, 0],
        },
    },
    zone_by_seat={1000: 1, 1001: 1, 1002: 2, 1003: 2},
    zone_names={1: 'Standard', 2: 'Premium'},
)
TOKEN = 'organization-token-for-tests'
# pretix keeps sales channels as a model and enables all of them by default. eventyay keeps a list
# and has a separate switch for published tickets.
EVENT_EXTRA = {} if HOST == 'pretix' else {'sales_channels': ['web'], 'tickets_published': True}
if NEW_PERMISSIONS:
    ORGANIZER_PERMISSIONS = {'all_event_permissions': True}
    NO_SETTINGS_PERMISSIONS = {'limit_event_permissions': {'event.orders:read': True}}
else:
    ORGANIZER_PERMISSIONS = {'can_change_event_settings': True, 'can_change_items': True}
    NO_SETTINGS_PERMISSIONS = {'can_view_orders': True}
PUBLIC_KEY = '11111111-2222-3333-4444-555555555555'
EVENT_ID = '66666666-7777-8888-9999-000000000000'


@pytest.fixture
def host_event(settings):
    settings.ALLOWED_HOSTS = ['testserver']
    settings.SITE_URL = 'https://testserver'
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Seatmap test', slug='smp-test')
        event = Event.objects.create(
            organizer=organizer,
            name='Seatmap test event',
            slug='smp-event',
            date_from=now() + timedelta(days=30),
            live=True,
            currency='EUR',
            plugins=f'{HOST}.plugins.banktransfer,seatmap_pro',
            **EVENT_EXTRA,
        )
        products = {}
        for name, price in (('Standard', Decimal('12.00')), ('Premium', Decimal('24.00'))):
            product = event_products(event).create(name=name, default_price=price, admission=True)
            quota = Quota.objects.create(event=event, name=name, size=10)
            quota_products(quota).add(product)
            products[name] = product
        event.settings.set('require_registered_account_for_tickets', False)
        event.settings.set('redirect_to_checkout_directly', False)
        user = User.objects.create(email='organizer@smp-test.invalid', fullname='Organizer')
        team = Team.objects.create(
            organizer=organizer,
            name='Organizers',
            all_events=True,
            **ORGANIZER_PERMISSIONS,
        )
        team.members.add(user)
    return organizer, event, products, user


def settings_url(organizer, event):
    return f'/control/event/{organizer.slug}/{event.slug}/seatmap-pro/'


def frame_config(html):
    node = BeautifulSoup(html, 'html.parser').find('script', id='seatmap-pro-config')
    assert node is not None, 'The seating frame does not contain the Seatmap Pro configuration'
    return json.loads(node.string)


@pytest.mark.django_db
def test_import_select_and_cart(host_event):
    organizer, event, products, user = host_event
    control = Client()
    control.force_login(user)
    url = settings_url(organizer, event)

    response = control.get(url)
    assert response.status_code == 200, response.status_code
    assert b'Load venue' in response.content

    with patch('seatmap_pro.importer.BookingApi.venue', return_value=VENUE) as venue:
        response = control.post(
            url,
            {
                'action': 'load',
                'api_url': 'https://booking.seatmap.pro',
                'organization_token': TOKEN,
                'public_key': PUBLIC_KEY,
                'event_id': EVENT_ID,
            },
        )
    assert response.status_code == 302, response.content[:2000]
    venue.assert_called_once_with(EVENT_ID)
    assert TOKEN.encode() not in control.get(url).content

    response = control.get(url)
    page = BeautifulSoup(response.content, 'html.parser')
    categories = {
        next(page.find('label', attrs={'for': select['id']}).stripped_strings): select['name'].split('_')[1]
        for select in page.select('select[name^="category_"]')
    }
    assert set(categories) == {'Premium', 'Standard'}

    response = control.post(
        url,
        {'action': 'apply', **{f'category_{i}': products[name].pk for name, i in categories.items()}},
    )
    assert response.status_code == 302, response.content[:2000]

    with scopes_disabled():
        event.refresh_from_db()
        assert event.seating_plan.name == 'Seatmap Pro: Small Hall'
        assert event.seats.count() == 4
        assert event.seats.get(seat_guid=seat_guid(1002)).product == products['Premium']
        entries = {entry.action_type: entry for entry in LogEntry.objects.filter(event=event)}
    assert str(entries['seatmap_pro.plan.saved'].display()) == 'The seating plan was loaded from Seatmap Pro.'
    assert str(entries['seatmap_pro.settings.changed'].display()).startswith('The Seatmap Pro connection')
    assert TOKEN not in entries['seatmap_pro.settings.changed'].data

    buyer = Client()
    response = buyer.get(f'/{organizer.slug}/{event.slug}/seatingframe/')
    assert response.status_code == 200, response.status_code
    config = frame_config(response.content)
    assert config['publicKey'] == PUBLIC_KEY and config['eventId'] == EVENT_ID
    assert TOKEN not in response.content.decode()
    assert set(config['seats']) == {'1000', '1001', '1002', '1003'}
    assert config['seats']['1002']['field'] == f'seat_{products["Premium"].pk}'
    assert 'https://cdn.jsdelivr.net' in response.get('Content-Security-Policy', '')

    response = buyer.post(
        f'/{organizer.slug}/{event.slug}/cart/add',
        {
            f'seat_{products["Standard"].pk}': [seat_guid(1000), seat_guid(1001)],
            f'seat_{products["Premium"].pk}': [seat_guid(1002)],
        },
    )
    assert response.status_code == 302, response.status_code
    with scopes_disabled():
        guids = set(CartPosition.objects.filter(event=event).values_list('seat__seat_guid', flat=True))
    assert guids == {seat_guid(1000), seat_guid(1001), seat_guid(1002)}

    other = Client()
    config = frame_config(other.get(f'/{organizer.slug}/{event.slug}/seatingframe/').content)
    assert set(config['seats']) == {'1003'}

    # Both hosts also render the map on the event front page, so the policy must allow the renderer there.
    front_page = other.get(f'/{organizer.slug}/{event.slug}/')
    assert front_page.status_code == 200, front_page.status_code
    assert set(frame_config(front_page.content)['seats']) == {'1003'}
    assert 'https://cdn.jsdelivr.net' in front_page.get('Content-Security-Policy', '')


@pytest.mark.django_db
def test_settings_need_permission(host_event):
    organizer, event, products, user = host_event
    with scopes_disabled():
        viewer = User.objects.create(email='viewer@smp-test.invalid', fullname='Viewer')
        team = Team.objects.create(organizer=organizer, name='Viewers', all_events=True, **NO_SETTINGS_PERMISSIONS)
        team.members.add(viewer)
    client = Client()
    client.force_login(viewer)
    response = client.get(settings_url(organizer, event))
    assert response.status_code == 403, response.status_code
    response = client.post(settings_url(organizer, event), {'action': 'apply'})
    assert response.status_code == 403, response.status_code


@pytest.mark.django_db
def test_settings_need_enabled_plugin(host_event):
    organizer, event, products, user = host_event
    with scopes_disabled():
        event.plugins = f'{HOST}.plugins.banktransfer'
        event.save()
    client = Client()
    client.force_login(user)
    assert client.get(settings_url(organizer, event)).status_code == 404
