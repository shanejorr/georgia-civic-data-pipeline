# GOSA Education Gold Data Topics

*Data source: https://download.gosa.ga.gov/*

This document provides an overview of all processed education data topics from the Governor's Office of Student Achievement (GOSA) available in the gold data layer.

## Summary

- **Total Topics**: 30
- **Data Source**: Governor's Office of Student Achievement (GOSA)
- **Location**: `data/gold/education/`

---

## Topics

### ACT Scores

- **Folder**: `act_scores`
- **Description**: ACT test scores for Georgia schools, districts, and state. Includes scores by test component (Composite, English, Math, Reading, Science) and demographic group.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Advanced Placement (AP) Scores

- **Folder**: `advanced_placement_scores`
- **Description**: Advanced Placement exam participation and performance data. Includes number of students tested, total tests taken, and tests scoring 3 or higher by AP subject.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Attendance

- **Folder**: `attendance`
- **Description**: Student attendance data including percentage of students in various absence categories (5 or fewer days, 6-15 days, over 15 days) and chronic absenteeism rates.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Certified Personnel

- **Folder**: `certified_personnel`
- **Description**: Certified personnel statistics including data on certificate levels, certification status, gender, employment status, position metrics (salaries, contract days), race/ethnicity, and years of experience by employee type (administrators, teachers, support personnel).
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### Direct Certification

- **Folder**: `direct_certification`
- **Description**: Direct certification percentages for Georgia public schools and districts in one fact table at three detail levels (school, district, state). Direct certification identifies students eligible for free meals based on participation in means-tested assistance programs (SNAP, TANF, foster care, Head Start, Medicaid from FY2024) without requiring a separate application. Merges the formerly separate `direct_certification_school` and `direct_certification_district` folders.
- **Years**: 2014-2024
- **Scopes**: schools, districts, states

### Dropout Rate (7-12)

- **Folder**: `dropout_rate_7_12`
- **Description**: Counts and rates of students who dropped out of grades 7-12 with demographic breakdowns.
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### Dropout Rate (9-12)

- **Folder**: `dropout_rate_9_12`
- **Description**: Counts and rates of students who dropped out of grades 9-12 with demographic breakdowns.
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### Educator Qualifications: Emergency and Provisional Credentials

- **Folder**: `educator_qualifications_emergency_and_provisional_credentials`
- **Description**: Educator qualifications data including emergency, provisional, and out-of-field credentials. Includes FTE counts and percentages by poverty level (total, high poverty, low poverty).
- **Years**: 2018-2024
- **Scopes**: districts, schools

### Educator Qualifications: Inexperienced Teachers and Leaders

- **Folder**: `educator_qualifications_inexperienced_teachers_leaders`
- **Description**: Inexperienced teacher and leader data. Inexperienced educators are those with less than 3 years of experience in their role. Includes FTE counts and percentages by personnel category and poverty level.
- **Years**: 2018-2024
- **Scopes**: districts, schools, states

### Educator Qualifications: Out-of-Field Teachers

- **Folder**: `educator_qualifications_out_of_field_teachers`
- **Description**: Out-of-field teacher data. Out-of-field teachers are those teaching without proper certification for their assigned subject area. Includes FTE counts and percentages by poverty level.
- **Years**: 2018-2024
- **Scopes**: districts, schools

### English Learners EL Exit Rate

- **Folder**: `english_learner_exit_rate`
- **Description**: Annual single-year English Learner exit rates at both the district and state level. Exit rate is calculated as the number of EL students who exited divided by the total number of EL students. The `detail_level` column distinguishes district rows from state rows.
- **Years**: 2019-2024
- **Scopes**: districts, states

### Enrollment by Grade Level

- **Folder**: `enrollment_by_grade_level`
- **Description**: Student enrollment counts by grade level and enrollment period. Includes fall and spring enrollment data for kindergarten through 12th grade.
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### Enrollment by Subgroup Programs

- **Folder**: `enrollment_by_subgroup_programs`
- **Description**: Student enrollment data by demographic subgroups and special programs. Includes counts and percentages for programs like gifted, special education, ESOL, early intervention, and vocational education.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Financial Efficiency Star Rating (FESR)

- **Folder**: `financial_efficiency_star_rating`
- **Description**: Financial Efficiency Star Rating for school districts and schools in one fact table. FESR measures how efficiently districts and schools use resources relative to student outcomes. Includes enrollment, expenditures, per-pupil expenditures, and CCRPI performance scores. Merges the formerly separate `financial_efficiency_star_rating_fesr_district` and `financial_efficiency_star_rating_fesr_school` folders.
- **Years**: 2014-2024
- **Scopes**: districts, schools

### Georgia Alternate Assessment (GAA)

- **Folder**: `georgia_alternate_assessment`
- **Description**: Assessment results for students with significant cognitive disabilities who cannot participate in the general assessment program. Includes performance level breakdowns by subject area and demographic group.
- **Years**: 2004-2007, 2011-2019, 2022-2024
- **Scopes**: districts, schools, states

