# DDXPlus Dataset Schema Report (Task B)

**Date of Audit:** October 26, 2026  
**Auditor:** Antigravity Data Audit Engine  
**Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  

---

## 1. Executive Summary

This report establishes the verified empirical schema of the DDXPlus dataset across its knowledge-base files (`release_conditions.json`, `release_evidences.json`) and patient case records (`release_*_patients`).

Every patient case consists of a single unindexed row structured as a comma-separated value record containing 6 top-level fields. The schema lacks an explicit unique patient identifier (e.g., UUID or MRN). Patient state is recorded as a set of compressed symbolic tokens mapped back to the evidence dictionary.

---

## 2. Patient Case Record Schema Breakdown

| Column Name | Storage Type | Python/JSON In-Memory Type | Required / Optional | Null Count (Val Split) | LLM Access / Verifier Policy |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `AGE` | `integer` | `int` (0 to 109) | Required | 0 (0.0%) | **Available to LLM** at Turn 1 (demographics). |
| `SEX` | `string` | `string` (`'M'` or `'F'`) | Required | 0 (0.0%) | **Available to LLM** at Turn 1 (demographics). |
| `INITIAL_EVIDENCE` | `string` | `string` (e.g. `'E_154'`) | Required | 0 (0.0%) | **Available to LLM** as initial chief complaint. |
| `EVIDENCES` | `string` (quoted) | `list[str]` (size 2 to 45) | Required | 0 (0.0%) | **Shielded from LLM initially.** Progressively revealed by simulator/patient upon targeted questioning. Full set used by **Verifier**. |
| `PATHOLOGY` | `string` | `string` (49 condition names) | Required | 0 (0.0%) | **STRICTLY SHIELDED from LLM.** Retained exclusively as evaluation ground truth and verifier convergence target. |
| `DIFFERENTIAL_DIAGNOSIS`| `string` (quoted) | `list[list[str, float]]` | Required | 0 (0.0%) | **STRICTLY SHIELDED from LLM.** Used by verifier to measure diagnostic ranking alignment and entropy. |

---

## 3. Field-by-Field Detailed Analysis

### 3.1 `AGE`
* **Data Type:** Integer (0–109).
* **Clinical Meaning:** Patient chronological age in completed years. Value `0` represents infants (< 1 year old).
* **Missingness:** 0% missing in validation.
* **Representative Example:** `55`
* **Capstone Policy:** Exposed in Turn 1 context prompt (`"A 55-year-old female presents to the clinic..."`).

### 3.2 `SEX`
* **Data Type:** Character code (`'M'` for Male, `'F'` for Female).
* **Clinical Meaning:** Biological sex assigned at birth. (Note: Intersex or non-binary categories are absent in DDXPlus).
* **Missingness:** 0% missing in validation (51.4% F, 48.6% M).
* **Representative Example:** `'F'`
* **Capstone Policy:** Exposed in Turn 1 context prompt.

### 3.3 `INITIAL_EVIDENCE`
* **Data Type:** String token referencing an evidence ID (e.g., `'E_154'`).
* **Clinical Meaning:** The presenting symptom or chief complaint that prompted the patient to seek medical care.
* **Audit Finding:** In 100% of cases, this token is also contained within the patient's full `EVIDENCES` list.
* **Representative Example:** `'E_154'` (Decodes to: *"Is your skin much paler than usual?"*).
* **Capstone Policy:** Converted to a natural first-person patient complaint and supplied in Turn 1.

### 3.4 `EVIDENCES`
* **Data Type:** Quoted string containing a serialized Python string list (e.g., `"['E_7', 'E_55_@_V_25', 'E_56_@_2']"`).
* **Clinical Meaning:** The complete set of positive clinical findings, active symptoms, and confirmed medical antecedents manifested by this synthetic case.
* **Absence Rule:** DDXPlus assumes a closed-world model: any evidence from the 223 dictionary items that is NOT present in this list is clinically negative (`0`).
* **Representative Example:**
  ```python
  ['E_7', 'E_24', 'E_53', 'E_54_@_V_180', 'E_55_@_V_25', 'E_56_@_2', 'E_154', 'E_208']
  ```
* **Capstone Policy:**
  - *LLM:* Hidden. Items are only revealed when the LLM asks relevant questions (Gradual-Reveal Form).
  - *Verifier:* Maintained as the patient ground-truth state graph $\mathcal{S}^*$. The verifier tracks whether the LLM's clinical reasoning is coherent with the evidence elicited so far.

### 3.5 `PATHOLOGY`
* **Data Type:** String matching one of the 49 keys in `release_conditions.json`.
* **Clinical Meaning:** The single underlying true pathology / final definitive diagnosis.
* **Missingness:** 0% missing. 100% resolve to valid entries in `release_conditions.json`.
* **Representative Example:** `'Anemia'`
* **Capstone Policy:**
  - **CRITICAL INFORMATION BARRIER:** The condition label must never appear in the dialogue context provided to the LLM. Leaking this label invalidates diagnostic evaluation.
  - *Verifier Role:* Serves as the asymptotic diagnostic target. Used to evaluate whether the LLM's posterior belief distribution converges toward the ground truth.

### 3.6 `DIFFERENTIAL_DIAGNOSIS`
* **Data Type:** Quoted string containing serialized pairs of `[condition_name, probability]`.
* **Clinical Meaning:** The posterior probability distribution over candidate diagnoses computed by the dataset's underlying Bayesian diagnostic network given the patient's full evidence set.
* **Representative Example:**
  ```python
  [['Anemia', 0.2507], ['Atrial fibrillation', 0.1861], ['Cluster headache', 0.1172]]
  ```
* **Audit Finding:** The true `PATHOLOGY` is present in this candidate list in **100.00%** of cases, is the Top-1 candidate in **73.37%** of cases, and is within Top-3 in **92.78%** of cases.
* **Capstone Policy:** Shielded from LLM. Used by the verification layer as a gold-standard diagnostic prior to evaluate whether the LLM is entertaining clinically sound differential candidates.

---

## 4. Notable Structural Absenteeism (Fields NOT Present)

| Missing Concept | Impact on Capstone | Mitigation |
| :--- | :--- | :--- |
| **No Unique Case ID (`ID` / `UUID`)** | Rows cannot be referenced by a persistent unique key across splits. | We must generate deterministic hashes: `SHA256(Split_RowIndex_Age_Sex_Pathology)`. |
| **No Longitudinal Timestamps** | Symptoms do not have explicit calendar timestamps (e.g., "Day 1", "Day 5"). | The order of evidence reveal in multi-turn dialogues must be staged using clinical onset tiers (Chief complaint $\rightarrow$ Primary symptoms $\rightarrow$ History $\rightarrow$ Targeted exam). |
| **No Vital Signs Numerical Values** | Temperature in °C, Heart Rate in bpm, and Blood Pressure in mmHg are not stored as numbers. | Binary tokens indicate abnormal ranges (e.g., `E_91` = Fever present, `E_220` = Tachycardia present). |
| **No Free-Text Clinical Notes** | Raw dataset is purely tabular/symbolic. | A deterministic verbalizer (`case_decoder.js`) converts symbolic states into natural clinical dialogue utterances. |
