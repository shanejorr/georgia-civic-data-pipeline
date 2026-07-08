# Provenance — fbi_cde / nibrs_offenses

**Source**: FBI Crime Data Explorer (CDE), <https://cde.ucr.cjis.gov> — "Documents & Downloads"
page (`https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads`).
**Retrieved**: 2026-07-02T12:22–12:24Z, via
`uv run python -m src.etl.criminal_justice.fbi_cde.download --roster`.
**License**: US federal government work — public domain.

## Retrieval method (unstable URLs — re-discover, never hardcode)

The CDE downloads page is an SPA; every bulk file is served from a private S3 bucket
(`cde-prd-data.s3.us-gov-east-1.amazonaws.com`) via **signed URLs that expire in ~15 minutes**.
The downloader re-discovers everything each run:

1. NIBRS state-year keys follow `nibrs/incident/{YEAR}/GA-{YEAR}.zip` (pattern extracted from
   the SPA's download component JS). Years are probed 2016→current; a year exists iff step 2
   returns a URL.
2. Each key is exchanged for a signed URL at
   `GET https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}` and downloaded immediately.
3. The SRS estimates key is read from the SPA metadata file
   `https://cde.ucr.cjis.gov/LATEST/webapp/assets/JSON/downloads/downloads.json` (entry id `srs`),
   so the filename year-range tracks new releases.

## Files

| File | Size | sha256 |
|------|------|--------|
| `GA-2018.zip` | 169,850 B | `d5ba63dc…adb08eb` |
| `GA-2019.zip` | 5,564,346 B | `a73c8d56…203d86d` |
| `GA-2020.zip` | 27,667,372 B | `d983e861…040fdc` |
| `GA-2021.zip` | 33,020,320 B | `5622a126…0795e8` |
| `GA-2022.zip` | 35,864,779 B | `d1b14af4…5c641fc` |
| `GA-2023.zip` | 34,483,024 B | `d3af5298…366b2962` |
| `GA-2024.zip` | 35,001,158 B | `500467d4…7446c991` |
| `srs_estimates/estimated_crimes_1979_2024.csv` | 211,770 B | `8dfaa630…da1421c` |

Full sha256 values: run `sha256sum` in this directory; the truncated forms above are for
eyeball comparison only.

- **GA-{YEAR}.zip** — Georgia NIBRS master extract for one data year: relational CSVs
  (`agencies.csv`, `NIBRS_INCIDENT`, `NIBRS_OFFENSE`, `NIBRS_VICTIM`, `NIBRS_OFFENDER`,
  `NIBRS_ARRESTEE`, `NIBRS_ARRESTEE_GROUPB`, weapon/bias/location/property segments, plus
  code-lookup tables; ~45–49 members per zip). 2018 zips nest under a `GA/` folder; 2020+
  zips are flat. **Kept unextracted** — bronze is the verbatim zip. All zips pass
  `python -m zipfile -t` (verified 2026-07-02).
- **No GA zips exist before 2018 or after 2024** (probed 1991–2026 on 2026-07-02; the
  signed-URL endpoint returns nothing for missing years). 2025 should appear after the FBI's
  annual release — re-run the downloader.
- **srs_estimates/** — the CDE's small national+state SRS "estimated crimes" CSV, 1979–2024
  (last modified 2025-08-05 per `downloads.json`). Columns: year, state, population,
  violent_crime, homicide, rape (legacy+revised), robbery, aggravated_assault, property_crime,
  burglary, larceny, motor_vehicle_theft, caveats. This is the pre-2019 GA SRS history stopgap
  (see caveats below).

## API spot-check (recorded 2026-07-02)

`GET https://api.usa.gov/crime/fbi/cde/summarized/state/GA/homicide?from=01-2022&to=12-2022&API_KEY=DEMO_KEY`
→ HTTP 200; monthly GA offense actuals for 2022: Jan 63, Feb 59, Mar 72, Apr 83, May 83,
Jun 80, Jul 72, Aug 76, Sep 61, Oct 83, Nov 72, Dec 80 (rate 0.58–0.83 per 100k), plus GA/US
clearances. API dates must be `MM-YYYY`. DEMO_KEY calls used this session: 3 total
(agency roster probe, this spot-check, roster re-fetch by the downloader) — DEMO_KEY allows
only ~25–50/day; set `CDE_API_KEY` (free data.gov key) for anything routine.

## Caveats

- **Shared bronze**: `nibrs_arrests` has no bronze of its own — its inputs are the
  `NIBRS_ARRESTEE*` segments inside these same zips (see
  `../nibrs_arrests/_provenance.md`). Do not duplicate the zips there.
- **SRS→NIBRS break (Oct 2019)**: Georgia transitioned to NIBRS; 2018–2019 zips cover only
  early-adopter agencies (2018 is 0.2 MB — a handful of agencies). Pre-2019 GA history is SRS
  only. Any gold series must version/flag the methodology break; never splice SRS estimates
  and NIBRS counts into one unlabeled series.
- **NIBRS counts are unestimated** — raw agency reports, not the FBI's estimation-adjusted
  CIUS figures; they will differ from `srs_estimates/` values even in overlapping years.
- **Agency (ORI) grain** — county rollups require the `ori_to_county` crosswalk
  (`data/bronze/_crosswalks/ori_to_county/`), a hard prerequisite.
- **Follow-up (documented gap)**: full pre-2019 GA SRS history at agency/state grain
  (offenses-known "Return A" `master_files/reta/reta-{year}.zip` and arrests
  `master_files/asr/asr-{year}.zip`, 1985+) exists behind the same signed-URL endpoint but the
  files are **national fixed-width masters needing codebooks** (~40 years × 2 families) — out
  of scope here. Alternative: the API's summarized state endpoints, which need a real
  data.gov key (40+ years × offenses exceeds the DEMO_KEY budget).
