# Provenance — fbi_cde / nibrs_arrests (shared bronze — no files here)

**This topic has no bronze files of its own.** Its raw inputs are the Georgia NIBRS
master zips stored once in **`../nibrs_offenses/`** (`GA-2018.zip` … `GA-2024.zip`) —
specifically the arrestee segments inside each zip:

- `NIBRS_ARRESTEE.csv` (Group A incident-linked arrests)
- `NIBRS_ARRESTEE_GROUPB.csv` (Group B arrest-only offenses)
- `NIBRS_ARRESTEE_WEAPON.csv` / `NIBRS_ARRESTEE_GROUPB_WEAPON.csv`
- code lookups (`NIBRS_ARREST_TYPE.csv`, age/race/ethnicity tables) and `agencies.csv`

This mirrors how derived education topics share a single bronze directory (e.g.,
`enrollment_demographic_shares` / `enrollment_program_participation` under
`enrollment_by_subgroup_programs/`): the multi-hundred-MB masters are stored exactly once
and both `nibrs_offenses` and `nibrs_arrests` transforms read from
`data/bronze/criminal_justice/fbi_cde/nibrs_offenses/`.

For source URLs, retrieval method, timestamps, checksums, license (public domain), the
API spot-check record, and caveats (SRS→NIBRS break Oct 2019, unestimated counts,
ORI→county crosswalk prerequisite, expiring signed URLs), see
**`../nibrs_offenses/_provenance.md`**. Downloader:
`src/etl/criminal_justice/fbi_cde/download.py`.
