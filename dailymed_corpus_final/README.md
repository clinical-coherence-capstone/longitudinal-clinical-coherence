# DailyMed Medication Evidence Corpus & Quality Audit Suite

**Capstone Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  
**Project ID:** PW_27_MHR_04  
**Project Guide:** Dr. Mamatha H R  
**Team Members:** Kruthika C B, Kavana P G, Sambhram M, Samrudh C Patil  
**Component:** Study 1 Ground-Truth Evidence Corpus (DailyMed Official Drug Labels)  

---

## 1. Project Overview

This repository houses the reproducible, traceable evidence corpus built from official FDA drug labeling on DailyMed (National Library of Medicine). It provides the ground-truth evidence layer used by the **Longitudinal Clinical Coherence Verifier** to test for:
1. **Target-Evidence Binding Failures** (e.g., attributing metformin boxed warnings to alogliptin or confusing metoprolol with metformin).
2. **Combination-Product Overextensions** (e.g., applying single-ingredient alogliptin renal dosing rules to fixed-dose combination tablets).
3. **Evidence Fidelity & Qualifier Preservation** (e.g., verifying that eGFR cutoffs, negations, and meal-timing constraints are preserved).
4. **Temporal Coherence / Stale Label Detection** (e.g., verifying detection of recent label safety updates).

---

## 2. Directory Structure

```text
dataset_Medpress/
├── README.md                                 # Reproducibility instructions and corpus overview
├── DailyMed_Corpus_Audit_Report.md           # Full audit report, quality metrics, and proposed pilot scope
├── label_manifest.csv                        # Manifest registering downloaded labels, URLs, dates, and hashes
├── medication_evidence.csv                   # Audited evidence units (CSV format)
├── medication_evidence.jsonl                 # Audited evidence units (JSONL format for verifier ingestion)
├── controlled_evidence_tests.csv             # Evaluation fixtures across all 7 mandatory failure modes
├── audit_script.py                           # Automated validator script for manifest and evidence records
├── limitations_and_open_questions.md         # Clinical caveats, unresolved issues, and review points
│
└── dailymed_corpus/                          # Structured archival directory
    ├── manifests/
    │   └── label_manifest.csv
    ├── processed/
    │   ├── medication_evidence.csv
    │   └── medication_evidence.jsonl
    ├── raw_labels/
    │   ├── 20260826_14d98490-4f8f-4d2f-a4e9-7a3d7a0199ba.pdf   # Original uncorrupted PDF (46 pages)
    │   └── 14d98490-4f8f-4d2f-a4e9-7a3d7a0199ba.xml           # Official Structured Product Labeling (SPL) XML
    ├── reports/
    │   ├── DailyMed_Corpus_Audit_Report.md
    │   └── audit_execution_summary.json
    ├── scripts/
    │   ├── audit_script.py                   # Automated validation suite
    │   ├── build_corpus_data.py              # Generator for structured evidence and test cases
    │   └── make_all.py                       # Manifest generator script
    └── tests/
        └── controlled_evidence_tests.csv
```

---

## 3. Environment and Dependencies

The corpus pipeline is designed to be completely reproducible with Python 3.10+ and standard or lightweight open-source packages:

- Python 3.10+ (tested on Python 3.14)
- `pypdf` (for PDF text and metadata verification)
- `lxml` (for parsing HL7 Structured Product Labeling XML)
- `requests` or standard `urllib` (for fetching DailyMed REST API endpoints)

To install dependencies:
```bash
pip install pypdf lxml requests pandas
```

---

## 4. Exact Reproduction Steps

### Step 1: Run the Automated Audit Validator
To verify that all manifest entries, raw label checksums, evidence fields, fidelity assertions, and test fixtures pass validation:

```bash
python audit_script.py
```
*Expected Output:*
```text
================================================================================
  DAILYMED MEDICATION EVIDENCE CORPUS AUTOMATED AUDIT SUITE
================================================================================
[1] MANIFEST INTEGRITY CHECK: 1 label(s) registered
    SHA-256 Verified: PDF (664172 bytes) & XML (312280 bytes)
[2] EVIDENCE RECORDS AUDIT: 24 units extracted
    Unique active ingredients: 3 ['Alogliptin', 'Alogliptin + Metformin hydrochloride', 'Metformin hydrochloride']
    Missing metadata fields: 0
    Manually reviewed & verified sample: 24 / 24 (100%)
[3] CLINICAL FIDELITY & QUALIFIER AUDIT
    [OK] All fidelity snippets and negations verified
[4] CONTROLLED EVIDENCE TEST FIXTURES: 8 test cases
    All 7 mandatory test failure modes covered
OVERALL AUDIT VERDICT: PASS [Traceable, Faithful, Reproducible]
```

### Step 2: Regenerate Evidence and Test Fixtures (Optional)
If modifying extraction rules or adding new evidence records:
```bash
python dailymed_corpus/scripts/build_corpus_data.py
python dailymed_corpus/scripts/audit_script.py
```

---

## 5. Schema Reference

### `medication_evidence.csv` / `.jsonl`
Each evidence record contains 18 standardized fields:
1. `evidence_id`: Unique persistent identifier (`DM-EV-ALOG-MET-###`).
2. `active_ingredient`: Target pharmacological active ingredient.
3. `product_name`: Exact product name from the FDA label.
4. `all_active_ingredients`: Semicolon-separated list of all ingredients in the formulation.
5. `dosage_form`: Physical dosage form (e.g. `tablet, film coated`).
6. `strength`: Labeled dosage strengths.
7. `labeler`: Manufacturer or labeler entity.
8. `dailymed_set_id`: Permanent GUID assigned by DailyMed.
9. `label_revision_date`: Date stated on the source label.
10. `access_date`: Retrieval date.
11. `section_name`: Official label section heading.
12. `evidence_text`: Faithful, unsummarized excerpt from the label.
13. `source_url`: Permanent DailyMed URL.
14. `source_locator`: Combined LOINC code, XML element UUID, and PDF page numbers.
15. `evidence_scope`: Categorization (`Combination product`, `Single ingredient`, or `Product-specific`).
16. `extraction_method`: Extraction mechanism (`SPL XML parser with manual clinical fidelity verification`).
17. `verification_status`: Status (`verified`).
18. `notes`: Contextual nuances and testing relevance.

---

## 6. Research Safety and Licensing Notice

- **Public Domain Data:** Drug labels on DailyMed are created under the auspices of the U.S. Food and Drug Administration and the National Library of Medicine. In the United States, they are public domain materials.
- **Academic Research Scope:** This corpus is prepared exclusively for academic evaluation of clinical NLP and multi-turn dialogue verification algorithms.
- **Non-Clinical Disclaimer:** This corpus is not a clinical decision support tool or an electronic prescribing system. It must not be used for direct human clinical diagnosis, patient management, or medication dispensing.
