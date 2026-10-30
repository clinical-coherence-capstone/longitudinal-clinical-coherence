# DDXPlus Documentation, Licensing, and Scientific Limitations (Task H)

**Date of Audit:** October 27, 2026  
**Auditor:** Antigravity Data Audit Engine  
**Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  

---

## 1. Dataset Origin and Academic Licensing

* **Canonical Publication:**  
  *DDXPlus: A New Dataset For Automatic Medical Diagnosis*  
  Arsène Fansi Tchango, Rishab Goel, Zhi Wen, Julien Chen, Joumana Ghosn.  
  *36th Conference on Neural Information Processing Systems (NeurIPS 2022) Track on Datasets and Benchmarks.*
* **License Type:**  
  Open Data Commons Attribution License (ODC-By v1.0) / Creative Commons Attribution 4.0 International (CC BY 4.0).
* **Permitted Use:**  
  Freely permitted for non-commercial academic research, pedagogical benchmarking, and algorithmic development.
* **Redistribution Policy:**  
  Redistribution of modified portions is permitted provided proper attribution is maintained. The original raw dataset files should not be republished publicly in unvetted third-party repositories without license preservation.
* **Mandatory Citation:**
  ```bibtex
  @inproceedings{tchango2022ddxplus,
    title={{DDXPlus}: A New Dataset for Automatic Medical Diagnosis},
    author={Ars{\`e}ne Fansi Tchango and Rishab Goel and Zhi Wen and Julien Chen and Joumana Ghosn},
    booktitle={Thirty-sixth Conference on Neural Information Processing Systems Datasets and Benchmarks Track},
    year={2022}
  }
  ```

---

## 2. Core Scientific & Clinical Limitations

While DDXPlus is a clean, large-scale benchmark, researchers must account for several major clinical limitations:

### 2.1 Purely Synthetic Cohort (Bayesian Graph Sampling)
* Patients in DDXPlus are not real human beings from an Electronic Health Record (EHR). They are stochastic instantiations sampled from a directed graphical model.
* Consequently, cases lack the messy ambiguity, atypical presentations, and idiosyncratic language seen in real emergency departments.

### 2.2 Strict Single-Pathology Assumption
* Every patient case in DDXPlus is assigned exactly **one primary pathology** (e.g. *Anemia* OR *GERD*).
* In real clinical medicine (especially geriatric cohorts, which comprise 14.8% of the dataset), patients suffer from **multimorbidity** (e.g., congestive heart failure, diabetes, and osteoarthritis concurrently). DDXPlus cannot benchmark multi-pathology reasoning.

### 2.3 Absence of Continuous Physiological Dynamics
* DDXPlus features are discrete tokens. It lacks continuous numerical time-series for vital signs (e.g. Mean Arterial Pressure, continuous ECG telemetry, capillary blood glucose, SpO2 curves).
* Shock, respiratory distress, and sepsis trajectories cannot be simulated with high physiological realism.

### 2.4 The Closed-World Negation Assumption
* In DDXPlus, absent evidence is treated as confirmed negative evidence.
* In multi-turn clinical conversations, an unasked symptom is **unknown**, not negative. The verifier must explicitly decouple "not yet elicited" from "clinically ruled out".

---

## 3. Human Clinical Expert Review Requirement

**Crucial Recommendation:**  
A synthetic pathology label in DDXPlus does **not** grant automatic clinical validity to every simulated dialogue.  
Before deploying dialogue scenarios in our Capstone evaluation:
1. **Clinical Prompt Review:** A qualified clinician must review the verbalized dialogues for a representative sample (at least 20 cases) to verify that the patient persona's phrasing and progression are medically sound.
2. **Verifier Threshold Alignment:** Clinicians must calibrate the point at which an LLM's diagnostic pivot is deemed "premature" vs "justified by new evidence".
