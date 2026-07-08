# georgia_milestones_end_of_course — Bronze Data Structure

## Overview

- Topic: georgia_milestones_end_of_course
- Source: georgiainsights
- Files: 72 files spanning Winter 2014 through Full-Year 2024-2025 (10 administrations worth of xls/xlsx/zip)
- Unreadable files: none (every .xls, .xlsx, and .zip opens with the xlrd / openpyxl / zipfile toolchain)
- Year representation: The administration and school year are encoded **only in the filename** (and repeated in each sheet's title row). There is no `year` column inside the tables. Naming patterns:
  - `Winter YYYY …` / `Winter-YYYY-…` / `Winter_YYYY_…` — mid-year winter administration, **data year = YYYY+1** (e.g., `Winter 2014 EOC State.xls` publishes results for school year 2014-2015).
  - `Spring YYYY …` / `Spring-YYYY-…` / `Spring_YYYY_…` — end-of-year spring administration, **data year = YYYY** (e.g., `Spring_2019_EOC-State_Level.xlsx` covers school year 2018-2019's spring results).
  - `Full Year YYYY …` / `Full_Year_YYYY-YYYY …` / `Full-Year-YYYY-YYYY-…` — combined Fall+Winter+Spring administration aggregated over a full school year. The YYYY in `Full_Year_2021_EOC-…` is the spring year (school year 2020-2021, sheet titles spell it out as "Full Year 2020-2021 (Fall, Winter, Spring)"). `Full_Year_2021-2022_EOC-…` and `Full-Year-2024-2025-EOC-…` use the explicit two-year range.
- Filename-to-data year offset: no year column exists in the tables, so parsing must be driven entirely by filename pattern. `Full-Year-YYYY1-YYYY2` → data year is the spring year YYYY2. `Winter YYYY` → data year = YYYY + 1 (school-year end). `Spring YYYY` → data year = YYYY. Three pre-2017 files (`Full_Year_2021_EOC-…`) embed the full range in the sheet title (`Full Year 2020-2021 (Fall, Winter, Spring) 2021`), i.e., spring year 2021.
- Detail levels: state (one row per content area in one file), system/district (one row per district per content area), school (one row per school per content area). Files are named accordingly (`…State_Level`, `…System_Level`, `…School_Level`).
- Percentage scale: 0–100 across every era for every percentage column (e.g., `% Beginning Learner = 25.789` for 25.8%). Also applies to the `Reading Status` Lexile split (`% Below Grade Level`, `% Grade Level or Above`) and to every `% SGP *` column. `Mean Scale Score` and `SGP Median` are absolute score values (roughly 400–650 and 1–99 respectively).
- Checksums generated: 2026-05-22

## Source Provenance

- **Source URL**: Georgia Insights (GaDOE) public data downloads — exact page URL not recorded at acquisition time
- **Retrieved**: unknown — predates provenance tracking
- **Method**: manual download (assumed; not recorded at acquisition time)

## File Checksums

Generated: 2026-05-22

| File | SHA-256 |
|------|---------|
| Full-Year-2023-2024-EOC-School-Level.xlsx | 9e7629bb2393682754fb45b098319b2c1f1fe3fb8e1dc47b24c485234dcc859b |
| Full-Year-2023-2024-EOC-State-Level.xlsx | d54aa695fadc6241d5a01782d82168e38adf0b083c7622fe3d4144a89e62989f |
| Full-Year-2023-2024-EOC-System-Level.xlsx | 9402233fe831d8e0594723d957ca0b26ca80158e2e6aa67da84aba58f9624630 |
| Full-Year-2024-2025-EOC-School-Level.xlsx | 5064d8c1b22efe3973391d997d25e4125bc53442e8f38757fa5043c831bede95 |
| Full-Year-2024-2025-EOC-State-Level.xlsx | f8e24cc67bfb311aa836dd0e8667e1b266692ba20b8f25c0120b0fcd40937201 |
| Full-Year-2024-2025-EOC-System-Level.xlsx | 80ca789144284a1757ec9e1f4497c29512efd2a84fa47699501a12bbf83fee1a |
| Full-Year_2023_EOC-School_Level.xlsx | c1ae6aaa64d78486e57a215456c3abde42a459160aa34ed542c54f072844118e |
| Full-Year_2023_EOC-State_Level.xlsx | 9530834eb4af95c965b6f9bb894a9118f8d7f72be55aa276cb956f339942fca4 |
| Full-Year_2023_EOC-System_Level.xlsx | 92a3b4b1ddc7107921dc5324fdbf2b36ff223ee5daf76a960da00342fe0a965b |
| Full_Year_2021-2022_EOC-School_Level.xlsx | 41fa6f7df04d7ba1d6e973b312d37f2c117d0d0dcb5c0bbf578005bb31b8672b |
| Full_Year_2021-2022_EOC-State_Level.xlsx | 8ecdd9b1307012ccc79cbd19f6837fc87b594dbb3e9dfe797a59f6201969e407 |
| Full_Year_2021-2022_EOC-System_Level.xlsx | 4a8670e74ffd7638c42a4bd5d52542fd3acd90c2ca567aca14a200efc59bfee5 |
| Full_Year_2021_EOC-School_Level.xlsx | 732644eacba151cc6c1c5c3ba9c909db081a3cd36ff6d9d776df7e1e2376c12b |
| Full_Year_2021_EOC-State_Level.xlsx | 662fd559ade25e9c8986d711f4b6a799820d3fc10b85a7eef6535eada0147d06 |
| Full_Year_2021_EOC-System_Level.xlsx | e1e8417193e45e3278a0a42676e3c935566da476a946e71c5952d3e8d83b4b3c |
| Spring 2015 EOC School.zip | 021394f7427bbbae95f41b91013173003577bc767feae129ada78e79a8e4fe07 |
| Spring 2015 EOC State - All Content Areas.xls | 3e3e739ca9ee0c2cc6ae4726d1812dfdbde346bd9c1868bcaa9fd13d9ad4316c |
| Spring 2015 EOC System.zip | 64fc84e9bc7788bb66261486764ea4068c36e69bcbbd13bbe13f16a60ee0a355 |
| Spring-2024-EOC-School-Level.xlsx | 69ed8282c2ad7afe45cc1bccde3dbbe713809d9751d1feb5111154c9c5188125 |
| Spring-2024-EOC-State-Level.xlsx | b144d8473eb053d49d32b5cea62fe064cc2ca7f72849a437bc98a487112773f9 |
| Spring-2024-EOC-System-Level.xlsx | 5dba778d80861555d36ae337a55f54f02e36e3b347604a663a5f38a9c0bea42e |
| Spring-2025-EOC-School-Level.xlsx | 4db2e9e7dba3b11b25d3d0d56fc35842b273861203aa44a2892349e1fccd3cab |
| Spring-2025-EOC-State-Level.xlsx | 571020fabfb702f470b7875fd3f12537dee52e9cf61a80d53f1adb2a1d231055 |
| Spring-2025-EOC-System-Level.xlsx | 1bf934c66a5db8fd6e00fa8fb28030c54de14294118f446064caa8eeecdaac68 |
| Spring_2016_EOC-School_Level.zip | 78aaf2e84b912f03616e47fd6db88355d12b1c62c01dd21606a023b94bbe438c |
| Spring_2016_EOC-State_Level.xlsx | 91f00f1828522f3ab1fe334d28f33eaf8e87ca305af0307346f3f771b652bf79 |
| Spring_2016_EOC-System_Level.zip | 95af58b555ca0b879d3cafd63a9361b563445d34b3982766a64b9055f73a7153 |
| Spring_2017_EOC-SchoolLevel.zip | a6781d1c87eefee04b12b2e4d7908a400f2f2d658b0a02c2db7898a44a92533c |
| Spring_2017_EOC-State_Level-All_Content_Areas.xlsx | 9423997c6282bb991fbcb31b5c1c4f20b1e0904ec732264a59178f0b76c8a7a3 |
| Spring_2017_EOC-System_Level.zip | 945a789349d7f26a2db695170fabf48bccf122b0e6d6172453a4c897911e3b50 |
| Spring_2018_EOC-State_Level.xlsx | ce55811b8b2b060e8845bc3c041d8707a968d52ced946ef19abf623e2192adad |
| Spring_2018_EOC_School.zip | f0802270d2c11be985981eac47f7ce67f85aff66f67503c54f61d2ab055dec50 |
| Spring_2018_EOC_System.zip | b4e5ff542284b4f44e79b1c3d06a32386d7942cc35a08b6b1ceee45e728f2cd3 |
| Spring_2019_EOC-School_Level.xlsx | 18325ccaecaae85e8c8cae578e20d8a04f97bd773ec80748c778738ef9532988 |
| Spring_2019_EOC-State_Level.xlsx | f18ca9efbd5b6a42731d8a8f6395f03294ce6642067f5ff3bf7a1233981a1b96 |
| Spring_2019_EOC-System_Level.xlsx | d1ec73b4550091c29ae3c04b1fee94c8b17438b660775fb34058da01a408e50e |
| Spring_2022_EOC-School_Level.xlsx | 127661700a8bad38969eecf06a9b7c4f1147318c71f4c4ab692ee6328f951516 |
| Spring_2022_EOC-State_Level.xlsx | 078b94f1e9020bcb3d21da7b4aaa62e393346cd63810fdbae030c516b9d7fd2e |
| Spring_2022_EOC-System_Level.xlsx | cb874206e4fe85b51d0cb42fbe89d7f6d831488dbfb488a22be9e5ebb9c21097 |
| Spring_2023_EOC-School_Level.xlsx | 6321395661072c6bb48d8a13d3b502bb4c287d6144812dfb7d4b506c7ad41937 |
| Spring_2023_EOC-State_Level.xlsx | 35ea9b3dd5646beebe9b02de4b42baecb5f133daa74972bc09239b072a7b2508 |
| Spring_2023_EOC-System_Level.xlsx | c83306bdd6a35daa01aab05a2b4dce3058510dae15a79be8f3f04859c0c52d53 |
| Winter 2014 EOC School.zip | 5c8d301d6df71afb242e35cc4fcc587a9031f53bff1aaa0850eee04fe771ec32 |
| Winter 2014 EOC State - All Content Areas.xls | 3523c4c3c725bbc4b2569b55d7f2cb41b4a8d80e33c1b44a1c28d1de94e7368b |
| Winter 2014 EOC System.zip | a11fbaa36809a9a48567d08230c9efb9e8bbbd256b83353fdd32a2a60fd81505 |
| Winter-2022-EOC-School-Level.xlsx | 8d6b56b4489531ac50a859b13c9007db4ab9a881d3c949b2a080ce5aa97e295e |
| Winter-2022-EOC-State-Level.xlsx | 6a6d6c0cf820bfc2ad212734b4c5b8335a30ec33891690acf4658054f39faa55 |
| Winter-2022-EOC-System-Level.xlsx | 200dd1374ec15a1769760e18e7572fc86fd23aa4bcb05a39b1ca15dc2b036eb7 |
| Winter-2023-EOC-School-Level.xlsx | 68c46507945eb99204a59068ccb910c35ab79a9d4a9b12a0856f37a09f72eaf1 |
| Winter-2023-EOC-State-Level.xlsx | 53365cd2b90c0faf8229e87705d5a160efd9e41dd989df19a9c191dc2a28e8b7 |
| Winter-2023-EOC-System-Level.xlsx | 3e752edebaccf1eb500619047c187fb99677c426b18b3f59190e61322cc3e72d |
| Winter-2024-EOC-School-Level.xlsx | 23c95b1531a24b3dc30310cca0ebce6aebb094ee0478503677663db8a5613cb8 |
| Winter-2024-EOC-State-Level.xlsx | eaf10ad3eaca4f4143fec3edd44eed3681a20b25076a621a2ff17b0b6f12135d |
| Winter-2024-EOC-System-Level.xlsx | 10c2641b9726abe0390a82b55a63e71453284055b97ad97b45b5723459539d0d |
| Winter_2015_EOC_School.zip | c712a30f309547b547a0442fdfd238a512abd371c8c0a7d133c946449a405b98 |
| Winter_2015_EOC_State_All-Content-Areas.xls | 782ee8121fae56a2d85122508619d37666f5330a4112b67edfd62c841b1e338a |
| Winter_2015_EOC_System.zip | f1e11e7b0b308a7c2e4affd1bf443816baa3f4cb522b8ef56d52a59031576716 |
| Winter_2016_EOC_School.zip | 16e4569a37d1b2816f6f524bf6a09c2d7ac5e723544a4fd0ccef254f7d9d7973 |
| Winter_2016_EOC_State-All_Content_Areas.xls | 759015caaf0b3ddd71c67b8024541fb6413cbb664310cfa2e748970145c568cd |
| Winter_2016_EOC_System.zip | 645e955fc894a6b2d27222739109ea81bd5219d811e631119a5445a53e52fa94 |
| Winter_2017_EOC-School_Level.xlsx | 8547efc550668bf24e9e90c9eb83997d86cf2988dbe8ae580080a9dd7deaafc2 |
| Winter_2017_EOC-State_Level.xlsx | 1eeeb9036b70c95878386249e1eb5374db3e7d8c7eb1f3ddb5dc303be4011707 |
| Winter_2017_EOC-System_Level.xlsx | 56aa59910d9bc8e01886808d70b7eea0a5fabaf4c9ca8737de088ce663cc666c |
| Winter_2018_EOC-School_Level.xlsx | 0559e80f475b03ad8abe617a2e0d1633d0e6f0f6352d16ce9129cd73cc1b6c5e |
| Winter_2018_EOC-State_Level.xlsx | b6549ef413d72d76019f8cbf48e0d5fb86eb2e9bbea45c5be7341445e4730ec3 |
| Winter_2018_EOC-System_Level.xlsx | 3b97f40260004e620c7185d3e1e43276479d96b9c692c79ae0ad82d85a6dd432 |
| Winter_2019_EOC-School_Level.xlsx | e116fe0979fbc07696a058255fa1ebfce31a47676beba54ea18a05b68ec72f36 |
| Winter_2019_EOC-State_Level.xlsx | fa7c6b671220b10b2497b8fd581e985b095df267b2904ecd8a4f297f6d0e094b |
| Winter_2019_EOC-System_Level.xlsx | d7f734a6b05a7d10d2b4a22177c1d26cd6978b1928282bfc08bdaa11ad2a9b8e |
| Winter_2021_EOC-School_Level.xlsx | f2f4c67bbfeb15257eee30fffc19989327456353aa376fd062f40baee9849ad8 |
| Winter_2021_EOC-State_Level.xlsx | ed671f3d890f5bc73d8d0cd2632658a7320782f293810cc9365d55943822b3e5 |
| Winter_2021_EOC-System_Level.xlsx | dde5129eae832dbb546265ea31f87a83d814cf4c9fa058f44258b8534c2f7e41 |

## Excel Sheet Structure

Layout varies dramatically across administrations — the transform has to detect file type, extract year + administration from filename, then dispatch to the right layout handler.

| Era | Files | Sheets | Layout notes |
|-----|-------|--------|--------------|
| **2014 Winter / 2015 Spring (xls-in-zip)** | `Winter 2014 EOC School.zip`, `Winter 2014 EOC System.zip`, `Spring 2015 EOC School.zip`, `Spring 2015 EOC System.zip` (4 total) | One `.xls` per content area inside the zip (`School - History.xls`, `System - Biology.xls`, etc.) | Each xls has ONE sheet named after the content area (e.g. `School - History`). Title in row 0, single-row header in row 1, data from row 2. Content area is **derived from the filename within the zip**, not a column. |
| **2014 Winter / 2015 Spring state-only (xls direct)** | `Winter 2014 EOC State - All Content Areas.xls`, `Spring 2015 EOC State - All Content Areas.xls` (2 total) | Single sheet (`State - All EOC` or `State`) | Title in row 0, header row 1, data rows 2+. Content area lives in a `Content Area` column; ten rows (one per subject). |
| **2015 Winter / 2016 Winter state (xls direct)** | `Winter_2015_EOC_State_All-Content-Areas.xls`, `Winter_2016_EOC_State-All_Content_Areas.xls` (2 total) | Single sheet (`State` or `State - All Content Areas`) | Same single-row-header layout as above. Winter 2016 has a blank row 2, so data starts at row 3. |
| **2015 Winter / 2016 Winter + 2016 Spring (xls/xlsx in zip)** | `Winter_2015_EOC_School.zip`, `Winter_2015_EOC_System.zip`, `Winter_2016_EOC_School.zip`, `Winter_2016_EOC_System.zip`, `Spring_2016_EOC-School_Level.zip`, `Spring_2016_EOC-System_Level.zip` (6 total) | One workbook per content area inside the zip | Mix of `.xls` (2015/2016 Winter) and `.xlsx` (2016 Spring). **Winter 2016 Schools and 2016 Spring School files have a blank row 2** so data starts at row 3. 2016 Spring School files use a single `Key` column that concatenates system_code (3 digits) + school_code (4 digits zero-padded) into a 7-digit int (e.g., `6010103`). |
| **2017 Spring (xlsx in zip)** | `Spring_2017_EOC-SchoolLevel.zip`, `Spring_2017_EOC-System_Level.zip` (2 total) | One `.xlsx` per content area inside the zip, each with ONE sheet | Single-row header (no sub-header). School Code is a **bare integer** (e.g., `103`), not the zero-padded `"0103"` used from Winter 2017 onward. A trailing unnamed `None` column may appear at index 12 — strip it. |
| **2017 Spring state-only (xlsx direct)** | `Spring_2017_EOC-State_Level-All_Content_Areas.xlsx` (1 total) | Single sheet `State - All Content Areas` | Same 9-column single-row-header layout as Spring 2016 state. |
| **2017 Winter — 2020 Spring (xlsx direct)** | `Winter_2017_…`, `Winter_2018_…`, `Spring_2018_…`, `Winter_2019_…`, `Spring_2019_…` (State/System/School × 5 winter/spring = 15 total; **plus** `Spring_2018_EOC_School.zip` and `Spring_2018_EOC_System.zip` which wrap the xlsx) | Ten per-content-area sheets (`State - 9th Grade Literature`, `State - American Literature`, … `State - Economics`) | **Two-row header layout begins here.** Row 0 = title, row 1 = main header, row 2 = sub-header for Reading Status (literature sheets only), data from row 3. Reading Status appears in both Lit sheets (9th Grade & American), giving them 2 extra columns (`% Below Grade Level (Lexile < 1050L)` and `% Grade Level or Above (Lexile ≥ 1050L)`). 9th Grade Lit uses Lexile **1050L**; American Lit uses Lexile **1050L** too in 2018-2019 (it moves to 1185L starting 2021). Non-literature sheets keep the simpler single-row header shape. |
| **2021 Winter (xlsx direct)** | `Winter_2021_…-School/System/State_Level.xlsx` (3 total) | Five sheets only: American Literature, Coordinate Algebra, Algebra I, Biology, US History | 9th Grade Literature, Analytic Geometry, Geometry, Physical Science, Economics all **disappear** here. Same two-row-header layout as Era 4, but only American Lit has Reading Status (at Lexile 1185L threshold for the first time — the college/career Lexile cutoff bumped up). |
| **Full Year 2020-2021 (xlsx direct)** | `Full_Year_2021_EOC-School/System/State_Level.xlsx` (3 total) | Six sheets: American Literature, Coordinate Algebra, Algebra I, Biology, **Phys Science Gr8** (school/system) / **Physical Science Gr8** (state), US History | Adds a new column `Percent of Enrolled Students Tested` (filenames use inconsistent sheet names for Phys Science — `Phys Science Gr8` vs `Physical Science Gr8`; handle both). |
| **Spring 2022 — Winter 2023 (xlsx direct)** | `Spring_2022_…`, `Winter-2022-…`, `Spring_2023_…`, `Winter-2023-…`, `Full_Year_2021-2022_…`, `Full-Year_2023_…` (18 total) | Five sheets (American Lit, Coordinate Algebra, Algebra I, Biology, US History). Winter-2023 only has **three** sheets (drops Coordinate Algebra and Algebra I). | Two-row header layout. American Lit has Reading Status at Lexile 1185L. No SGP columns yet. No `Percent of Enrolled Students Tested` column. |
| **Spring 2024 / Winter 2024 / Full-Year 2023-2024 (xlsx direct)** | `Spring-2024-…`, `Winter-2024-…`, `Full-Year-2023-2024-…` (9 total) | Four sheets: American Literature, **Algebra CC**, Biology, US History | `Algebra CC` (Coordinate Algebra / "Algebra: Concepts & Connections") **replaces** both Coordinate Algebra and Algebra I. Adds a `Standard Deviation` column on all sheets and **SGP columns** (`Number Received SGP`, `SGP Median`, `% SGP Low Growth`, `% SGP Typical Growth`, `% SGP High Growth`) on `Algebra CC` only. |
| **Spring 2025 / Full-Year 2024-2025 (xlsx direct)** | `Spring-2025-…`, `Full-Year-2024-2025-…` (6 total) | Same four sheets (American Lit, Algebra CC, Biology, US History) | Adds SGP columns on the **American Literature** sheet too (alongside the existing Reading Status split). Algebra CC continues to have SGP. Biology and US History still have no SGP. |

Transform dispatch notes:

- Most xlsx files place the **title in row 0, the main header in row 1, and a sub-header in row 2**, with data starting in row 3. Only the four top-level state-level xls/xlsx from 2014-2017 (and Winter 2015/2016 state) use a single-row header.
- `.xls` files inside `Winter 2014 / 2015 / 2016 / Spring 2015` zips follow the **single-row-header** layout (row 0 title, row 1 header, row 2 data, no sub-header).
- `Winter_2016_EOC_School/*.xls` and `2016 Spring School` workbooks have a blank row 2 before data — skip blank rows when loading.
- Within every zip, `zipfile.ZipFile` + `xlrd` (for .xls) or `openpyxl` (for .xlsx) is the working combination. `Winter_2016_EOC_School.zip` is the only zip that keeps its files under a nested subdirectory (`Winter_2016_EOC_School/…`).
- The 2018 Spring administration has both a zipped all-subjects xlsx (`Spring_2018_EOC_School.zip` / `_System.zip`) **and** a direct `Spring_2018_EOC-State_Level.xlsx`; the state xlsx is NOT in a zip.

## Summary

Georgia Milestones End-of-Course (EOC) assessments are state-mandated high-school-level tests. For each administration (Winter mid-year retests, Spring end-of-year primary, and Full-Year aggregations combining Fall + Winter + Spring), the Georgia Insights portal publishes three detail levels (state, district/system, school) and for each, counts and percentages of students at four achievement levels — **Beginning, Developing, Proficient, Distinguished Learner** — along with aggregate `% Developing Learner & Above` and `% Proficient Learner & Above`. Additional topic-specific metrics:

- **Mean Scale Score** (approx. 400–650 absolute score) and, from 2023-2024 onwards, **Standard Deviation** of the scale score
- **Reading Status** on Literature sheets: `% Below Grade Level (Lexile < 1050L)` / `% Grade Level or Above (Lexile ≥ 1050L)` in 2018-2019, thresholds move to **1185L** from Full-Year 2020-2021 onward
- **Student Growth Percentile (SGP)** bundle on Algebra CC from 2023-2024 and on American Literature from 2024-2025: `Number Received SGP`, `SGP Median` (1–99), plus `% SGP Low Growth` / `% SGP Typical Growth` / `% SGP High Growth`
- **Percent of Enrolled Students Tested** (only on Full_Year 2020-2021 files — reflecting the COVID year when participation dropped below the usual ~100%)

Content areas tested have evolved considerably: 2014 and early 2015 had 8–10 subjects (including Coordinate Algebra, Analytic Geometry, Algebra I, Geometry, Physical Science, Economics). By Winter 2021 this narrows to 5 (American Lit, Coordinate Algebra, Algebra I, Biology, US History). Winter 2023 drops to 3 (removes both algebras). Spring 2024 introduces **Algebra: Concepts & Connections** (`Algebra CC`) — Georgia's new combined algebra course that replaced Coordinate Algebra and Algebra I — leaving a stable 4-subject slate of American Literature, Algebra CC, Biology, US History from 2023-2024 onward.

## Eras

The topic has **12 eras** defined by the combination of file format (xls vs xlsx, zipped vs direct), sheet layout (single vs two-row header), content-area list, and presence/absence of columns (Reading Status, SGP, Standard Deviation, Percent Enrolled). Because every file is divided into **per-content-area sheets** at detail levels, an "era" here is defined at the (file-format, header-shape, column-set) level rather than per-year.

For brevity, the sections below group eras by their column-set signature. Each era shows the representative columns, sample data, statistics, nulls, and suppression markers. The transform must switch between these signatures on a per-file-per-sheet basis.

### Era 1: Winter 2014 / Spring 2015 — xls-in-zip, one content area per file

**Files:** `Winter 2014 EOC School.zip`, `Winter 2014 EOC System.zip`, `Spring 2015 EOC School.zip`, `Spring 2015 EOC System.zip` (plus the state-level xls outside the zip). Read each member `.xls` with `xlrd.open_workbook(file_contents=bytes)` and extract the content area name from the filename (e.g., `School - History.xls` → `U.S. History`).

**School-level columns (13):**

| Column | Description |
|--------|-------------|
| System Code | District identifier as a float that must be cast to 3-digit zero-padded int/string (e.g. 601.0 → `601`) |
| School Code | School identifier as a float that must be cast to 3-digit zero-padded int/string (e.g. 103.0 → `0103` after zero-padding to 4 digits; **note** older xls files use only 3 digits natively — confirm with alignment against later files) |
| System Name | District name, upper case |
| School Name | School name, often truncated (13–16 char limit) |
| N | Number of students tested (Int64) |
| Mean Scale Score | Average scale score, numeric |
| % Beginning Learner | % at lowest achievement level (0–100) |
| % Developing Learner | % at Developing level (0–100) |
| % Proficient Learner | % at Proficient level (0–100) |
| % Distinguished Learner | % at highest level (0–100) |
| % Developing Learner & Above | `% Developing + % Proficient + % Distinguished` |
| % Proficient Learner & Above | `% Proficient + % Distinguished` |
| RESA | Regional Educational Service Agency name (categorical, 16 distinct in state) |

**System-level columns (11):** same as school without School Code and School Name. **Note:** Spring 2015 System also adds a `Standard Deviation` column making 12 cols (unique to this era).

**State-level (xls direct) columns (9):** `Content Area, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above`. There are no geography columns — one row per content area.

#### Sample Data (Winter 2014 School - History.xls)

```text
Row 2:  System Code=601  School Code=103  APPLING COUNTY  APPLING HIGH        N=117  Mean=516.17  %Beg=21.37  %Dev=31.62  %Prof=42.74  %Dist=4.27  RESA=FIRST DISTRICT
Row 3:  System Code=602  School Code=103  ATKINSON COUNTY ATKINSON HIGH       N=51   Mean=498.04  %Beg=33.33  %Dev=43.14  %Prof=23.53  %Dist=0.00  RESA=OKEFENOKEE
Row 4:  System Code=603  School Code=302  BACON COUNTY    BACON HIGH          N=63   Mean=487.05  %Beg=42.86  %Dev=41.27  %Prof=15.87  %Dist=0.00  RESA=OKEFENOKEE
Row 5:  System Code=604  School Code=105  BAKER COUNTY    BAKER K TWELVE      N=20   Mean=492.85  %Beg=45.00  %Dev=30.00  %Prof=20.00  %Dist=5.00  RESA=SOUTHWEST GEORGIA
Row 6:  System Code=605  School Code=189  BALDWIN COUNTY  BALDWIN HIGH        N=4    Mean='     -----' (suppressed) RESA=OCONEE
```

#### Statistics (Winter 2014 School - History, 321 non-null rows)

| statistic | N | Mean Scale Score | % Beginning | % Developing | % Proficient | % Distinguished |
|-----------|------|------|------|------|------|------|
| count | 321 | 176 | 176 | 176 | 176 | 176 |
| null_count | 0 | 145 | 145 | 145 | 145 | 145 |
| mean | 56.9 | 498.45 | 36.05 | 34.69 | 25.05 | 4.21 |
| std | 76.6 | 26.9 | 22.3 | 12.0 | 15.5 | 5.4 |
| min | 1 | 439.70 | 0.0 | 0.0 | 0.0 | 0.0 |
| max | 325 | 564.46 | 100.0 | 75.0 | 57.3 | 30.1 |

(High null count reflects suppression of scores where N is below the reporting threshold.)

#### Null Counts

All key columns (System Code, School Code, N, RESA) are non-null. `Mean Scale Score` and the four `% Learner` columns are null in 145/321 rows (where the school had too few students to report).

#### Categorical Columns

| Column | Distinct Values |
|--------|----------------|
| System Name | 137 distinct Georgia school district names, upper case (`APPLING COUNTY`, `ATLANTA PUBLIC SCHOOLS`, …) |
| School Name | 315 distinct school names, upper case and **truncated to 13–16 chars** (`APPLING HIGH`, `BAKER K TWELVE`, `TALIAFERRO SC`, …) |
| RESA | 17 distinct values in Era 1: `CENTRAL SAVANNAH RIV`, `CHATTAHOOCHEE-FLINT`, `COASTAL PLAINS`, `FIRST DISTRICT`, `GRIFFIN`, `HEART OF GEORGIA`, `METRO`, `MIDDLE GEORGIA`, `NORTH GEORGIA`, `NORTHEAST GEORGIA`, `NORTHWEST GEORGIA`, `OCONEE`, `OKEFENOKEE`, `PIONEER`, `SOUTHWEST GEORGIA`, `WEST GEORGIA`, plus a single `' '` (whitespace) value for rows with missing RESA |

#### Suppression Markers

| Column | Non-Numeric Values |
|--------|-------------------|
| Mean Scale Score | `'     -----'` (five spaces + 5 dashes) |
| % Beginning Learner | `'     -----'` |
| % Developing Learner | `'     -----'` |
| % Proficient Learner | `'     -----'` |
| % Distinguished Learner | `'     -----'` |
| % Developing Learner & Above | `'     -----'` |
| % Proficient Learner & Above | `'     -----'` |

### Era 2: Winter 2015 / Winter 2016 / Spring 2016 — xls or xlsx-in-zip, one content area per workbook

**Files:** `Winter_2015_EOC_School.zip`, `Winter_2015_EOC_System.zip`, `Winter_2016_EOC_School.zip`, `Winter_2016_EOC_System.zip`, `Spring_2016_EOC-School_Level.zip`, `Spring_2016_EOC-System_Level.zip` (6 zip archives). Plus direct state-level xls/xlsx: `Winter_2015_EOC_State_All-Content-Areas.xls`, `Winter_2016_EOC_State-All_Content_Areas.xls`, `Spring_2016_EOC-State_Level.xlsx`.

**Key distinction from Era 1:** Spring 2016 School files use a single `Key` column = `system_code * 10000 + school_code_as_int` (e.g. `6010103` decodes to system `601` + school `0103`). Spring 2016 System files use separate `System Code`/`System Name`. All 2016 files have a blank row 2 before data starts at row 3 (for the xlsx files); xls files may or may not.

**Spring 2016 School columns (13):** `Key, System Name, School Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA, (None)` — a trailing empty column at index 12 that must be dropped.

**Spring 2016 System columns (11):** `System Code, System Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**Winter 2015 / 2016 School columns (12):** `Key, System Name, School Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA` (no trailing None column).

**Winter 2015 / 2016 System columns (11):** same as Spring 2016 System.

#### Suppression Markers

Mixed across Era 2 files:
- Winter 2016 School xls files: `'--'` (2-char marker)
- Spring 2016 School xlsx files: `'---'` (3-char marker) — e.g. `(6040105, 'BAKER COUNTY', 'BAKER COUNTY K12 SCHOOL', 1, '---')`
- Spring 2015 School xls files (carrying over from Era 1): `'     -----'`
- 2015/2016 state files: no suppression markers observed (state aggregates always have enough students)

#### Categorical Columns

- `RESA` in Winter/Spring 2016 files uses **title case** (`First District`, `Okefenokee`, `Chattahoochee-Flint`) instead of the upper-case form used in Era 1 and Era 4+. 17 distinct values including whitespace-only.
- `System Name` / `School Name`: upper case in xls era, **title case** in 2016 xlsx era (`APPLING COUNTY HIGH SCHOOL` vs `Appling County High School`).

### Era 3: Spring 2017 — xlsx-in-zip, one content area per workbook + state all-content-areas

**Files:** `Spring_2017_EOC-SchoolLevel.zip`, `Spring_2017_EOC-System_Level.zip`, `Spring_2017_EOC-State_Level-All_Content_Areas.xlsx` (3 files).

**School columns (14, with a trailing unnamed None column):** `System Code, School Code, System Name, School Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA, (None)` — the 14th column is always `None` and must be dropped.

**System columns (11):** `System Code, System Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**State columns (9):** `Content Area, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above` — one row per content area (10 rows).

**Quirks:** Spring 2017 School `School Code` is a **bare integer** (e.g., `103`) with **no zero-padding**, unlike all later xlsx eras where it's a string (`'0103'`). Sheet names are shortened — e.g., `School - 9th Grade Lit.`. `RESA` uses title case (`First District`).

### Era 4: Winter 2017 — Spring 2019 — xlsx direct, per-content-area sheets, two-row header begins

**Files (15):** `Winter_2017_EOC-State/System/School_Level.xlsx`, `Winter_2018_EOC-*`, `Spring_2018_EOC-State_Level.xlsx`, `Winter_2019_EOC-*`, `Spring_2019_EOC-*`, **plus** `Spring_2018_EOC_School.zip` and `Spring_2018_EOC_System.zip` which each wrap a single xlsx with the same structure as the direct Spring_2018_EOC-State_Level.xlsx.

**Sheet list (10):** `State/System/School - 9th Grade Literature`, `… - American Literature`, `… - Coordinate Algebra`, `… - Analytic Geometry`, `… - Algebra I`, `… - Geometry`, `… - Biology`, `… - Physical Science`, `… - US History`, `… - Economics`.

**Two-row-header layout begins here.** For every sheet:
- Row 0 = title
- Row 1 = main header (e.g., `System Code, School Code, System Name, School Name, Number Tested, Reading Status*, None, Mean Scale Score, % Beginning Learner, …`)
- Row 2 = sub-header, only used by **Literature sheets** to split Reading Status into `% Below Grade Level (Lexile < 1050L)` and `% Grade Level or Above (Lexile ≥ 1050L)`
- Row 3 = first data row

**Literature sheet columns (15, School):** `System Code, School Code, System Name, School Name, Number Tested, % Below Grade Level (Lexile < 1050L), % Grade Level or Above (Lexile ≥ 1050L), Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`. System-level drops the 2 school columns (13). State-level drops geography and RESA (11).

**Non-Literature sheet columns (13, School):** `System Code, School Code, System Name, School Name, Number Tested, Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`. System-level 11 cols. State-level 9 cols.

**School Code format starts here:** from Winter 2017 onward, School Code is a zero-padded **string** like `'0103'` — NOT an int.

#### Sample Data (Spring 2019 School - 9th Grade Literature)

```text
Row 3:  System Code=601   School Code='0103'  APPLING COUNTY  APPLING COUNTY HIGH SCHOOL    Number Tested=129  %BelowGradeLevel=21.71   %GradeLevelOrAbove=78.29   Mean=524.67   %Beg=13.18   %Dev=39.53   %Prof=37.21   %Dist=10.08   RESA=FIRST DISTRICT
Row 4:  System Code=602   School Code='0103'  ATKINSON COUNTY  ATKINSON COUNTY HIGH SCHOOL  Number Tested=60   %BelowGradeLevel=20.00   %GradeLevelOrAbove=80.00   Mean=515.95   %Beg=15.00   %Dev=41.67   %Prof=40.00   %Dist=3.33    RESA=OKEFENOKEE
Row 5:  System Code=603   School Code='0202'  BACON COUNTY    BACON COUNTY MIDDLE SCHOOL    Number Tested=51   %BelowGradeLevel=0.00    %GradeLevelOrAbove=100.00  Mean=564.47   %Beg=0.00    %Dev=3.92    %Prof=72.55   %Dist=23.53   RESA=OKEFENOKEE
```

#### Suppression Markers

From Era 4 onward the universal marker is `'--'` (two hyphens), applied to every metric column when suppressed. The `Number Tested` column is always numeric and never suppressed. `Reading Status` and every `% Learner` and `Mean Scale Score` column can contain `'--'`.

### Era 5: Winter 2021 — xlsx direct, 5 sheets (COVID-trimmed)

**Files:** `Winter_2021_EOC-State/System/School_Level.xlsx` (3 files).

**Sheets (5):** American Literature, Coordinate Algebra, Algebra I, Biology, US History. 9th Grade Lit, Analytic Geometry, Geometry, Physical Science, and Economics are all gone. Reading Status now appears **only on American Literature**, and the Lexile threshold moves from 1050L to **1185L**.

**American Literature columns (15, School):** `System Code, School Code, System Name, School Name, Number Tested, % Below Grade Level (Lexile < 1185L), % Grade Level or Above (Lexile ≥ 1185L), Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**Non-literature sheet columns** are the same 13/11/9 shape as Era 4.

### Era 6: Full Year 2020-2021 (xlsx direct) — COVID participation column

**Files:** `Full_Year_2021_EOC-State/System/School_Level.xlsx` (3 files). Sheet title spells it out: `Full Year 2020-2021 (Fall, Winter, Spring) 2021 Georgia Milestones…`.

**Sheets (6):** American Literature, Coordinate Algebra, Algebra I, Biology, `Phys Science Gr8` (school/system) / `Physical Science Gr8` (state), US History. **Physical Science is unique to this administration** — it's an 8th-grade test that was folded in for this reporting year only.

**Unique column:** `Percent of Enrolled Students Tested` (0–100) appears on every sheet, between `Number Tested` and (on American Literature) the Reading Status split. This column captures that participation rates were well below 100% during COVID. State sheets also include a footer note row: `'Note: Georgia Milestones 2020-2021 results are reported with the percent of enrolled students tested.'` which must be filtered out.

**American Literature School columns (16):** `System Code, School Code, System Name, School Name, Number Tested, Percent of Enrolled Students Tested, % Below Grade Level (Lexile < 1185L), % Grade Level or Above (Lexile ≥ 1185L), Mean Scale Score, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**Non-literature School columns (14):** as above, drop the two Reading Status columns.

#### Sample Data (Full Year 2020-2021 System - American Literature)

```text
Row 3:  System Code=601  APPLING COUNTY   Number Tested=227  PctEnrolled=99.12  %Below=44.05  %GradeOrAbove=55.95  Mean=492.29  %Beg=35.24  %Dev=38.77  %Prof=22.91  %Dist=3.08   RESA=FIRST DISTRICT
Row 4:  System Code=602  ATKINSON COUNTY  Number Tested=102  PctEnrolled=97.12  %Below=36.27  %GradeOrAbove=63.73  Mean=500.22  %Beg=24.51  %Dev=45.10  %Prof=27.45  %Dist=2.94   RESA=OKEFENOKEE
Row 5:  System Code=603  BACON COUNTY     Number Tested=101  PctEnrolled=90.99  %Below=56.44  %GradeOrAbove=43.56  Mean=472.39  %Beg=42.57  %Dev=52.48  %Prof=4.95   %Dist=0.00   RESA=OKEFENOKEE
```

### Era 7: Spring 2022 — Winter 2023 — xlsx direct, 5 sheets (no SGP, no PctEnrolled)

**Files:** `Spring_2022_…`, `Winter-2022-…`, `Spring_2023_…`, `Winter-2023-…`, `Full_Year_2021-2022_…`, `Full-Year_2023_…` — 18 files total (State/System/School × 6 administrations).

**Sheets:**
- Full Year 2021-2022, Spring 2022, Winter 2022, Spring 2023, Full-Year 2023: five sheets (American Lit, Coordinate Algebra, Algebra I, Biology, US History).
- **Winter-2023** has only **three** sheets (American Literature, Biology, US History) — drops both algebras for the Winter retest.

American Literature continues to use Reading Status at Lexile **1185L**. No `Percent of Enrolled Students Tested` and no SGP columns. `Standard Deviation` is present (appears between `Mean Scale Score` and the `% Learner` block on every sheet).

**American Literature School columns (16):** `System Code, School Code, System Name, School Name, Number Tested, % Below Grade Level (Lexile < 1185L), % Grade Level or Above (Lexile ≥ 1185L), Mean Scale Score, Standard Deviation, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**Non-literature School columns:** Era 4 non-literature shape plus `Standard Deviation` after `Mean Scale Score`.

### Era 8: Spring 2024 / Winter 2024 / Full-Year 2023-2024 — Algebra CC arrives, SGP on Algebra CC

**Files:** `Spring-2024-State/System/School-Level.xlsx`, `Winter-2024-…`, `Full-Year-2023-2024-…` (9 files total).

**Sheets (4):** American Literature, **Algebra CC**, Biology, US History. Algebra CC (aka "Algebra: Concepts & Connections") replaces both Coordinate Algebra and Algebra I.

**New columns:**
- **SGP** (Student Growth Percentile) block appears on **Algebra CC only**: `Number Received SGP, SGP Median, % SGP Low Growth, % SGP Typical Growth, % SGP High Growth`.
- American Lit still has Reading Status (Lexile 1185L) — no SGP yet.
- `Standard Deviation` continues to appear after `Mean Scale Score` on every sheet (carried over from Era 7).

**American Literature School columns (16):** `System Code, School Code, System Name, School Name, Number Tested, % Below Grade Level (Lexile < 1185L), % Grade Level or Above (Lexile ≥ 1185L), Mean Scale Score, Standard Deviation, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

**Algebra CC School columns (19):** `System Code, School Code, System Name, School Name, Number Tested, Mean Scale Score, Standard Deviation, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, Number Received SGP, SGP Median, % SGP Low Growth, % SGP Typical Growth, % SGP High Growth, RESA`.

**Biology / US History School columns (14):** `System Code, School Code, System Name, School Name, Number Tested, Mean Scale Score, Standard Deviation, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, RESA`.

(System-level drops the 2 school columns; state-level drops 4 geography + RESA columns.)

### Era 9: Spring 2025 / Full-Year 2024-2025 — SGP now on American Literature too

**Files:** `Spring-2025-…`, `Full-Year-2024-2025-…` (6 files).

**Sheets (4):** American Literature, Algebra CC, Biology, US History.

**Change vs Era 8:** SGP block is added to **American Literature** (bringing it up to 21 columns at school-level) alongside the existing Reading Status split. Algebra CC still has SGP. Biology and US History remain without SGP.

**American Literature School columns (21):** `System Code, School Code, System Name, School Name, Number Tested, % Below Grade Level (Lexile < 1185L), % Grade Level or Above (Lexile ≥ 1185L), Mean Scale Score, Standard Deviation, % Beginning Learner, % Developing Learner, % Proficient Learner, % Distinguished Learner, % Developing Learner & Above, % Proficient Learner & Above, Number Received SGP, SGP Median, % SGP Low Growth, % SGP Typical Growth, % SGP High Growth, RESA`.

#### Sample Data (Full-Year 2024-2025 School - American Literature, 510 rows)

```text
Row 3: System Code=601   School Code='0103'  APPLING COUNTY  APPLING COUNTY HIGH SCHOOL
       Number Tested=259  %Below=37.07  %GradeOrAbove=62.93  Mean=502.79  StdDev=52.30
       %Beg=25.87  %Dev=41.31  %Prof=26.64  %Dist=6.18  %DevAbove=74.13  %ProfAbove=32.82
       #SGP=236  SGP_Median=50  %SGP_Low=34.32  %SGP_Typical=31.36  %SGP_High=34.32
       RESA=FIRST DISTRICT
```

#### Statistics (Era 9, numeric columns after casting)

| statistic | Number Tested | Mean Scale | StdDev | %Beg | %Prof & Above | SGP Median | %SGP High |
|-----------|---------------|-----------|--------|------|----------------|------------|-----------|
| count     | 510           | 447       | 447    | 447  | 447            | 432        | 432       |
| null_count (due to `'--'` suppression) | 0 | 63 | 63 | 63 | 63 | 78 | 78 |
| mean      | 264.1         | 503.9     | 51.75  | 29.2 | 36.6           | 47.8       | 32.1      |
| std       | 204.1         | 28.3      | 6.1    | 17.3 | 19.2           | 11.5       | 11.0      |
| min       | 1             | 414.9     | 27.3   | 0.0  | 0.0            | 4.5        | 0.0       |
| 25%       | 79            | 487.7     | 48.4   | 17.5 | 23.9           | 41.0       | 25.1      |
| 50%       | 251           | 501.9     | 51.5   | 27.3 | 33.5           | 48.0       | 31.9      |
| 75%       | 410           | 520.1     | 55.5   | 38.3 | 47.6           | 54.0       | 38.3      |
| max       | 966           | 603.1     | 72.5   | 91.9 | 98.6           | 84.0       | 69.7      |

#### Null Counts

School identifier columns (System Code, School Code, System Name, School Name) and `Number Tested` are always non-null. SGP block has slightly more nulls than the main metrics because a smaller subset of schools gets reported SGP. `RESA` is null for ~12 rows (state-chartered schools without a RESA assignment, e.g. `GEORGIA SCHOOL FOR INNOVATION AND T`).

#### Categorical Columns

- `RESA` in Era 8/9: 16 distinct values (same 16 as Era 1, all upper case again).
- `System Name`: ~180 distinct Georgia districts (upper case).
- `School Name`: many hundreds of schools (upper case in modern era, unlike 2016).

#### Suppression Markers

| Column (all numeric metric columns) | Non-Numeric Values |
|---|---|
| Reading Status (% Below / % Above), Mean Scale Score, Standard Deviation, every `% Learner`, SGP block | `'--'` |
| RESA | (`null` for state charters) |

## ETL Considerations

1. **No year column inside any sheet.** The transform must parse the year from the filename using regex-based dispatch, mapping each pattern to a (data_year, administration) tuple:
   - `Winter YYYY` → `data_year = YYYY + 1`, `administration = 'winter'` (mid-year retest of prior spring)
   - `Spring YYYY` / `Spring_YYYY` / `Spring-YYYY` → `data_year = YYYY`, `administration = 'spring'`
   - `Full_Year_YYYY` → `data_year = YYYY`, `administration = 'full_year'` (e.g., Full_Year_2021 = school year 2020-2021)
   - `Full_Year_YYYY1-YYYY2` / `Full-Year-YYYY1-YYYY2` → `data_year = YYYY2`, `administration = 'full_year'`
   The administration dimension is a new gold categorical column — users will want to filter by winter/spring/full-year.

2. **Three coexisting administrations for most years.** From Winter 2017 onward, each school year produces up to three files per detail level (Winter, Spring, Full-Year). Gold should retain all three as separate rows keyed by `(year, administration, detail, content_area, ...)` — they are NOT duplicates of each other (winter is a retest cohort, spring is primary, full-year is the aggregated combination).

3. **Zip unpacking.** 14 `.zip` files wrap either individual-content-area xlsx/xls workbooks (Winter 2014 / Spring 2015 / Winter 2015 / Winter 2016 / Spring 2016 / Spring 2017) or a single all-subjects xlsx (Spring 2018). The transform must stream-open with `zipfile.ZipFile` rather than requiring extraction. `Winter_2016_EOC_School.zip` has an extra subdirectory in its paths (`Winter_2016_EOC_School/…`).

4. **Two header rows from 2017 Winter onward (xlsx), one header row before that (xls).** Row 0 is always the title. For xlsx, header spans rows 1–2 with row 2 as the sub-header for Reading Status (e.g., `% Below Grade Level (Lexile < 1185L)`) and SGP (e.g., `Number Received SGP`). For xls files, header is only row 1. Sub-header values need to OVERRIDE the parent `Reading Status^` / `SGP` label in the merged header since those parent labels are not useful on their own.

5. **Data starts at row 2 or 3, sometimes with a blank spacer row.** Winter 2016 School and Spring 2016 School workbooks have a blank row at index 2 before actual data. For xlsx with the 2-row header, data starts at row 3. For xls with a 1-row header, data starts at row 2 — but some workbooks still have a blank row 2, so skip-empty-rows logic is essential.

6. **Trailing None columns.** Spring 2016 School and Spring 2017 School workbooks have an extra empty column at index 12 (and sometimes beyond). Drop columns whose header is `None`.

7. **Footnote rows at the bottom.** State-level sheets in Era 9 (Full-Year 2024-2025) include a footnote row starting with `'^To achieve a reading status designation…'`, and Full Year 2020-2021 state sheets include `'Note: Georgia Milestones 2020-2021 results are reported with the percent of enrolled students tested.'`. Filter out any row whose `Content Area` or first column starts with `^` or `Note`.

8. **System Code / School Code formatting inconsistency.**
   - **2014 Winter / 2015 Spring / 2015 Winter / 2016 Winter (.xls in zip or direct state):** Both codes come through as floats (`601.0`, `103.0`). Cast to zero-padded string: system → 3-digit `"601"`, school → 4-digit `"0103"`.
   - **2016 Spring School (.xlsx in zip):** Single `Key` column as 7-digit int (`6010103`). Split: `system_code = int(key[:3])`, `school_code = key[3:].zfill(4)`.
   - **2017 Spring (.xlsx in zip):** Two columns `System Code` (int), `School Code` (int, **not** zero-padded — raw `103`). Convert School Code → `str(int).zfill(4)`.
   - **Winter 2017 onward (.xlsx direct):** `System Code` int, `School Code` zero-padded string (`"0103"`). No conversion needed.
   - Gold should store `district_code` as a 3-digit zero-padded string and `school_code` as a 4-digit zero-padded string, consistent with `data/bronze/education/georgiainsights/attendance_dashboard/bronze-data-structure.md` and other georgiainsights topics. The Spring 2016 state-level xlsx uses GOSA codes already in that form via Systems Code / School Code columns on School-level zipped members.

9. **System/School Name casing inconsistency.** Era 1 and Era 4+ use uppercase (`APPLING COUNTY HIGH SCHOOL`); Era 2 (2016 xlsx, including zip members) uses title case (`Appling County High School`); Era 1/2 xls files aggressively truncate school names (`APPLING HIGH`, `BAKER K TWELVE`). Dimension-table population should normalize to the **latest** canonical name — don't trust any single era's representation.

10. **RESA casing inconsistency.** Upper case in 2014-2015 and 2017+ (`FIRST DISTRICT`). Title case in 2016 (`First District`). Era 1 state data has no RESA column at all. Normalize to upper case (matching the latest files) when building a RESA dimension, but treat RESA as a `dimension_attribute` of a district rather than a fact-table column.

11. **Suppression markers vary by era.**
    - `'     -----'` (5 spaces + 5 dashes) in Era 1 (Winter 2014, Spring 2015)
    - `'--'` (2 hyphens) from Winter 2016 School onward and in every xlsx era
    - `'---'` (3 hyphens) in Spring 2016 School xlsx files
    - The transform should replace all of these (and any all-whitespace value) with null before casting to Float64. Use `strict=False` casting as a safety net but prefer an explicit string-to-null mapping for auditability.

12. **Content area naming drift.**
    - `Ninth Grade Literature & Composition` vs `9th Grade Literature & Composition` vs sheet name `9th Grade Literature` — all refer to the same test.
    - `U.S. History` / `United States History` / `U S History` / `US History` / `History` — all the same.
    - `Coordinate Algebra`, `Analytic Geometry`, `Algebra I`, `Geometry` all existed through Era 4; retired in Era 8 in favor of **`Algebra: Concepts & Connections`** (sheet name `Algebra CC`).
    - `American Literature & Composition` vs `American Literature` — same test.
    - Normalize to a canonical set of content-area strings in the gold file (e.g., `american_literature`, `algebra_cc`, `coordinate_algebra`, `algebra_i`, `analytic_geometry`, `geometry`, `ninth_grade_literature`, `biology`, `physical_science`, `physical_science_gr8`, `economics`, `us_history`).

13. **Suppression of school-level metrics preserves row but nulls numeric columns.** Rows with very low `Number Tested` (typically < 10) have every metric column replaced by the suppression marker but keep their geography columns populated. The transform should KEEP these rows (they're informative about "we attempted to test, but count was too low") and emit nulls for the numeric metrics.

14. **`Percent of Enrolled Students Tested` is unique to Full Year 2020-2021.** Do NOT carry this column into gold if the user wants schema parity across years — or emit it as a nullable column that's only populated for year=2021 rows with administration=full_year. Its presence is a COVID artifact reflecting that participation dropped from the usual ~99-100% to ~50-90%.

15. **Reading Status Lexile threshold changed.** 1050L in 2018-2019 Literature sheets (both 9th Grade Lit and American Lit); 1185L from 2021 Winter onward (American Lit only since 9th Grade Lit was discontinued). If the gold table flattens these into `% Below Grade Level` and `% Grade Level Or Above`, include the Lexile threshold as metadata so downstream users can compare apples-to-apples.

16. **SGP block presence varies.** Algebra CC has SGP from Spring 2024 onward. American Literature has SGP from Spring 2025 onward. Biology and US History never have SGP. Gold should either emit SGP metrics as nullable columns (nulls where unavailable) or as a separate SGP-detail fact table keyed by `(year, administration, detail, geography_fk, content_area)`.

17. **State-level rows have NO geography columns.** The State-level files emit `Content Area` as their only geography-like identifier (which is redundant with sheet name). For gold, the transform should add a `detail` column = `'state'` / `'district'` / `'school'` and use constant geography FKs for state rows (e.g., `district_code = NULL`, `school_code = NULL`). Alternatively, model state as a separate fact table at `data/gold/education/gosa_eoc_state/`.

18. **Spring 2016 State and Spring 2017 State All-Content-Areas files do not split content areas into sheets.** These two files have a single sheet with one row per content area — unlike every other state-level file. Easy to handle: the existing state-level logic that reads `Content Area` out of a column works for both the multi-sheet modern files (where content area comes from sheet name) and these single-sheet files (where content area is a column).

19. **The older xls files (Era 1 School/System) have TRUNCATED school names** due to a column width limit in the xls format (`APPLING HIGH`, `TALIAFERRO SC`, `ATL SCH DEAF`). These are not usable as canonical school names — the dimension table should sourcer names from the latest xlsx files and join bronze rows via the school code.

20. **Header trailing whitespace.** Column headers like `'SGP '` (trailing space) and `'RESA '` appear in the raw files. Strip whitespace and collapse inner double spaces (`'% Grade Level  or Above'` → `'% Grade Level or Above'`) when normalizing.

## Gold Schema Classification

The following classifies every bronze column encountered across all eras, with notes on era-specific handling. Columns that appear under different spellings in different eras are grouped under the canonical bronze name used in the newest era.

| Bronze Column | Gold Role | Gold Name | Notes |
|---------------|-----------|-----------|-------|
| (filename year / administration) | fact_key | `year`, `administration` | Parsed from filename (see ETL note 1). `administration ∈ {'winter', 'spring', 'full_year'}`. |
| (sheet name OR `Content Area`) | fact_categorical | `content_area` | Normalized snake_case canonical label (see ETL note 12). For multi-sheet files, derive from sheet name; for 2016/2017 single-sheet state files, read from the `Content Area` column; for 2014-2015 zipped-xls files, derive from the inner filename. |
| System Code / `Key` (left 3 digits) | fact_key | `district_code` | 3-digit zero-padded GOSA district code (FK to `districts` dimension in `education/_dimensions/`). Float in 2014-2016 xls → cast to int → zero-pad. |
| School Code / `Key` (right 4 digits) | fact_key | `school_code` | 4-digit zero-padded GOSA school code (FK to `schools` dimension). Bare int in 2017 Spring → zero-pad. NULL on state/district-level rows. |
| System Name | dimension_attribute | — | Goes in `districts` dimension. Era-dependent casing — take latest, upper case. NOT kept in fact table. |
| School Name | dimension_attribute | — | Goes in `schools` dimension. 2014-2015 values are truncated; take latest uppercase canonical form. NOT kept in fact table. |
| RESA | dimension_attribute | — | Goes in `districts` dimension as `resa_name`. Upper case. NOT kept in fact table. |
| (detail derived from filename) | fact_categorical | `detail` | `'state'` / `'district'` / `'school'` — distinguishes the three parallel detail-level fact rows. |
| N / Number Tested | fact_metric | `num_tested` | Int64. Never suppressed. Universal across all eras. |
| Mean Scale Score | fact_metric | `mean_scale_score` | Float64 absolute score (typically 400-650). Suppressed cells → null. |
| Standard Deviation | fact_metric | `scale_score_std_dev` | Float64. Era 8+ only; null for earlier years. |
| % Beginning Learner | fact_metric | `pct_beginning_learner` | Float64 0-100 scale. Suppressed → null. |
| % Developing Learner | fact_metric | `pct_developing_learner` | 0-100. |
| % Proficient Learner | fact_metric | `pct_proficient_learner` | 0-100. |
| % Distinguished Learner | fact_metric | `pct_distinguished_learner` | 0-100. |
| % Developing Learner & Above | fact_metric | `pct_developing_learner_and_above` | 0-100. Redundant with sum of Developing + Proficient + Distinguished but emitted by the source — keep as reported. |
| % Proficient Learner & Above | fact_metric | `pct_proficient_learner_and_above` | 0-100. Redundant with sum of Proficient + Distinguished but emitted by the source — keep as reported. |
| % Below Grade Level (Lexile < 1050L / 1185L) | fact_metric | `pct_below_grade_level_lexile` | 0-100. Null outside Literature sheets. See ETL note 15 about threshold change; consider storing `reading_lexile_threshold ∈ {1050, 1185}` in metadata or as a separate dimension column. |
| % Grade Level or Above (Lexile ≥ 1050L / 1185L) | fact_metric | `pct_grade_level_or_above_lexile` | 0-100. Null outside Literature sheets. |
| Number Received SGP | fact_metric | `number_received_sgp` | Int64. Null for sheets/years without SGP (all of Eras 1-7; Algebra CC from Era 8; American Lit from Era 9). |
| SGP Median | fact_metric | `sgp_median` | Int64 1-99. Null where no SGP reported. |
| % SGP Low Growth | fact_metric | `pct_sgp_low_growth` | 0-100. Null where no SGP reported. |
| % SGP Typical Growth | fact_metric | `pct_sgp_typical_growth` | 0-100. |
| % SGP High Growth | fact_metric | `pct_sgp_high_growth` | 0-100. |
| Percent of Enrolled Students Tested | fact_metric | `pct_enrolled_tested` | 0-100. Only populated for Full Year 2020-2021 files — null elsewhere. COVID-year artifact. |
| (trailing unnamed `None` columns in 2016/2017) | not_in_gold | — | Always empty; drop during ingest. |
| (title row at row 0) | not_in_gold | — | Not a data column. |
| (footnote rows starting with `^` or `Note`) | not_in_gold | — | Filter out before casting. |

## Corrections

- **2026-06-12 (transform authoring)** — claims re-verified against all 72 bronze files during the clean-start rebuild; evidence is from raw `header=None, dtype=str` reads of the named files/sheets.
  - **Standard Deviation timeline is wrong in the Summary and Era 5.** The Summary says Standard Deviation appears "from 2023-2024 onwards" and the Era 5 section describes Winter 2021 as "the same two-row-header layout as Era 4" (which has no Standard Deviation). In fact every `Winter_2021_EOC-*` sheet carries a `Standard Deviation` column (e.g. `Winter_2021_EOC-School_Level.xlsx :: School - Biology` row 1: `… Mean Scale Score, Standard Deviation, % Beginning Learner …`). The `Full_Year_2021_EOC-*` (Era 6) files do NOT have it. Correct presence: Spring 2015 System files (as documented), Winter 2021 files, and every file from Spring 2022 onward.
  - **Era 8: Winter-2024 Algebra CC has NO SGP block.** Era 8 claims SGP columns on Algebra CC for "Spring 2024 / Winter 2024 / Full-Year 2023-2024". `Winter-2024-EOC-School-Level.xlsx :: School - Algebra CC` has only the 14-column no-SGP shape (`System Code … % Proficient Learner & Above, RESA`). Only the Spring-2024 and Full-Year-2023-2024 Algebra CC sheets carry SGP headers — and those sheets are empty (next bullet).
  - **Spring-2024 and Full-Year-2023-2024 Algebra CC sheets are EMPTY templates** (previously undocumented). School/System sheets are header-only (3 raw rows: title, header, sub-header; zero data rows); State sheets have exactly one row whose `Content Area` is "Algebra: Concepts and Connections" with every metric cell blank. Consequence: gold year=2024 has no `algebra_concepts_and_connections` rows; the first populated Algebra CC data is Winter-2024 (gold year=2025, no SGP) and Spring/Full-Year 2025 (with SGP). GaDOE published combined Winter+Spring 2024 Algebra CC results elsewhere; ingesting them requires re-harvesting the bronze workbooks.
  - **The "blank row 2" in 2016 School workbooks does not exist.** Era 2 / ETL note 5 claim Winter 2016 School and Spring 2016 School workbooks have a blank row 2 before data. Raw reads show data starting immediately at row 2 in both (`Winter_2016_EOC_School.zip :: …/School - Biology.xls` row 2 = `6010103, APPLING COUNTY, …`; `Spring_2016_EOC-School_Level.zip :: Biology_School.xlsx` row 2 = `6010103, …`). Only `Winter_2016_EOC_State-All_Content_Areas.xls` has the blank row 2 (that part of the claim is correct). Harmless either way — the transform filters fully-null rows era-agnostically.
  - **Footnote inventory (§7) is incomplete.** Footnote/footer rows are not limited to Era 9 state sheets and Full Year 2020-2021 state sheets. A full-file scan finds 150 such rows: `^To achieve a reading status…` on Era 8/9 American Literature sheets at ALL detail levels; `*To achieve a reading status…` on Era 4-7 literature sheets at all detail levels; the four Full-Year 2020-2021 footers (`Note: …`, `For more information…`, `The EOG analysis…`, `https://…`) plus `*Only spring 8th grade Physical Science test takers…` on School and System files as well as State; and `Results for all students tested at this school/in this district are not available at this time.` placeholder rows in the Spring 2015 School/System zips (Coordinate Algebra, Analytic Geometry, 9th Grade Literature members). The transform filters on the full observed prefix set and ledgers the drops as `footnote_row`.
