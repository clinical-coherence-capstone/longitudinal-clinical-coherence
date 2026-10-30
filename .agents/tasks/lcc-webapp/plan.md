# Implementation Plan — LCC Streamlit Web Application

> **Workspace root:** `c:\Users\91895\OneDrive\Desktop\Longitudinal-Clinical-Coherence`
> **Project root:** `lcc_system/`
> **Constraint:** No existing file under `lcc_system/src/` or `lcc_system/tests/` may be touched.

---

## Key Interface Facts (verified from source)

These are hard constraints. Every new file must respect them exactly.

| Interface | Actual signature |
|-----------|-----------------|
| `StateExtractor.__init__` | `(evidence_vocab: dict[str,EvidenceVocabEntry] \| None = None)` |
| `StateExtractor.extract_from_turn` | `(turn: ConversationTurn, turn_index: int) → list[ClinicalFact]` — takes a **ConversationTurn object**, never a plain string |
| `CoherenceVerifier.__init__` | `(state_manager: StateManager, evidence_retriever: EvidenceRetriever, normalizer: MedicationNormalizer)` — three positional args |
| `CoherenceVerifier.verify` | `(response_text, evidence_used: list[EvidenceRecord], turn_index: int, conversation: Conversation) → list[CoherenceFlag]` |
| `DecisionGate.evaluate` | `(flags: list[CoherenceFlag]) → tuple[str, str]` — returns `(decision_str, reasoning_str)`, **not** a `VerificationResult` |
| `ResponseGenerator.__init__` | `(state_manager: StateManager, evidence_retriever: EvidenceRetriever, provider: str = 'mock')` |
| `StateManager.__init__` | `StateManager(case_id: str)` |
| `PatientState` | dataclass: `case_id, version, turn_number, timestamp, facts: dict[str,ClinicalFact], revealed_evidence_ids, medications` |
| `ClinicalFact` | dataclass: `fact_id, description, status, source_turn, timestamp, confidence, is_antecedent` |
| `Conversation` | dataclass: `case_id: str, turns: list[ConversationTurn], current_turn: int` |
| `ConversationTurn` | dataclass: `turn_index: int, speaker: str, text: str, revealed_evidence_ids: list[str], injection: dict` |

---

## New File Structure

```
lcc_system/
  webapp/
    __init__.py          NEW — package marker
    database.py          NEW — SQLite schema + CRUD
    auth.py              NEW — bcrypt auth helpers
    pipeline.py          NEW — full backend pipeline wrapper
    app.py               NEW — Streamlit application
    lcc_webapp.db        RUNTIME — created automatically, not committed
  tests/
    test_database.py     NEW — database tests
    test_auth.py         NEW — auth tests
    test_pipeline.py     NEW — pipeline tests
    (all existing test files — UNTOUCHED)
  requirements.txt       UPDATED — append streamlit + bcrypt
  README.md              UPDATED — append web app section
```

---

## Implementation Plan

- [ ] 1. **Update requirements.txt** — append two new dependency lines.
      Append `streamlit>=1.35.0` and `bcrypt>=4.1.0` as new lines after the existing `pytest>=7.4.0`.
      Do NOT rewrite or delete the existing line.
      Files: `lcc_system/requirements.txt`
      Verify: `python -m pip install -r requirements.txt` exits 0 (run from `lcc_system/`).

- [ ] 2. **Create `webapp/__init__.py`** — empty package marker.
      Content: one docstring `'Longitudinal Clinical Coherence — Streamlit web application package.'`
      Files: `lcc_system/webapp/__init__.py`
      Verify: `python -c "import sys; sys.path.insert(0,'lcc_system'); from webapp import __init__"` exits 0.

