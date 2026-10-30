# Comprehensive Dataset Audit Report: DDXPlus

**Project Title:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  
**Audit Conducted:** October 26–27, 2026  
**Auditor:** Antigravity Data Audit Engine  
**Dataset Under Review:** DDXPlus (NeurIPS 2022 Benchmark Release)  

---

## 1. Executive Summary

We have performed an exhaustive, reproducible data audit of the DDXPlus benchmark dataset to evaluate its scientific suitability for constructing controlled multi-turn clinical LLM experiments.

Across all 5 top-level archive components and 3 nested patient splits, we inspected and verified **1,292,579 individual patient cases**, **25,559,788 clinical evidence tokens**, **49 condition definitions**, and **223 evidence question mappings**. 

### Verdict & Final Recommendation
* **Pilot Feasibility Recommendation:** **CONDITIONAL GO**
* **Core Strengths:**
  1. Complete structural integrity: **0% missing values**, **0% corrupted fields**, and **100.00% evidence and condition mapping resolution** across the entire 1.29M-patient corpus.
  2. Substantial clinical feature depth (mean of **19.8 positive findings per case**, max 47), perfectly supporting 5 to 8 interactive conversational dialogue turns.
  3. Stable, physician-curated Bayesian differential diagnosis priors with 100.00% ground-truth retention and 92.87% Top-3 diagnostic accuracy.
* **Mandatory Pre-Implementation Resolutions:**
  1. **Cross-Split Leakage Deduplication:** We discovered **6,167 leaked cases between Train and Test** and **509 leaked cases between Validation and Test**. Evaluated test cases must be filtered using our deterministic deduplication hash protocol.
  2. **Stratified Class Sampling:** The dataset exhibits an extreme **251.6 : 1 class imbalance** between common viral infections (URTI: 6.33%) and rare critical conditions (Bronchiolitis: 0.025%). Test scenarios must be sampled using stratified quotas across the 5 clinical triage severity tiers.
  3. **Lexical Normalization Layer:** The evaluation harness must incorporate alias mappings for condition typos (e.g. `"Larygospasm"` $\rightarrow$ `"Laryngospasm"`) and split composite ICD-10 codes (`"j17, j18"`).

---

## 2. Dataset Inventory and Verified Record Counts

All checksums (SHA-256) and record counts were computed empirically via read-only stream inspection of the provided files:

| File / Archive Path | Storage Format | Size (Bytes) | Verified Records | SHA-256 Checksum | Parsing Status |
| :--- | :--- | :---: | :---: | :--- | :---: |
| `DDX Plus.zip` (Parent Archive) | ZIP Archive | 178,758,020 | 5 entries | `4b051d9cbf5c9942ce0df86801ef73f13d633ea4395da93d950912711c21e6e2` | OK |
| `release_conditions.json` | JSON (UTF-8) | 20,889 | 49 conditions | `56edf4682d8e86a4209fc3a33932e50ce03d1cc1fecc326c26d5ef8fa5c24890` | OK |
| `release_evidences.json` | JSON (UTF-8) | 120,263 | 223 evidences | `281c78b044ae60514e28ecc9052d08a8225dd3e2db3f00f8788b99c47b05e0c0` | OK |
| `release_train_patients.zip` | ZIP (Nested) | 140,923,730 | 1 CSV | `174ae1d56f36a15b7144838ecd214e1e1748a5369fc90c559529b6dc6ecfb218` | OK |
| $\llcorner$ `release_train_patients` | CSV (Uncompressed)| 670,584,506 | **1,025,602** | `93933e9a9a7a00d618a931deda7767485af299fe4635bf189a7c63b510e8b172` | OK |
| `release_validate_patients.zip` | ZIP (Nested) | 18,706,053 | 1 CSV | `625a96855becf0efe5da339fd3d440aa99597d48f784957a97dacc3fceaa7e40` | OK |
| $\llcorner$ `release_validate_patients` | CSV (Uncompressed)| 87,371,169 | **132,448** | `b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed` | OK |
| `release_test_patients.zip` | ZIP (Nested) | 18,986,243 | 1 CSV | `ad3bb981f3453fd7abffb35cc595a1c02197e409c581bff97c1265c33eb00d23` | OK |
| $\llcorner$ `release_test_patients` | CSV (Uncompressed)| 88,582,473 | **134,529** | `f7ac3eae934c85780fc9b109a6cac5771540619a02690bee6fc0ab402baec186` | OK |
| **Total Patient Population** | — | **846,538,148** | **1,292,579** | — | **100% OK** |

---

## 3. Schema & Mapping Validation

### 3.1 Coded Token Grammar
DDXPlus compresses clinical evidence using a 3-way token grammar:
* **Binary (`B`) — 208 items (93.3%):** Plain evidence key (e.g. `'E_91'` = Fever). Absent evidence implies negative (`0`).
* **Multi-Choice (`M`) — 5 items (2.2%):** Encoded with delimiter `_@_` mapping to 165 spatial body locations (e.g. `'E_55_@_V_25'` = Pain in Epigastrium).
* **Categorical / Ordinal (`C`) — 10 items (4.5%):** Visual analog scales 0–10 (e.g. `'E_56_@_2'` = Pain intensity 2/10) or discrete options (`'E_204_@_V_7'` = Travel to SE Asia).

