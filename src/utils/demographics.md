# Demographic Mappings

All bronze → gold demographic mappings used by `normalize_demographic_column()`.

**Mutual exclusivity within a category.** Within any single demographic category (race, gender, English-learner status, disability status, economic status), the canonical values are mutually exclusive — a student appears in exactly one row per category per natural-key group. The `all` value is the unfiltered total and is allowed to overlap with every other row. Notably, the race-category values `asian`, `pacific_islander`, and `asian_pacific_islander` are mutually exclusive: a topic that publishes the split rows (`asian` + `pacific_islander`) does NOT also publish the combined rollup (`asian_pacific_islander`), and vice versa. See `data-cleaning-standards` skill §5a–§5b for the rule and the canonical Asian / Pacific Islander example.

| `demo_bronze` | `demo_gold` | `demo_name` |
|---|---|---|
| ALL | all | Aggregate |
| ALL STUDENTS | all | Aggregate |
| TOTAL | all | Aggregate |
| TOTAL ALL | all | Aggregate |
| ASIAN | asian | Race/Ethnicity |
| ASIANS | asian | Race/Ethnicity |
| ASIAN-AMERICAN | asian | Race/Ethnicity |
| ASIAN-AMERICAN/PACIFIC ISLANDER | asian_pacific_islander | Race/Ethnicity |
| ASIAN/PACIFIC ISLANDER | asian_pacific_islander | Race/Ethnicity |
| ASIAN / PACIFIC ISLANDER | asian_pacific_islander | Race/Ethnicity |
| ASIAN AND PACIFIC ISLANDER | asian_pacific_islander | Race/Ethnicity |
| ASIAN-PACIFIC ISLANDER | asian_pacific_islander | Race/Ethnicity |
| BLACK | black | Race/Ethnicity |
| BLACKS | black | Race/Ethnicity |
| AFRICAN-AMERICAN | black | Race/Ethnicity |
| AFRICAN-AMERICAN/BLACK | black | Race/Ethnicity |
| AFRICAN AMERICAN | black | Race/Ethnicity |
| BLACK OR AFRICAN AMERICAN | black | Race/Ethnicity |
| HISPANIC | hispanic | Race/Ethnicity |
| HISPANICS | hispanic | Race/Ethnicity |
| HISPANI | hispanic | Race/Ethnicity |
| LATINO | hispanic | Race/Ethnicity |
| HISPANIC/LATINO | hispanic | Race/Ethnicity |
| MEXICAN-AMERICAN | hispanic | Race/Ethnicity |
| MEXICAN-AMERICAN/CHICANO/LATINO | hispanic | Race/Ethnicity |
| MEXICAN-AMIERICAN/CHICANO/LATINO | hispanic | Race/Ethnicity |
| PUERTO RICAN/CUBAN/OTHER HISPANIC | hispanic | Race/Ethnicity |
| WHITE | white | Race/Ethnicity |
| WHITES | white | Race/Ethnicity |
| CAUCASIAN | white | Race/Ethnicity |
| CAUCASIAN-AMERICAN | white | Race/Ethnicity |
| CAUCASIAN-AMERICAN/WHITE | white | Race/Ethnicity |
| MULTI | multiracial | Race/Ethnicity |
| MULTIRACIAL | multiracial | Race/Ethnicity |
| MULTIRACIALS | multiracial | Race/Ethnicity |
| MULTI-RACIAL | multiracial | Race/Ethnicity |
| TWO OR MORE RACES | multiracial | Race/Ethnicity |
| TWO OR MORE | multiracial | Race/Ethnicity |
| TWO OR MORE RACE(S) | multiracial | Race/Ethnicity |
| TWOORMORE | multiracial | Race/Ethnicity |
| INDIAN | native_american | Race/Ethnicity |
| INDIANS | native_american | Race/Ethnicity |
| AMERICAN INDIAN | native_american | Race/Ethnicity |
| AMERICAN_INDIAN | native_american | Race/Ethnicity |
| AMERICAN_INDIANS | native_american | Race/Ethnicity |
| NATIVE AMERICAN | native_american | Race/Ethnicity |
| NATIVE | native_american | Race/Ethnicity |
| AMERICAN INDIAN/ALASKAN NATIVE | native_american | Race/Ethnicity |
| AMERICAN INDIAN / ALASKAN NATIVE | native_american | Race/Ethnicity |
| AMERICAN INDIAN/ALASKA NATIVE | native_american | Race/Ethnicity |
| AMERICAN INDIAN/ALASKAN | native_american | Race/Ethnicity |
| NATIVE AMER/ALASKAN NATIVE | native_american | Race/Ethnicity |
| NATIVE AMERICAN/ ALASKAN NATIVE | native_american | Race/Ethnicity |
| AMERICAN INDIAN OR ALASKAN NATIVE | native_american | Race/Ethnicity |
| PACIFIC ISLANDER | pacific_islander | Race/Ethnicity |
| PACIFIC | pacific_islander | Race/Ethnicity |
| NATIVE HAWAIIAN | pacific_islander | Race/Ethnicity |
| NATIVE HAWAIIAN/PACIFIC ISLANDER | pacific_islander | Race/Ethnicity |
| HAWAIIAN/PACIFIC ISLANDER | pacific_islander | Race/Ethnicity |
| NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER | pacific_islander | Race/Ethnicity |
| OTHER | other | Race/Ethnicity |
| OTHER RACE | other | Race/Ethnicity |
| O | other | Race/Ethnicity |
| RACE_UNKNOWN | race_unknown | Race/Ethnicity |
| RACE UNKNOWN | race_unknown | Race/Ethnicity |
| UNKNOWN | race_unknown | Race/Ethnicity |
| UNKNOWN RACE | race_unknown | Race/Ethnicity |
| R | race_unknown | Race/Ethnicity |
| REFUSED | race_unknown | Race/Ethnicity |
| NOT REPORTED | race_unknown | Race/Ethnicity |
| MALE | male | Gender |
| MALES | male | Gender |
| FEMALE | female | Gender |
| FEMALES | female | Gender |
| ED | economically_disadvantaged | Economic Status |
| ECONOMICALLY DISADVANTAGED | economically_disadvantaged | Economic Status |
| FREE/REDUCED LUNCH | economically_disadvantaged | Economic Status |
| FREE REDUCED LUNCH | economically_disadvantaged | Economic Status |
| FRL | economically_disadvantaged | Economic Status |
| LOW INCOME | economically_disadvantaged | Economic Status |
| NOT_ED | not_economically_disadvantaged | Economic Status |
| NOT ED | not_economically_disadvantaged | Economic Status |
| NOT ECONOMICALLY DISADVANTAGED | not_economically_disadvantaged | Economic Status |
| NOT ECONOMICALLY DISADV | not_economically_disadvantaged | Economic Status |
| SWD | students_with_disabilities | Disability |
| STUDENTS WITH DISABILITIES | students_with_disabilities | Disability |
| STUDENTS WITH DISABILITY | students_with_disabilities | Disability |
| STUDENT WITH DISABILITIES | students_with_disabilities | Disability |
| DISABILITY | students_with_disabilities | Disability |
| SPECIAL EDUCATION | students_with_disabilities | Disability |
| SPED | students_with_disabilities | Disability |
| DISABLED | students_with_disabilities | Disability |
| NOT_SWD | students_without_disabilities | Disability |
| NOT SWD | students_without_disabilities | Disability |
| STUDENTS WITHOUT DISABILITIES | students_without_disabilities | Disability |
| STUDENTS WITHOUT DISABILITY | students_without_disabilities | Disability |
| STUDENT WITHOUT DISABILITIES | students_without_disabilities | Disability |
| EL | english_learners | Esol |
| LEP | english_learners | Esol |
| ENGLISH LEARNERS | english_learners | Esol |
| ENGLISH LEARNER | english_learners | Esol |
| LIMITED ENGLISH PROFICIENT | english_learners | Esol |
| LIMITED ENGLISH | english_learners | Esol |
| ESOL | english_learners | Esol |
| NOT_EL | not_english_learners | Esol |
| NOT EL | not_english_learners | Esol |
| NOT LIMITED ENGLISH PROFICIENT | not_english_learners | Esol |
| NOT LIMITED ENGLISH | not_english_learners | Esol |
| MIGRANT | migrant | Migrant_status |
| MIGRANT STUDENTS | migrant | Migrant_status |
| NOT_MIGRANT | not_migrant | Migrant_status |
| NOT MIGRANT | not_migrant | Migrant_status |
| NON-MIGRANT | not_migrant | Migrant_status |
| NON MIGRANT | not_migrant | Migrant_status |
| HOMELESS | homeless | homeless |
| FOSTER CARE | foster_care | foster_care |
| FOSTER | foster_care | foster_care |
| MILITARY | military | military |
| MILITARY CONNECTED | military_connected | military |
| MILITARY CONNECTED YOUTH | military_connected | military |
| MILITARY FAMILY | military_connected | military |
| ACTIVE DUTY | active_duty | military |
| GRADE PK | pre_kindergarten | Grade Level |
| PRE KINDERGARTEN | pre_kindergarten | Grade Level |
| PRE-KINDERGARTEN | pre_kindergarten | Grade Level |
| PREK | pre_kindergarten | Grade Level |
| PRE-K | pre_kindergarten | Grade Level |
| GRADE KK | kindergarten | Grade Level |
| KINDERGARTEN | kindergarten | Grade Level |
| GRADE 1 | grade_1 | Grade Level |
| GRADE 01 | grade_1 | Grade Level |
| GRADE 2 | grade_2 | Grade Level |
| GRADE 02 | grade_2 | Grade Level |
| GRADE 3 | grade_3 | Grade Level |
| GRADE 03 | grade_3 | Grade Level |
| GRADE 4 | grade_4 | Grade Level |
| GRADE 04 | grade_4 | Grade Level |
| GRADE 5 | grade_5 | Grade Level |
| GRADE 05 | grade_5 | Grade Level |
| GRADE 6 | grade_6 | Grade Level |
| GRADE 06 | grade_6 | Grade Level |
| GRADE 7 | grade_7 | Grade Level |
| GRADE 07 | grade_7 | Grade Level |
| GRADE 8 | grade_8 | Grade Level |
| GRADE 08 | grade_8 | Grade Level |
| GRADE 9 | grade_9 | Grade Level |
| GRADE 09 | grade_9 | Grade Level |
| GRADE 10 | grade_10 | Grade Level |
| GRADE 11 | grade_11 | Grade Level |
| GRADE 12 | grade_12 | Grade Level |
