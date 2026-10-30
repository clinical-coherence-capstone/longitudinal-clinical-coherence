# DDXPlus Duplicates and Cross-Split Leakage Report (Task E)

**Date of Audit:** October 27, 2026  
**Auditor:** Antigravity Data Audit Engine  
**Project:** Longitudinal Clinical Coherence: A Real-Time, State-Aware Verification Layer for Multi-Turn Clinical LLM Conversations  

---

## 1. Executive Summary

A critical requirement of this audit is to assess whether DDXPlus contains duplicate records and cross-split data leakage. Because DDXPlus does not assign unique patient IDs, we generated deterministic clinical fingerprints for all **1,292,579 records**:
$$\text{Fingerprint} = \text{Age} \parallel \text{Sex} \parallel \text{Pathology} \parallel \text{Sorted}(\text{Evidences})$$

Our analysis reveals **significant intra-split duplication** and **empirical cross-split leakage**:
* **Intra-Split Duplicates:** 30,309 total exact duplicates (Train: 29,823 [2.91%], Val: 216 [0.16%], Test: 270 [0.20%]).
* **Cross-Split Leakage:**
  - **Train $\leftrightarrow$ Val:** 5,525 cases (0.54% of Train, 4.17% of Val fingerprints).
  - **Train $\leftrightarrow$ Test:** 6,167 cases (0.60% of Train, 4.58% of Test fingerprints).
  - **Val $\leftrightarrow$ Test:** 509 cases (0.38% of Test).

---

## 2. Quantitative Duplication and Leakage Matrix

| Partition Comparison | Identical Clinical Fingerprint Matches | Percentage of Split | Integrity Classification |
| :--- | :---: | :---: | :---: |
| **Intra-Train Duplicates** | 29,823 | 2.91% of Train | High Internal Redundancy |
| **Intra-Val Duplicates** | 216 | 0.16% of Val | Low Internal Redundancy |
| **Intra-Test Duplicates** | 270 | 0.20% of Test | Low Internal Redundancy |
| **Train $\leftrightarrow$ Validation Leakage** | **5,525** | 0.54% of Train | **Confirmed Split Leakage** |
| **Train $\leftrightarrow$ Test Leakage** | **6,167** | 0.60% of Train | **Confirmed Split Leakage** |
| **Validation $\leftrightarrow$ Test Leakage**| **509** | 0.38% of Test | **Confirmed Split Leakage** |

---

## 3. Root Cause Analysis

Why does identical case leakage occur in a benchmark dataset?

1. **Discrete Stochastic Sampling:**  
   DDXPlus generates synthetic patient records by sampling from a discrete Bayesian network parameterized with physician-curated conditional probability tables. The feature space consists of 223 discrete evidence items across 49 conditions.
2. **Stereotypical Clinical Profiles:**  
   Certain common clinical entities (such as uncomplicated *Viral pharyngitis* or *URTI* in young adults) have a high concentration of probability mass on a compact set of core symptoms:
   $$\{\text{Sore throat}, \text{Cough}, \text{Rhinorrhea}, \text{Fever}\} \subset \mathcal{S}$$
   When over 1.29 million cases are sampled stochastically, identical feature vectors are independently generated multiple times across separate sampling runs.
3. **Absence of Post-Generation Cross-Split Deduplication:**  
   The dataset creators split the sampled cases into Train, Validation, and Test partitions without applying a global hash deduplication filter.

---

## 4. Impact on Capstone Multi-Turn LLM Evaluation

If an evaluator naively samples cases from the DDXPlus test split without checking for leakage:
1. **Contaminated Few-Shot Prompting:** If validation or training cases are used as in-context few-shot examples or for prompt tuning, the LLM may encounter identical clinical profiles during the test evaluation.
2. **Verifier Prior Memorization:** If the state-aware verifier's transition graph or Bayesian prior is calibrated on training cases, it will possess an artificial advantage on the leaked test cases.

---

## 5. Mandatory Remedies and Deduplication Protocol

To guarantee scientific defensibility in our Capstone experiments, we establish the following **3-Step Deduplication Protocol**:

1. **Deterministic Hashing:** Compute `SHA256(Age + Sex + Pathology + Sorted_Evidences)` for every case.
2. **Exclude Leaked Test Cases:** Remove the 6,167 Train-Test overlapping cases and 509 Val-Test overlapping cases from the test pool $\mathcal{D}_{\text{test}}$.
3. **De-duplicated Candidate Pool:** Select our multi-turn experimental sample exclusively from the remaining **127,853 verified strictly-unseen test cases**.
