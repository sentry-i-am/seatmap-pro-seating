from collections import defaultdict
from itertools import accumulate

MARGIN = 40
UNASSIGNED = 'Seatmap Pro: no pricing zone'


def decode(values):
    return list(accumulate(values or []))


def seat_guid(seat_id):
    return f'seatmap-{seat_id}'


def seat_id_from_guid(guid):
    prefix, _, value = guid.partition('-')
    if prefix != 'seatmap' or not value.isdigit():
        raise ValueError(f'Not a Seatmap Pro seat: {guid}')
    return int(value)


def category_names(zone_names):
    names = {}
    used = set()
    for zone_id, name in sorted(zone_names.items()):
        label = name or f'Zone {zone_id}'
        if label in used:
            label = f'{label} ({zone_id})'
        used.add(label)
        names[zone_id] = label
    return names


def build_layout(name, public_layout, zone_by_seat, zone_names):
    plain = public_layout['plainSeats']
    seat_ids = decode(plain['ids'])
    xs = decode(plain['x'])
    ys = decode(plain['y'])
    row_ids = decode(plain['rowIds'])
    names = plain['names']

    row_id_list = decode([row['id'] for row in public_layout.get('rows', [])])
    rows = {row_id: row for row_id, row in zip(row_id_list, public_layout.get('rows', []))}
    sectors = {sector['id']: sector for sector in public_layout.get('sectors', [])}
    categories = category_names(zone_names)

    seats = [
        (seat_id, x, y, row_id, label)
        for seat_id, x, y, row_id, label in zip(seat_ids, xs, ys, row_ids, names)
        if seat_id in zone_by_seat
    ]
    if not seats:
        raise ValueError('The Seatmap Pro event has no seats with numbers')

    min_x = min(seat[1] for seat in seats) - MARGIN
    min_y = min(seat[2] for seat in seats) - MARGIN
    max_x = max(seat[1] for seat in seats) + MARGIN
    max_y = max(seat[2] for seat in seats) + MARGIN

    grouped = defaultdict(lambda: defaultdict(list))
    for seat_id, x, y, row_id, label in seats:
        row = rows.get(row_id, {})
        grouped[row.get('sectorId')][row_id].append(
            {
                'seat_guid': seat_guid(seat_id),
                'seat_number': str(label),
                'position': {'x': x - min_x, 'y': y - min_y},
                'category': categories.get(zone_by_seat[seat_id], UNASSIGNED),
            }
        )

    zones = []
    for sector_id, sector_rows in grouped.items():
        zones.append(
            {
                'name': sectors.get(sector_id, {}).get('name') or '',
                'zone_id': f'seatmap-{sector_id}',
                'position': {'x': 0, 'y': 0},
                'rows': [
                    {
                        'row_number': str(rows.get(row_id, {}).get('rowNumber') or ''),
                        'position': {'x': 0, 'y': 0},
                        'seats': row_seats,
                    }
                    for row_id, row_seats in sector_rows.items()
                ],
            }
        )

    used = {seat['category'] for zone in zones for row in zone['rows'] for seat in row['seats']}
    return {
        'name': name or 'Seatmap Pro',
        'categories': [{'name': label} for label in sorted(used)],
        'zones': zones,
        'size': {'width': max_x - min_x, 'height': max_y - min_y},
    }
