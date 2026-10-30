# DailyMed Medication Evidence Corpus: Limitations and Open Questions

**Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  
**Project ID:** PW_27_MHR_04  
**Date:** October 29, 2026  
**Document Purpose:** To record unresolved clinical and engineering questions, identify intrinsic limitations of label-based evidence, and propose explicit decision points for capstone team and clinician review.

---

## 1. Intrinsic Limitations of Official Medication Labels as Ground Truth

While FDA Structured Product Labeling (SPL) via DailyMed provides the highest regulatory authority for approved claims, relying on label evidence introduces several known boundaries that our verifier must account for:

### A. Static Regulatory Snapshots vs Living Clinical Practice
- **Regulatory Lag:** FDA label revisions occur only when manufacturers submit supplemental applications (sNDAs) or when the FDA mandates safety labeling changes. Guideline-recommended practices (e.g., American Diabetes Association Standards of Care) often recommend modern practices (e.g., first-line SGLT2i/GLP-1RA therapy in CKD or heart failure) before older drug labels reflect these changes.
- **Off-Label Evidence Absence:** Many clinically standard medication practices (e.g., metformin use for polycystic ovary syndrome [PCOS], or low-dose naltrexone) are not approved FDA indications and will therefore appear as "unsupported claims" if checked solely against DailyMed labels.
  - *Mitigation for Verifier:* The verifier must explicitly report finding: `"Not supported by FDA approved label text"` rather than declaring the claim `"Clinically false"`.

### B. Fixed-Dose Combination Product Inflexibility
- As demonstrated in our audit of alogliptin + metformin hydrochloride tablets, fixed-dose combination products have unique formulation constraints (e.g., inability to titrate one active ingredient independently in renal impairment).
- When a patient in a dialogue asks about "taking alogliptin", the verifier must verify whether the patient is taking monotherapy or the combination tablet before retrieving evidence, because renal safety guidelines differ sharply between the two.

### C. Black Box Warnings vs General Warnings Severity Gradients
- Drug labels differentiate between:
  1. **Boxed Warnings** (highest level of FDA warning; e.g. Metformin-associated lactic acidosis, Lisinopril fetal toxicity).
  2. **Contraindications** (absolute prohibitions; e.g. eGFR <30 mL/min/1.73m², acute metabolic acidosis).
  3. **Warnings and Precautions** (clinical risks requiring monitoring or caution; e.g. pancreatitis, heart failure, vitamin B12 deficiency).
  4. **Adverse Reactions** (observed event frequencies).
- Many LLMs flatten these distinct legal/clinical tiers into generic statements (e.g., saying "metformin is dangerous in kidney disease" without distinguishing moderate monitoring from severe contraindication).

---

## 2. Open Questions Requiring Capstone Team Decision

Before proceeding to bulk download the remaining labels in the pilot, the capstone team should align on the following 5 strategic decisions:

### Question 1: Approval of Proposed 8-Ingredient Pilot Set
- **Proposed Scope:**
  1. Alogliptin (DPP-4i monotherapy)
  2. Metformin IR (Biguanide immediate-release)
  3. Metformin XR (Biguanide extended-release)
  4. Linagliptin (Non-renally eliminated DPP-4i peer)
  5. Metoprolol (Beta-blocker LASA confusion control)
  6. Glipizide (Sulfonylurea DDI control)
  7. Empagliflozin (SGLT2i contrast control)
  8. Lisinopril (ACEi multi-turn polypharmacy control)
- *Decision Needed:* Does the team approve this 8-drug pilot, or should any ingredient be replaced?

### Question 2: Raw Label Format Retention (XML vs PDF)
- **Finding:** SPL/XML is compact (~300 KB), machine-readable, and provides precise LOINC codes and element UUIDs. PDFs are larger (~600 KB to 2 MB) and represent the visual package insert.
- *Proposed Policy:* For all pilot medications, download and store both the authoritative SPL/XML (for automated parsing) and the corresponding PDF (for human clinician audit).
- *Decision Needed:* Confirm whether both formats should be downloaded for all subsequent labels.

### Question 3: Label Selection Rule Among Multiple Generic Manufacturers
- **Finding:** A generic drug (e.g. metformin) often has 50+ SPL records on DailyMed from different labelers/repackagers (e.g., Teva, Viatris, Sun Pharma, Heritage).
- *Proposed Policy:* Prioritize:
  1. The Reference Listed Drug (RLD) / Brand-name NDA holder where available (e.g., Bristol-Myers Squibb for Glucophage, Boehringer Ingelheim for Tradjenta).
  2. An authorized generic or high-volume established manufacturer with full prescribing information and recent revision dates.
  3. Avoid repackagers (Type 0 / secondary distributors) that may have truncated packaging descriptions.
- *Decision Needed:* Confirm this prioritization rule for selecting canonical labels.

### Question 4: Granularity of Evidence Chunking
- **Current Approach:** We extracted 24 concise evidence units from the seed label, with each unit focused on an individual clinical fact (e.g., Section 2.2 renal contraindication is separate from Section 2.2 combination dosing inflexibility).
- *Trade-off:* Atomic chunks provide razor-sharp attribution and prevent distractor leakage, but require more extraction records. Coarse section chunks (e.g., the entire Section 5) contain full context but may dilute the verifier's NLI score.
- *Decision Needed:* Confirm whether atomic evidence chunking should be maintained across all pilot labels.

### Question 5: Evaluation Criteria for Verifier Decisions
- In multi-turn dialogue, if an LLM states a fact that is true for another drug in the patient's history, should the verifier output:
  - `REFUSE` (halt response),
  - `WARN` (attach caveat), or
  - `CLARIFY` (prompt user for clarification)?
- *Proposed Rule (per presentation Slide 16):*
  - Strict Target Mismatch (Wrong Drug) -> `REFUSE + EXPLAIN`
  - Qualifier Loss (Dropped Renal Cutoff) -> `WARN + ATTACH QUALIFIER`
  - Ambiguous Formulation -> `CLARIFY`

---

## 3. Plan for Clinician Review

Before final deployment into the capstone benchmark:
1. Conduct a blinded review of the 8 controlled test cases with our project guide (Dr. Mamatha H R) and consulting clinicians.
2. Confirm that the gold-standard `expected_verifier_outcome` for each test fixture accurately represents patient safety standards.
3. Validate that our target attribution definitions match clinical reasoning benchmarks in literature (e.g. Caruzzo et al. 2026, Scanlin et al. 2026).
