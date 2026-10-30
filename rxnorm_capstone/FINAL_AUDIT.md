# Final scientific audit (generated)

Critical checks failing: none

Overall: PASS 26, FAIL 1 (A4: cosmetic README size discrepancy in the vendor README, non-critical), NOT_VERIFIED 3.

| Audit question | Status | Supporting source / check |
|---|---|---|
| Are all reported RxCUIs supported by the actual uploaded release? | PASS | checks D1 (unique expected-TTY resolution), D3 (name = SAB=RXNORM atom), D4 (SUPPRESS=N, CVF=4096), B2; source line in `concepts.csv`. D2 pins are same-release, so not independent |
| Are terminology types and relationships interpreted correctly? | PASS | B4 direction/TTY pairs vs Appendix 1 over all exported-type rows; E2, E4; E1 cross-paths. Appendix 1 pair table transcribed by hand (3 omissions found and fixed during the run) - re-check if NLM changes it |
| Are ingredient concepts and drug products kept distinct? | PASS | separate rows/TTYs; contrast checks K01-K03; ingredient sets only through RXNREL; independent name-substring recount matched for 5/5 ingredients |
| Any mappings ambiguous, duplicate or unsupported? | PASS | 0 duplicates, 0 unresolved seeds; 11 probe inputs deliberately unresolved; 0 multi-concept string collisions exist in the subset (so MULTIPLE never occurs) |
| Does the dataset genuinely cover the planned identity contrasts? | PASS | C1-C9, C11 pass 21/21 checks; C10 covers non-matching inputs only. Cross-turn swap is a conversation property: NOT COVERED by terminology alone |
| Is the number of concepts justified for the intended scope? | PASS | 29 concepts derived from the coverage plan for a starter resource; this is not an evaluation sample-size justification |
| Is sufficiency for experiments / evaluation established? | NOT VERIFIED | needs more families, look-alike/sound-alike pairs from an external list, conversation test set and its own power analysis |
| Are all counts derived programmatically? | PASS | metrics computed in `build_rxnorm_component.py`; I1 recount from written CSVs; `render_docs.py` recounts again and aborts on mismatch |
| Are README and code consistent with the actual CSV? | PASS | README generated from the data; byte-identical rerun verified manually |
| Are limitations, licensing conditions and provenance documented? | PASS | README sections 2/10, `SOURCE_AND_LICENSE.md`; licensing text taken from RxNorm Terms of Service (last reviewed 2022-01-31); the UMLS license itself was not inspected; not legal advice |
| Is the DailyMed linkage correctly marked pending? | PASS | check H1; no set IDs populated |
| Release-notes counts for 10/05/2026 match this archive? | NOT VERIFIED | X1: no 2026 release notes retrieved |
| Archive authenticity versus an official checksum? | NOT VERIFIED | X2: SHA-256 recorded locally, no NLM checksum retrieved for this file |
| Semantic type per concept? | NOT VERIFIED | X3: RXNSTY.RRF not in the prescribable ZIP |
| Archive not modified by the run? | PASS | I3 hash before == after |

## Machine checks (from `reports/validation_report.json`)

