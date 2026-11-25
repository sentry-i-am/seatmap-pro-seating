from unittest import mock

import pytest

from seatmap_pro.booking_api import ALLOWED_HOSTS_VARIABLE, BookingApi, checked_api_url
from seatmap_pro.signals import merge_csp


def test_default_api_url_is_allowed():
    assert checked_api_url('') == 'https://booking.seatmap.pro'
    assert checked_api_url('https://Booking.Seatmap.pro/') == 'https://booking.seatmap.pro'


@pytest.mark.parametrize(
    'url',
    [
        'http://booking.seatmap.pro',
        'https://attacker.example',
        'https://booking.seatmap.pro.attacker.example',
        'https://user:pass@booking.seatmap.pro',
        'https://booking.seatmap.pro?x=1',
        'https://169.254.169.254',
        'file:///etc/passwd',
    ],
)
def test_other_api_urls_are_refused(url):
    with pytest.raises(ValueError):
        checked_api_url(url)


def test_administrator_can_allow_an_on_premise_host(monkeypatch):
    monkeypatch.setenv(ALLOWED_HOSTS_VARIABLE, 'seatmap.internal.example:8443, other.example')
    assert checked_api_url('https://seatmap.internal.example:8443/') == 'https://seatmap.internal.example:8443'
    with pytest.raises(ValueError):
        checked_api_url('https://seatmap.internal.example')


def test_client_does_not_follow_redirects():
    session = mock.Mock()
    session.get.return_value = mock.Mock(status_code=200, json=lambda: {})
    BookingApi('', 'token', 'key', session=session).event('abc')
    assert session.get.call_args.kwargs['allow_redirects'] is False
    assert session.get.call_args.kwargs['headers']['X-API-Key'] == 'token'


def test_client_refuses_a_disallowed_host():
    with pytest.raises(ValueError):
        BookingApi('https://attacker.example', 'token', 'key')


def test_new_directive_keeps_default_src_sources():
    policy = merge_csp("default-src 'self'", {'script-src': ['https://cdn.jsdelivr.net']})
    assert "script-src 'self' https://cdn.jsdelivr.net" in policy


def test_none_is_dropped_when_sources_are_added():
    policy = merge_csp("default-src 'none'; img-src 'none'", {'img-src': ['https:']})
    assert 'img-src https:' in policy
    assert "default-src 'none'" in policy
