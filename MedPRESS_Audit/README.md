# MedPRESS – access steps (as of 2026-10-27)

**Status: dataset NOT yet downloaded by us. Do these steps yourself and record what you see.**

1. Make a free Hugging Face account using YOUR OWN details (never someone else's).
2. Open https://huggingface.co/datasets/samanjoy2/MedPRESS_Benchmark
3. The page is gated: read the access agreement, then accept it only if you are comfortable with its terms. Screenshot the agreement text (this is useful evidence for the "License unclear" finding).
4. After access, record: license shown (if any), files list, number of rows, column names.
5. What the dataset card says (NOT yet checked against real files): 600 English cases; CSV; 3 files in `Data/` (200 rows each, one per scenario family); 12 columns: case_id, scenario_family, topic, unsafe_or_false_belief, safe_stance_summary, 5 turn columns, triage_needed, triage_trigger. Total ~1.05 MB.
6. Compare with the paper: 600 cases, 3 families x 200, 20 topics per family x 10 variants (paper p.3).
7. Do not re-upload the data to a public repo until the license is clear.
8. Note: the card's loading example may use a different repo name than the page. Check the repo path before running `load_dataset`.

## Files in this folder
MedPRESS_Feasibility_Report.md, MedPRESS_Source_Links.md, MedPRESS_Suitability_Table.csv, README.md, tools/check_medpress.py

## How we checked it (28 Oct 2026)
1. Download the 3 CSVs from the repo's `Data/` folder into `MedPRESS_raw/`. Do not edit or re-save them.
2. Run `python check_medpress.py MedPRESS_raw` (needs Python + pandas). It is read-only.
3. Output: row counts, columns, duplicate IDs, empty cells, topics, triage counts. Results are in the Feasibility Report, section 3b.
4. The card's example code says `samanjoy2/medpress_dataset` / `split="test"`; the repo is `MedPRESS_Benchmark`. We did not use that code.
