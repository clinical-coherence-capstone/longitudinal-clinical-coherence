# Coverage matrix (generated)

| ID | Contrast | Concepts/inputs | Checks pass | Failure mode it supports testing | What it does NOT establish |
|---|---|---|---|---|---|
| C1 | ingredient_vs_product | 4 | 3/3 | An ingredient-level fact treated as evidence about one specific strength/dose form (or vice versa) | Does not show which product a patient actually takes; does not show the evidence is correct |
| C2 | single_vs_combination | 4 | 2/2 | Evidence about a single agent attributed to its combination product (or the reverse) | Does not show the clinical statement is wrong, only that the two targets are distinct concepts |
| C3 | strength_variants_same_combination | 2 | 1/1 | Strength-specific evidence attributed to the wrong strength variant of the same combination | Does not model titration, dosing schedule, or clinical appropriateness of a strength |
| C4 | strength_variants_single_ingredient | 6 | 3/3 | Strength-level confusion within one ingredient | Same as C3; only two variants per ingredient are sampled, not all |
| C5 | dose_form_variants | 4 | 2/2 | Evidence for one release profile attributed to another | Does not encode pharmacokinetics or interchangeability |
| C6 | salt_form_precise_ingredient | 6 | 2/2 | Treating salt forms as identical, or as different drugs, without the verifier knowing which | Whether salt forms are clinically interchangeable is not represented in RxNorm |
| C7 | distinct_medication_wrong_target | 3 | 2/2 | Evidence about drug A attributed to drug B after a later-turn target switch | RxNorm shows distinctness only; turn structure and the attribution error come from other data |
| C8 | shared_ingredient_different_partner | 7 | 3/3 | Partial-overlap confusion, e.g. evidence for one combination attributed to another sharing an ingredient | Overlap is detected structurally; clinical relevance of the overlap is not represented |
| C9 | brand_vs_generic | 6 | 3/3 | Brand/generic identity handling; same ingredients and strength but different concepts | Does not establish label equivalence or that a DailyMed label corresponds to the concept |
| C10 | underspecified_or_nonmatching_input | 11 | 4/4 | Forced matching of an underspecified or differently-worded medication mention | Exact string matching only; not a measure of how a real linking system behaves. No string in this subset maps to more than one RXCUI, so multi-concept string ambiguity is not represented |
| C11 | ingredient_level_mention_fanout | 8 | 8/8 | Treating an ingredient-level mention as sufficient to identify one specific product (strength/dose form) | Fan-out is counted over the Current Prescribable Content subset only; it is not a count of all products ever marketed |

## Members per contrast

**C1 ingredient_vs_product**: alogliptin [IN 1368001]; metformin [IN 6809]; metoprolol [IN 6918]; metformin hydrochloride 500 MG Oral Tablet [SCD 861007]

**C2 single_vs_combination**: alogliptin [IN 1368001]; alogliptin / metformin [MIN 1368384]; alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet [SCD 1368392]; alogliptin 12.5 MG Oral Tablet [SCD 1368034]

**C3 strength_variants_same_combination**: alogliptin 12.5 MG / metformin hydrochloride 1000 MG Oral Tablet [SCD 1368385]; alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet [SCD 1368392]

**C4 strength_variants_single_ingredient**: alogliptin 12.5 MG Oral Tablet [SCD 1368034]; alogliptin 25 MG Oral Tablet [SCD 1368006]; metformin hydrochloride 1000 MG Oral Tablet [SCD 861004]; metformin hydrochloride 500 MG Oral Tablet [SCD 861007]; metoprolol tartrate 25 MG Oral Tablet [SCD 866924]; metoprolol tartrate 50 MG Oral Tablet [SCD 866514]

**C5 dose_form_variants**: 24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet [SCD 860975]; 24 HR metoprolol succinate 25 MG Extended Release Oral Tablet [SCD 866427]; metformin hydrochloride 500 MG Oral Tablet [SCD 861007]; metoprolol tartrate 25 MG Oral Tablet [SCD 866924]

**C6 salt_form_precise_ingredient**: alogliptin benzoate [PIN 1368000]; metformin hydrochloride [PIN 235743]; metoprolol succinate [PIN 221124]; metoprolol tartrate [PIN 203191]; 24 HR metoprolol succinate 25 MG Extended Release Oral Tablet [SCD 866427]; metoprolol tartrate 25 MG Oral Tablet [SCD 866924]

**C7 distinct_medication_wrong_target**: metformin [IN 6809]; metoprolol [IN 6918]; metoprolol tartrate 50 MG Oral Tablet [SCD 866514]

**C8 shared_ingredient_different_partner**: hydrochlorothiazide [IN 5487]; metoprolol [IN 6918]; sitagliptin [IN 593411]; alogliptin / metformin [MIN 1368384]; hydrochlorothiazide / metoprolol [MIN 214621]; metformin / sitagliptin [MIN 729717]; hydrochlorothiazide 25 MG / metoprolol tartrate 50 MG Oral Tablet [SCD 866482]