- [ ] 3. **Create `webapp/database.py`** — SQLite schema and all CRUD functions.

      **Schema (5 tables):**
      ```sql
      CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id),
          title TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER NOT NULL REFERENCES conversations(id),
          role TEXT NOT NULL CHECK(role IN ('user','assistant')),
          content TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS patient_states (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER NOT NULL REFERENCES conversations(id),
          turn_number INTEGER NOT NULL,
          state_json TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS verification_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          message_id INTEGER NOT NULL REFERENCES messages(id),
          flags_json TEXT NOT NULL,
          gate_decision TEXT NOT NULL,
          reasoning TEXT NOT NULL,
          created_at TEXT NOT NULL
      );
      ```

      **Function signatures (all use `stdlib sqlite3` only):**
      ```python
      DB_PATH: Path = Path(__file__).parent / 'lcc_webapp.db'

      def get_connection() -> sqlite3.Connection
      def init_db() -> None
      def create_user(username: str, password_hash: str) -> int           # raises IntegrityError on duplicate
      def get_user_by_username(username: str) -> sqlite3.Row | None
      def get_user_by_id(user_id: int) -> sqlite3.Row | None
      def create_conversation(user_id: int, title: str) -> int
      def get_conversations_for_user(user_id: int) -> list[sqlite3.Row]   # ORDER BY updated_at DESC
      def get_conversation(conversation_id: int, user_id: int) -> sqlite3.Row | None  # WHERE id=? AND user_id=?
      def add_message(conversation_id: int, role: str, content: str) -> int
      def get_messages(conversation_id: int) -> list[sqlite3.Row]         # ORDER BY id ASC
      def save_patient_state(conversation_id: int, turn_number: int, state_json: str) -> None
      def get_latest_patient_state(conversation_id: int) -> str | None    # ORDER BY turn_number DESC LIMIT 1
      def save_verification_result(message_id: int, flags_json: str, gate_decision: str, reasoning: str) -> None
      def get_verification_result(message_id: int) -> sqlite3.Row | None
      ```

      `get_conversation` enforces ownership by including `user_id` in the WHERE clause — this is the security boundary.
      All write functions call `conn.commit()`.
      Files: `lcc_system/webapp/database.py`
      Verify: `python -m pytest tests/test_database.py -v` (written in item 7).

- [ ] 4. **Create `webapp/auth.py`** — bcrypt password hashing and user auth helpers.

      **Design decisions:**
      - Use `bcrypt.hashpw` / `bcrypt.checkpw` — never store plain text.
      - Minimum password length: 8 characters.
      - `login_user` never returns the password hash; returns `(bool, str, int|None)`.
      - Validation errors return early with `(False, reason_str)` before touching the DB.

      **Function signatures:**
      ```python
      MIN_PASSWORD_LEN: int = 8

      def hash_password(plain: str) -> str
      def verify_password(plain: str, hashed: str) -> bool
      def register_user(username: str, password: str) -> tuple[bool, str]
      def login_user(username: str, password: str) -> tuple[bool, str, int | None]
      ```

      `register_user` validates username (non-empty, ≤50 chars) and password length, then calls `hash_password` and `create_user`. On `sqlite3.IntegrityError` returns `(False, 'Username already taken.')`.
      `login_user` calls `get_user_by_username`, then `verify_password`. Returns `(False, 'Invalid credentials.', None)` on both "not found" and "wrong password" — same message to prevent username enumeration.
      Files: `lcc_system/webapp/auth.py`
      Verify: `python -m pytest tests/test_auth.py -v` (written in item 7).

