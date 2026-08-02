# poke-track

Checks specific retail product pages for Pokemon card stock and notifies you (Discord and/or
email) when something comes back in stock.

## Reliability by store — read this first

Only **Best Buy** has a real, sanctioned API for checking stock. Target, Walmart, and Pokemon
Center gate live inventory behind bot detection (Akamai/PerimeterX), confirmed by testing real
product pages during development:

| Store          | Method                          | Reliability                                                                 |
|----------------|----------------------------------|------------------------------------------------------------------------------|
| Best Buy       | Official Products API           | Reliable. Needs a free API key.                                             |
| Target         | Headless browser (Playwright)   | Best-effort. Worked in testing, but Target can start blocking automated traffic at any time. |
| Pokemon Center | Headless browser (Playwright)   | Best-effort. Returned a 403 bot-check in testing even with a real browser — may or may not work from your deployment's IP. |
| Walmart        | Not implemented                 | Their CDN (PerimeterX) hard-blocks the very first request before any page even loads. Not feasible without proxy rotation / fingerprint evasion, which this project intentionally doesn't do. |

When a checker can't verify status (blocked, page layout changed, etc.) it reports `unknown`
rather than guessing — it logs the reason, never sends a false notification, and keeps whatever
stock status it last confirmed until the next successful check.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

Then:

```bash
cp config.example.yaml config.yaml   # add the products you want to track
cp .env.example .env                 # add your API key / webhook / SMTP creds
```

### config.yaml

Each entry needs a `store` (`bestbuy`, `target`, or `pokemoncenter`) and either:

- **`url`** — a specific product page URL. Works for any store. For Best Buy you can use the
  numeric SKU instead (found in the product page URL after `/sku/`). This is how you get restock
  alerts for one exact product: whenever that page flips from out-of-stock to in-stock, you're
  notified — which is how Pokemon TCG restocks actually work (existing listings going in and out
  of stock repeatedly), so this covers "the random restocks."

- **`search`** (Best Buy only) — a search term plus `match_keywords` (e.g. `"Elite Trainer Box"`,
  `"Booster Box"`, `"Booster Bundle"`). Every matching product is tracked automatically, including
  ones that don't exist yet when you write the config — e.g. a brand new set's ETB gets picked up
  the first poll after Best Buy lists it, no config change needed. See `config.example.yaml` for a
  working example.

  This only works for Best Buy because they have an official search API. Target/Pokemon Center's
  search and category pages sit behind the same bot detection as their product pages (often worse
  — category pages get hit by bots far more often), so auto-discovering brand-new listings there
  isn't something this project can do reliably. For those two, add the URL yourself once a new
  product is listed (even in a "coming soon" state) and the restock-alert behavior above takes it
  from there.

### .env

- `BESTBUY_API_KEY` — free instant signup at [developer.bestbuy.com](https://developer.bestbuy.com/).
- `DISCORD_WEBHOOK_URL` — Discord: Server Settings → Integrations → Webhooks → New Webhook.
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `EMAIL_TO` — for a Gmail account, use an
  [App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification).

A notifier only turns on once *all* of its required variables are set — you can configure just
Discord, just email, or both.

## Running it

```bash
# one-off check of everything in config.yaml, prints results, exits
python -m poke_track.main --once

# send a test message to your configured notifier(s) to confirm they're wired up
python -m poke_track.main --test-notify

# run continuously, polling every `poll_interval_seconds`
python -m poke_track.main
```

Optional: `--renotify-after-hours N` re-sends a notification if an item is still in stock N hours
after the last alert (default: only notify once per out-of-stock → in-stock transition).

State (what was last seen in/out of stock, and when you were last notified) is kept in
`state.json` next to the config file.

## Deploying to run 24/7

The project ships as a Docker image (based on Playwright's official image, since Target/Pokemon
Center checks need a real Chromium browser — the image is a few hundred MB larger than a plain
Python image as a result):

```bash
docker build -t poke-track .
docker run -d --name poke-track \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/state.json:/app/state.json \
  --env-file .env \
  poke-track
```

For an always-on cloud host, [Fly.io](https://fly.io) works well for this (no HTTP port needed,
just a background worker):

```bash
cp fly.toml.example fly.toml   # edit app name / region
fly launch --no-deploy
fly secrets set BESTBUY_API_KEY=... DISCORD_WEBHOOK_URL=... SMTP_HOST=... SMTP_USER=... SMTP_PASS=... EMAIL_TO=...
fly deploy
```

Bake your `config.yaml` into the image (add `COPY config.yaml .` to the `Dockerfile`) or mount it
via a [Fly volume](https://fly.io/docs/volumes/) — the example `fly.toml` doesn't set one up by
default. Any other Docker host (Railway, a small VPS, etc.) works the same way.

## Being a reasonable citizen about this

- Default poll interval is 5 minutes, with a random 1–3s delay between checking each product —
  tune `poll_interval_seconds` in `config.yaml`, but avoid polling aggressively.
- This is for personal use. You're responsible for complying with each retailer's terms of use —
  the Target/Pokemon Center checkers are unofficial and reverse-engineered from page behavior, and
  may stop working (or get your IP flagged) if a site changes.

## Running tests

```bash
pytest
```

Tests cover config loading, notification state transitions, and each checker's parsing logic
(using real page/DOM text captured while building this, plus a representative Best Buy API
response) — no live network calls or a real browser are needed to run the suite.