### 3.2 Resolution Integrity
* **Evidence Key Resolution:** 100.00% of 25.56 million evaluated patient tokens resolved without a single orphan or unmapped ID.
* **Condition Key Resolution:** 100.00% of patient pathology labels resolved to `release_conditions.json`.
* **Deprecation Gap:** 5 gapped IDs exist in the evidence sequence (`E_36`, `E_68`, `E_85`, `E_117`, `E_122`), requiring dictionary-key iteration rather than integer range loops.

---

## 4. Data Quality & Class Distribution Results

### 4.1 Demographic Balance
The dataset reflects consistent cross-split demographics:
* **Age:** Continuous range from 0 to 109 years (Mean: 39.7 years; Median: 39 years). Cohorts: 18.3% Pediatric (0–17), 66.8% Adult (18–64), 14.8% Geriatric (65+).
* **Sex:** 51.5% Female (665,273 cases) vs. 48.5% Male (627,306 cases).

### 4.2 Severe Class Imbalance
While all 49 conditions are represented, class frequencies range from over 81,000 cases to fewer than 350 cases across the corpus:
* **Top 3 Common Conditions:** URTI (81,767 cases - 6.33%), Viral pharyngitis (78,222 cases - 6.05%), Anemia (64,410 cases - 4.98%).
* **Bottom 3 Rare Conditions:** Croup (3,463 cases - 0.27%), Ebola (908 cases - 0.07%), Bronchiolitis (325 cases - 0.025%).
* **Imbalance Ratio:** **251.6 : 1**.

---

## 5. Duplicate and Leakage Findings

Because cases lack unique identifiers, we hashed cases by `(Age, Sex, Pathology, Sorted_Evidences)`:
1. **Intra-Split Redundancy:**
   * Train: 29,823 duplicate cases (2.91%)
   * Validation: 216 duplicate cases (0.16%)
   * Test: 270 duplicate cases (0.20%)
2. **Cross-Split Leakage:**
   * **Train $\leftrightarrow$ Validation:** 5,525 identical cases (0.54% of Train).
   * **Train $\leftrightarrow$ Test:** 6,167 identical cases (0.60% of Train).
   * **Validation $\leftrightarrow$ Test:** 509 identical cases (0.38% of Test).
3. **Scientific Impact:** Leaked cases must be purged from the benchmark evaluation set to prevent artificial memorization.

---

## 6. Multi-Turn Suitability Assessment (The 3 Forms)

We evaluated representative patient cases across 3 experimental forms:
1. **Form 1 (Complete-Context Control):** All ~20 findings provided in a single prompt block. Serves as the performance upper-bound.
2. **Form 2 (Gradual Reveal):** Facts partitioned into 4 clinical stages (Chief Complaint $\rightarrow$ Characterization $\rightarrow$ Review of Systems $\rightarrow$ History/Meds). Tests state tracking.
3. **Form 3 (Pushback / Correction):**
   * *Legitimate Correction:* Patient corrects a doctor's mistaken finding; verifier tests if the LLM updates its differential appropriately.
   * *Adversarial Sycophancy:* Patient pushes back without medical merit; verifier tests if the LLM resists capitulation.

**Conclusion:** The dataset is fully capable of driving all three conditions deterministically.

---

## 7. Ground-Truth and Error-Injection Design

We established a formal evaluation schema covering 6 failure and control modes:
* `ERR-1`: Wrong-Entity / Target Association (Hallucination)
* `ERR-2`: Stale State After Fact Correction (Failure to purge refuted facts)
* `ERR-3`: Failure to Preserve Explicit Correction (Catastrophic forgetting)
* `ERR-4`: Unsupported Change of Belief under Pressure (Sycophancy)
* `CTRL-5`: Legitimate State Update (Control: Valid evidence shift)
* `CTRL-6`: Dual-Entity Disambiguation (Control: Patient vs relative history)

---

## 8. Limitations, Licensing & Citations

* **License:** Permitted for academic research under ODC-By v1.0 / CC BY 4.0.
* **Limitations:** Synthetic Bayesian cohort; strictly one primary condition per patient (no multimorbidity); no continuous vital sign curves; closed-world negation assumption.
* **Human Review:** Generated natural dialogue prompts must undergo spot clinical review by a licensed clinician before publication.

---

## 9. Blockers & Required Pre-Implementation Actions

| Blocker ID | Description | Severity | Remediation Plan |
| :---: | :--- | :---: | :--- |
| **BLK-1** | 6,676 cross-split leaked test cases. | Critical | Exclude all test cases matching train/val hashes. |
| **BLK-2** | Extreme 251.6:1 class imbalance. | High | Implement severity-stratified sampling quotas. |
| **BLK-3** | Typo `"Larygospasm"` and composite ICDs. | Medium | Integrate alias lookup dictionary in evaluation harness. |
| **BLK-4** | Raw files minified and cryptic. | Low | Use our verified `case_decoder.js` for dialogue verbalization. |

---

## 10. Clear Go/No-Go Recommendation

### Final Verdict: **GO (With Mandatory Deduplication & Stratification)**

**Justification:**  
DDXPlus is an exceptionally clean, large, and mathematically coherent benchmark. The defects discovered during this audit (leakage, class imbalance, and typographical anomalies) are completely manageable via programmatic preprocessing. It provides the exact structured ground truth, triage severity tiers, and multi-feature depth needed to successfully demonstrate and scientifically validate our **Real-Time, State-Aware Verification Layer**.
