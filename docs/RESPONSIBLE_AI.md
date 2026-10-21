# Responsible AI

## Intended use

Parkha is for vegetable and cereal farmers in Nepal, the agrovet shop staff they ask, and
municipal agriculture technicians. It answers three kinds of question: what to do about a pest
(non-chemical steps first), whether a product is banned, and when it is safe to harvest after
spraying. It is a decision aid that always points back to the Agriculture Knowledge Centre, not a
replacement for it.

**Not intended for:** pest identification from symptoms or photos, fungicide and herbicide
advice (the label table covers insecticides only), livestock or human health, or any use where
its answer replaces the product label.

## Who the errors hurt

| Error | Who is hurt | How Parkha leans |
|---|---|---|
| Harvest date too early | The people who eat the vegetables; the farmer, if the lot is destroyed at Kalimati | Never estimated: computed from the label, the longest row for the crop, counted from the last spray |
| A banned product recommended | The farmer and sprayer (most banned products are highly toxic), the household | The ban list overrides every label; the gate rejects any banned product named without "banned" |
| A dose too high | Sprayer, consumer, environment | Doses only as returned for that product, per ropani and kattha; never per tank |
| A product with no verified waiting period | Consumer | No date, no dose; "read the label, ask your AKC" |
| Refusing a legitimate question | The farmer, who goes back to guessing | Measured: no legitimate eval question is refused; 1 of 15 paraphrases rejected, on purpose |
| Missing a crisis | A person in crisis | Crisis is checked first, in three scripts, before anything else, and again by the guardrail |

When in doubt the system is built to be wrong in the direction of waiting longer and saying less.

## Crisis

Pesticide ingestion is the second leading cause of suicide in Nepal, after hanging (Nepal
Police data via The Kathmandu Post, December 2024); 952 people died that way in fiscal year
2023-24. A pesticide assistant will be asked how much is lethal. Parkha answers any crisis wording,
in English, Nepali or romanised Nepali, with a short, kind message and Nepal's national suicide
prevention helpline, **1166**, and suggests asking someone to lock pesticides away. It gives no
pesticide information in that answer, the question is never stored, and only a count reaches
CloudWatch (the CrisisAlarm tells a human to review the wording and reach).

The patterns are mine and have not been reviewed by a mental health professional. That review is
a condition for real use.

## Before anyone relies on it

1. **A second person checks every row of `data/labels.csv` and `data/nepal_banned.csv` against the
   source PDFs.** The gate can't catch a wrong row (FAILURE_MODES #14), and I transcribed them
   through a text reader.
2. **An agronomist reviews the 13 notes in `corpus/`** (`review_status` is "not reviewed" for all of
   them). The non-chemical steps are standard IPM practice, but I wrote them, and some specifics
   (trap spacing, sand or ash in maize whorls) should be checked against current Nepali guidance.
3. **A native Nepali reader reviews the Nepali templates and notes**, including whether the pest
   names (फौजी कीरा, हीरे पुतली, सुलसुले) are what farmers in the hills and the Terai actually say.
4. **A mental health professional reviews the crisis wording and patterns.**
5. **Run `make eval-bedrock`** and look at the fallback and rewrite rates in Nepali.

## Language coverage

Nepali (Devanagari), romanised Nepali and English. Maithili, Bhojpuri and Tharu, spoken by many
of the Terai's farmers, are not served. 15 of the 50 eval questions are Nepali or romanised; the
romanised detection is a heuristic that will miss some questions.

## Transparency

Every answer returns its sources (the note it was built on, the label document, the ban source)
so an agrovet or technician can check it. Answers say when Parkha has no verified waiting period
rather than filling the gap. The README and EVALUATION.md say what has and hasn't been measured.

## Privacy

Questions are stored with phone numbers redacted, for 30 days, to find bad answers and grow the
evaluation set from real questions. No accounts, no location. Crisis questions are never stored.
