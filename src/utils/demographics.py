"""Demographic name normalization utilities.

This module provides standardized demographic categories and mappings
from various source formats to canonical names used across all datasets.

Usage:
    Use `normalize_demographic_column()` as the single canonical path for
    raw → canonical demographic mapping in every transform.py:

    ```python
    from src.utils.demographics import normalize_demographic_column

    df = df.with_columns(
        normalize_demographic_column("demographic_raw").alias("demographic")
    )
    ```

Adding demographics:
    1. New spelling of an existing demographic (e.g., "GIFTED" -> "gifted"):
       Add one entry to DEMOGRAPHIC_ALIASES. No other changes needed.

    2. New canonical demographic (e.g., "gifted" doesn't exist yet):
       a. Add alias(es) to DEMOGRAPHIC_ALIASES mapping to the new canonical key.
       b. Add the canonical key to DEMOGRAPHIC_CATEGORIES with its category.
       c. Rebuild: uv run python -m src.etl.build_demographics_dimension
"""

import polars as pl

# Sentinel value written to the demographic column when a raw value does not
# match any alias. Downstream validators (see validators.check_demographics)
# flag any rows that end up with this value — add the missing mapping to
# DEMOGRAPHIC_ALIASES rather than filtering those rows out.
SENTINEL_UNMATCHED_DEMOGRAPHIC: str = "99999999"


