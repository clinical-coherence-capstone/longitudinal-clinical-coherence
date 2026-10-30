# Longitudinal Clinical Coherence (LCC) System

A real-time, state-aware verification layer for multi-turn clinical LLM conversations.

## Setup

```bash
cd lcc_system
pip install -r requirements.txt
```

## Running Tests

```bash
cd lcc_system
python -m pytest tests/ -v
```

## Running the Demo

```bash
cd lcc_system
python demo.py
```

## Project Structure

```
lcc_system/
├── src/                  # All source modules
│   ├── models.py         # Shared dataclasses
│   ├── dataset_loader.py # Dataset I/O
│   └── ...               # Additional modules (FEAT-002+)
├── tests/                # Pytest unit tests
├── data/                 # Runtime-generated scratch dir (not committed)
├── demo.py               # CLI entry point
├── requirements.txt
└── README.md
```

## Notes

- Raw datasets live outside `lcc_system/` and are never modified.
- Python stdlib only; no external packages beyond pytest.
- No API keys required for the CLI demo.

<!-- Sections below will be finalized in FEAT-003 -->

## Architecture

*To be documented in FEAT-003.*

## Evaluation

*To be documented in FEAT-003.*
