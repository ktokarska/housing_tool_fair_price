# Method 3 (public AVM) — manual capture guide

Method 3 cross-checks each valuation against a **public automated valuation (AVM)** figure.
By design these are **captured manually** for the calibration sample and pinned into the
snapshot — no live scraping ships. Until an area has a captured `avm.csv`, calibration runs on
Methods 1 and 2 only, and every M3 result is `available: false` ("no AVM snapshot").

This guide turns a blank template into a captured `avm.csv`. **No values are ever invented** —
an un-captured row stays blank and loads as "no AVM", exactly as if the row were absent.

## 1. Generate the template

```
python scripts/build_avm_template.py --slug <slug> --types D,S,T,F --date 2026-06-19
```

Writes `data/snapshots/2026-06-19/<slug>/avm.template.csv`, one row per sold property of the
calibrated types, keyed by its HM Land Registry `unique_id`.

## 2. Fill it in by hand

For each row, look the property up on a public AVM service and record the figures. **Partial
fill is fine** — only filled rows get Method 3; blanks are skipped. A stratified subset is a
legitimate, lighter alternative to capturing every row.

### Columns

| Column | Filled? | Read by M3? | Meaning |
|---|---|---|---|
| `property_key` | pre-filled | yes (the join key) | HM Land Registry `unique_id` of the sold property. Do not edit. |
| `postcode`, `paon`, `street`, `property_type`, `deed_date`, `price_paid` | pre-filled | no | Helper context to locate the property on the AVM. |
| `avm_estimate` | **you** | **yes** | The AVM's £ point estimate. Leave blank if not captured. |
| `captured_date` | **you** | no (provenance) | Date you looked it up, `YYYY-MM-DD`. |
| `source_url` | **you** | yes (provenance) | The exact AVM page URL the figure came from. |
| `listing_visible` | **you** | **yes** | `true` if the AVM page displayed the property's own live listing/asking price, else `false`. |

### The contamination rule (why `listing_visible` matters)

If the AVM page showed the subject's live listing, the AVM may just be echoing the asking
price — not an independent signal. Mark `listing_visible = true` and reconciliation
**automatically excludes that M3 value from the spread, confidence, and range** (the
live-listing rule in `verdict_calc.py`). It is still recorded as a displayed reference. When
in doubt, mark `true`.

## 3. Activate it

Rename `avm.template.csv` → `avm.csv` in the same folder, then re-run:

```
python scripts/calibrate_geo.py --slug <slug> --types D,S,T,F --date 2026-06-19
```

Method 3 is already wired into the agent, so it activates automatically for every filled row.
The calibration record will then reconcile on all three methods.

## 4. (Optional) re-pin the snapshot

`avm.csv` becomes part of the pinned snapshot. If you want it under checksum control like
`sold.csv`/`epc.csv`, extend `scripts/build_manifest.py` to include it and regenerate the
manifest. Calibration is version-gated, so re-pinning is the moment to re-confirm the verdict.

## Honesty notes

- Blank `avm_estimate` ⇒ no M3 for that subject. The harness never guesses an AVM value.
- A captured AVM is one of three methods, not an override; it changes the **median** and the
  **spread**, nothing more.
- Capturing AVM data does not pre-determine a PASS. The verdict is recomputed blind from
  residuals, and an area can still QUARANTINE.
