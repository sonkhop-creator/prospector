# Prospector

Automates the Phiri Digital Strategy Local Visibility Audit: finds every
business in a niche + suburb, scores their digital visibility, and ranks
the field so you can see who's invisible.

## Status

Real, runnable code — not a mockup. Two dependencies:

1. A Google Places API (New) key with Places API enabled, set as
   `GOOGLE_PLACES_API_KEY` in your environment.
2. `pip install -r requirements.txt`

## Status: all six dimensions built

Four dimensions (Search presence, Listing completeness, Review signal, Local
competitiveness) come from a single Places Text Search call. The other two
(Site/booking path, Content freshness) need a Places Details call per
business — that costs one extra API call per business, so it's opt-in via
`--full`.

Verified against 6 real Johannesburg businesses via manual lookup before
being wired in — see `examples/`. Not yet run end-to-end against the live
Details API with a real key (this was built and validated in a sandbox with
no API access) — that first real `--full` run is the next actual test.

## Run a scan

```bash
export GOOGLE_PLACES_API_KEY="your-key-here"

# Fast pass — 4 dimensions, one API call total
python -m prospector.cli --niche "borehole pump repair" --location "Roodepoort, Gauteng" --out scan.md

# Full pass — all 6 dimensions, one extra API call per business
python -m prospector.cli --niche "borehole pump repair" --location "Roodepoort, Gauteng" --full --out scan.md
```

## What's in here

- `places_client.py` — Google Places API (New) wrapper
- `scorer.py` — six-dimension scoring engine, honest about what's not yet computable
- `report.py` — markdown report renderer
- `cli.py` — command-line entry point
- `examples/roodepoort_borehole_scan.md` — a real scan run against live data,
  generated while building this
