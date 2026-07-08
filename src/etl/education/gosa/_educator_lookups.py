"""Shared district/school name-resolution for the educator-qualifications topics.

All three educator-qualifications topics
(`educator_qualifications_emergency_and_provisional_credentials`,
`educator_qualifications_out_of_field_teachers`,
`educator_qualifications_inexperienced_teachers_leaders`) source from the same
GOSA educator-quality bronze family, which publishes district and school
NAMES only — no codes. Resolving those names against the education dimensions
(`data/gold/education/_dimensions/`) is the core difficulty the three
transforms share, so the curated alias/override data, the documented
source-gap rules, AND the resolution logic all live here. Add new entries
here, not in any per-topic transform.py.

The module has two halves:

1. **Curated data** — alias maps, direct code pins, and source-gap lists,
   carried over from the v1 pipeline (where each entry was verified against
   bronze + the dimensions) and re-verified for the rebuild. Three hard-won
   v1 rules are encoded in the data design:

   * **Never resolve a name shared by multiple dimension codes by
     "lowest/first code wins".** When a charter name exists under both a
     3-digit umbrella (782/783) and a specific 7-digit campus code — or
     under a school-less sibling code — the ambiguous bronze form is PINNED
     explicitly in ``MANUAL_DISTRICT_CODE_OVERRIDES`` to the campus code
     that actually carries the matching schools-dim row.
   * **GOSA truncates name cells (~52 chars for INSTN_NAME, ~22 chars for
     some SCHOOL_DSTRCT_NM rows), producing ambiguous placeholders.** A
     truncated form whose distinguisher was erased (e.g. Genesis
     Boys/Girls) can prefix-match MULTIPLE dim rows; such forms get an
     explicit FORCE_DROP / SOURCE_GAP entry with rationale instead of an
     arbitrary binding.
   * **Prefer immutable code targets over name-to-name aliases** whenever
     the dimension's canonical name churns between rebuilds (the "State
     Specialty Schools I-" prefix toggles depending on which bronze year
     wins "latest name" in the dim build). ``MANUAL_DISTRICT_CODE_OVERRIDES``
     binds bronze names straight to the stable district_code;
     ``MANUAL_DISTRICT_CI_OVERRIDES`` is reserved for dim names that are
     stable across rebuilds.

2. **Resolution logic** (rewritten clean-room for the rebuild) — the
   dimension lookups, the year-aware certified_personnel lookups, and the
   ``EducatorNameResolver`` chain the transforms call per (year,
   district_name, school_name, detail_level) combination.

What the transforms consume:

* ``load_dimension_lookups()`` / ``load_year_aware_lookups()`` — build the
  lookup tables once per run (the year-aware build is cached process-wide).
* ``EducatorNameResolver.resolve_row()`` — the full per-row chain (state
  sentinel, district resolution, school resolution, school-first fallback,
  placeholder-charter rescue).
* ``is_state_charter_placeholder_district`` / ``is_source_gap_district`` /
  ``is_source_gap_school`` — the documented row-drop predicates each
  transform applies AFTER resolution and BEFORE its residual-unresolved
  guard raises.
* ``is_force_drop_district_agg`` — drop predicate for RESOLVED-but-ambiguous
  truncated district-aggregate placeholders. Only the inexperienced topic's
  hybrid-rescue path produces such rows; the other two transforms do not
  wire it in (and must not — it would change their gold).
* ``STATE_DISTRICT_SENTINEL`` / ``STATE_INSTN_SENTINEL`` /
  ``DISTRICT_AGG_SUFFIX`` — the shared bronze aggregate-row conventions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from src.utils.readers import parse_school_year

logger = logging.getLogger(__name__)

# Dimension tables the resolver matches against.
DISTRICTS_DIM_PATH = Path("data/gold/education/_dimensions/districts.parquet")
SCHOOLS_DIM_PATH = Path("data/gold/education/_dimensions/schools.parquet")

# The certified_personnel topic ships BOTH names AND codes per row, so it
# fuels the year-aware (name -> code) lookups (see YearAwareLookups).
CERTIFIED_PERSONNEL_BRONZE_DIR = Path("data/bronze/education/gosa/certified_personnel")

# Aggregate-row sentinels shared by every educator-quality bronze file
# (verified across 2018-2024 in all three topics' structure docs).
STATE_DISTRICT_SENTINEL = "State of Georgia"
STATE_INSTN_SENTINEL = "All Georgia Schools"
DISTRICT_AGG_SUFFIX = "- All Schools"


# =============================================================================
# Curated data — district-name overrides
# =============================================================================

# District-name overrides applied before the dimension lookup
# (case-insensitive). Key: lowercased raw bronze district name; value:
# lowercased target name the dimension lookup will recognize.
#
# Use this map ONLY when the dim canonical name is stable across rebuilds.
# When the dim name moves between rebuilds (e.g. the "State Specialty
# Schools I-" prefix toggles depending on which year of bronze is "latest"),
# use ``MANUAL_DISTRICT_CODE_OVERRIDES`` below instead — it maps directly to
# the immutable district_code and is immune to dim renaming churn.
MANUAL_DISTRICT_CI_OVERRIDES: dict[str, str] = {
    # Bronze abbreviates / re-labels these four; the dim stores the
    # canonical long form. Each pair is confirmed by cross-referencing
    # other GOSA topics where both name and code appear.
    "chatham county": "savannah-chatham county",
    "dalton city": "dalton public schools",
    "decatur city": "city schools of decatur",
    "spalding county": "griffin-spalding county",
    # Bronze truncates the name at 22 chars in some 2021-2023 rows; the
    # untruncated form appears in the dim.
    "department of juvenile": "department of juvenile justice",
    # NOTE: generic truncated district labels ("State Charter Schools " /
    # "State Charter Schools-") are NOT aliased — they are redundant
    # district-aggregate publications of data already captured by the
    # corresponding bare school-name rows (every state-charter district
    # except 7991895 has exactly one school, so the district aggregate
    # equals the school row). ``is_state_charter_placeholder_district``
    # drops them to prevent double-counting.
}

# Direct bronze-name -> district_code pins (case-insensitive keys). Use this
# map for charter / specialty districts whose canonical dim NAME changes
# between rebuilds (build_dimensions picks "latest year wins" across GOSA +
# Georgia Insights, and those sources publish the same code under variant
# labels — sometimes with a "State Specialty Schools I-" prefix, sometimes
# without). The district_code itself is stable, so binding the bronze name
# directly to the code sidesteps the rename churn entirely.
#
# Every entry was verified against districts.parquet (the resolver raises at
# runtime if a pinned code disappears from the dim — see
# EducatorNameResolver.resolve_district).
MANUAL_DISTRICT_CODE_OVERRIDES: dict[str, str] = {
    # CCAT — bronze "Commission Charter Schools- CCAT School"; the dim
    # carries this district under code 7830103. Pinned by code for
    # resilience against dim renames.
    # TODO(verify-ccat-rename): the dim row at 7830103 currently labels this
    # district "State Specialty Schools II- Statesboro STEAM Academy" — the
    # CCAT charter is administratively related to Statesboro STEAM but the
    # rename is NOT a literal name match. Confirm against GOSA's commission-
    # charter registry that 7830103 is the correct successor of "CCAT School"
    # before relying on this binding for downstream analysis.
    "commission charter schools- ccat school": "7830103",
    # Ivy Preparatory Academy — bronze treats it as a Commission Charter
    # container; the dim entry lives under code 7820612 (with or without a
    # "State Specialty Schools I-" prefix depending on the rebuild).
    "commission charter schools- ivy preparatory academy school": "7820612",
    # Southwest Georgia STEM — bronze publishes under both Commission
    # Charter and State Charter Schools II container prefixes. Dim has one
    # entry classified as commission_charter at code 7830612.
    "commission charter schools- southwest georgia s.t.e.m. charter academy": "7830612",
    "state charter schools ii- southwest georgia s.t.e.m. charter academy": "7830612",
    # D.E.L.T.A. STEAM Academy: dim renames this to "Delta STEAM Academy"
    # (period-stripped, container prefix dropped) at code 7830633. Bronze
    # 2023-2024 carries the punctuated long form.
    "state charter schools ii- d.e.l.t.a. steam academy": "7830633",
    # Coastal Plains satellite — bronze "...Candler Campus" maps to district
    # 7820618. Dim name swings between "Coastal Plains High School" and the
    # "State Specialty Schools I-" prefixed form; the code is stable.
    (
        "state charter schools- coastal plains charter high school - candler campus"
    ): "7820618",
    # Dubois Integrity Academy — the bronze trailing "I" is an artifact of
    # the State Charter Schools-I container prefix being incompletely
    # stripped. Dim entry: 7820617 (label varies between rebuilds).
    "state charter schools- dubois integrity academy i": "7820617",
    # Foothills Madison Campus — the bronze "(Madison Campus)" parenthetical
    # is dropped in the dim, which uses code 7820613.
    "state charter schools- foothills charter high school (madison campus)": "7820613",
    # Cirrus Charter Academy — the dim carries this name at TWO codes: 783
    # (the commission-charter umbrella container) and 7830611 (the specific
    # physical district that the schools dim attaches school_code 0611 to).
    # An exact-name match would land on the umbrella (783 sorts first in the
    # dim), FK-orphaning the school-level rows — pin to the campus code.
    "commission charter schools- cirrus charter academy": "7830611",
    "state charter schools ii- cirrus charter academy": "7830611",
    # Mountain Education Center School — bronze "Center School" is renamed
    # "High School" in the dim (code 7820108). Note 7820109 is a separate
    # "Mountain Education Charter High Sch" entity; this bronze form binds
    # to 7820108 specifically (the legacy main campus).
    "state charter schools- mountain education center school": "7820108",
    # Odyssey — binds to 7820110 because the schools dimension carries the
    # matching school entry (0110 "Odyssey Charter School") under 7820110.
    # The dim ALSO has a 782-0110 "Odyssey Charter" district row with no
    # school under it — binding there would FK-orphan school-level rows.
    "state charter schools- odyssey school": "7820110",
    # Coweta Charter Academy — binds to 7830610 because the schools dim
    # carries school_code 0610 under 7830610. The dim has another district
    # 7830601 ("Coweta Charter Academy") with NO school entry; binding
    # there would orphan the FK.
    "commission charter schools- coweta charter academy": "7830610",
    "state charter schools ii- coweta charter academy": "7830610",
    # Fulton Leadership Academy — binds to 7830310; the dim also has a
    # 783-0310 ("Fulton Leadership") district with NO school entry.
    "commission charter schools- fulton leadership academy": "7830310",
    # --- 2023-2024 52-char-truncation pins (June 2026 dim-rebuild fix) ---
    # GOSA truncates INSTN_NAME at 52 chars in 2023-2024; the inexperienced
    # topic's hybrid-rescue path turns these into district-aggregate rows
    # keyed on the truncated name. After the June 2026 dim rebuild those
    # truncated forms would bind to the WRONG code via a first-match name
    # dedup (a 3-digit umbrella or a school-less sibling), so pin each to
    # its specific campus code. The full (untruncated) forms in 2018-2022
    # already resolve correctly.
    #   Fulton Leadership Academy -> 7830310 (also unblocks the residual
    #   guard; the truncated row was previously unresolved and raised).
    "state charter schools ii- fulton leadership academy": "7830310",
    #   Atlanta Heights Charter School -> 7830410 (campus w/ school 0410;
    #   the truncated form otherwise binds to the school-less 7820410
    #   sibling).
    "state charter schools ii- atlanta heights charter sc": "7830410",
    #   International Charter School of Atlanta -> 7820614 (campus w/
    #   school 0614; the truncated form otherwise binds to the 782
    #   umbrella). The DISTINCT "...International Charter Acad[emy of
    #   Georgia]" entity stays at 7830620 (different school) and is
    #   intentionally NOT pinned here.
    "state charter schools- international charter school": "7820614",
    # Georgia Cyber Academy — dim canonical name swings between "Ga Cyber
    # Academy" and "State Specialty Schools I- Georgia Cyber Academy
    # (Virtual)"; the 7-digit charter code 7820120 is stable.
    "state charter schools- georgia cyber academy": "7820120",
    # Georgia Connections Academy — same dim-rename pattern as Cyber.
    "state charter schools- georgia connections academy": "7820412",
    # Utopian Academy For The Arts — the dim has three variants: 782-0121
    # "Utopian Academy" (short, no schools under it), 7820121 "Utopian
    # Academy For The Arts Charte" (truncated, has the 0121 school), and
    # 7820619 (the separate Trilith campus). Pin to 7820121 — the district
    # the schools dim actually keys the matching school under.
    "state charter schools- utopian academy for the arts charter school": "7820121",
    # 52-char truncated form of the same entity (2023 inexperienced bronze,
    # via the hybrid-rescue path). The truncation-tolerant compare hits two
    # Utopian entries (7820121 + 7820619 Trilith), so pin explicitly.
    "state charter schools- utopian academy for the arts": "7820121",
    # 52-char truncated form of "State Charter Schools II- Southwest
    # Georgia S.T.E.M. Charter Academy" (2023 inexperienced bronze). The
    # dots-vs-no-dots difference defeats the truncation-tolerant prefix
    # compare against the dim's "Southwest Georgia Stem Charter Acad".
    "state charter schools ii- southwest georgia s.t.e.m.": "7830612",
    # 52-char truncated form of the Coastal Plains Candler Campus entry
    # (2023 inexperienced bronze, hybrid-rescue path).
    "state charter schools- coastal plains charter high s": "7820618",
    # 52-char truncated forms whose dim target keeps the FULL "State
    # Specialty Schools II-" container prefix (2023-2024 inexperienced
    # bronze, hybrid-rescue path). The mechanical chain cannot bind these:
    # the bare suffix ("yi hwang academy of langua") prefix-matches no dim
    # name because the dim label itself starts with the container prefix,
    # and the prefixed exact lookup fails on the truncation. The v1
    # pipeline resolved them via a prefixed truncation-tolerant compare;
    # the rebuild pins them per the module rule (pins over wider rules).
    # Targets verified against districts.parquet and the approved v1 gold.
    "state charter schools ii- yi hwang academy of langua": "7830625",
    "state charter schools ii- zest preparatory academy s": "7830645",
}

# GOSA truncation expansions for SCHOOL_DSTRCT_NM, applied BEFORE the
# year-aware lookup (which keys on the full cert-personnel name). The
# emergency/out-of-field 2023-2024 bronze truncates these district names in
# the header; without the expansion the year-aware school lookup (which the
# duplicate-school-name cardinality guard depends on, e.g. Decatur's two
# "Oakhurst Elementary School" dim rows) would miss these rows.
# The inexperienced topic layers its own additions on top via the
# ``district_name_expansions`` resolver parameter.
TRUNCATED_DISTRICT_NAME_EXPANSIONS: dict[str, str] = {
    "city schools of decatu": "city schools of decatur",
    "savannah-chatham count": "savannah-chatham county",
}

# Charter / specialty container-name prefixes. Bronze uses one canonical
# prefix (left); the dimension historically stores rows under multiple
# prefix variants (right). The resolver tries each target prefix plus the
# bare suffix, stopping on the first case-insensitive hit. Identical across
# all three educator topics (verified against each v1 transform).
CHARTER_PREFIX_REMAP: list[tuple[str, list[str]]] = [
    (
        "state charter schools ii-",
        ["state specialty schools ii-", "state charter schools ii-"],
    ),
    (
        "state charter schools-",
        ["state specialty schools i-", "state charter schools-"],
    ),
    (
        "commission charter schools-",
        [
            "state specialty schools ii-",
            "state specialty schools i-",
            "commission charter schools-",
        ],
    ),
    (
        "state schools-",
        ["state schools-"],
    ),
]


# =============================================================================
# Curated data — school-name aliases
# =============================================================================

# School-name aliases applied during school resolution (case-insensitive).
# Key: lowercased raw bronze school name; value: lowercased canonical name
# that exists in the schools dimension for the same district. Only
# non-mechanical renames/abbreviations live here — cases the mechanical
# rules in ``EducatorNameResolver.resolve_school`` already catch (suffix
# expansion for "es"/"ms"/"hs", token-suffix match for APS first-name
# prefixes, truncation-tolerant prefix match) are NOT listed.
#
# CAUTION when adding entries: an alias whose source and target forms
# CO-EXIST in the same bronze year collapses two physical schools onto one
# natural key — the collision guard will raise (divergent metrics) or dedup
# will silently drop a row (identical metrics). Verify year exclusivity
# before aliasing; see the Riverside / Lindley / Eddie White notes in
# SOURCE_GAP_SCHOOLS for pairs that CANNOT be safely aliased.
SCHOOL_NAME_ALIASES: dict[str, str] = {
    # Habersham County — bronze 2018-2019 published "9th Grade Academy";
    # dim records it as "Habersham Ninth Grade Academy".
    "9th grade academy": "habersham ninth grade academy",
    # Cobb County — bronze publishes "Acworth Intermediate School" in every
    # year; dim records the same physical school as "Acworth Elementary
    # School". No same-year co-occurrence with any other "Acworth" row.
    "acworth intermediate school": "acworth elementary school",
    # Tift County — "Primary" -> "Elementary" post-2020 rename family.
    "annie belle clark primary school": "annie belle clark elementary school",
    # Department of Juvenile Justice — "Center" vs "Campus" rename.
    "atlanta youth detention center": "atlanta youth development campus",
    # Baker County — dim records "Learning Academy"; bronze 2018-2019 used
    # "Learning Center".
    "baker county learning center": "baker county learning academy",
    # APS — bronze typo "Elmentary" (missing 'e') AND the current dim keeps
    # a 35-char truncated, punctuation-stripped label for (761, 0604), so
    # the mechanical prefix compare fails in both directions. Target the
    # dim's current canonical truncated form; cert personnel confirms the
    # code under the full name.
    "bazoline e. usher/collier heights elmentary school": (
        "bazoline e usher collier heights el"
    ),
    # DeKalb County — bronze 2023-2024 truncates the name at 52 chars and
    # the current dim truncates its label at 35 chars with the "H." period
    # stripped ("Barack H Obama Elementary Magnet Sc", 644/1103), so neither
    # prefix direction matches mechanically.
    "barack h. obama elementary magnet school of technolo": (
        "barack h obama elementary magnet sc"
    ),
    # Bremen City — the 4th grade academy was reclassified to include 5th
    # grade; both bronze spacing variants point to the same dim entry.
    "bremen 4th  grade academy": "bremen 4th & 5th grade academy",
    "bremen 4th grade academy": "bremen 4th & 5th grade academy",
    # Franklin County — bronze 2018-2019 published two distinct Carnesville
    # schools per year. Dim has both: 0107 "Carnesville Elementary School"
    # and 2050 "Carnesville Elementary Primary School". Map the
    # Intermediate row to 0107 so it does NOT collide with the Primary row.
    "carnesville elementary intermediate school": "carnesville elementary school",
    # Carrollton City — "Jr. High School" is the historical name of what
    # the dim records as "Carrollton Middle School".
    "carrollton jr. high school": "carrollton middle school",
    # Carrollton City — the separate "Middle-Upper Elementary School"
    # coexisted with the Jr. High; map it to the distinct dim entry 0106
    # "Carrollton Upper Elementary" so the two do not collide.
    "carrollton middle-upper elementary school": "carrollton upper elementary",
    "centennial academy": "centennial place academy (charter)",
    # DeKalb County — "Chamblee Charter High School" renamed "Chamblee
    # High School" in the current dim.
    "chamblee charter high school": "chamblee high school",
    # APS Charles Drew — bronze 2018-2022 used JA/SA; dim and bronze 2023+
    # use Ja/Sr (junior/senior).
    "charles drew charter school ja/sa": "charles drew charter ja/sr academy",
    # APS — renamed "Cleveland Avenue Elementary School" by 2023.
    "cleveland elementary school": "cleveland avenue elementary school",
    # State charter — Coastal Plains: dim entry is "Coastal Plains High
    # School" (district 7820618). The 2023+ bronze drops the "- Candler
    # Campus" suffix and publishes the bare form under the generic "State
    # Charter Schools-" container; alias both forms so the school-first
    # fallback binds the (district, school) pair to (7820618, 0618).
    "coastal plains charter high school - candler campus": (
        "coastal plains high school"
    ),
    "coastal plains charter high school": "coastal plains high school",
    # APS — Coretta Scott King: bronze misspells "Corretta" (double-r) and
    # sometimes omits "Young"; the current dim keeps a 35-char truncated
    # label for the Leadership Academy entity (761/1410, "Coretta Scott
    # King Young Womens Lea"). The separate "...Leadership Academy - C"
    # continuation entry (0908) and the "...Academy High School" entry
    # (0121) are different dim rows and are left for exact matches.
    "corretta scott king womens' leadership academy": (
        "coretta scott king young womens lea"
    ),
    "corretta scott king young womens' leadership academy": (
        "coretta scott king young womens lea"
    ),
    # Richmond County — bronze short form vs dim program name.
    "davidson magnet school": "davidson fine arts magnet",
    # DeKalb County — "Academy of Technology and the Environment Charter"
    # renamed "Agriculture Technology And Environment" (single form per
    # year; only one matching dim school in district 644).
    "dekalb academy of technology and the environment charter school": (
        "dekalb agriculture technology and environment school"
    ),
    # NOTE: do NOT alias "DeKalb Elementary School of the Arts" to "DeKalb
    # School of the Arts" — both labels appear as separate bronze rows in
    # the same year, so collapsing them creates duplicate natural keys.
    # See SOURCE_GAP_SCHOOLS.
    # APS — early college rename.
    "early college high school at carver": "carver high school early college",
    # Gainesville City — Fair Street rebrand (dropped "Baccalaureate
    # World" in 2023).
    "fair street international baccalaureate world school": (
        "fair street international academy"
    ),
    # City Schools of Decatur — bronze omits the "Upper" grade qualifier.
    "fifth avenue elementary": "fifth avenue upper elementary school",
    # Ben Hill County — bronze truncates "Academy" to "Aca" AND duplicates
    # "School" once; the current dim keeps a 35-char truncated label
    # (609/0291, "Fitzgerald High School College And").
    "fitzgerald high school school college and career aca": (
        "fitzgerald high school college and"
    ),
    # State charter — Foothills Athens satellite. Dim records "Foothills
    # Regional High School" (district 7820613). 2023 bronze truncates the
    # parenthetical at 52 chars, so alias the truncated form too.
    "foothills charter high school (central office - athens)": (
        "foothills regional high school"
    ),
    "foothills charter high school (central office - athe": (
        "foothills regional high school"
    ),
    # 2023 bronze additionally publishes the bare form (no campus
    # parenthetical) under the generic "State Charter Schools-" placeholder
    # container; mirrors the bare "coastal plains charter high school"
    # alias above.
    "foothills charter high school": "foothills regional high school",
    "freedom park elementary": "freedom park k-8 school",
    # Tift County — "Primary" vs "Elementary" rename.
    "g. o. bailey primary school": "g. o. bailey elementary school",
    # Fulton County — the June 2026 dim rebuild's "latest name wins" picked
    # a truncated, apostrophe-less label "Georgia Baptist Childrens Home
    # And" for (660, 0307). Bronze publishes the full punctuated name
    # (2018-2022) and a 52-char truncation of it (2023-2024); the apostrophe
    # ("Children's" vs "Childrens") defeats the mechanical prefix compare in
    # both directions. certified_personnel confirms (660, 0307) under the
    # full name in every year EXCEPT 2020 (the school is absent from that
    # file), so the year-aware path covers 2018-2019/2021-2022 and these
    # aliases cover 2020 plus the truncated 2023-2024 forms.
    "georgia baptist children's home and family ministries": (
        "georgia baptist childrens home and"
    ),
    "georgia baptist children's home and family ministrie": (
        "georgia baptist childrens home and"
    ),
    # --- Campus-code repins after the rebuild-era schools-dim refresh ---
    # The current schools dim carries many charter schools TWICE: under the
    # 3-digit umbrella district (782/783) with the FULL school name, and
    # under the specific 7-digit campus district with a 35-char TRUNCATED
    # name. A bronze full-name match therefore lands on the umbrella entry
    # only — the "never resolve by lowest/first code" footgun in school
    # form. Each alias below points the bronze full name at the campus
    # entry's truncated label so resolution binds the campus code (verified
    # against the approved v1 gold bindings for 2023). These fire only when
    # the year-aware certified_personnel path misses (2023's placeholder-
    # container district rows); in other years year-aware resolves first.
    "georgia connections academy (virtual)": "georgia connections academy",
    "genesis innovation academy for girls": "genesis innovation academy for girl",
    "georgia school for innovation and the classics": (
        "georgia school for innovation and t"
    ),
    "international charter school of atlanta": "international charter school of atl",
    "southwest georgia s.t.e.m. charter academy": (
        "southwest georgia stem charter acad"
    ),
    "utopian academy for the arts charter school": (
        "utopian academy for the arts charte"
    ),
    # Same campus-repin pattern, added for the inexperienced topic's 2023-
    # 2024 bare school-name rows under the generic placeholder container.
    # The current dim keeps only a 35-char truncated label for each campus
    # (no full-name umbrella twin exists — verified schools.parquet), so
    # the name-only fallback misses without the alias and the row would be
    # dropped as an unresolvable placeholder. For the emergency /
    # out-of-field topics these aliases are inert-or-equivalent: their
    # container-prefixed district rows resolve via the year-aware or
    # within-district truncation-tolerant steps first, and their 2023 bare
    # placeholder forms carry metrics identical to the prefixed
    # republications (any divergence would trip the collision guard).
    "international charter academy of georgia": (
        "international charter academy of ge"
    ),
    "georgia fugees academy charter school": "georgia fugees academy charter scho",
    "yi hwang academy of language excellence": (
        "yi hwang academy of language excell"
    ),
    "destinations career academy of georgia (virtual)": (
        "destinations career academy of geor"
    ),
    "utopian academy for the arts trilith": "utopian academy for the arts trilit",
    # APS rebrand: "Grady High School" renamed "Midtown High School" in
    # 2021; bronze rows from 2018-2021 carry the old name.
    "grady high school": "midtown high school",
    # Henry County — dim records "Patrick Henry High School"; bronze
    # 2018-2019 used "Henry County High School" (only one Henry-named high
    # school in the district).
    "henry county high school": "patrick henry high school",
    # Decatur County — Hutto reclassified Middle -> Elementary in 2023;
    # only one form per year in bronze.
    "hutto middle school": "hutto elementary school",
    # Commission Charter — dim stores "Ivy Preparatory Academy, Inc";
    # bronze "Ivy Preparatory Academy School" is the school-level row
    # under the same district.
    "ivy preparatory academy school": "ivy preparatory academy, inc",
    # Jackson County — "Comprehensive" dropped from the high school name.
    "jackson county comprehensive high school": "jackson county high school",
    "johnson magnet": "johnson health science and engineering magnet school",
    # Decatur County — "...Elementary" renamed "...Primary School" in 2023.
    "jones-wheat elementary school": "jones-wheat primary school",
    # "Elem" abbreviation not covered by the " es" mechanical suffix rule.
    "kemp elem school": "kemp elementary school",
    # APS Kindezi — bronze bare "Kindezi" (2018-2022) maps to dim "The
    # Kindezi School". The "Kindezi Old 4Th Ward" rows have their own dim
    # entries and are unaffected.
    "kindezi": "the kindezi school",
    "kipp atlanta collegiate academy": "kipp atlanta collegiate charter school",
    # APS KIPP renames (2023 dim adopts the "Charter School" forms).
    "kipp strive academy": "kipp strive charter school",
    "kipp vision": "kipp vision charter school",
    "kipp ways primary school": "kipp ways primary charter school",
    # KIPP WAYS = "KIPP West Atlanta Young Scholars"; bronze 2018-2022 used
    # the long form, the dim adopted the short acronym form in 2023.
    "kipp west atlanta young scholars academy": "kipp ways academy charter school",
    # "Career Academy" -> "College and Career Academy" rename pattern.
    "lanier career academy": "lanier college and career academy",
    "len lastinger primary school": "len lastinger elementary school",
    # APS legacy name.
    "maynard h. jackson, jr. high school": "maynard jackson high school",
    "metter career academy": "metter college and career academy",
    # State charter — Mountain Education: the dim stores "Mountain
    # Education High School" under district 7820108; bronze used "Center
    # School" through 2019 and "Charter High School" 2020+. Both map to the
    # canonical dim name so the district code pin (-> 7820108) resolves the
    # school side too.
    "mountain education center school": "mountain education high school",
    "mountain education charter high school": "mountain education high school",
    # State charter — Foothills Madison Campus school-side normalization
    # (the district pin sends the row to 7820613).
    "foothills charter high school (madison campus)": "foothills regional high school",
    # State charter — Odyssey school-side normalization (district pin
    # -> 7820110). A different "Odyssey School" at district 796 is
    # unaffected — exact match wins there before the alias path runs.
    "odyssey school": "odyssey charter school",
    # Gainesville City — Mundy Mill rebranded "Arts Academy".
    "mundy mill academy": "mundy mill arts academy",
    # DeKalb County — bronze typo "Murphy" vs dim "Murphey".
    "murphy candler elementary school": "murphey candler elementary school",
    # Department of Juvenile Justice — "Center" vs "Campus" rename.
    "muscogee youth development center": "muscogee youth development campus",
    # City Schools of Decatur — the "New" prefix was dropped from 2022.
    "new glennwood elementary": "glennwood elementary school",
    # Gainesville City — New Holland rebrand to "Leadership Academy".
    "new holland core knowledge academy": "new holland leadership academy",
    "new holland knowledge academy": "new holland leadership academy",
    # Tift County — satellite campus of Tift County High that maps to
    # Northeast Middle School in the dim.
    "northeast campus, tift county high school": "northeast middle school",
    "northside primary school": "northside elementary school",
    "oakview elementary": "oak view elementary",
    # Pickens County — bronze 2018 "Middle School" form; dim records
    # "Junior High School" (no same-year co-occurrence).
    "pickens county middle school": "pickens county junior high school",
    # Randolph County — renamed "Randolph County Middle School" in 2023+.
    "randolph clay middle school": "randolph county middle school",
    # SAIL Charter Academy — 2023 bronze truncates the school name at 52
    # chars in two variants the mechanical truncation rules cannot catch
    # (container prefix in one; mid-word cut in the other), and the current
    # dim keeps a 35-char truncated label (7830618/0618, "Sail Charter
    # Academy - School For A").
    "sail charter academy - school for arts-infused learn": (
        "sail charter academy - school for a"
    ),
    "state charter schools ii- sail charter academy - sch": (
        "sail charter academy - school for a"
    ),
    # City Schools of Decatur — bronze omits the "Upper" grade qualifier.
    "talley street elementary school": "talley street upper elementary school",
    # Taylor County — dim adopted the post-2023 rename.
    "taylor county upper elementary": "taylor county elementary",
    # Tift County — "School" vs the more specific "Elementary School".
    "j. t. reddick school": "j. t. reddick elementary school",
    # Decatur County — "...Elementary" renamed "...Primary School" in 2023.
    "west bainbridge elementary school": "west bainbridge primary school",
    # City Schools of Decatur — Renfroe renamed Beacon Hill in 2023;
    # mutually exclusive years.
    "renfroe middle school": "beacon hill middle school",
    # APS — King Middle renamed to the fuller "Martin L. King Jr." form
    # post-2022; mutually exclusive years.
    "king middle school": "martin l. king jr. middle school",
    # APS — Inman renamed David T Howard in 2022; mutually exclusive years.
    "inman middle school": "david t howard middle school",
    # Clarke County — Alps Road renamed Bettye Henderson Holston in 2024;
    # mutually exclusive years.
    "alps road elementary school": "bettye henderson holston elementary school",
    # Fulton County — Latin Grammar / Latin College Prep rebranded to RISE
    # in 2020; bronze uses the Latin names 2018-2019 only.
    "latin grammar school": "rise grammar school",
    "latin college prep": "rise prep school",
    # Greene County — Union Point Elementary consolidated into the
    # district-wide Greene County Primary School in 2020; mutually
    # exclusive years. (Greensboro Elementary has its own dim entry.)
    "union point elementary": "greene county primary school",
}


# =============================================================================
# Curated data — source-gap predicates
# =============================================================================
#
# Bronze entities that are unconditionally NOT mappable to any single dim
# entity. Each transform applies these filters AFTER the resolution loop and
# BEFORE its residual-unresolved guard raises, logging the filtered count
# and recording it in the manifest (record_filtered). After the filters and
# the alias maps above, the residual unresolved set MUST be empty —
# otherwise the transform raises so future bronze drift cannot silently
# regress into a new pattern of dropped rows.

# Generic truncated charter-container district labels published by the 2023
# educator-quality bronze: "State Charter Schools " (trailing space) and
# "State Charter Schools-" (trailing dash). Rows under these labels whose
# school name cannot be independently rescued are REDUNDANT
# district-aggregate publications of data already captured by the bare
# school-name rows under the same charter entity (every state-charter
# district except 7991895 has exactly one school, so the district aggregate
# mathematically equals the single school row — verified against well-formed
# 2022 bronze). Dropping them prevents double-counting; it is NOT data loss.
# Data reviews have re-flagged this drop before — it is deliberate.
_STATE_CHARTER_PLACEHOLDER_RE = re.compile(
    r"^state charter schools[\s\-]*$",
    re.IGNORECASE,
)


def is_state_charter_placeholder_district(district_name: str) -> bool:
    """True if ``district_name`` is a generic truncated charter container.

    Matches both ``"State Charter Schools "`` (trailing whitespace) and
    ``"State Charter Schools-"`` (trailing dash) — the 2023 bronze's
    placeholder labels. See the module-level rationale above: rows dropped
    under this predicate are redundant aggregate republications, not
    unrecoverable entities.
    """
    return bool(_STATE_CHARTER_PLACEHOLDER_RE.match(district_name.strip()))


# Specific district labels (NOT generic placeholders) with NO confirmed
# match in districts.parquet. These rows are dropped at the district level —
# the nearest-named dim entry is a different physical campus and binding to
# it would silently mis-attribute facts (fidelity over coverage). When a dim
# entry becomes available, promote the entry to
# MANUAL_DISTRICT_CODE_OVERRIDES and remove it here.
SOURCE_GAP_DISTRICT_NAMES: frozenset[str] = frozenset(
    {
        # Ivy Prep Kirkwood — appears in 2018-2022 bronze. The schools dim
        # has no Kirkwood entry under any district code, and the closest
        # districts.parquet candidate (7830110 = "State Charter Schools II-
        # Ivy Preparatory Academy at Gwinnett") is a different physical
        # campus. The school-level row is covered by SOURCE_GAP_SCHOOLS;
        # this entry covers the district-aggregate "...- All Schools" row.
        "state charter schools- ivy prep academy at kirkwood for girls school",
        # 52-char truncated form of the Kirkwood entity name (2023
        # inexperienced bronze, hybrid-rescue path). Same gap.
        "state charter schools- ivy prep academy at kirkwood",
        # 52-char truncation of "State Charter Schools II- Genesis
        # Innovation Academy for ..." erases the Boys/Girls distinguisher,
        # ambiguously prefix-matching two sister dim rows. No safe
        # single-target bind.
        "state charter schools ii- genesis innovation academy",
        # 52-char truncation of "State Charter Schools- Foothills Charter
        # High School ..." erases the campus distinguisher, ambiguously
        # prefix-matching multiple Foothills dim rows.
        "state charter schools- foothills charter high school",
    }
)


def is_source_gap_district(district_name: str) -> bool:
    """True if ``district_name`` is a documented district-level source gap.

    Case-insensitive on the lowercased + stripped district name. Applied by
    the transforms to UNRESOLVED rows only (resolved rows never reach it).
    """
    return district_name.lower().strip() in SOURCE_GAP_DISTRICT_NAMES


# District-aggregate placeholder names that must be dropped EVEN WHEN they
# resolve to a code. The SOURCE_GAP_DISTRICT_NAMES filter fires only on
# unresolved rows; but a 52-char-truncated, distinguisher-erased placeholder
# can prefix-match a sister dim row and resolve to an ARBITRARY one of two
# campuses (e.g. Genesis Boys 7830615 vs Girls 7830616). The bare
# school-name rows already publish the correct per-campus values, so the
# resolved district-aggregate row is a redundant, arbitrarily-attributed
# double-count. Only the inexperienced topic's hybrid-rescue path produces
# such rows — it is the only transform that wires this predicate in.
FORCE_DROP_DISTRICT_AGG_NAMES: frozenset[str] = frozenset(
    {
        # "State Charter Schools II- Genesis Innovation Academy" (exactly
        # 52 chars) — Boys/Girls erased by truncation; prefix-binds
        # arbitrarily to 7830615/7830616. The Genesis Boys (7830615/0615)
        # and Girls (7830616/0616) school rows carry the real values.
        "state charter schools ii- genesis innovation academy",
    }
)


def is_force_drop_district_agg(district_name: str) -> bool:
    """True if a RESOLVED district-aggregate row must still be dropped.

    For ambiguous truncated placeholder names (see
    ``FORCE_DROP_DISTRICT_AGG_NAMES``) whose prefix binds arbitrarily to one
    of two sister campuses; the bare school-name rows carry the real values.
    Case-insensitive on the lowercased + stripped district name.
    """
    return district_name.lower().strip() in FORCE_DROP_DISTRICT_AGG_NAMES


# School-level source gaps: (lower(district_name), lower(school_name)) pairs
# confirmed against the schools dimension to have NO single-target dim
# entry. Buckets:
#   (a) K-8/K-12 combined campuses the dim splits into separate ES/MS/HS
#       rows (no single dim row represents the aggregate),
#   (b) closed schools with no dim replacement,
#   (c) placeholder names for under-construction campuses,
#   (d) pre-merge sibling schools that co-occur in the same bronze year, so
#       aliasing either to the post-merge name collides with the other,
#   (e) aggregate labels the dim splits across multiple per-region entries,
#   (f) charter-context schools whose district resolves but no schools-dim
#       entry exists under that district code.
# To rescue an entry, EITHER extend the schools dimension build OR add a
# SCHOOL_NAME_ALIASES entry (only when the alias cannot collide with a
# sibling).
SOURCE_GAP_SCHOOLS: frozenset[tuple[str, str]] = frozenset(
    {
        # (a) K-8 / K-12 combined campuses — dim splits into ES + MS (+ HS)
        ("baker county", "baker county k12 school"),
        ("richmond county", "belair k-8 school"),
        ("richmond county", "richmond hill k-8"),
        ("glascock county", "glascock county consolidated school"),
        # (d) pre-merge sibling pairs — aliasing either collides w/ the other
        ("cobb county", "riverside primary school"),
        ("cobb county", "riverside intermediate school"),
        ("tattnall county", "glennville middle school"),
        ("tattnall county", "reidsville middle school"),
        ("clayton county", "eddie white academy"),
        ("clayton county", "eddie white elementary school"),
        # (b) closed schools with no dim replacement
        ("atlanta public schools", "brown middle school"),
        ("atlanta public schools", "aps-forrest hills academy"),
        ("bartow county", "south central middle school"),
        # (e) aggregate labels split across multiple per-region dim entries
        ("henry county", "henry county middle school"),
        # co-existing alongside the dim's representative without a clean alias
        ("cobb county", "lindley 6th grade academy"),
        ("dekalb county", "dekalb elementary school of the arts"),
        ("atlanta public schools", "miles intermediate school"),
        # (c) placeholder names for under-construction campuses
        ("forsyth county", "future elementary school #5"),
        ("cobb county", "mountain view elementary replacement"),
        # pre-consolidation single-year school (dim has Hill City / Harmony /
        # Tate but no Jasper Elementary)
        ("pickens county", "jasper elementary school"),
        # real school 2018-2023 that disappears from bronze in 2024 with no
        # dim entry (Cottrell Elementary 693/2050 is a distinct school)
        ("lumpkin county", "lumpkin county elementary school"),
        # (f) charter-context: district resolves but no schools-dim entry
        # exists under that district code
        (
            "state charter schools- provost academy georgia",
            "provost academy georgia",
        ),
        (
            "state charter schools- ivy prep academy at kirkwood for girls school",
            "ivy prep academy at kirkwood for girls school",
        ),
        (
            "state charter schools- ivy prep academy at kirkwood for girls school",
            "ivy preparatory academy, inc",
        ),
        # CCAT charter — the schools dim places "Ccat School" under district
        # 795, which is itself missing from districts.parquet, so the FK
        # guard rejects it. Bronze publishes the row under both the "Ccat
        # School" label (early years) and the rebranded "Statesboro Steam
        # Academy" label (observed in inexperienced 2024).
        (
            "commission charter schools- ccat school",
            "ccat school",
        ),
        (
            "commission charter schools- ccat school",
            "statesboro steam academy",
        ),
        # Duplicate name in the schools dim AND in certified_personnel 2023:
        # the dim carries two Barrow County rows for this name (0300, 0309)
        # and cert personnel 2023 itself publishes BOTH codes under the same
        # name, so neither the year-aware path nor the cardinality-guarded
        # exact match can disambiguate. The downstream drop masks require
        # school_code IS NULL, so this entry only suppresses bronze years
        # where resolution genuinely fails (2023); in other years cert
        # personnel resolves the name unambiguously to 0300.
        ("barrow county", "barrow arts and sciences academy"),
    }
)


def is_source_gap_school(district_name: str, school_name: str) -> bool:
    """True if (district_name, school_name) is a documented source gap.

    Case-insensitive on lowercased + stripped names, matching how
    :data:`SOURCE_GAP_SCHOOLS` is keyed.
    """
    key = (district_name.lower().strip(), school_name.lower().strip())
    return key in SOURCE_GAP_SCHOOLS


# =============================================================================
# Dimension lookups
# =============================================================================


@dataclass(frozen=True)
class DimensionLookups:
    """Name -> code lookup tables built from the education dimensions.

    Attributes:
        district_by_name: lower(district_name) -> district_code. Deduped by
            name: when two dim rows share a name, a ``standard``-type row
            wins, otherwise the first row in parquet order wins (codes sort
            ascending in the dim build, so first == lowest code — exactly
            the footgun MANUAL_DISTRICT_CODE_OVERRIDES pins around).
            Iteration order == districts.parquet row order; the truncation-
            tolerant matching steps depend on it being deterministic.
        district_codes: every district_code in districts.parquet, NOT
            deduped by name. The FK-validity guard set — `.values()` of
            district_by_name would drop name-collision losers (e.g. the
            7830610 "Coweta Charter Academy" row) and falsely reject pins.
        school_by_district_and_name: (district_code, lower(school_name)) ->
            school_code, first-write-wins on duplicate names in a district.
        schools_by_name: lower(school_name) -> [(district_code,
            school_code), ...] preserving ALL dim entries (fuels the
            school-first fallback and the duplicate-name cardinality guard).
        school_pairs: every (district_code, school_code) pair in
            schools.parquet — the FK-validity set for school resolution.
    """

    district_by_name: dict[str, str]
    district_codes: frozenset[str]
    school_by_district_and_name: dict[tuple[str, str], str]
    schools_by_name: dict[str, list[tuple[str, str]]]
    school_pairs: frozenset[tuple[str, str]]


def load_dimension_lookups(
    districts_path: Path = DISTRICTS_DIM_PATH,
    schools_path: Path = SCHOOLS_DIM_PATH,
) -> DimensionLookups:
    """Build the name -> code lookup tables from the education dimensions."""
    districts = pl.read_parquet(districts_path)
    schools = pl.read_parquet(schools_path)

    district_by_name: dict[str, str] = {}
    for name, code, dtype in districts.select(
        "district_name", "district_code", "district_type"
    ).iter_rows():
        name_lo = name.lower()
        # Standard-type rows win name collisions (a county district beats a
        # same-named charter container); otherwise first row wins. Dict
        # insertion position is preserved on overwrite, keeping iteration
        # order == parquet row order for the prefix-matching steps.
        if name_lo not in district_by_name or dtype == "standard":
            district_by_name[name_lo] = code

    school_by_district_and_name: dict[tuple[str, str], str] = {}
    schools_by_name: dict[str, list[tuple[str, str]]] = {}
    school_pairs: set[tuple[str, str]] = set()
    for dc, sc, name in schools.select(
        "district_code", "school_code", "school_name"
    ).iter_rows():
        name_lo = name.lower()
        school_by_district_and_name.setdefault((dc, name_lo), sc)
        schools_by_name.setdefault(name_lo, []).append((dc, sc))
        school_pairs.add((dc, sc))

    logger.info(
        "Dimension lookups: %d district names (%d codes), %d (district, "
        "school-name) pairs, %d distinct school names, %d FK school pairs",
        len(district_by_name),
        districts.height,
        len(school_by_district_and_name),
        len(schools_by_name),
        len(school_pairs),
    )
    return DimensionLookups(
        district_by_name=district_by_name,
        district_codes=frozenset(districts["district_code"].to_list()),
        school_by_district_and_name=school_by_district_and_name,
        schools_by_name=schools_by_name,
        school_pairs=frozenset(school_pairs),
    )


# =============================================================================
# Year-aware lookups (built from certified_personnel bronze)
# =============================================================================
#
# The educator-quality bronze publishes only NAMES. The global dimensions
# keep only the LATEST name per entity, so a historical bronze name can bind
# to the WRONG code when the name moved between entities over time.
# Verified example: 2018 bronze "KIPP West Atlanta Young Scholars Academy"
# belongs to school_code 0605 in the 2018 certified_personnel file, but the
# dim's latest-name snapshot would bind it to 0704 (a different physical
# school that holds a similar name today).
#
# certified_personnel ships BOTH names AND codes per row with
# LONG_SCHOOL_YEAR, so a per-year (name -> code) lookup built from it is
# faithful at each year's name boundary. The resolvers consult it FIRST and
# fall back to the global-dim path when it has no unambiguous answer.


@dataclass(frozen=True)
class YearAwareLookups:
    """Per-year (name -> code) resolvers built from certified_personnel.

    Names mapping to MORE than one code within a year are ambiguous: every
    resolver returns ``None`` for them so the global-dim path (with its own
    guards) decides instead.
    """

    district_by_year: dict[int, dict[str, set[str]]] = field(default_factory=dict)
    school_by_year: dict[int, dict[tuple[str, str], set[tuple[str, str]]]] = field(
        default_factory=dict
    )
    school_by_year_by_name: dict[int, dict[str, set[tuple[str, str]]]] = field(
        default_factory=dict
    )

    def resolve_district(self, year: int, district_name: str) -> str | None:
        """Resolve a district name to its code for ``year``; None if absent
        from that year's cert personnel or ambiguous (multiple codes)."""
        codes = self.district_by_year.get(year, {}).get(district_name.lower().strip())
        if codes is None or len(codes) != 1:
            return None
        return next(iter(codes))

    def resolve_school_pair(
        self, year: int, district_name: str, school_name: str
    ) -> tuple[str, str] | None:
        """Resolve (district_code, school_code) by year + both names; None
        when absent or ambiguous."""
        pairs = self.school_by_year.get(year, {}).get(
            (district_name.lower().strip(), school_name.lower().strip())
        )
        if pairs is None or len(pairs) != 1:
            return None
        return next(iter(pairs))

    def resolve_school_pair_by_name(
        self, year: int, school_name: str
    ) -> tuple[str, str] | None:
        """Resolve (district_code, school_code) by school name alone —
        useful when the bronze district label is a charter umbrella that
        never appears in cert personnel. None when absent or ambiguous."""
        pairs = self.school_by_year_by_name.get(year, {}).get(
            school_name.lower().strip()
        )
        if pairs is None or len(pairs) != 1:
            return None
        return next(iter(pairs))


