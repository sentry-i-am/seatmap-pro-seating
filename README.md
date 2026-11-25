# Seatmap Pro seating for pretix and eventyay

This plugin lets buyers pick seats on a [Seatmap Pro](https://seatmap.pro) venue map in pretix or eventyay.
Prices, reservations, the cart, and orders stay in your ticketing system. Seatmap Pro supplies the venue
drawing and the map the buyer clicks on.

**Status:** early version. Tested on eventyay `dev` (commit `75ce5f9`). pretix support uses the same code
and is not verified yet.

## What you need

- You have a Seatmap Pro account. Its settings give you an organization token and a public key.
- The venue is drawn in the Seatmap Pro editor, and an event on that venue is published.
- You can install Python packages on your pretix or eventyay server.

## Install

```bash
pip install git+https://github.com/sentry-i-am/seatmap-pro-seating.git
```

Restart the web and worker processes. Then enable **Seatmap Pro** in the plugin list of your event.

## Set up an event

1. In the event settings, open **Seatmap Pro**.
2. Fill in the organization token and the public key. Add the ID of the Seatmap Pro event, then select
   **Load venue**.
3. Each Seatmap Pro pricing zone appears as a seat category. Choose the product sold for each one and
   select **Save seating plan**.

The plugin stores the plan in the system's own seating model, one seat per Seatmap Pro seat. A seat keeps
its ID when you edit the venue in Seatmap Pro and load it again. The host refuses the new plan if it
removes a seat that is already sold.

## What the buyer sees

When a buyer opens the page for choosing seats, the plugin loads the Seatmap Pro renderer and shows the venue. Only seats that are free in
your ticketing system can be selected, and they show the price of the mapped product. The selected seats
go to the cart through the standard seat fields, so availability checks, quotas, and checkout work as usual.

The organization token stays on your server. The browser receives only the public key and the event ID.

## Privacy and security notes

- The renderer is the published npm package `@seatmap.pro/renderer`, version 1.75.0. The page loads it
  from `cdn.jsdelivr.net`.
- The renderer reads the venue from the Seatmap Pro public API.
- On the page for choosing seats, the plugin extends the Content Security Policy with these hosts and allows
  images over `https:` for the venue background.

## Limitations

- Event series are not supported.
- Products with variations cannot be mapped to a pricing zone.
- Standing areas from Seatmap Pro are not imported.
- The price on the map is the product's default price. Vouchers apply in the cart.

## Development

```bash
pip install -e .
pytest tests/test_layout.py
```

`tests/host/test_host_flow.py` runs the full flow inside the host's own test suite: copy it into the
host's tests directory and run it there.

## License

The plugin is licensed under the Apache License 2.0. The Seatmap Pro renderer and services are covered by
the [Seatmap Pro terms of service](https://seatmap.pro/tos/).