- [ ] 5. **Create `webapp/pipeline.py`** — full backend pipeline wrapper.

      **sys.path setup** (at top of file, before any src imports):
      ```python
      import sys
      from pathlib import Path
      sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
      ```

      **Cached resource factory** (decorated with `@st.cache_resource`):
      ```python
      @st.cache_resource
      def _get_shared_resources():
          loader = DatasetLoader()
          normalizer = MedicationNormalizer(loader)
          retriever = EvidenceRetriever(loader, normalizer)
          vocab = loader.load_evidence_vocab()
          return loader, normalizer, retriever, vocab
      ```
      This ensures `DatasetLoader` file I/O runs once per Streamlit server process.

      **PatientState serialization:**
      ```python
      def serialize_state(state: PatientState) -> str:
          return json.dumps(dataclasses.asdict(state))  # recursive; handles nested ClinicalFact dicts

      def deserialize_state(json_str: str, case_id: str) -> PatientState:
          d = json.loads(json_str)
          facts = {k: ClinicalFact(**v) for k, v in d.get('facts', {}).items()}
          return PatientState(
              case_id=d['case_id'], version=d['version'],
              turn_number=d['turn_number'], timestamp=d['timestamp'],
              facts=facts,
              revealed_evidence_ids=d.get('revealed_evidence_ids', []),
              medications=d.get('medications', []),
          )
      ```

      **StateManager reconstruction:**
      ```python
      def rebuild_state_manager(conversation_id: int) -> StateManager:
          case_id = str(conversation_id)
          sm = StateManager(case_id=case_id)
          state_json = get_latest_patient_state(conversation_id)
          if state_json is not None:
              saved_state = deserialize_state(state_json, case_id)
              sm.current_state = saved_state        # direct attribute assignment
              sm.current_version = saved_state.version
          return sm
      ```
      Rationale: `StateManager.__init__` accepts only `case_id`; there is no from-state constructor, so we set the attributes directly after construction. This is safe because both are plain Python attributes.

      **Main pipeline function:**
      ```python
      def run_pipeline(
          user_message: str,
          conversation_id: int,
          turn_index: int,
          prior_messages: list[dict],
      ) -> dict:
      ```

      Full execution order inside `run_pipeline`:
      1. Call `_get_shared_resources()` → `_, normalizer, retriever, vocab`
      2. `sm = rebuild_state_manager(conversation_id)`
      3. Construct `ConversationTurn(turn_index=turn_index, speaker='patient', text=user_message, revealed_evidence_ids=[], injection={})` — **must be a ConversationTurn, not a string**
      4. `extractor = StateExtractor(evidence_vocab=vocab)` → `new_facts = extractor.extract_from_turn(turn, turn_index)`
      5. `updated_state = sm.update(turn_index, new_facts)`
      6. `save_patient_state(conversation_id, turn_index, serialize_state(updated_state))`
      7. Build `Conversation` from `prior_messages + [current user message]`:
         - each `prior_messages` dict has `role` ('user'|'assistant') and `content`
         - `speaker = 'patient' if role == 'user' else 'doctor'`
         - `Conversation(case_id=str(conversation_id), turns=[...], current_turn=turn_index+1)`
      8. `response_gen = ResponseGenerator(sm, retriever, provider='mock')` → `response_text, evidence_used = response_gen.generate_response(conversation)`
      9. `verifier = CoherenceVerifier(sm, retriever, normalizer)` → `flags = verifier.verify(response_text, evidence_used, turn_index, conversation)`
      10. `gate = DecisionGate()` → `decision_str, reasoning_str = gate.evaluate(flags)` — tuple unpacking, not VerificationResult
      11. Build and return result dict with keys: `response_text`, `verification` (dict), `facts` (list of dicts), `state_summary` (dict), `evidence` (list of dicts)

      **`verification` sub-dict shape:**
      ```python
      {
          'pass_through': decision_str == 'PASS',
          'gate_decision': decision_str,       # 'PASS'|'CLARIFY'|'WARN'|'REFUSE'
          'reasoning': reasoning_str,
          'flags': [{'check_id':..., 'severity':..., 'description':..., 'turn_index':..., 'evidence':...}, ...]
      }
      ```

      Files: `lcc_system/webapp/pipeline.py`
      Verify: `python -m pytest tests/test_pipeline.py -v`

- [ ] 6. **Create `webapp/app.py`** — complete Streamlit application.

      **Module-level setup** (runs on every Streamlit script reload):
      ```python
      st.set_page_config(page_title='LCC Clinical Assistant', page_icon='🏥', layout='wide')
      init_db()
      ```

      **Session state keys:** `user_id` (int|None), `username` (str|None), `conv_id` (int|None), `page` ('login'|'main').

      **Auth page (`show_auth_page()`):**
      - Two tabs: "Login" and "Register"
      - Login tab: username + password fields, Login button → `login_user` → on success set session state + `st.rerun()`
      - Register tab: username + password + confirm-password fields, Register button → validate match → `register_user`
      - `st.warning(...)` disclaimer on both tabs: "⚠️ Research prototype only — NOT a medical diagnosis service."

      **Sidebar (`show_sidebar()`):**
      - "New Conversation" button → `create_conversation(user_id, title=f'Chat {datetime.now().strftime(...)}')` → set `conv_id` → `st.rerun()`
      - List previous conversations as buttons (label = title + date); clicking sets `conv_id` + `st.rerun()`
      - Logout button → clear `user_id`, `username`, `conv_id`, set `page='login'` → `st.rerun()`

      **Chat display (`show_main_app()`):**
      - Guard: verify `conv_id` ownership via `get_conversation(conv_id, user_id)`. If `None`, show error and clear `conv_id`.
      - Render historical messages with `st.chat_message('user'|'assistant')`, show timestamps via `st.caption`.
      - For historical assistant messages: call `get_verification_result(msg['id'])`, if found deserialize `flags_json` and show `show_verification_expander`.
      - `user_input = st.chat_input('Type your message...')` at bottom.
      - On new input: `add_message(conv_id, 'user', user_input)` → `run_pipeline(...)` with spinner → `add_message(conv_id, 'assistant', result['response_text'])` → `save_verification_result(asst_msg_id, json.dumps(result['verification']), ...)` → `st.rerun()`
      - `turn_index = len(messages)` (0-indexed; count of existing messages before this turn)

      **Verification expander (`show_verification_expander(result: dict)`):**
      - `with st.expander('🔍 Verification Details', expanded=False):`
      - Section 1: Extracted Clinical Facts — `st.table` or `st.markdown` list of `result['facts']`
      - Section 2: Patient State Summary — version, turn_number, medications, facts_count, contradictions
      - Section 3: Retrieved Evidence — per-record: evidence_id, active_ingredient, section_name, truncated evidence_text, clickable `[source]({url})` link
      - Section 4: Coherence Check — gate_decision with colour (green=PASS, yellow=CLARIFY/WARN, red=REFUSE), reasoning text, then each flag: check_id + severity + description

      **Entry point pattern (needed because Streamlit imports the module):**
      ```python
      def main():
          _init_session()
          if st.session_state.user_id is None:
              show_auth_page()
          else:
              show_main_app()

      main()   # called at module level so Streamlit runs it
      ```

      Files: `lcc_system/webapp/app.py`
      Verify: `python demo.py` still passes; `python -m pytest tests/ -v` all pass; `streamlit run webapp/app.py` starts.

