# DDXPlus Dataset Audit — Reproducibility Guide

This repository directory contains the full audit suite and verified deliverables for the DDXPlus benchmark evaluation for our Capstone project:  
**“Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations.”**

---

## 1. Directory Structure

```text
Dataset Audit/
├── DDX Plus.zip                     # Original unmodified dataset distribution archive
├── DDX Plus/                        # Extracted original source files
│   ├── release_conditions.json      # 49 pathology definitions & triage severities
│   ├── release_evidences.json       # 223 clinical evidence questions & value sets
│   ├── release_train_patients.zip   # Nested training archive (1,025,602 cases)
│   ├── release_validate_patients.zip# Nested validation archive (132,448 cases)
│   └── release_test_patients.zip    # Nested test archive (134,529 cases)
├── audit_scripts/                   # High-performance Node.js audit scripts
│   ├── audit_conditions.js          # Audits release_conditions.json
│   ├── audit_evidences.js           # Audits release_evidences.json
│   ├── case_decoder.js              # Translates raw tokens to human clinical vignettes
│   ├── audit_validation_split.js    # Streams & audits validation split (132k cases)
│   ├── audit_test_split.js          # Streams & audits test split & Val-Test leakage
│   ├── audit_train_split.js         # Streams & audits train split & global leakage
│   ├── generate_inventory.js        # Generates 01_file_inventory.csv
│   └── generate_profile_deliverables.js # Generates split, condition, & issue CSVs
├── audit_output/                    # Verified Audit Deliverables
│   ├── 01_file_inventory.csv        # Task A: Complete file inventory & SHA-256
│   ├── 02_schema_report.md          # Task B: Empirical dataset schema
│   ├── 03_mapping_validation.md     # Task C: Evidence & condition mapping report
│   ├── 04_dataset_profile.md        # Task D: Comprehensive profiling report
│   ├── 05_leakage_and_duplicates.md # Task E: Cross-split leakage & duplicate report
│   ├── 06_multi_turn_suitability.md # Task F: Multi-turn experimental forms report
│   ├── 07_error_injection_design.md # Task G: Error injection & verifier schema
│   ├── 08_documentation_and_limitations.md # Task H: License & limitations report
│   ├── condition_mapping_summary.csv# Task C: All 49 conditions tabular map
│   ├── evidence_mapping_summary.csv # Task C: All 223 evidences tabular map
│   ├── condition_distribution.csv   # Task D: Class frequencies across splits
│   ├── split_summary.csv            # Task D: Cross-split metrics comparison
│   ├── data_quality_issues.csv      # Task D: Structured data quality log
│   ├── val_split_summary.json       # Raw validation split metrics
│   ├── test_split_summary.json      # Raw test split metrics
│   └── train_split_summary.json     # Raw train split metrics
├── DDXPlus_Audit_Report.md          # Complete Final Executive Audit Report
└── README.md                        # This reproducibility documentation
```

---

## 2. Software and Environment Requirements

* **Operating System:** Windows 10/11 x64
* **Node.js:** v24.20.0 (or v16.0.0+)
* **PowerShell:** 5.1+ (or PowerShell Core 7+)
* **Zero External NPM Dependencies:** All audit scripts are authored using native Node.js standard modules (`fs`, `readline`, `crypto`, `path`) to guarantee frictionless reproducibility without `npm install` failures.

---

## 3. Step-by-Step Reproduction Commands

To reproduce the entire audit from scratch, run these commands from the `Capstone` workspace root:

```powershell
# 1. Audit Condition Reference Knowledge Base
node "Dataset Audit/audit_scripts/audit_conditions.js"

# 2. Audit Evidence Reference Knowledge Base
node "Dataset Audit/audit_scripts/audit_evidences.js"

# 3. Test Human-Readable Case Vignette Decoder
node "Dataset Audit/audit_scripts/case_decoder.js"

# 4. Audit Validation Split (132,448 cases)
node "Dataset Audit/audit_scripts/audit_validation_split.js"

# 5. Audit Test Split and Val-Test Leakage (134,529 cases)
node "Dataset Audit/audit_scripts/audit_test_split.js"

# 6. Audit Train Split and Global Leakage (1,025,602 cases)
node "Dataset Audit/audit_scripts/audit_train_split.js"

# 7. Generate Profile Tables and Final Inventory
node "Dataset Audit/audit_scripts/generate_inventory.js"
node "Dataset Audit/audit_scripts/generate_profile_deliverables.js"
```

---

## 4. Key Verification Findings Summary

1. **Total Population:** **1,292,579 records** (1,025,602 Train, 132,448 Val, 134,529 Test).
2. **Missing / Corrupted Data:** **0.00%** across the entire corpus.
3. **Evidence Key Resolution:** **100.00%** (0 unresolved tokens across 25.56 million evaluations).
4. **Class Imbalance:** 251.6 : 1 ratio between URTI (81,767) and Bronchiolitis (325).
5. **Cross-Split Leakage:** 5,525 Train-Val duplicates, 6,167 Train-Test duplicates, and 509 Val-Test duplicates.
6. **Verdict:** **CONDITIONAL GO** (requires deduplication hash filter and severity-stratified sampling).