### Georgia Milestones EOC Assessment by Grade

- **Folder**: `georgia_milestones_end_of_course_by_grade_level`
- **Description**: End-of-Course assessment results broken down by grade level, test subject, and demographic group.
- **Years**: 2015-2019, 2021-2024
- **Scopes**: districts, schools, states

### Georgia Milestones EOC Lexile Scores

- **Folder**: `georgia_milestones_end_of_course_lexile`
- **Description**: End-of-Course Lexile scores measuring reading ability. Includes 9th Grade Literature and American Literature assessments. Not disaggregated by demographics - all rows represent all students.
- **Years**: 2015-2019, 2021-2024
- **Scopes**: districts, schools, states

### Georgia Milestones EOG Assessment by Grade

- **Folder**: `georgia_milestones_end_of_grade_by_grade_level`
- **Description**: End-of-Grade assessment results by individual grade level (grades 3-8), test subject, and demographic group.
- **Years**: 2015-2019, 2021-2024
- **Scopes**: districts, schools, states

### Georgia Milestones EOG Lexile Scores

- **Folder**: `georgia_milestones_end_of_grade_lexile`
- **Description**: End-of-Grade Lexile scores measuring reading ability. Data includes all students (no demographic breakdowns).
- **Years**: 2015-2019, 2021-2024
- **Scopes**: districts, schools, states

### Graduation Rate (4-Year Cohort)

- **Folder**: `graduation_rate_4_year_cohort`
- **Description**: 4-year cohort graduation rates tracking the percentage of students who graduate within 4 years of entering 9th grade, broken down by demographic groups.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### High School Completers

- **Folder**: `high_school_completers`
- **Description**: High school completion and graduation credentials data including counts of students receiving various diplomas and certificates (general education, college prep, vocational, special education, certificates of attendance) by demographic group.
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### HOPE Eligible Graduates

- **Folder**: `hope_eligible_graduates`
- **Description**: HOPE (Helping Outstanding Pupils Educationally) scholarship eligibility data. HOPE provides merit-based scholarships for Georgia students. Eligibility determined by high school GPA requirements. Includes number of graduates, HOPE-eligible graduates, and eligibility rates.
- **Years**: 2004-2024
- **Scopes**: schools, states

### Postsecondary C11 Report

- **Folder**: `postsecondary_c11`
- **Description**: High school graduation and postsecondary enrollment data showing graduates who enrolled in a postsecondary institution within 16 months of graduation, by demographic group.
- **Years**: 2010-2022
- **Scopes**: districts, schools, states

### Postsecondary C12 Report

- **Folder**: `postsecondary_c12`
- **Description**: High school graduation, postsecondary enrollment, and credit completion data showing graduates who enrolled within 16 months and completed 24 credits within 2 years of enrollment, by demographic group.
- **Years**: 2008-2020
- **Scopes**: districts, schools, states

### Retained Students

- **Folder**: `retained_students`
- **Description**: Student retention (grade retention) data tracking students who were held back a grade level. Includes total enrollment, number retained, and percentage retained by demographic including race/ethnicity and gender.
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Revenues and Expenditures

- **Folder**: `revenues_and_expenditures`
- **Description**: Revenue and expenditure data including K-12 revenues (federal, local, state) and expenditures (instruction, administration, transportation, etc.). Values include both total dollars and dollars per FTE.
- **Years**: 2011-2024
- **Scopes**: districts, schools, states

### Salaries and Benefits

- **Folder**: `salaries_and_benefits`
- **Description**: Salary and benefit data broken down by personnel category (General Administration, School Administration, Teachers and Paraprofessionals). Includes total salaries, benefits, combined totals, and percentages relative to revenues and expenditures.
- **Years**: 2011-2024
- **Scopes**: districts, states

### SAT Scores (Highest)

- **Folder**: `sat_scores_highest`
- **Description**: SAT test scores representing highest scores achieved by students. Covers pre-2016 format (2400 scale with Critical Reading, Math, Writing) and post-2016 redesign (1600 scale with Evidence-Based Reading and Writing, Math).
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### SAT Scores (Recent)

- **Folder**: `sat_scores_recent`
- **Description**: SAT test scores representing most recent scores achieved by students. Covers pre-2016 format (2400 scale) and post-2016 redesign (1600 scale).
- **Years**: 2004-2024
- **Scopes**: districts, schools, states

### Student Mobility Rate

- **Folder**: `student_mobility_rate`
- **Description**: Student mobility rate data for school districts and schools in one fact table. Mobility rate measures the percentage of students who entered or withdrew from a district or school during the school year. High mobility rates may indicate demographic instability and impact educational outcomes. Merges the formerly separate `student_mobility_rates_district` and `student_mobility_rates_school` folders.
- **Years**: 2012-2024
- **Scopes**: districts, schools