- [ ] 7. **Create new test files** — `tests/test_database.py`, `tests/test_auth.py`, `tests/test_pipeline.py`.

      All three files must add both `src/` and the `webapp/` parent to `sys.path` at the top:
      ```python
      import sys, os
      SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
      WEBAPP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
      if SRC_DIR not in sys.path: sys.path.insert(0, SRC_DIR)
      if WEBAPP_DIR not in sys.path: sys.path.insert(0, WEBAPP_DIR)
      ```
      Then import from `webapp.database`, `webapp.auth`, `webapp.pipeline` using full dotted names.

      **`test_database.py` test list:**
      - `test_init_db_creates_tables`: monkeypatch `database.DB_PATH` to `tmp_path/'test.db'`, call `init_db()`, query `sqlite_master` and assert all 5 table names present.
      - `test_create_and_get_user`: create user, `get_user_by_username` returns row with matching username.
      - `test_duplicate_username_raises`: two `create_user` calls with same username → `sqlite3.IntegrityError`.
      - `test_create_and_get_conversation`: create user + conversation, `get_conversations_for_user` returns 1 row.
      - `test_conversation_ownership_enforced`: create 2 users, conv for user1, `get_conversation(conv_id, user2_id)` → `None`.
      - `test_add_and_get_messages`: `add_message` ×2, `get_messages` → 2 rows in insertion order.
      - `test_save_and_get_patient_state`: save two state JSONs at turn 0 and turn 1, `get_latest_patient_state` returns the turn-1 JSON.
      - `test_save_and_get_verification_result`: `add_message`, `save_verification_result`, `get_verification_result` → row with correct `gate_decision`.

      **`test_auth.py` test list:**
      - `test_hash_password_not_plain`: `hash_password('secret') != 'secret'`
      - `test_verify_password_correct`: `verify_password('secret', hash_password('secret'))` is `True`
      - `test_verify_password_wrong`: `verify_password('wrong', hash_password('secret'))` is `False`
      - `test_register_user_success`: monkeypatch DB_PATH, call `register_user('alice', 'password123')`, assert `(True, ...)`.
      - `test_register_short_password`: `register_user('bob', 'short')` → `(False, ...)`.
      - `test_register_duplicate_username`: register 'alice' twice → second call returns `(False, 'Username already taken.')`.
      - `test_login_success`: register then login → `(True, ..., int)` where int is user id.
      - `test_login_wrong_password`: register then login with wrong pw → `(False, ..., None)`.
      - `test_login_unknown_user`: login without register → `(False, ..., None)`.

      **`test_pipeline.py` test list:**
      Before importing `pipeline`, patch `streamlit.cache_resource` to a passthrough:
      ```python
      import unittest.mock as mock
      # At module level:
      with mock.patch('streamlit.cache_resource', lambda f: f):
          from webapp import pipeline
      ```
      Also monkeypatch `webapp.pipeline.save_patient_state` and `webapp.pipeline.get_latest_patient_state` for all tests.
      - `test_run_pipeline_returns_expected_keys`: `run_pipeline('I have fatigue', 999, 0, [])` → dict has keys `response_text`, `verification`, `facts`, `state_summary`, `evidence`.
      - `test_run_pipeline_gate_decision_is_valid`: `result['verification']['gate_decision']` in `{'PASS','CLARIFY','WARN','REFUSE'}`.
      - `test_run_pipeline_extracts_facts`: message='I have fatigue and chest pain' → `len(result['facts']) >= 1`.
      - `test_serialize_deserialize_roundtrip`: build `PatientState` with two `ClinicalFact`s, `serialize_state` → `deserialize_state`, assert `facts` keys and `status` values match.
      - `test_rebuild_state_manager_no_prior_state`: monkeypatch `get_latest_patient_state` → `None`, `rebuild_state_manager(1).current_version == 0`.
      - `test_rebuild_state_manager_with_prior_state`: monkeypatch `get_latest_patient_state` → JSON from `serialize_state` of a state at version 3, `rebuild_state_manager(1).current_version == 3`.
      - `test_build_conversation_maps_roles`: `prior_messages = [{'role':'user','content':'hello'},{'role':'assistant','content':'hi'}]`, `build_conversation(1, msgs, 2)` → `turns[0].speaker == 'patient'`, `turns[1].speaker == 'doctor'`.

      Files: `lcc_system/tests/test_database.py`, `lcc_system/tests/test_auth.py`, `lcc_system/tests/test_pipeline.py`
      Verify: `python -m pytest tests/ -v` — all old + new tests pass.

