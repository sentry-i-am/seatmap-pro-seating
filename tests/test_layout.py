import json
import os
from pathlib import Path

import pytest

from seatmap_pro.layout import UNASSIGNED, build_layout, decode, seat_guid, seat_id_from_guid

PUBLIC_LAYOUT = {
    'rows': [
        {'id': 500, 'rowNumber': 'A', 'sectorId': 10},
        {'id': 1, 'rowNumber': 'B', 'sectorId': 10},
        {'id': 1, 'rowNumber': '1', 'sectorId': 20},
    ],
    'sectors': [
        {'id': 10, 'name': 'Stalls', 'isGa': False},
        {'id': 20, 'name': 'Balcony', 'isGa': False},
    ],
    'plainSeats': {
        'names': ['1', '2', '1', '7', '8'],
        'ids': [1000, 1, 1, 1, 1],
        'x': [100, 30, -30, 200, 30],
        'y': [100, 0, 30, -60, 0],
        'rowIds': [500, 0, 1, 1, 0],
        'sectorIds': [10, 0, 0, 10, 0],
    },
}
ZONE_BY_SEAT = {1000: 1, 1001: 1, 1002: 2, 1003: 3, 1004: None}
ZONE_NAMES = {1: 'Standard', 2: 'Premium', 3: 'Standard'}


def seats_of(layout):
    return {
        seat['seat_guid']: (zone['name'], row['row_number'], seat)
        for zone in layout['zones']
        for row in zone['rows']
        for seat in row['seats']
    }


def test_decode_running_sum():
    assert decode([1000, 1, 1]) == [1000, 1001, 1002]
    assert decode(None) == []


def test_guid_round_trip():
    assert seat_id_from_guid(seat_guid(1421484)) == 1421484
    with pytest.raises(ValueError):
        seat_id_from_guid('ext-1')


def test_layout_keeps_seatmap_structure():
    layout = build_layout('Hall', PUBLIC_LAYOUT, ZONE_BY_SEAT, ZONE_NAMES)
    seats = seats_of(layout)

    assert set(seats) == {seat_guid(n) for n in range(1000, 1005)}
    assert seats[seat_guid(1002)][:2] == ('Stalls', 'B')
    assert seats[seat_guid(1003)][:2] == ('Balcony', '1')
    assert seats[seat_guid(1000)][2]['seat_number'] == '1'


def test_layout_positions_start_at_margin():
    layout = build_layout('Hall', PUBLIC_LAYOUT, ZONE_BY_SEAT, ZONE_NAMES)
    seats = seats_of(layout)

    assert seats[seat_guid(1000)][2]['position'] == {'x': 40, 'y': 70}
    assert seats[seat_guid(1003)][2]['position'] == {'x': 240, 'y': 40}
    assert layout['size'] == {'width': 310, 'height': 140}


def test_duplicate_zone_names_stay_distinct():
    layout = build_layout('Hall', PUBLIC_LAYOUT, ZONE_BY_SEAT, ZONE_NAMES)
    seats = seats_of(layout)

    assert seats[seat_guid(1000)][2]['category'] == 'Standard'
    assert seats[seat_guid(1003)][2]['category'] == 'Standard (3)'
    assert seats[seat_guid(1004)][2]['category'] == UNASSIGNED
    assert [c['name'] for c in layout['categories']] == sorted(
        ['Premium', 'Standard', 'Standard (3)', UNASSIGNED]
    )


def test_seats_without_pricing_data_are_skipped():
    layout = build_layout('Hall', PUBLIC_LAYOUT, {1000: 1}, ZONE_NAMES)
    assert set(seats_of(layout)) == {seat_guid(1000)}


def test_layout_matches_seating_plan_schema():
    schema_path = os.environ.get('SEATING_PLAN_SCHEMA')
    if not schema_path:
        pytest.skip('Set SEATING_PLAN_SCHEMA to the host seating-plan.schema.json')
    jsonschema = pytest.importorskip('jsonschema')
    schema = json.loads(Path(schema_path).read_text())
    jsonschema.validate(build_layout('Hall', PUBLIC_LAYOUT, ZONE_BY_SEAT, ZONE_NAMES), schema)
