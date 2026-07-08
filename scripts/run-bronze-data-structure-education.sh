#!/usr/bin/env bash
# Run bronze-data-structure skill on all education topics in parallel batches of 5.
# Each invocation gets a fresh context window via `claude -p`.
#
# Usage: caffeinate -i bash scripts/run-bronze-data-structure-education.sh
#
# Options:
#   --skip-existing   Skip topics that already have a bronze-data-structure.md

set -euo pipefail

SKIP_EXISTING=false
for arg in "$@"; do
  case "$arg" in
    --skip-existing) SKIP_EXISTING=true ;;
  esac
done

BATCH_SIZE=5
BRONZE_DIR="data/bronze/education"
LOG_DIR="logs/bronze-data-structure"
mkdir -p "$LOG_DIR"

# Build the list of topics: "sub_topic topic"
TOPICS=(
  # georgiainsights
  "georgiainsights attendance_dashboard"
  "georgiainsights ccrpi_climate_star_rating"
  "georgiainsights ccrpi_content_mastery"
  "georgiainsights ccrpi_graduation_rate"
  "georgiainsights ccrpi_progress"
  "georgiainsights ccrpi_readiness"
  "georgiainsights ccrpi_scoring_by_component"
  "georgiainsights enrollment_march_gender_race_ethnicity"
  "georgiainsights enrollment_by_grade"
  "georgiainsights enrollment_october_disability"
  "georgiainsights enrollment_october_gender_race_ethnicity"
  "georgiainsights free_reduced_lunch"
  "georgiainsights georgia_milestones_end_of_course"
  "georgiainsights georgia_milestones_end_of_grade"
  "georgiainsights georgia_student_growth_model_end_of_course"
  "georgiainsights georgia_student_growth_model_end_of_grade"
  "georgiainsights pathway_graduation_rate"
  "georgiainsights wida_access"
  # gosa
  "gosa act_scores"
  "gosa advanced_placement_scores"
  "gosa attendance"
  "gosa certified_personnel"
  "gosa direct_certification_district"
  "gosa direct_certification_school"
  "gosa dropout_rate_7_12"
  "gosa dropout_rate_9_12"
  "gosa educator_qualifications_emergency_and_provisional_credentials"
  "gosa educator_qualifications_inexperienced_teachers_leaders"
  "gosa educator_qualifications_out_of_field_teachers"
  "gosa english_learner_exit_rate"
  "gosa enrollment_by_grade_level"
  "gosa enrollment_by_subgroup_programs"
  "gosa financial_efficiency_star_rating"
  "gosa georgia_alternate_assessment"
  "gosa georgia_milestones_end_of_course_by_grade_level"
  "gosa georgia_milestones_end_of_course_lexile"
  "gosa georgia_milestones_end_of_grade_by_grade_level"
  "gosa georgia_milestones_end_of_grade_lexile"
  "gosa graduation_rate_4_year_cohort"
  "gosa high_school_completers"
  "gosa hope_eligible_graduates"
  "gosa postsecondary_c11"
  "gosa postsecondary_c12"
  "gosa retained_students"
  "gosa revenues_and_expenditures"
  "gosa salaries_and_benefits"
  "gosa sat_scores_highest"
  "gosa sat_scores_recent"
  "gosa student_mobility_rate"
)

TOTAL=${#TOPICS[@]}
echo "=== Bronze Data Structure: Education ==="
echo "Total topics: $TOTAL | Batch size: $BATCH_SIZE | Skip existing: $SKIP_EXISTING"
echo ""

completed=0
skipped=0
failed=0
batch_num=0

for ((i = 0; i < TOTAL; i += BATCH_SIZE)); do
  batch_num=$((batch_num + 1))
  batch_end=$((i + BATCH_SIZE))
  if ((batch_end > TOTAL)); then batch_end=$TOTAL; fi

  echo "--- Batch $batch_num: topics $((i + 1))–$batch_end of $TOTAL ---"

  pids=()
  batch_topics=()

  for ((j = i; j < batch_end; j++)); do
    entry="${TOPICS[$j]}"
    sub_topic="${entry%% *}"
    topic="${entry#* }"

    # Skip if bronze-data-structure.md already exists
    if $SKIP_EXISTING && [[ -f "$BRONZE_DIR/$sub_topic/$topic/bronze-data-structure.md" ]]; then
      echo "  SKIP: education $sub_topic $topic (already exists)"
      skipped=$((skipped + 1))
      continue
    fi

    log_file="$LOG_DIR/${sub_topic}__${topic}.log"
    echo "  START: education $sub_topic $topic"

    claude -p "/bronze-data-structure education $sub_topic $topic" \
      --verbose \
      > "$log_file" 2>&1 &

    pids+=($!)
    batch_topics+=("$sub_topic $topic")
  done

  # Wait for all processes in this batch
  for idx in "${!pids[@]}"; do
    pid="${pids[$idx]}"
    entry="${batch_topics[$idx]}"
    if wait "$pid"; then
      echo "  DONE: education $entry"
      completed=$((completed + 1))
    else
      echo "  FAIL: education $entry (see $LOG_DIR/${entry// /__}.log)"
      failed=$((failed + 1))
    fi
  done

  echo ""
done

echo "=== Summary ==="
echo "Completed: $completed | Skipped: $skipped | Failed: $failed | Total: $TOTAL"
