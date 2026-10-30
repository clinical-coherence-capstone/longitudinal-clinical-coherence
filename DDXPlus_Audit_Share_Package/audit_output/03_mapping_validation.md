# DDXPlus Mapping Validation Report (Task C)

**Date of Audit:** October 26, 2026  
**Auditor:** Antigravity Data Audit Engine  
**Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  

---

## 1. Executive Summary

This report documents the verification of the medical knowledge-base and feature mapping definitions provided in the DDXPlus benchmark release:
1. `release_conditions.json` (49 conditions, 20,889 bytes)
2. `release_evidences.json` (223 evidence items, 120,263 bytes)

Both files parse successfully as valid JSON structures with UTF-8 encoding. All clinical feature references across conditions and evidence definitions resolve with **0% unresolved references**. However, several data anomalies (typographical errors, composite ontology codes, token encoding patterns) must be normalized before these mappings can be safely consumed by LLM prompt builders and verifier modules.

---

## 2. Core Quantitative Metrics

| Metric | Measured Value | Validation Status |
| :--- | :--- | :--- |
| **Unique Condition Keys** | `49` | Verified |
| **Unique Evidence Keys** | `223` | Verified |
| **Gapped / Deprecated Evidence IDs** | `5` (`E_36`, `E_68`, `E_85`, `E_117`, `E_122`) | Verified |
| **Condition-to-Evidence Unresolved References** | `0` (0.0%) | Verified |
| **Duplicate Keys in Condition Map** | `0` (0.0%) | Verified |
| **Duplicate Keys in Evidence Map** | `0` (0.0%) | Verified |
| **Missing English Questions** | `0` (0.0%) | Verified |
| **Missing French Questions** | `0` (0.0%) | Verified |
| **Unique Value Code Keys (`V_...`)** | `199` | Verified |
| **Total Mapped Value Code Translations** | `698` | Verified |

---

## 3. Evidence Schema & Token Encoding Grammar

Clinical evidences in DDXPlus are partitioned into two functional categories:
* **Antecedents (`is_antecedent: true`) — 113 items:** Pre-existing chronic diseases, surgical history, family history, lifestyle risk factors, occupational exposures, medications, and international travel.
* **Symptoms & Physical Exam Findings (`is_antecedent: false`) — 110 items:** Chief complaints, acute presenting symptoms, pain characteristics, dermatological lesions, and physical inspection findings.

### Data Types and Token Syntax

DDXPlus employs three distinct data types (`data_type`):

1. **Binary (`B`) — 208 items (93.3%):**
   * *Semantics:* Binary presence (`1` / `true`) vs. absence (`0` / `false`).
   * *Dataset default:* `0` (absence).
   * *Token representation in patient records:* Plain evidence ID string (e.g., `'E_91'` = Fever, `'E_66'` = Dyspnea, `'E_79'` = Cigarette smoking).
   * *Critical note on negation:* In DDXPlus, absent binary evidence implies negative/denied findings. If an evidence token does not appear in a patient's evidence list, the synthetic patient generator assumed the finding was evaluated and absent.

2. **Multi-Choice (`M`) — 5 items (2.2%):**
   * *Semantics:* Multi-select categorical questions where a patient can manifest multiple concurrent values.
   * *Items:*
     - `E_55`: Pain location (165 anatomical sites, default `V_123` = "nowhere")
     - `E_57`: Pain radiation location (165 anatomical sites, default `V_123` = "nowhere")
     - `E_54`: Pain characterization (16 descriptors: sharp, burning, cramp, crushing, etc., default `V_11` = "NA")
     - `E_133`: Lesion / rash location (165 anatomical sites, default `V_123` = "nowhere")
     - `E_152`: Swelling / edema location (165 anatomical sites, default `V_123` = "nowhere")
   * *Token representation in patient records:* Encoded token with delimiter `_@_` (e.g., `'E_55_@_V_25'`, `'E_55_@_V_62'`).