# Mapping from source variations to canonical names.
# Keys are normalized to uppercase for case-insensitive matching.
DEMOGRAPHIC_ALIASES: dict[str, str] = {
    # All students
    "ALL": "all",
    "ALL STUDENTS": "all",
    "TOTAL": "all",
    "TOTAL ALL": "all",  # C11 Report XLSX header
    "ALL RACES": "all",  # OASIS (GA DPH) race-breakdown total row
    "ALL SEXES": "all",  # OASIS (GA DPH) sex-breakdown total row
    # Asian
    "ASIAN": "asian",
    "ASIANS": "asian",  # Plural form in GOSA column names (Number_of_Asians)
    "ASIAN-AMERICAN": "asian",
    # Combined legacy aggregate (pre-1997 OMB taxonomy: Asian + NHPI rolled
    # into one bucket). Maps to its own canonical key so sources publishing
    # the combined form do not silently lose the Pacific Islander signal.
    "ASIAN-AMERICAN/PACIFIC ISLANDER": "asian_pacific_islander",
    "ASIAN/PACIFIC ISLANDER": "asian_pacific_islander",
    # Georgia Insights variant: spaces around the slash
    "ASIAN / PACIFIC ISLANDER": "asian_pacific_islander",
    "ASIAN AND PACIFIC ISLANDER": "asian_pacific_islander",
    "ASIAN-PACIFIC ISLANDER": "asian_pacific_islander",
    # Black
    "BLACK": "black",
    "BLACKS": "black",  # Plural form in GOSA column names (Number_of_Blacks)
    "AFRICAN-AMERICAN": "black",
    "AFRICAN-AMERICAN/BLACK": "black",
    "AFRICAN AMERICAN": "black",
    "BLACK OR AFRICAN AMERICAN": "black",
    "BLACK OR AFRICAN-AMERICAN": "black",  # OASIS (GA DPH) hyphenated variant
    # Hispanic/Latino
    "HISPANIC": "hispanic",
    "HISPANICS": "hispanic",  # Plural form in GOSA column names (Number_of_Hispanics)
    "HISPANI": "hispanic",  # truncated in some sources
    "LATINO": "hispanic",
    "HISPANIC/LATINO": "hispanic",
    "MEXICAN-AMERICAN": "hispanic",
    "MEXICAN-AMERICAN/CHICANO/LATINO": "hispanic",
    "MEXICAN-AMIERICAN/CHICANO/LATINO": "hispanic",  # typo in source
    "PUERTO RICAN/CUBAN/OTHER HISPANIC": "hispanic",
    # White
    "WHITE": "white",
    "WHITES": "white",  # Plural form in GOSA column names (Number_of_Whites)
    "CAUCASIAN": "white",
    "CAUCASIAN-AMERICAN": "white",
    "CAUCASIAN-AMERICAN/WHITE": "white",
    # Multiracial
    "MULTI": "multiracial",
    "MULTIRACIAL": "multiracial",
    "MULTIRACIALS": "multiracial",  # Plural form in GOSA column names
    "MULTI-RACIAL": "multiracial",
    "TWO OR MORE RACES": "multiracial",
    "TWO OR MORE": "multiracial",
    "TWO OR MORE RACE(S)": "multiracial",  # C11 Report XLSX header
    "TWOORMORE": "multiracial",  # C11 Report CSV prefix
    # Native American
    "INDIAN": "native_american",
    "INDIANS": "native_american",  # Plural form
    "AMERICAN INDIAN": "native_american",
    "AMERICAN_INDIAN": "native_american",  # Underscore variant from column name norm
    "AMERICAN_INDIANS": "native_american",  # Plural with underscore
    "NATIVE AMERICAN": "native_american",
    "NATIVE": "native_american",  # C11 Report CSV prefix
    "AMERICAN INDIAN/ALASKAN NATIVE": "native_american",
    "AMERICAN INDIAN / ALASKAN NATIVE": "native_american",  # spaces around slash
    "AMERICAN INDIAN/ALASKA NATIVE": "native_american",
    "AMERICAN INDIAN/ALASKAN": "native_american",
    "NATIVE AMER/ALASKAN NATIVE": "native_american",  # Attendance data variant
    # HS Completers variant (space before slash)
    "NATIVE AMERICAN/ ALASKAN NATIVE": "native_american",
    "AMERICAN INDIAN OR ALASKAN NATIVE": "native_american",
    "AMERICAN INDIAN OR ALASKA NATIVE": "native_american",  # OASIS (GA DPH)
    "AMIND": "native_american",  # Juvenile Justice Clearinghouse Race Value code
    "NATAMER": "native_american",  # Juvenile Justice Clearinghouse Raw Data 2 code
    # Pacific Islander
    "PACIFIC ISLANDER": "pacific_islander",
    "PACIFIC": "pacific_islander",  # C11 Report CSV prefix
    "NATIVE HAWAIIAN": "pacific_islander",
    "NATIVE HAWAIIAN/PACIFIC ISLANDER": "pacific_islander",
    "HAWAIIAN/PACIFIC ISLANDER": "pacific_islander",
    "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER": "pacific_islander",
    # Gender
    "MALE": "male",
    "MALES": "male",  # Plural form in GOSA column names (Number_of_Males)
    "FEMALE": "female",
    "FEMALES": "female",  # Plural form in GOSA column names (Number_of_Females)
    # Economic status
    "ED": "economically_disadvantaged",
    "ECONOMICALLY DISADVANTAGED": "economically_disadvantaged",
    "FREE/REDUCED LUNCH": "economically_disadvantaged",
    "FREE REDUCED LUNCH": "economically_disadvantaged",  # C11 Report XLSX header
    "FRL": "economically_disadvantaged",
    "LOW INCOME": "economically_disadvantaged",
    # Students with disabilities
    "SWD": "students_with_disabilities",
    "STUDENTS WITH DISABILITIES": "students_with_disabilities",
    "STUDENTS WITH DISABILITY": "students_with_disabilities",
    "DISABILITY": "students_with_disabilities",  # C11 Report XLSX header
    "SPECIAL EDUCATION": "students_with_disabilities",
    "SPED": "students_with_disabilities",
    "DISABLED": "students_with_disabilities",
    # English learners
    "EL": "english_learners",
    "LEP": "english_learners",
    "ENGLISH LEARNERS": "english_learners",
    "ENGLISH LEARNER": "english_learners",
    "LIMITED ENGLISH PROFICIENT": "english_learners",
    "LIMITED ENGLISH": "english_learners",
    "ESOL": "english_learners",
    # Not English learners (inverse category)
    "NOT_EL": "not_english_learners",
    "NOT EL": "not_english_learners",
    "NOT LIMITED ENGLISH PROFICIENT": "not_english_learners",
    "NOT LIMITED ENGLISH": "not_english_learners",
    # Migrant
    "MIGRANT": "migrant",
    "MIGRANT STUDENTS": "migrant",
    # Not migrant (inverse category)
    "NOT_MIGRANT": "not_migrant",
    "NOT MIGRANT": "not_migrant",
    "NON-MIGRANT": "not_migrant",
    "NON MIGRANT": "not_migrant",
    # Homeless
    "HOMELESS": "homeless",
    # Foster care
    "FOSTER CARE": "foster_care",
    "FOSTER": "foster_care",
    # Military connected. Federal definitions distinguish three populations:
    # - "Military Connected" (broad): students with any DoD-connected family
    #   member (active duty, reserves, National Guard, retired, etc.).
    # - "Active Duty": dependents of currently-serving active-duty members
    #   (a SUBSET of Military Connected — not disjoint).
    # - Plain "Military": kept for sources that publish a single combined
    #   bucket without distinguishing the two. Do NOT alias "Military
    #   Connected" or "Active Duty" here — that double-counts.
    "MILITARY": "military",
    "MILITARY CONNECTED": "military_connected",
    "MILITARY CONNECTED YOUTH": "military_connected",
    "MILITARY FAMILY": "military_connected",
    "ACTIVE DUTY": "active_duty",
    # Inverse/complement categories (used in attendance data)
    # These represent students NOT in a special category
    "NOT_SWD": "students_without_disabilities",
    "NOT SWD": "students_without_disabilities",
    "STUDENTS WITHOUT DISABILITIES": "students_without_disabilities",
    "STUDENTS WITHOUT DISABILITY": "students_without_disabilities",
    "NOT_ED": "not_economically_disadvantaged",
    "NOT ED": "not_economically_disadvantaged",
    "NOT ECONOMICALLY DISADVANTAGED": "not_economically_disadvantaged",
    # Truncated form in GOSA graduation rate data
    "NOT ECONOMICALLY DISADV": "not_economically_disadvantaged",
    # Other/Unknown categories (used in SAT/ACT data)
    "OTHER": "other",
    "OTHER RACE": "other",
    "O": "other",  # SAT data column suffix for "Other"
    "RACE_UNKNOWN": "race_unknown",
    "RACE UNKNOWN": "race_unknown",
    "UNKNOWN": "race_unknown",
    "UNKNOWN RACE": "race_unknown",
    "R": "race_unknown",  # SAT data column suffix for "Race Unknown"
    "REFUSED": "race_unknown",
    "NOT REPORTED": "race_unknown",
    # Grade levels (from Georgia Insights attendance dashboard + FTE enrollment)
    "GRADE PK": "pre_kindergarten",  # Georgia Insights FTE: "Grade PK" column
    "PRE KINDERGARTEN": "pre_kindergarten",
    "PRE-KINDERGARTEN": "pre_kindergarten",
    "PREK": "pre_kindergarten",
    "PRE-K": "pre_kindergarten",
    "GRADE KK": "kindergarten",  # Georgia Insights FTE: "Grade KK" column
    "KINDERGARTEN": "kindergarten",
    "GRADE 1": "grade_1",
    "GRADE 2": "grade_2",
    "GRADE 3": "grade_3",
    "GRADE 4": "grade_4",
    "GRADE 5": "grade_5",
    "GRADE 6": "grade_6",
    "GRADE 7": "grade_7",
    "GRADE 8": "grade_8",
    "GRADE 9": "grade_9",
    "GRADE 10": "grade_10",
    "GRADE 11": "grade_11",
    "GRADE 12": "grade_12",
    # Zero-padded grade labels (Georgia Insights FTE: "Grade 01" ... "Grade 09")
    "GRADE 01": "grade_1",
    "GRADE 02": "grade_2",
    "GRADE 03": "grade_3",
    "GRADE 04": "grade_4",
    "GRADE 05": "grade_5",
    "GRADE 06": "grade_6",
    "GRADE 07": "grade_7",
    "GRADE 08": "grade_8",
    "GRADE 09": "grade_9",
    # Singular forms (Georgia Insights uses singular "Student")
    "STUDENT WITH DISABILITIES": "students_with_disabilities",
    "STUDENT WITHOUT DISABILITIES": "students_without_disabilities",
    # IDEA disability categories (special-education enrollment by disability
    # type — the GaDOE/IDEA primary-exceptionality axis). Identity aliases on
    # the canonical snake value so the categories register in the demographics
    # dimension; the source codes (AUT, SLD, ...) are mapped to these values in
    # the enrollment_october_disability transform.
    "AUTISM": "autism",
    "BLIND_LOW_VISION": "blind_low_vision",
    "DEAF": "deaf",
    "DEAF_BLIND": "deaf_blind",
    "EMOTIONAL_BEHAVIORAL_DISORDER": "emotional_behavioral_disorder",
    "HOSPITAL_HOMEBOUND": "hospital_homebound",
    "MILD_INTELLECTUAL_DISABILITY": "mild_intellectual_disability",
    "MODERATE_INTELLECTUAL_DISABILITY": "moderate_intellectual_disability",
    "OTHER_HEALTH_IMPAIRMENT": "other_health_impairment",
    "ORTHOPEDIC_IMPAIRMENT": "orthopedic_impairment",
    "PROFOUND_INTELLECTUAL_DISABILITY": "profound_intellectual_disability",
    "SIGNIFICANT_DEVELOPMENTAL_DELAY": "significant_developmental_delay",
    "SPEECH_LANGUAGE_IMPAIRMENT": "speech_language_impairment",
    "SEVERE_INTELLECTUAL_DISABILITY": "severe_intellectual_disability",
    "SPECIFIC_LEARNING_DISABILITY": "specific_learning_disability",
    "TRAUMATIC_BRAIN_INJURY": "traumatic_brain_injury",
    "VISUAL_IMPAIRMENT": "visual_impairment",
}