| ID | Status | Critical | Check | Detail |
|---|---|---|---|---|
| A1 | PASS | True | Archive contains RXNCONSO/RXNREL/RXNSAT.RRF and a README | all present |
| A2 | PASS | True | README states a release date matching the ZIP file name (10052026 = October 05, 2026) | {"readme_title_date": "10/05/2026", "readme_full_release_date": "October 05, 2026", "readme_first_line": "October 05, 2026"} |
| A3 | PASS | True | RRF file sizes listed in the archive README equal actual sizes | {"RXNCONSO.RRF": 30680217, "RXNREL.RRF": 198901737, "RXNSAT.RRF": 284273759} |
| A4 | FAIL | False | README declared size of itself equals actual size | declared 1035 vs actual 3073 (cosmetic: README text edited after size was written) |
| B1 | PASS | True | RXNCONSO/RXNREL lines have exactly the documented field count with a trailing delimiter | {"RXNCONSO.RRF": {"lines": 247028, "malformed_lines": 0}, "RXNREL.RRF": {"lines": 2589722, "malformed_lines": 0}} |
| B2 | PASS | True | Each RXNORM concept has at most one main-term-type atom (Appendix 5 statement) | violations: 0 |
| B3 | PASS | True | Prescribable subset contains no suppressed/obsolete RXNCONSO rows (SUPPRESS=N, CVF=4096 everywhere) | {"suppress:N": 247028, "cvf:4096": 247028} |
| B6 | PASS | True | RXNREL CUI-level RXNORM rows: SUPPRESS values are only blank or N (blank = 'not yet in use' per Tech Doc 12.7) | {"": 553500} |
| B4 | PASS | True | Relationship direction (subject=RXCUI2, object=RXCUI1) agrees with Appendix 1 TTY pairs across all exported-RELA CUI-level rows in the subset | 361048/361048 rows documented; undocumented pairs: {} |
| D1 | PASS | True | Every seed concept resolves to exactly one RXNORM concept of the expected term type (no substitution) | 29/29 resolved |
| D2 | PASS | True | Resolved RXCUIs equal the RXCUIs pinned in config (regression check; pins were taken from this same release, so this detects drift between releases, not independent truth) | mismatches: [] |
| D3 | PASS | True | For every selected concept the input name equals the SAB=RXNORM normalized-name atom (not just a synonym) | mismatches: [] |
| D4 | PASS | True | Selected concepts' main atoms are SUPPRESS=N and CVF=4096 | violations: [] |
| E1 | PASS | True | Every selected concept: ingredient chain resolved via RXNREL; each SCD/SBD has exactly one dose form, strength components and (SBD) one brand; names are consistent with relationship-derived components; cross-paths (SCDC-path vs MIN-path, SBD vs its generic SCD) agree | problems: [] |
| E2 | PASS | True | All exported relationship rows are of a (subject TTY, RELA, object TTY) combination documented in Appendix 1 (and at least one row was exported) | undocumented: 0 of 368 |
| E3 | PASS | True | No duplicate relationship identifiers (RUI) in relationships.csv (non-empty set) | 368 rows |
| E4 | PASS | True | Every exported relationship row has its inverse-direction row in the exported set (RxNorm stores one row per direction) | rows lacking inverse: 0 of 368 |
| B5 | PASS | True | RXNSAT lines have exactly the documented field count with a trailing delimiter | {"lines": 3382290, "malformed_lines": 0} |
| E5 | PASS | True | No duplicate RXCUI rows in concepts.csv | 29 rows |
| F1 | PASS | False | Probe/canonical inputs behave as designed where an expectation was declared (UNIQUE/NONE); OBSERVE inputs carry no expectation | mismatches: [] |
| E6 | PASS | True | Every selected SCD/SBD has at least one verified ingredient link | 14 products checked |
| G2 | PASS | True | Every selected IN/MIN concept is contained in more than one SCD in the subset (ingredient-level mention is not product-unique) | alogliptin=10; hydrochlorothiazide=71; metformin=70; metoprolol=19; sitagliptin=19; alogliptin / metformin=2; hydrochlorothiazide / metoprolol=3; metformin / si |
| G1 | PASS | True | All declared contrast checks hold on relationship-derived data | 21/21 pass; failing: [] |
| H1 | PASS | True | No DailyMed set ID is populated; all link statuses are PENDING_NOT_VERIFIED |  |
| I1 | PASS | True | Headline counts recomputed from the written CSV files equal the counts in the validation report |  |
| I2 | PASS | True | Required concept fields are non-empty and RXCUIs are numeric | empty: [] |
| I3 | PASS | True | Source ZIP SHA-256 identical before and after the run (archive not modified) | 8ed351c29f3cb56bedeb8e2bcb8fa56931f8d7eb88e2280dc9772d7d3eb16977 |
| X1 | NOT_VERIFIED | True | Release notes data counts (TTY counts, NDC counts) for the 10/05/2026 release compared with this archive | No 2026 release-notes page could be retrieved; official page not inspected for this release |
| X2 | NOT_VERIFIED | True | ZIP authenticity versus an NLM-published MD5/SHA for RxNorm_full_prescribe_10052026.zip | No published checksum for this file was retrieved; local SHA-256 recorded for future comparison |
| X3 | NOT_VERIFIED | True | Semantic type (STY) per concept | RXNSTY.RRF is not part of the Current Prescribable Content ZIP; concept_type is derived from TTY (Appendix 5) only |

## Still incomplete

* DailyMed linkage (teammate-owned).
* Release-notes comparison, official checksum comparison, semantic types (X1-X3).
* Broader concept coverage and look-alike/sound-alike pairs from an authoritative external list.
* Pack concepts (GPCK/BPCK) and non-oral forms.
* Conversation-level test set for cross-turn medication swaps (outside this component).
* Independent human review of the contrast pairs by a pharmacist or terminology specialist.
