# Provenance — _crosswalks / ori_to_county

**Source**: FBI Crime Data Explorer public REST API,
`https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/GA` (agency/ORI roster for Georgia).
API docs: <https://www.justice.gov/developer>; free data.gov key (`API_KEY` query param;
`DEMO_KEY` works but is limited to ~25–50 requests/day).
**Retrieved**: 2026-07-02T12:23Z (HTTP 200), via
`uv run python -m src.etl.criminal_justice.fbi_cde.download --roster`.
**License**: US federal government work — public domain.

## Files

| File | Size | sha256 |
|------|------|--------|
| `cde_agency_by_state_abbr_ga.json` | 203,057 B | `e169eb5b263c22d69813a9fa14e955b7ad23523bbfbce95135688998914c1dde` |

Raw JSON, re-serialized with `indent=1` only (no field changes). Structure: a dict keyed by
**county-name string** → list of agency objects with fields
`ori, counties, agency_name, agency_type_name, state_abbr, state_name, is_nibrs,
nibrs_start_date, latitude, longitude`.

- **664 agencies** under **192 keys**. Georgia has 159 counties — the extra keys are
  **comma-joined multi-county strings** for agencies spanning counties (e.g.
  `"BANKS, HABERSHAM"`, `"BARROW, GWINNETT, HALL, JACKSON"`). The per-agency `counties`
  field carries the same string. The transform must split these and decide a
  primary-county rule (or fractional allocation) before mapping to FIPS via the
  county-name→FIPS crosswalk.
- This roster is the **hard prerequisite** for county rollups of all agency-grain FBI CDE
  data (`nibrs_offenses`, `nibrs_arrests`, `hate_crimes`, `law_enforcement_employees`).
- Secondary/validation signal: `lee_1960_2025.csv`
  (`data/bronze/criminal_justice/fbi_cde/law_enforcement_employees/`) carries a
  `county_name` per ORI per year.

## API verification (same session)

Spot-check `GET …/summarized/state/GA/homicide?from=01-2022&to=12-2022&API_KEY=DEMO_KEY`
→ HTTP 200 with monthly GA actuals/rates (details recorded in
`data/bronze/criminal_justice/fbi_cde/nibrs_offenses/_provenance.md`). DEMO_KEY calls used
across the whole session: 3.

## Caveats

- County names are uppercase source spellings — normalize before joining to the
  `county_name_to_fips` crosswalk; watch multi-county strings (above).
- Roster reflects current agency status (`is_nibrs`, `nibrs_start_date`); historical ORIs
  that stopped reporting may need supplementing from the LEE file or the LEAIC (ICPSR)
  crosswalk if unmatched ORIs surface in older years.
- Refresh with `--roster` (1 API call); set `CDE_API_KEY` env var for a real data.gov key.