3. **Categorical / Ordinal (`C`) — 10 items (4.5%):**
   * *Semantics:* Single-select categorical or discrete numerical scales (0–10).
   * *Items:*
     - `E_56`: Pain intensity on visual analog scale (0 to 10)
     - `E_58`: Pain precision / localization accuracy (0 to 10)
     - `E_59`: Pain onset speed / pace (0 to 10)
     - `E_134`: Pain intensity of skin lesion (0 to 10)
     - `E_132`: Lesion swelling severity (0 to 10)
     - `E_136`: Lesion itching severity (0 to 10)
     - `E_130`: Lesion color (`V_11`=NA, `V_86`=dark, `V_107`=yellow, `V_138`=pale, `V_156`=pink)
     - `E_135`: Lesion size > 1cm (`V_10`=No, `V_12`=Yes)
     - `E_131`: Lesions peeling (`V_10`=No, `V_12`=Yes)
     - `E_204`: Recent international travel (`V_10`=No, `V_0` through `V_9` = specific geographic regions)
   * *Token representation in patient records:* Encoded token with delimiter `_@_` (e.g., `'E_56_@_2'`, `'E_204_@_V_7'`).

---

## 4. Identified Data Anomalies & Quality Issues

### 4.1 Condition Typo (`"Larygospasm"`)
* **Anomaly:** Condition #24 is keyed as `"Larygospasm"` (missing the letter 'n').
* **Impact:** In standard medical English, the correct term is `"Laryngospasm"`. Evaluators using exact string matching against raw DDXPlus keys will falsely fail any LLM or clinical reviewer providing the canonical medical spelling.
* **Resolution:** An alias lookup map must be deployed in the evaluation layer:
  `{"Laryngospasm": "Larygospasm"}`.

### 4.2 Composite ICD-10 Code (`"j17, j18"`)
* **Anomaly:** Condition #39 (`Pneumonia`) contains a comma-separated composite string `"j17, j18"` rather than a single ICD-10 code.
* **Impact:** Standard ontology mapping tools expecting a single ICD-10 string will fail or misclassify pneumonia billing queries.
* **Resolution:** Split on `,` and lowercase/uppercase normalize during ontology alignment.

### 4.3 ICD-10 Casing Inconsistency
* **Anomaly:** 15 ICD-10 codes are recorded in lowercase (`g44.009`, `a15`, `j40`, `j44.1`, `i26`, `j06.9`, `j11.1`, `j01`, `j32`, `j21`, `c34`, `d86`, `c25`, `a98.4`, `f41`), while 33 codes are uppercase (`J93`, `K22.3`, `B20`, `D64.9`, `I21`, etc.).
* **Resolution:** Standardize all ICD-10 codes to uppercase before evaluation.

### 4.4 Discontinuous Evidence Sequence
* **Anomaly:** Evidence IDs span `E_0` through `E_227`, but 5 IDs are absent: `E_36`, `E_68`, `E_85`, `E_117`, `E_122`.
* **Impact:** Code that iterates blindly using `for i in range(228): key = f"E_{i}"` will throw `KeyError`.
* **Resolution:** Always iterate over `Object.keys(evidences)` rather than synthetic numeric ranges.

### 4.5 Context-Dependent Semantics of Value Codes (`V_...`)
* **Anomaly:** Value codes like `V_10` do not have a universal global meaning. In `E_135` and `E_131`, `V_10` means `"N"` (No). In `E_204`, `V_10` means `"N"` (No travel). In contrast, anatomical codes (`V_14` through `V_165`) represent distinct human body parts and are shared across pain, radiation, rash, and swelling questions.
* **Resolution:** Never look up `V_...` codes in a flat dictionary without scoping to the parent evidence definition `evidences[E_id]["value_meaning"][V_id]`.

---

## 5. Architectural Role in the Capstone Verification Layer

In our capstone project (*"Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations"*):

1. **State-Tracking Ground Truth:** The decoded questions and values establish the patient's explicit ground-truth state graph $\mathcal{S}^* = \{(e_i, v_i)\}_{i=1}^N$.
2. **Conversation Utterance Synthesis:** The verified English question text (`question_en`) and natural language value mappings (`value_meaning[V_id].en`) allow deterministic transformation of synthetic patient cases into human dialogues without semantic drift.
3. **Information Shielding:** Condition ground truth, severity ratings, and unrevealed symptoms are held exclusively by the verification engine and shielded from the dialogue context until elicited by the conversational agent.