**C9 brand_vs_generic**: Kazano [BN 1372692]; Lopressor [BN 203344]; Nesina [BN 1368007]; alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet [Kazano] [SBD 1368398]; alogliptin 25 MG Oral Tablet [Nesina] [SBD 1368012]; metoprolol tartrate 50 MG Oral Tablet [Lopressor] [SBD 866516]

**C10 underspecified_or_nonmatching_input**: metformin HCl -> NONE; alogliptin and metformin -> NONE; alogliptin metformin -> NONE; metformin / alogliptin -> NONE; alogliptin 12.5 mg / metformin 500 mg -> NONE; metoprolol 50 mg -> NONE; metoprolol / hydrochlorothiazide -> NONE; sitagliptin / metformin -> NONE; Toprol XL -> NONE; metformin 500 mg oral tablet -> NONE; metformin extended release -> NONE

**C11 ingredient_level_mention_fanout**: alogliptin [IN 1368001]: 10 SCDs; hydrochlorothiazide [IN 5487]: 71 SCDs; metformin [IN 6809]: 70 SCDs; metoprolol [IN 6918]: 19 SCDs; sitagliptin [IN 593411]: 19 SCDs; alogliptin / metformin [MIN 1368384]: 2 SCDs; hydrochlorothiazide / metoprolol [MIN 214621]: 3 SCDs; metformin / sitagliptin [MIN 729717]: 10 SCDs

## Contrast check detail

| Check | Contrast | Predicate | A | B | Result |
|---|---|---|---|---|---|
| K01 | C1 | ingredient_in | metformin (6809) | metformin hydrochloride 500 MG Oral Tablet (861007) | PASS |
| K02 | C1 | ingredient_in | alogliptin (1368001) | alogliptin 12.5 MG Oral Tablet (1368034) | PASS |
| K03 | C1 | ingredient_in | metoprolol (6918) | metoprolol tartrate 50 MG Oral Tablet (866514) | PASS |
| K04 | C2 | ingredient_proper_subset | alogliptin 12.5 MG Oral Tablet (1368034) | alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet (1368392) | PASS |
| K05 | C2 | ingredient_proper_subset | alogliptin (1368001) | alogliptin / metformin (1368384) | PASS |
| K06 | C3 | same_ingredients_diff_strength | alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet (1368392) | alogliptin 12.5 MG / metformin hydrochloride 1000 MG Oral Tablet (1368385) | PASS |
| K07 | C4 | same_ingredients_diff_strength | metformin hydrochloride 500 MG Oral Tablet (861007) | metformin hydrochloride 1000 MG Oral Tablet (861004) | PASS |
| K08 | C4 | same_ingredients_diff_strength | alogliptin 12.5 MG Oral Tablet (1368034) | alogliptin 25 MG Oral Tablet (1368006) | PASS |
| K09 | C4 | same_ingredients_diff_strength | metoprolol tartrate 25 MG Oral Tablet (866924) | metoprolol tartrate 50 MG Oral Tablet (866514) | PASS |
| K10 | C5 | same_ingredients_diff_doseform | metformin hydrochloride 500 MG Oral Tablet (861007) | 24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet (860975) | PASS |
| K11 | C5 | same_ingredients_diff_doseform | metoprolol tartrate 25 MG Oral Tablet (866924) | 24 HR metoprolol succinate 25 MG Extended Release Oral Tablet (866427) | PASS |
| K12 | C6 | same_ingredient_diff_pin | metoprolol tartrate (203191) | metoprolol succinate (221124) | PASS |
| K13 | C6 | same_ingredient_diff_pin | metoprolol tartrate 25 MG Oral Tablet (866924) | 24 HR metoprolol succinate 25 MG Extended Release Oral Tablet (866427) | PASS |
| K14 | C7 | ingredient_sets_disjoint | metformin (6809) | metoprolol (6918) | PASS |
| K15 | C7 | ingredient_sets_disjoint | metformin hydrochloride 500 MG Oral Tablet (861007) | metoprolol tartrate 50 MG Oral Tablet (866514) | PASS |
| K16 | C8 | share_exactly_one_ingredient | alogliptin / metformin (1368384) | metformin / sitagliptin (729717) | PASS |
| K17 | C8 | ingredient_proper_subset | metoprolol (6918) | hydrochlorothiazide / metoprolol (214621) | PASS |
| K18 | C8 | ingredient_proper_subset | metoprolol tartrate 50 MG Oral Tablet (866514) | hydrochlorothiazide 25 MG / metoprolol tartrate 50 MG Oral Tablet (866482) | PASS |
| K19 | C9 | brand_of | alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet (1368392) | alogliptin 12.5 MG / metformin hydrochloride 500 MG Oral Tablet [Kazano] (1368398) | PASS |
| K20 | C9 | brand_of | alogliptin 25 MG Oral Tablet (1368006) | alogliptin 25 MG Oral Tablet [Nesina] (1368012) | PASS |
| K21 | C9 | brand_of | metoprolol tartrate 50 MG Oral Tablet (866514) | metoprolol tartrate 50 MG Oral Tablet [Lopressor] (866516) | PASS |

The cross-turn category (a medication in a later turn that differs from an earlier one) is **not** a terminology property: C7/C8 supply the identity pairs that such conversation tests can draw on, nothing more.
