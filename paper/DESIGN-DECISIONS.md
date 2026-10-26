# Layer 3 (Khatt) — Design Decision Log

Append-only. Annotate, never rewrite.

- **D1 (2026-10-19):** Undo recipes captured *before* execution, not reconstructed after.
  Rationale: reconstruction is impossible for deletes/moves once state is gone.
  Grounding: litreview gap (saga work hand-writes compensation; no agent system stores
  per-action recipes). Implemented in `adapters/*capture_undo`, engine ARMED stage.
- **D2 (2026-10-19):** Permission gate is deterministic code; no LLM judgment.
  Rationale: adaptive attacks degrade advisory classifiers (litreview ref 25).
  Implemented in `gate.py`; evaluated adversarially in Track B.
- **D3 (2026-10-19, owner):** Email send in scope via an external sending system
  (adapter); classified IRREVERSIBLE; explicit recorded confirmation required.
- **D4 (2026-10-19, owner):** Managed trash inside the Qafiya store replaces OS-native
  trash; purge is itself a recorded IRREVERSIBLE action.
- **D5 (2026-10-19, owner):** Hash-chained action log from v1 for tamper-evidence.
- **D6 (2026-10-19):** Exactness of undo is proven by state-hash comparison
  (pre-action vs post-undo), never by executor self-report. Implemented as
  `state_hash()` in `experiments/run_all.py`.
- **D8 (2026-10-26, external audit revision):** Implemented
  `instructions_26_oct_2026.md`. (1) Abstract and conclusion defect label corrected
  to "injected permission and precondition defects". (2) Added the Layer-2 renderer
  stub (`actionlayer/renderer.py`) with `render_confirmation`/`render_audit_view`,
  wired into the confirmation path as a display path only; `prototype/test_renderer_stub.py`
  asserts the interface exists and is invoked on confirmation, not on refusal —
  chose the stub over removing the claim (monitor to update INTERFACES.md).
  (3) Track A reframed: 37/37 presented as a by-construction correctness check;
  findings led by classification-before-commitment, conflict refusal,
  irreversibility gating. (4) Permission Manifests reference year fixed to 2026.
  (5) Spec header marked v0.1 FROZEN (2026-10-20). Frozen battery not re-run, per
  instructions.

- **D7 (2026-10-20, monitor integration):** Followed MONITOR-GUIDE.md with owner
  go. (1) Tamper-evident chain replaced by the inherited Qafiya substrate chain
  v1.3 (`qafiya_core_chain`, reference impl vendored from
  `00-monitor/packages/qafiya-v1.3-hash-chain/`); `audit/verify_chain.py` is now a
  thin wrapper. (2) Storage conformed to Qafiya §8: `datasets/action_log/` and
  `datasets/grants/` with `schema.json + data.jsonl + history.jsonl +
  bindings.jsonl + SUPERSEDED.json`; adapters' content stays at root. (3) Ids are
  prefixed sortable (`a_*`, `g_*`). (4) Layer-2 rewiring deferred — dvr/1.0 not
  yet confirmed frozen. Headline results unchanged (37/37, 15/15, 39/39) — the
  integration moved mechanisms, not numbers. Spec bumped accordingly.

- **D9 (2026-10-26, claim-map alignment):** Two fixes so the paper matches the maps
  exactly: §undo-semantics now states the delete exception (trash id captured at the
  moment of the move), matching SC-ABS-002's note; semantic-map line number for
  SC-EV-003 corrected (253). Quote sweep: 24/24 semantic quotes verbatim-present in
  the draft; data verifier exit 0; compile clean.

## Oversight episodes (for the AI-usage disclosure section)
- **E1 (2026-10-19):** First spine run reported 64.9% reversibility. Root cause was in
  our own undo code (empty parent directories left behind) and in the measurement
  (byte-wise hashing of adapter DB files instead of semantic hashing). Fixed, re-run,
  37/37. Lesson: the frozen-spine discipline caught a real defect before the paper
  carried it.
- **E2 (2026-10-19, rigor pass):** Paper claimed "nine action types"; the frozen
  battery contains fifteen. Paper-only number, corrected via claim map.
- **E3 (2026-10-19, semantic pass):** Track C harness marked artifact-less setup
  actions as failed dependencies (5 skips), while the draft said "two battery actions
  were skipped" next to 36/36. Harness fixed; rerun yields 2 legitimate skips and
  39/39; draft updated. Class: existence/attribution defect in the experiment harness
  surfaced by prose-vs-data checking.
