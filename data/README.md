# Data

Three small tables, all hand-transcribed from public sources and checked in, because a wrong
row here is the most dangerous bug this project can have. Every row names its source.

| File | Rows | What | Source |
|---|---:|---|---|
| `labels.csv` | 40 | Insecticide label claims: product, crop, pests, rate per hectare, **waiting period in days** | India's CIB&RC *Major Uses of Pesticides*: insecticides up to 01/02/2023 (`cib-2023`), bio-insecticides as on 31/03/2024 (`cib-bio-2024`) |
| `nepal_banned.csv` | 26 | Pesticides banned in Nepal, with year | BMC Public Health 2021, Table 2 (`pmc8201746`); The Kathmandu Post, 9 December 2024 (`kp-2024-12-09`) |
| `sources.csv` | 11 | Every source cited by the tables and the notes in `corpus/` | |

## Why an Indian label table for Nepal

Most insecticides sold in Nepal are made in India and carry Indian label claims; Nepal's own
registered-pesticide lists (npponepal.gov.np) give product registrations, not per-crop waiting
periods. So the waiting periods come from the Indian labels, and **Nepal's ban list overrides
them**: carbofuran, carbosulfan and chlorpyrifos all have Indian label rows here and are all banned
in Nepal. Parkha never recommends them (`parkha/labels.py`, `tests/test_labels.py`).

## What was left out, and how blanks are read

- Only crops grown widely in Nepal and only the pests in `parkha/lexicon.py` were transcribed.
  The source has hundreds of rows; this is a deliberately small, checkable subset.
- A blank `waiting_days` means the label gives none ("-"), and Parkha treats it as **unknown, never
  zero**: no harvest date is computed. Chlorpyrifos 20% EC rows are blank in the source.
- A blank `unit` means the source's unit was ambiguous (the neem WSP and 5% extract rows). Parkha
  then gives the waiting period but no dose.
- Rows with a range ("1000-1500") keep it; the rate per ropani and kattha is computed from it.

## Known issues with the sources

- The insecticide PDF's text layer ends at Cyantraniliprole, so products later in the alphabet
  (emamectin benzoate, imidacloprid, spinosad and others) are **not** in the table. Parkha knows
  their names and says it has no verified waiting period instead of guessing.
- The two ban sources disagree on dates: phorate is listed as banned in 2015 and again in the
  December 2024 gazette order; the 2019 group is dated 2018 in one source (Nepal's fiscal year
  2075 BS spans both). The table keeps the earlier year and notes the second order.
- I could not download the PDFs directly from my build environment and transcribed them through a
  text reader. Each row should be checked against the PDF by a second person before real use;
  see docs/RESPONSIBLE_AI.md.