# Canonical demographic names derived from alias values
CANONICAL_DEMOGRAPHICS: set[str] = set(DEMOGRAPHIC_ALIASES.values())

# Category classification for each canonical demographic.
# Used by build_demographics_dimension.py to produce the demographics dimension table.
# When adding a new canonical demographic via DEMOGRAPHIC_ALIASES,
# add its category here.
DEMOGRAPHIC_CATEGORIES: dict[str, str] = {
    # Aggregate
    "all": "aggregate",
    # Race/ethnicity
    "asian": "race",
    "asian_pacific_islander": "race",
    "black": "race",
    "hispanic": "race",
    "white": "race",
    "multiracial": "race",
    "native_american": "race",
    "pacific_islander": "race",
    "other": "race",
    "race_unknown": "race",
    # Gender
    "male": "gender",
    "female": "gender",
    # Economic status
    "economically_disadvantaged": "economic_status",
    "not_economically_disadvantaged": "economic_status",
    # Special populations
    "students_with_disabilities": "sped",
    "students_without_disabilities": "sped",
    "english_learners": "esol",
    "not_english_learners": "esol",
    "migrant": "migrant_status",
    "not_migrant": "migrant_status",
    "homeless": "homeless_status",
    "foster_care": "foster_care",
    "military": "military",
    "military_connected": "military",
    "active_duty": "military",
    # Grade levels
    "pre_kindergarten": "grade",
    "kindergarten": "grade",
    "grade_1": "grade",
    "grade_2": "grade",
    "grade_3": "grade",
    "grade_4": "grade",
    "grade_5": "grade",
    "grade_6": "grade",
    "grade_7": "grade",
    "grade_8": "grade",
    "grade_9": "grade",
    "grade_10": "grade",
    "grade_11": "grade",
    "grade_12": "grade",
    # IDEA disability categories (primary exceptionality)
    "autism": "disability",
    "blind_low_vision": "disability",
    "deaf": "disability",
    "deaf_blind": "disability",
    "emotional_behavioral_disorder": "disability",
    "hospital_homebound": "disability",
    "mild_intellectual_disability": "disability",
    "moderate_intellectual_disability": "disability",
    "other_health_impairment": "disability",
    "orthopedic_impairment": "disability",
    "profound_intellectual_disability": "disability",
    "significant_developmental_delay": "disability",
    "speech_language_impairment": "disability",
    "severe_intellectual_disability": "disability",
    "specific_learning_disability": "disability",
    "traumatic_brain_injury": "disability",
    "visual_impairment": "disability",
}


def normalize_demographic_column(col: str | pl.Expr) -> pl.Expr:
    """Normalize a raw demographic column to canonical values.

    Single canonical path used by every transform.py. Casts to string, strips
    whitespace, uppercases, then maps via DEMOGRAPHIC_ALIASES. Unmatched values
    become SENTINEL_UNMATCHED_DEMOGRAPHIC so the validator can flag them.

    NULL values pass through as NULL (per data-cleaning-standards §5).

    Args:
        col: Column name (str) or Polars expression producing the raw values.

    Returns:
        Polars expression producing the canonical demographic string.

    Example:
        df = df.with_columns(
            normalize_demographic_column("demographic_raw").alias("demographic")
        )
    """
    expr = pl.col(col) if isinstance(col, str) else col
    normalized = (
        expr.cast(pl.Utf8)
        .str.strip_chars()
        .str.to_uppercase()
        .replace_strict(DEMOGRAPHIC_ALIASES, default=SENTINEL_UNMATCHED_DEMOGRAPHIC)
    )
    # Preserve NULLs: replace_strict(default=...) would overwrite them with
    # the sentinel, but standards require NULL-in → NULL-out.
    return pl.when(expr.is_null()).then(None).otherwise(normalized)
