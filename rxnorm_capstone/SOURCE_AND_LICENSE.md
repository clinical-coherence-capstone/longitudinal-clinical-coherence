# Source and licensing note

Evidence kept separate: **[ARCHIVE]** = read from the uploaded ZIP; **[EXTERNAL]** = NLM documentation pages inspected on 2026-10-26.
This is a project note, not legal advice.

## [ARCHIVE] Release
`RxNorm_full_prescribe_10052026.zip` (RxNorm Current Prescribable Content, README dated October 05, 2026, built from the October 05, 2026 Full Release). SHA-256 is in `reports/validation_report.json`. The archive README gives no licence text beyond pointing to NLM documentation.

## [EXTERNAL] Pages actually fetched (full page text read)
| Page | Used for | Page "last reviewed" |
|---|---|---|
| https://www.nlm.nih.gov/research/umls/rxnorm/docs/techdoc.html | file/field layouts (12.4, 12.5, 12.7), RELA direction rule, prescribable subset (11.6), NDC/UNII notes, source restriction levels | 2023-11-07 |
| https://www.nlm.nih.gov/research/umls/rxnorm/docs/appendix1.html | documented (TTY, RELA, TTY) relationship pairs | 2025-11-17 |
| https://www.nlm.nih.gov/research/umls/rxnorm/docs/appendix5.html | term-type definitions | 2024-08-02 |
| https://www.nlm.nih.gov/research/umls/rxnorm/docs/termsofservice.html | usage terms | 2022-01-31 |

## [EXTERNAL] Seen only as search-result snippets (primary page NOT fetched; treat as weakly verified)
* https://www.nlm.nih.gov/research/umls/rxnorm/docs/prescribe.html (mirror snippets): CVF=4096 marks the prescribable subset.
* https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html (mirror snippet): files since May 2020 are consistent with the 2020AA UMLS; prescribable ZIP listed as "no license required".
* https://www.nlm.nih.gov/databases/umls.html: UMLS licence required for full releases.

## Usage terms (paraphrased from the Terms of Service)
* RxNorm names and codes (RXCUIs) are US-government-created and public domain; NLM asks for acknowledgement.
* The full release contains proprietary source data with restriction levels; a free UMLS licence is needed for the full release. The prescribable subset used here is documented as downloadable without a licence and contains SAB=RXNORM, MTHSPL and MTHCMSFRF content (Tech Doc 11.6; SRL 0 for these sources, Tech Doc 3.1). Only SAB=RXNORM strings and relationships are copied into this dataset.
* Requested: include NLM's attribution statement in any product using RxNorm (copy the exact wording from the Terms of Service page above), do not imply NLM endorsement or use the NLM name/logo, and keep data current or clearly say it is not.
* Cite: Nelson SJ, Zeng K, Kilbourne J, Powell T, Moore R. RxNorm at 6 years. J Am Med Inform Assoc 2011;18(4):441-448, doi:10.1136/amiajnl-2011-000116.
* Redistribution of this dataset: it is derived from a single dated release; label it with the release date and state that it does not reflect later releases.

## Not verified
UMLS Metathesaurus licence text; 2026 release notes; an NLM checksum for this ZIP.
