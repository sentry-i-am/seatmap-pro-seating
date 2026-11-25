# Seatmap Pro seating for pretix and eventyay

This plugin lets buyers pick seats on a [Seatmap Pro](https://seatmap.pro) venue map in pretix or eventyay.
Prices, reservations, the cart, and orders stay in your ticketing system. Seatmap Pro supplies the venue
drawing and the map the buyer clicks on.

**Status:** early version. The test suite passes on pretix 2026.9.3 and on eventyay `dev` (commit `75ce5f9`).
A buyer has completed seat selection in a browser on eventyay. The same browser check on pretix is still open.

## What you need

- You have a Seatmap Pro account. Its settings give you an organization token and a public key.
- The venue is drawn in the Seatmap Pro editor, and an event on that venue is published.
- You can install Python packages on your pretix or eventyay server.

## Install

Install the package into the Python environment of your pretix or eventyay server. Then run the host's
`migrate` and `rebuild` commands. `rebuild` copies the plugin's `frame.js` into the collected static files,
and the buyer's seat map stays empty without it.

On pretix:

```bash
pip install seatmap-pro-seating
python -m pretix migrate
python -m pretix rebuild
```

On eventyay:

```bash
pip install seatmap-pro-seating
python -m eventyay migrate
python -m eventyay rebuild
```

Restart the web and worker processes. Then enable **Seatmap Pro** in the plugin list of your event.

If you run pretix or eventyay from a Docker image, the image collects static files at build time. Build
your own image on top of the official one that installs the plugin, then rebuilds the static files. On the
pretix image, that step is `cd /pretix/src && make production`.

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

The host shows the seat map on the event front page, on the voucher page, and in the separate window for
choosing seats. There the plugin loads the Seatmap Pro renderer and shows the venue. Only seats that are
free in your ticketing system can be selected, and they show the price of the mapped product. The selected seats
go to the cart through the standard seat fields, so availability checks, quotas, and checkout work as usual.

The organization token stays on your server. The browser receives only the public key and the event ID.

## Privacy and security notes

- The renderer is the published npm package `@seatmap.pro/renderer`, version 1.75.0. The page loads it
  from `cdn.jsdelivr.net`.
- The renderer reads the venue from the Seatmap Pro public API.
- On pages that show the map, the plugin adds these hosts to the Content Security Policy and allows images
  over `https:` for the venue background.
- The plugin writes connection changes and loaded plans to the event log. The organization token is never
  written to the log.
- The server sends the organization token only to `booking.seatmap.pro` over HTTPS and does not follow
  redirects. If you run Seatmap Pro on premise, the server administrator lists its Booking API host in the
  `SEATMAP_PRO_ALLOWED_API_HOSTS` environment variable, for example
  `SEATMAP_PRO_ALLOWED_API_HOSTS=seatmap.example.com`. Organizers can choose only from these hosts.

## Limitations

- Event series are not supported.
- Products with variations cannot be mapped to a pricing zone.
- Standing areas from Seatmap Pro are not imported.
- The price on the map is the product's default price. Vouchers apply in the cart.

## Security

Report security issues to hello@seatmap.pro and do not open a public issue for them.

## Development

```bash
pip install -e .
pytest tests/test_layout.py
```

`tests/host/test_host_flow.py` runs the full flow inside a host: settings, import, seat map, cart, and
permission checks. To run it on pretix, install pretix, `pytest-django`, and `beautifulsoup4` next to the
plugin:

```bash
pytest tests --ds=pretix.testutils.settings
```

To run it on eventyay, use the eventyay environment and its test settings, `tests.testutils.settings`.

Set `SEATING_PLAN_SCHEMA` to the host's `seating-plan.schema.json` to check the generated plan against it.

## License

The plugin is licensed under the Apache License 2.0. The Seatmap Pro renderer and services are covered by
the [Seatmap Pro terms of service](https://seatmap.pro/tos/).
