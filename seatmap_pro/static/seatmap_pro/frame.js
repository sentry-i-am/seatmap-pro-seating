const config = JSON.parse(document.getElementById('seatmap-pro-config').textContent);
const container = document.querySelector('[data-seatmap-pro]');
const inputs = document.querySelector('[data-seatmap-pro-inputs]');
const summary = document.querySelector('[data-seatmap-pro-summary]');
const submit = document.querySelector('[data-seatmap-pro-submit]');
const seats = new Map(Object.entries(config.seats).map(([id, seat]) => [Number(id), seat]));
const selected = new Map();
const format = new Intl.NumberFormat(document.documentElement.lang || undefined, {
  style: 'currency',
  currency: config.currency,
});

function refresh() {
  inputs.replaceChildren(
    ...[...selected.values()].map((seat) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = seat.field;
      input.value = seat.guid;
      return input;
    }),
  );
  const total = [...selected.values()].reduce((sum, seat) => sum + seat.price, 0);
  summary.textContent = selected.size
    ? config.labels.selected.replace('{count}', selected.size).replace('{total}', format.format(total))
    : '';
  submit.disabled = selected.size === 0;
}

const { SeatmapBookingRenderer } = await import(config.rendererUrl);
const renderer = new SeatmapBookingRenderer(container, {
  publicKey: config.publicKey,
  baseUrl: config.apiUrl,
  lockedSeatsFilter: (seat) => !seats.has(seat.id),
  onSeatSelect: (seat) => {
    const seatData = seats.get(seat.id);
    if (!seatData) return false;
    selected.set(seat.id, seatData);
    refresh();
    return true;
  },
  onSeatDeselect: (seat) => {
    selected.delete(seat.id);
    refresh();
    return true;
  },
});

await renderer.loadEvent(config.eventId);
renderer.setExternalPrices(
  [...seats.entries()].map(([id, seat]) => ({ id, seatKey: '', price: seat.price, priceId: seat.productId })),
);
renderer.updateSeatLocks((seat) => !seats.has(seat.id));
refresh();