- [ ] 8. **Update `README.md`** — append web app instructions.
      Append a `## Web Application` section with:
      - Setup: `pip install -r requirements.txt` (now includes streamlit + bcrypt)
      - Run command: `streamlit run webapp/app.py` (from `lcc_system/` directory)
      - URL: `http://localhost:8501`
      - User flow: register → login → New Conversation → chat
      - DB location: `lcc_system/webapp/lcc_webapp.db` (auto-created, not committed)
      - Disclaimer: research prototype, not clinically safe
      Files: `lcc_system/README.md`
      Verify: `Select-String -Path README.md -Pattern 'streamlit run webapp/app.py'` returns a match.

- [ ] 9. **Create/update `.gitignore`** — exclude the runtime DB and Python artifacts.
      Create `lcc_system/.gitignore` if it doesn't exist, or append to it if it does. Include:
      ```
      webapp/lcc_webapp.db
      __pycache__/
      *.pyc
      .pytest_cache/
      *.egg-info/
      ```
      Files: `lcc_system/.gitignore`
      Verify: file exists and contains `webapp/lcc_webapp.db`.

- [ ] 10. **Final integration verification** — run all tests and the CLI demo.
       ```
       cd lcc_system
       python -m pytest tests/ -v
       python demo.py
       ```
       All existing tests pass unchanged. All three new test files pass. `demo.py` prints ≥1 `[DECISION]` line and exits 0.
       Files: none (verification only)
       Verify: `python -m pytest tests/ -v` — zero failures, zero errors; `python demo.py` exits 0.

---

## Architecture Decisions

**Why `@st.cache_resource` for the shared resources?**
`DatasetLoader` opens several CSV/JSONL files. Running it on every user message would be slow (each file read + parse). `st.cache_resource` caches at the Streamlit server level, so all users share one loader/normalizer/retriever instance. These objects are stateless after construction, so sharing is safe.

**Why `StateManager` is per-conversation, reconstructed from SQLite?**
`StateManager` is stateful (it holds `current_state`, `history`, `_contradictions`). Each conversation has its own independent patient state. We can't cache it globally. Instead we serialize `current_state` to JSON after each turn (`dataclasses.asdict`) and reconstruct it at the start of the next turn by directly assigning `sm.current_state` and `sm.current_version`. The `history` and `_contradictions` lists are not persisted — they're ephemeral within a single turn's processing. This is acceptable because `CoherenceVerifier` reads contradictions via `sm.get_contradictions()` within the same pipeline call.

**Why not persist `history` and `_contradictions`?**
The coherence checks only need `get_current_state()` and `get_contradictions()` within one pipeline call. Persisting the full history would add significant JSON complexity for no benefit in this version.

**Why `conversation_id` as `case_id` for `StateManager`?**
`StateManager(case_id: str)` expects a string identifier. Using the database `conversation_id` (cast to str) uniquely ties the patient state to the conversation without introducing new IDs.

**Why `sqlite3` only, no SQLAlchemy?**
The existing project uses Python stdlib only. Adding SQLAlchemy would introduce a new dependency class (ORM) beyond what bcrypt and streamlit add. The schema is simple enough that raw `sqlite3` is straightforward.

**Why direct attribute assignment for `StateManager` reconstruction?**
`StateManager.__init__` takes only `case_id`. There is no factory constructor or `from_state` class method. Directly assigning `sm.current_state = saved_state` and `sm.current_version = saved_state.version` is the simplest correct approach given the source cannot be modified. Both are plain Python attributes set in `__init__` — this pattern is fully valid.

---

## Loop Stop Contract

The gate file is:
`c:\Users\91895\OneDrive\Desktop\Longitudinal-Clinical-Coherence\.agents\tasks\lcc-webapp\review.json`

Shape: `{"verdict": "APPROVED" | "CHANGES_REQUESTED", "findings": [...], "reviewDoc": "<path>"}`

The reviewer writes this file as its last act every iteration.
