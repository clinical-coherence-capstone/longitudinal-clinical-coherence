# Longitudinal Clinical Coherence (LCC) System

The Longitudinal Clinical Coherence (LCC) system is a real-time, state-aware verification layer
for multi-turn clinical LLM conversations. It implements a 10-component pipeline that tracks
patient state across conversation turns, normalizes medication mentions via RxNorm, retrieves
evidence from DailyMed, generates candidate clinical responses using a configurable LLM provider,
runs five deterministic coherence checks, and applies a rule-based decision gate that returns one
of PASS, CLARIFY, WARN, or REFUSE. All DDXPlus patient records are synthetically generated
and all pipeline logic uses Python stdlib only — no API key is required to run the demo.

## Setup

1. Python 3.11+ required.
2. Clone or unzip the project.
3. Change to the lcc_system directory:

```
cd lcc_system
```

4. Install dependencies:

```
pip install -r requirements.txt
```

## Run the Demo

```
python demo.py
```

## Run with a Different Case

```
python demo.py --case 2 --form pushback --verbose
```

## Run Tests

```
python -m pytest tests/ -v
```

## Run Evaluation

```
python demo.py --eval
```

## Use with an LLM API (Optional)

To use a real LLM instead of the mock provider, set the following environment variables
before running the demo. No API key is hardcoded anywhere in the source code.

On Windows:

```
set LCC_LLM_PROVIDER=openai
set LCC_API_KEY=sk-...
python demo.py
```

On Linux/macOS:

```
export LCC_LLM_PROVIDER=openai
export LCC_API_KEY=sk-...
python demo.py
```

## Project Structure

```
lcc_system/
├── src/
│   ├── __init__.py
│   ├── models.py                  # All 12 shared dataclasses
│   ├── dataset_loader.py          # Dataset I/O; generates synthetic DDXPlus cases
│   ├── conversation_generator.py  # Multi-turn conversation from PatientCase
│   ├── state_extractor.py         # Extracts ClinicalFact from conversation turns
│   ├── state_manager.py           # Versioned patient state with contradiction tracking
│   ├── medication_normalizer.py   # Maps medication text to RxNorm CUIs
│   ├── evidence_retriever.py      # Retrieves DailyMed evidence by section priority
│   ├── response_generator.py      # Mock + configurable LLM response generation
│   ├── coherence_verifier.py      # 5 deterministic coherence checks
│   ├── decision_gate.py           # Rule-based PASS/CLARIFY/WARN/REFUSE gate
│   └── evaluation.py              # Evaluation harness with 10 test scenarios
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_dataset_loader.py
│   ├── test_conversation_generator.py
│   ├── test_state_extractor.py
│   ├── test_state_manager.py
│   ├── test_medication_normalizer.py
│   ├── test_evidence_retriever.py
│   ├── test_response_generator.py
│   ├── test_coherence_verifier.py
│   ├── test_decision_gate.py
│   └── test_evaluation.py
├── data/                          # Runtime-generated scratch dir (not committed)
├── demo.py                        # CLI entry point
├── requirements.txt               # pytest>=7.4.0
└── README.md
```

External datasets (read-only, never modified):

```
../dailymed_corpus_final/medication_evidence.jsonl
../rxnorm_capstone/data/concepts.csv
../rxnorm_capstone/data/relationships.csv
../rxnorm_capstone/data/input_aliases.csv
../DDXPlus_Audit_Share_Package/audit_output/condition_mapping_summary.csv
../DDXPlus_Audit_Share_Package/audit_output/evidence_mapping_summary.csv
```

## Coherence Checks

The CoherenceVerifier runs five deterministic checks against each generated response:

1. **MED_TARGET_MISMATCH** — Response mentions a medication not associated with the patient.
2. **FACT_CONTRADICTION** — Response asserts a fact that contradicts an established patient state.
3. **SYCOPHANCY** — Response agrees with patient pushback that contradicts clinical evidence.
4. **EVIDENCE_MED_MISMATCH** — Retrieved evidence refers to medications not in patient state.
5. **STALE_STATE** — Response uses a corrected fact's old status after an explicit update.

## Decision Gate Rules

| Condition | Decision |
|-----------|----------|
| 0 flags | PASS |
| ERROR flag with check_id in {SYCOPHANCY, MED_TARGET_MISMATCH} | REFUSE |
| ERROR flag with check_id in {FACT_CONTRADICTION, STALE_STATE} | WARN |
| WARNING flags only (no ERROR) | CLARIFY |
| Unclassified ERROR | CLARIFY |

## Limitations

- The DailyMed corpus covers only the alogliptin/metformin combination product (24 records).
  Evidence retrieval returns empty results for all other medications.
- All DDXPlus patient records are synthetically generated using hard-coded case templates.
  No real patient data is used anywhere in the system.
- Coherence checks are deterministic keyword-based rules. No machine learning is used.
- This is a research prototype. It is NOT clinically validated and MUST NOT be used for
  clinical decision-making.

## Web Application

The LCC system includes an interactive Streamlit web application with multi-user authentication, SQLite persistence, and real-time clinical coherence verification.

### Prerequisites

Install the updated dependencies (including `streamlit` and `bcrypt`):

```bash
pip install -r requirements.txt
```

### Launch the Application

From the `lcc_system/` root directory, run:

```bash
streamlit run webapp/app.py
```

The app will start at `http://localhost:8501`.

### User Flow

1. **Register**: On first use, select the **Register** tab and create an account (minimum 8 characters for password). Passwords are securely hashed using bcrypt.
2. **Log In**: Switch to the **Login** tab and sign in.
3. **Conversations**: Click **➕ New Conversation** in the sidebar to start a new chat session. Previous conversations are saved and listed chronologically.
4. **Chat & Verification**: Type patient symptoms, history, or queries. The assistant responds while maintaining longitudinal state across turns.
5. **Verification Details**: Under each assistant response, expand **🔍 Verification Details** to view:
   - Extracted Clinical Facts (symptoms/antecedents with polarity and confidence)
   - Longitudinal Patient State Summary (version, turn, tracked medications, contradiction detection)
   - Retrieved DailyMed Evidence records and citations
   - Coherence Check & Decision Gate outcome (`PASS`, `CLARIFY`, `WARN`, `REFUSE`)

### Database

Chat histories, user credentials, patient states, and verification records are persisted automatically in `lcc_system/webapp/lcc_webapp.db` (created at runtime).

### Safety Disclaimer

⚠️ **Research Prototype Only**: This application is strictly an academic research prototype and is NOT a medical diagnosis or treatment advisory tool.
