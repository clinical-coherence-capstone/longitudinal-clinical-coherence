# Handoff for the capstone team

## How to consume this without confusing ingredients and products

1. **Join on `rxcui`, always as a string.** Never match on names or word overlap: `metformin` (IN 6809) is a different
   concept from `metformin hydrochloride 500 MG Oral Tablet` (SCD), from `metformin hydrochloride` (PIN, the salt) and from
   `alogliptin / metformin` (MIN).
2. **Check `tty` before using a concept as a medication target.** IN/PIN/MIN = ingredient-level; SCD = generic product (strength +
   dose form); SBD = branded product; BN = a brand name only. Evidence for an IN is not evidence for any one SCD.
3. **Compare medications by `ingredient_rxcuis`** (IN-level set), not by strings: that column is filled for every concept.
   Two concepts are the same *ingredient set* iff the sets are equal; they *overlap* iff the sets intersect (C8).
4. **Strength and dose form exist only on SCD/SBD** (`strength_components`, `dose_form`, `quantity_factor`). A blank on an
   IN/PIN/MIN row means not applicable, not missing.
5. **Respect relationship direction** in `relationships.csv`: read each row as `subject --rela--> object`.
6. **A failed lookup is an answer.** `input_aliases.csv` shows inputs that match nothing under exact matching. Do not
   fuzzy-match these into a concept; treat them as clarify/abstain cases for the verifier.
7. **Do not read `ndc_count_rxnorm` or `concept_ndc_rxnorm.csv` as label links.** They are the RxNorm side of a possible join only.

## DailyMed interface (pending; owner: DailyMed teammate)

RxNorm side provides: `rxcui`, `tty`, `rxnorm_name`, `ingredient_rxcuis`, `strength_components`, `dose_form`, `brand_name`,
and RxNorm-normalized 11-digit NDCs (`data/concept_ndc_rxnorm.csv`). The linkage is **not done**.
For each label the teammate should supply: set ID **and version/effective date** (RxNorm moves; a label changes), the
**ingredient list with active-moiety and strength per ingredient**, **dosage form**, **route**, **brand/proprietary name**,
**product NDC(s) and package NDC(s)**, **marketing category/application number**, and the label section the evidence came from.
A link may be marked verified only when ingredients, strength, dose form and (where relevant) brand of the *exact label
product* match the concept, with the NDC join used as a cross-check (NDC is package-level, so multiple NDCs per concept and
occasionally conflicting assignments are expected `[EXTERNAL]` Tech Doc sections 6-7). IN/PIN/MIN/BN concepts can link only to
ingredient-level evidence, never to a specific label product. Record unmatched labels explicitly instead of nearest-matching.

## Not to be claimed from this dataset

Clinical correctness of any statement; comprehensiveness; that exact-match behaviour predicts the behaviour of a real
medication linker; that the sample size supports statistical conclusions.