# Process-wide cache so the three educator transforms (and re-runs within
# one process) parse the ~14 certified_personnel CSVs once. Keyed by the
# resolved bronze path.
_YEAR_AWARE_CACHE: dict[str, YearAwareLookups] = {}


def _lenient_end_year(value: str | None) -> int | None:
    """Parse the ending year from a LONG_SCHOOL_YEAR cell; None if malformed."""
    if not value:
        return None
    try:
        return parse_school_year(value)
    except ValueError:
        return None


def _zfill_district_code(code: str) -> str:
    """Normalize a cert-personnel district code to the dim convention:
    3-digit standard codes are zero-padded; 7-digit charter codes pass
    through unchanged (mirrors the education domain CLAUDE.md rule)."""
    code = code.strip()
    if not code:
        return code
    return code.zfill(3) if len(code) <= 3 else code


def load_year_aware_lookups(
    bronze_dir: Path = CERTIFIED_PERSONNEL_BRONZE_DIR,
) -> YearAwareLookups:
    """Build (and cache) the per-year name -> code lookups.

    Reads every ``certified_personnel_*.csv`` as all-string (no schema
    inference — codes keep leading zeros; no suppression-marker nulling —
    the raw csv content is the source of truth here, matching how the
    lookups were originally curated). Rows with a malformed school year or
    a missing district code/name are skipped; school-level entries skip the
    aggregate sentinel ``INSTN_NUMBER == "ALL"``.

    A missing bronze directory yields empty lookups — every resolution then
    falls through to the global-dim path.
    """
    cache_key = str(bronze_dir.resolve())
    cached = _YEAR_AWARE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    district_by_year: dict[int, dict[str, set[str]]] = {}
    school_by_year: dict[int, dict[tuple[str, str], set[tuple[str, str]]]] = {}
    school_by_year_by_name: dict[int, dict[str, set[tuple[str, str]]]] = {}

    needed = [
        "LONG_SCHOOL_YEAR",
        "SCHOOL_DSTRCT_CD",
        "SCHOOL_DSTRCT_NM",
        "INSTN_NUMBER",
        "INSTN_NAME",
    ]
    for path in sorted(bronze_dir.glob("certified_personnel_*.csv")):
        frame = pl.read_csv(path, infer_schema_length=0)
        if any(col not in frame.columns for col in needed):
            logger.warning(
                "Year-aware lookups: %s lacks expected columns; skipped", path.name
            )
            continue
        for long_year, dist_code, dist_name, school_code, school_name in frame.select(
            needed
        ).iter_rows():
            year = _lenient_end_year(long_year)
            if year is None or not dist_code or not dist_name:
                continue
            dist_code_n = _zfill_district_code(dist_code)
            dist_name_lo = dist_name.strip().lower()
            district_by_year.setdefault(year, {}).setdefault(dist_name_lo, set()).add(
                dist_code_n
            )
            # Aggregate rows carry INSTN_NUMBER="ALL" — district info only.
            if (
                not school_code
                or school_code.strip().upper() == "ALL"
                or not school_name
            ):
                continue
            pair = (dist_code_n, school_code.strip().zfill(4))
            school_name_lo = school_name.strip().lower()
            school_by_year.setdefault(year, {}).setdefault(
                (dist_name_lo, school_name_lo), set()
            ).add(pair)
            school_by_year_by_name.setdefault(year, {}).setdefault(
                school_name_lo, set()
            ).add(pair)

    result = YearAwareLookups(
        district_by_year=district_by_year,
        school_by_year=school_by_year,
        school_by_year_by_name=school_by_year_by_name,
    )
    _YEAR_AWARE_CACHE[cache_key] = result
    logger.info(
        "Year-aware lookups built from %s: years %s",
        bronze_dir,
        sorted(district_by_year),
    )
    return result


