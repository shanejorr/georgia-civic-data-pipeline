"""Build the global demographics dimension table.

Produces data/gold/_dimensions/demographics.parquet from the canonical
demographic definitions in src/utils/demographics.py.

Usage:
    uv run python -m src.etl.build_demographics_dimension
"""

import logging
from pathlib import Path

import polars as pl

from src.utils.demographics import CANONICAL_DEMOGRAPHICS, DEMOGRAPHIC_CATEGORIES
from src.utils.dimension_contract_emitter import emit_demographics_contract

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/gold/_dimensions")
OUTPUT_FILE = OUTPUT_DIR / "demographics.parquet"

# Label overrides for canonical demographics whose natural human-readable
# label cannot be reproduced by snake_case → Title Case conversion (for
# example, when the natural label includes punctuation like a slash).
LABEL_OVERRIDES: dict[str, str] = {
    "asian_pacific_islander": "Asian/Pacific Islander",
    # IDEA disability categories whose natural label is not plain Title Case
    "blind_low_vision": "Blind/Low Vision",
    "deaf_blind": "Deaf-Blind",
    "emotional_behavioral_disorder": "Emotional/Behavioral Disorder",
    "hospital_homebound": "Hospital/Homebound",
    "speech_language_impairment": "Speech-Language Impairment",
}


def _derive_label(key: str) -> str:
    """Convert snake_case demographic key to a human-readable label.

    Examples: 'english_learners' -> 'English Learners',
              'grade_1' -> 'Grade 1'

    Keys whose natural label contains characters not produced by simple
    snake_case → Title Case conversion (e.g., a slash) can supply an
    override via LABEL_OVERRIDES.
    """
    if key in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[key]
    return key.replace("_", " ").title()


def build_demographics_dimension() -> pl.DataFrame:
    """Build the demographics dimension DataFrame from canonical definitions."""
    rows = []
    for key in sorted(CANONICAL_DEMOGRAPHICS):
        category = DEMOGRAPHIC_CATEGORIES.get(key)
        if category is None:
            logger.warning(
                f"Demographic '{key}' has no category in DEMOGRAPHIC_CATEGORIES — "
                f"assigning 'uncategorized'. Add it to demographics.py."
            )
            category = "uncategorized"

        rows.append(
            {
                "demographic": key,
                "demographic_label": _derive_label(key),
                "demographic_category": category,
            }
        )

    df = pl.DataFrame(rows).sort("demographic_category", "demographic")
    return df


class DimensionBuildError(RuntimeError):
    """Raised when the freshly built dimension fails its health assertions."""


def _assert_demographics_health(df: pl.DataFrame) -> None:
    """Hard gates: PK unique, full coverage of the canonical registry,
    no uncategorized keys."""
    dupes = df.filter(pl.col("demographic").is_duplicated())
    if dupes.height > 0:
        raise DimensionBuildError(
            f"demographics: duplicate keys: {dupes['demographic'].to_list()}"
        )
    built = set(df["demographic"].to_list())
    missing = sorted(CANONICAL_DEMOGRAPHICS - built)
    if missing:
        raise DimensionBuildError(
            f"demographics: canonical keys missing from the dimension: {missing}"
        )
    uncategorized = df.filter(pl.col("demographic_category") == "uncategorized")
    if uncategorized.height > 0:
        raise DimensionBuildError(
            "demographics: keys without a category (add to "
            f"DEMOGRAPHIC_CATEGORIES): {uncategorized['demographic'].to_list()}"
        )


def main() -> None:
    """Build and export the demographics dimension table."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    df = build_demographics_dimension()
    _assert_demographics_health(df)

    # Export to parquet
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUTPUT_FILE)

    logger.info(
        f"Wrote {df.height} demographics to {OUTPUT_FILE} "
        f"({df['demographic_category'].n_unique()} categories)"
    )

    # Emit the git-tracked ODCS contract for the global demographics dimension.
    # The demographic_category enum is derived from DEMOGRAPHIC_CATEGORIES, and
    # the schema 'semantics' custom property captures mutual-exclusivity rules.
    contract = emit_demographics_contract()
    logger.info(f"Emitted demographics dimension contract to {contract}")

    # Run the contract's own quality SQL against the parquet just written.
    from src.utils import contract_reader
    from src.utils.validators import check_contract_quality_sql

    result = check_contract_quality_sql(
        OUTPUT_FILE, contract_reader.load_contract(contract)
    )
    if result.status == "fail":
        raise DimensionBuildError(
            f"demographics: contract quality checks failed — "
            f"{result.details or [result.message]}"
        )
    logger.info(f"demographics.parquet: {result.message}")


if __name__ == "__main__":
    main()