# =============================================================================
# The resolver
# =============================================================================

# Bronze district labels signalling a charter container context. Used to
# gate the school-first fallback's permission to OVERRIDE a resolved
# district (a standard-district row must never migrate to another district
# just because its school name is unique elsewhere in the dim).
_CHARTER_CONTEXT_PREFIXES = (
    "state charter schools",
    "commission charter schools",
)

# Trailing junk bronze sometimes appends to district names ("State Charter
# Schools " / "State Charter Schools-").
_TRAILING_JUNK_RE = re.compile(r"[\s\-_/]+$")


def _tokenize(name: str) -> list[str]:
    """Tokenize a lowercased name on non-alphanumerics for suffix matching.

    Initials like "T. J." split into single-letter tokens (kept, so "T. J.
    Perkerson" stays distinguishable from a bare "Perkerson"); empty tokens
    are dropped.
    """
    return [tok for tok in re.split(r"[^a-z0-9]+", name) if tok]


class EducatorNameResolver:
    """Resolves bronze (district_name, school_name) pairs to dimension codes.

    One instance per transform run. The chain semantics are shared by all
    three educator-qualifications topics (verified identical across the v1
    transforms); the inexperienced topic layers its hybrid-rescue on top of
    ``resolve_row`` rather than replacing it.

    Args:
        dims: Dimension lookup tables (``load_dimension_lookups()``).
        year_aware: Per-year cert-personnel lookups
            (``load_year_aware_lookups()``).
        district_name_expansions: Topic-specific GOSA-truncation expansions
            applied to district names BEFORE the year-aware lookup, merged
            over :data:`TRUNCATED_DISTRICT_NAME_EXPANSIONS`.
    """

    def __init__(
        self,
        dims: DimensionLookups,
        year_aware: YearAwareLookups,
        district_name_expansions: dict[str, str] | None = None,
    ) -> None:
        self._dims = dims
        self._year_aware = year_aware
        self._expansions = {
            **TRUNCATED_DISTRICT_NAME_EXPANSIONS,
            **(district_name_expansions or {}),
        }

    # --- district -----------------------------------------------------------

    def canonical_district_name(self, district_name: str) -> str:
        """The truncation-expanded form of a bronze district name (the form
        the year-aware school lookup must see), or the input unchanged."""
        return self._expansions.get(district_name.lower().strip(), district_name)

    def resolve_district(self, year: int, district_name: str) -> str | None:
        """Resolve a bronze district name to a district_code, or None.

        Chain (first hit wins):
          0. normalize: lowercase, strip, drop trailing space/dash junk,
             expand known GOSA truncations;
          1. year-aware cert-personnel lookup (FK-guarded);
          2. MANUAL_DISTRICT_CODE_OVERRIDES pin (raises on a stale pin);
          3. MANUAL_DISTRICT_CI_OVERRIDES rename, then exact dim match;
          4. charter-prefix remap (bare suffix, each target prefix, then
             truncation-tolerant compare on the suffix);
          5. truncation-tolerant compare on the whole name (unique-match
             guarded in both directions).
        """
        name_lo = _TRAILING_JUNK_RE.sub("", district_name.lower().strip())
        name_lo = self._expansions.get(name_lo, name_lo)

        # (1) Year-aware: highest priority — cert personnel ships BOTH name
        # and code for the same school year, so the binding is faithful even
        # when the dim's latest-name snapshot would mis-resolve. FK-guarded
        # against codes the dim no longer carries.
        ya_code = self._year_aware.resolve_district(year, name_lo)
        if ya_code is not None and ya_code in self._dims.district_codes:
            return ya_code

        # (2) Direct code pin — immune to dim-name churn between rebuilds.
        pinned = MANUAL_DISTRICT_CODE_OVERRIDES.get(name_lo)
        if pinned is not None:
            if pinned not in self._dims.district_codes:
                # A stale pin would silently emit FK orphans the API drops
                # at join time — fail loudly so the pin gets corrected.
                raise RuntimeError(
                    f"MANUAL_DISTRICT_CODE_OVERRIDES maps {name_lo!r} -> "
                    f"district_code={pinned!r}, which is not in "
                    f"districts.parquet. Fix the pin (dim rebuild dropped or "
                    f"renamed the code) or move the entry to "
                    f"SOURCE_GAP_DISTRICT_NAMES if no dim entity exists."
                )
            return pinned

        # (3) Curated rename, then exact case-insensitive dim match.
        name_lo = MANUAL_DISTRICT_CI_OVERRIDES.get(name_lo, name_lo)
        code = self._dims.district_by_name.get(name_lo)
        if code is not None:
            return code

        # (4) Charter-prefix remap: only one source prefix can match.
        for src_prefix, target_prefixes in CHARTER_PREFIX_REMAP:
            if not name_lo.startswith(src_prefix):
                continue
            suffix = name_lo[len(src_prefix) :].strip()
            # The dim sometimes stores the bare entity name with no
            # container prefix at all — try that first.
            code = self._dims.district_by_name.get(suffix)
            if code is not None:
                return code
            for target in target_prefixes:
                code = self._dims.district_by_name.get(f"{target} {suffix}")
                if code is not None:
                    return code
            # Truncation-tolerant compare on the bare suffix (the dim
            # itself stores truncated labels like "Utopian Academy For The
            # Arts Charte"). First-hit semantics over the dim's stable
            # parquet row order — retained deliberately from v1 for
            # deterministic, parity-preserving binds.
            if len(suffix) >= 5:
                for dim_name, dim_code in self._dims.district_by_name.items():
                    if len(dim_name) >= 10 and suffix.startswith(dim_name):
                        return dim_code
                for dim_name, dim_code in self._dims.district_by_name.items():
                    if dim_name.startswith(suffix) and dim_name != suffix:
                        return dim_code
            break

        # (5) Truncation-tolerant compare on the whole name, unique-match
        # guarded so an ambiguous prefix (e.g. the generic 2023 charter
        # containers) returns None instead of an arbitrary bind. Minimum
        # lengths prevent short names from swallowing unrelated ones.
        if len(name_lo) >= 5:
            forward = [
                dim_code
                for dim_name, dim_code in self._dims.district_by_name.items()
                if dim_name.startswith(name_lo) and dim_name != name_lo
            ]
            if len(forward) == 1:
                return forward[0]
            reverse = [
                dim_code
                for dim_name, dim_code in self._dims.district_by_name.items()
                if len(dim_name) >= 10 and name_lo.startswith(dim_name)
            ]
            if len(reverse) == 1:
                return reverse[0]

        return None

    # --- school ---------------------------------------------------------------

    def resolve_school(
        self,
        year: int,
        district_name: str,
        school_name: str,
        district_code: str,
    ) -> str | None:
        """Resolve a bronze school name to a school_code within a district.

        Chain (first unambiguous hit wins):
          0. year-aware cert-personnel pair lookup — accepted only when it
             agrees with ``district_code`` AND the pair exists in the
             schools dim (no FK orphans);
          1. exact case-insensitive match, cardinality-guarded: two dim
             rows with the same name in the district (e.g. Decatur's two
             "Oakhurst Elementary School" rows) return None rather than an
             arbitrary code;
          2. curated alias (SCHOOL_NAME_ALIASES);
          3. mechanical "es"/"ms"/"hs" + bare-level suffix expansions;
          4. truncation-tolerant prefix compare within the district
             (unique-match guarded, >= 10 chars on the shorter side);
          5. token-suffix match (bronze tokens are the suffix of exactly
             one dim entry's tokens — catches APS-style dropped first-name
             prefixes like "Boyd Elementary School" for "William M. Boyd
             Elementary School").
        """
        name_lo = school_name.lower().strip()

        # (0) Year-aware — keyed on the truncation-EXPANDED district name.
        ya = self._year_aware.resolve_school_pair(
            year, self.canonical_district_name(district_name), school_name
        )
        if ya is not None:
            ya_dc, ya_sc = ya
            if ya_dc == district_code and (district_code, ya_sc) in (
                self._dims.school_pairs
            ):
                return ya_sc

        # (1) Exact match with a duplicate-name cardinality guard.
        in_district = [
            sc
            for dc, sc in self._dims.schools_by_name.get(name_lo, [])
            if dc == district_code
        ]
        if len(in_district) == 1:
            return in_district[0]
        if len(in_district) > 1:
            # Ambiguous within the district and year-aware didn't pick a
            # winner: refuse to guess. The row surfaces in the caller's
            # residual-unresolved guard unless a gap entry covers it.
            return None

        # (2) Curated alias to the dim's canonical name.
        aliased = SCHOOL_NAME_ALIASES.get(name_lo)
        if aliased is not None:
            code = self._dims.school_by_district_and_name.get((district_code, aliased))
            if code is not None:
                return code

        # (3) Mechanical suffix expansions common in GOSA sources.
        candidates: list[str] = []
        for abbrev, expansion in (
            (" es", " elementary school"),
            (" ms", " middle school"),
            (" hs", " high school"),
        ):
            if name_lo.endswith(abbrev):
                candidates.append(name_lo[: -len(abbrev)] + expansion)
        for bare in (" elementary", " middle", " high"):
            if name_lo.endswith(bare):
                candidates.append(name_lo + " school")
        for cand in candidates:
            code = self._dims.school_by_district_and_name.get((district_code, cand))
            if code is not None:
                return code

        # (4) Truncation-tolerant prefix compare within the district,
        # unique-match guarded in both directions (GOSA truncates
        # INSTN_NAME at ~52 chars in 2023-2024; the dim also stores some
        # truncated labels).
        if len(name_lo) >= 10:
            dim_longer = [
                sc
                for (dc, dim_name), sc in (
                    self._dims.school_by_district_and_name.items()
                )
                if dc == district_code
                and dim_name.startswith(name_lo)
                and dim_name != name_lo
            ]
            if len(dim_longer) == 1:
                return dim_longer[0]
            dim_shorter = [
                sc
                for (dc, dim_name), sc in (
                    self._dims.school_by_district_and_name.items()
                )
                if dc == district_code
                and len(dim_name) >= 10
                and name_lo.startswith(dim_name)
                and dim_name != name_lo
            ]
            if len(dim_shorter) == 1:
                return dim_shorter[0]

        # (5) Token-suffix match (>= 2 bronze tokens so a single word can
        # never swallow every school in the district).
        bronze_tokens = _tokenize(name_lo)
        if len(bronze_tokens) >= 2:
            suffix_matches = [
                sc
                for (dc, dim_name), sc in (
                    self._dims.school_by_district_and_name.items()
                )
                if dc == district_code
                for dim_tokens in (_tokenize(dim_name),)
                if len(dim_tokens) > len(bronze_tokens)
                and dim_tokens[-len(bronze_tokens) :] == bronze_tokens
            ]
            if len(suffix_matches) == 1:
                return suffix_matches[0]

        return None

    def school_first_fallback(
        self,
        district_name: str,
        school_name: str,
    ) -> tuple[str, str] | None:
        """Resolve by school name alone when the (district, school) path fails.

        Handles two bronze patterns: generic 2023 charter-container district
        labels (district unresolvable, but INSTN_NAME carries a real school
        name) and duplicate charter district names in the dim. Candidates
        whose district_code is missing from districts.parquet are rejected
        up front (the schools dim carries a few rows under orphan district
        codes — emitting one would FK-orphan the fact row).

        Returns (district_code, school_code) when exactly one FK-valid
        candidate remains — or, in a charter-context district, when the
        78-prefix / specific-7-digit narrowing isolates exactly one.
        """
        name_lo = school_name.lower().strip()
        aliased = SCHOOL_NAME_ALIASES.get(name_lo, name_lo)
        candidates = [
            (dc, sc)
            for dc, sc in self._dims.schools_by_name.get(aliased, [])
            if dc in self._dims.district_codes
        ]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Multiple districts carry this school name. Only a charter-context
        # bronze district label may disambiguate — never reassign a
        # standard-district row to another district on name uniqueness.
        district_lo = district_name.lower().strip()
        if district_lo.startswith(_CHARTER_CONTEXT_PREFIXES):
            charter = [(dc, sc) for dc, sc in candidates if dc.startswith("78")]
            if len(charter) == 1:
                return charter[0]
            # Prefer the specific 7-digit campus code over the 3-digit
            # umbrella container.
            specific = [(dc, sc) for dc, sc in charter if len(dc) >= 7]
            if len(specific) == 1:
                return specific[0]
        return None

    def rescue_placeholder_charter(
        self,
        district_name: str,
        school_name: str,
    ) -> tuple[str, str] | None:
        """Truncation-tolerant rescue for placeholder-charter rows.

        Applies ONLY when the bronze district label is the generic
        state-charter placeholder (see
        :func:`is_state_charter_placeholder_district`) — the 7-digit-only
        candidate filter below is what makes the wider bronze-prefix match
        safe in that context, so the rule must not be reused elsewhere.

        Candidate name forms: the (alias-normalized) bare bronze name plus
        every CHARTER_PREFIX_REMAP retarget. Each form is matched against
        the schools dim exactly AND as a strict prefix of a dim name
        (catching 52-char bronze truncations); hits are kept only when the
        district_code exists in districts.parquet AND is 7-digit. The
        3-digit umbrella codes (782/783/799) duplicate the specific 7-digit
        entries in the schools dim — binding to one would fragment a
        school's FK across district codes — and a same-named school in a
        standard 3-digit county district cannot legitimately host a
        state-charter row.

        Returns the (district_code, school_code) pair when exactly one
        remains across all forms; None otherwise (unresolvable placeholder
        rows are then dropped by the caller's placeholder filter — the
        right fix for a new case is a pin or gap entry, not a wider rule).
        """
        if not is_state_charter_placeholder_district(district_name):
            return None
        name_lo = school_name.lower().strip()
        name_lo = SCHOOL_NAME_ALIASES.get(name_lo, name_lo)

        forms: list[str] = [name_lo]
        for src_prefix, target_prefixes in CHARTER_PREFIX_REMAP:
            if not name_lo.startswith(src_prefix):
                continue
            suffix = name_lo[len(src_prefix) :].strip()
            if suffix:
                forms.append(suffix)
                forms.extend(f"{target} {suffix}" for target in target_prefixes)
            break
        # De-dup while preserving order (a retarget can equal the bare name).
        forms = list(dict.fromkeys(forms))

        pairs: set[tuple[str, str]] = set()
        for form in forms:
            for dc, sc in self._dims.schools_by_name.get(form, []):
                if dc in self._dims.district_codes and len(dc) == 7:
                    pairs.add((dc, sc))
            # Strict-prefix mode (bronze truncation), minimum 10 chars so a
            # short form cannot prefix-match half the dim. dim-as-prefix-of-
            # bronze is deliberately NOT supported — too collision-prone in
            # charter context; such cases get explicit aliases instead.
            if len(form) >= 10:
                for dim_name, entries in self._dims.schools_by_name.items():
                    if dim_name == form or not dim_name.startswith(form):
                        continue
                    for dc, sc in entries:
                        if dc in self._dims.district_codes and len(dc) == 7:
                            pairs.add((dc, sc))
        if len(pairs) == 1:
            return next(iter(pairs))
        return None

    # --- full row chain -------------------------------------------------------

    def resolve_row(
        self,
        year: int,
        district_name: str,
        school_name: str,
        detail_level: str,
    ) -> tuple[str | None, str | None]:
        """The full resolution chain for one bronze row.

        Returns (district_code, school_code); either may be None. State
        rows resolve to (None, None) by construction. School-level rows
        get the school chain plus, when the primary path fails, the
        school-first fallback (allowed to override the district only when
        the district was unresolved or the bronze label is a charter
        container) and the placeholder-charter rescue (only when both
        codes are still missing under a placeholder district label).
        """
        if district_name == STATE_DISTRICT_SENTINEL:
            return None, None

        district_code = self.resolve_district(year, district_name)
        school_code: str | None = None

        if detail_level == "school":
            if district_code is not None:
                school_code = self.resolve_school(
                    year, district_name, school_name, district_code
                )
            if school_code is None:
                district_lo = district_name.lower().strip()
                # A resolved standard district must keep its rows: only an
                # unresolved district or a charter-container label may be
                # overridden by the name-only fallback (e.g. APS "Cleveland
                # Elementary School" must not migrate to Fayette's only
                # same-named school).
                may_override = district_code is None or district_lo.startswith(
                    _CHARTER_CONTEXT_PREFIXES
                )
                if may_override:
                    fallback = self.school_first_fallback(district_name, school_name)
                    if fallback is not None:
                        district_code, school_code = fallback
                if school_code is None and district_code is None:
                    rescued = self.rescue_placeholder_charter(
                        district_name, school_name
                    )
                    if rescued is not None:
                        district_code, school_code = rescued

        return district_code, school_code
