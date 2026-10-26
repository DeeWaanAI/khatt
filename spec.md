# Layer 3 — Action Layer · Formal Specification v0.1 **FROZEN (2026-10-20)**

**Freeze note:** conformance verified by the monitor on 2026-10-20 (MONITOR-GUIDE.md
items 1–3 applied; storage §8-conformant, chain inherited from Qafiya v1.3, prefixed
sortable ids). Frozen 2026-10-26 per revision instructions; logged as D8. L6 may
consume this contract.

**Implements:** `brief.md` (owner-confirmed 2026-10-19, decisions in brief §6)
**Builds on:** Qafiya spec v1.1 (frozen) — action records are Qafiya records; data inputs are Qafiya provenance links.
**Scope discipline:** memory (Layer 4), model routing/planning (Layer 5), shell UI (Layer 6) are out of scope. Layer 2 renderer is mocked behind the interface in §8.

---

## 1. Definitions

- **Action** — a state change the agent performs or attempts: file operations over Qafiya
  stores, calendar operations, email operations.
- **Action record** — the single bound artifact (§3) that exists for every action from
  proposal to undo. Stored as a Qafiya record.
- **Permission scope** — a structured grant (§4) without which no action executes.
- **Undo recipe** — executable operations restoring prior state (§6).
- **Gate** — deterministic (non-LLM) code that checks scope and preconditions at commit time.

## 2. Action lifecycle (state machine)

```
PROPOSED → GATED ──refused──> REFUSED (terminal, record kept)
   │ granted
   ▼
ARMED ──(undo recipe captured, reversibility classified)──>
   │ user confirmation if IRREVERSIBLE or scope requires
   ▼
EXECUTING ──failure──> FAILED (record kept; partial state compensated where possible)
   │ success
   ▼
DONE ──undo requested & available──> UNDOING ──> UNDONE (terminal)
   │
   └──> terminal states: DONE / UNDONE / IRREVERSIBLE_DONE
```

Invariants:
- **I1.** No transition past GATED without a valid, unexpired permission scope.
- **I2.** No transition to EXECUTING without a captured undo recipe **or** an
  `IRREVERSIBLE` classification with explicit user confirmation on record.
- **I3.** Every transition is appended to the record's `execution_log` and the record is
  written to the Qafiya store at every transition. An action whose record cannot be
  written **does not run**.
- **I4.** REFUSED and FAILED are terminal states with kept records — refusals and
  failures are results, never hidden (Qafiya honesty rule).

## 3. The action record (schema)

Stored as a Qafiya record, type `action_record`, JSON-serializable:

```json
{
  "action_id": "prefixed sortable identifier (a_*; OS identity rule)",
  "created_at": "ISO-8601 UTC",
  "intent": {
    "verbatim": "user's request, exact string",
    "normalized": {"action_type": "file.move", "params": {...}},
    "parser": "scripted|llm", "parser_version": "..."
  },
  "actor": {"agent_id": "...", "session_id": "..."},
  "authority": {"user_id": "...", "grant_id": "ref to permission scope record"},
  "permission_scope": { "...": "§4 object, embedded copy (grants are immutable)" },
  "preconditions": [{"check": "target_exists", "params": {...}, "result": "pass|fail"}],
  "reversibility_class": "EXACT | COMPENSABLE | IRREVERSIBLE",
  "undo_recipe": {"ops": [...], "captured_at": "...", "expires_at": "...|null"},
  "data_inputs": [{"qafiya_ref": "...", "role": "read|write", "pre_hash": "...", "post_hash": "..."}],
  "execution_log": [{"ts": "...", "step": "...", "result": "..."}],
  "outcome": {"status": "success|failed|refused|partial", "reason": "..."},
  "undo_status": "not_requested|available|executed|expired|impossible",
  "confirmations": [{"kind": "irreversible_ack", "ts": "...", "user_id": "..."}]
}
```

- Tamper-evidence is inherited from the Qafiya substrate (v1.3): every commit
  appends a chained entry to `datasets/action_log/history.jsonl`
  (`qafiya_core_chain`; owner decision 3). Verification walks the chain and
  recomputes hashes; any mismatch = tamper, reported.
- Storage conforms to Qafiya §8: `datasets/action_log/` and `datasets/grants/`
  each carry `schema.json + data.jsonl + history.jsonl + bindings.jsonl +
  SUPERSEDED.json`; `files/`, `trash/`, `.snap/` are adapter-managed content
  addressed by records. Ids are prefixed sortable (`a_*` actions, `g_*` grants;
  OS identity rule, INTERFACES.md).
- `permission_scope` is embedded by value: later grant revocation cannot rewrite history.

## 4. Permission scopes

A grant is itself a Qafiya record (type `permission_grant`), immutable once created:

```json
{
  "grant_id": "prefixed sortable identifier (g_*)", "user_id": "...",
  "action_types": ["file.move", "file.edit"],
  "target_pattern": "/Documents/reports/**",
  "constraints": {"max_size_bytes": null, "not_before": "...", "expires_at": "..."},
  "requires_confirmation": ["IRREVERSIBLE", "email.send"]
}
```

Gate check (deterministic, in order):
1. Grant exists and `expires_at` not passed.
2. `normalized.action_type` ∈ `action_types`.
3. Resolved target path matches `target_pattern` **after canonicalization**
   (no `..`, symlinks resolved) — path-escape attempts fail here by construction.
4. All constraints hold.
5. If action class is IRREVERSIBLE or listed in `requires_confirmation`:
   require a `confirmations[]` entry recorded before EXECUTING.

Any failure → REFUSED with reason. **The gate is pure code; no LLM judgment is consulted**
(design consequence of the adaptive-attack findings, litreview §3.4).

## 5. Executors and adapters

- **File executor (primary, over Qafiya stores):** `file.create`, `file.move`,
  `file.rename`, `file.edit`, `file.delete`, `dir.create`, `dir.delete`.
  - `file.delete` **never unlinks**: it moves the entry into the Qafiya-managed trash
    (owner decision 2). Trash entries are Qafiya records with provenance to the delete
    action. `trash.purge` is itself an action, classified `IRREVERSIBLE`, gated.
- **Calendar adapter:** create/update/delete event via an existing calendar API.
  create→delete is `EXACT`; update is `COMPENSABLE` (restore prior fields).
- **Email adapter (owner decision 1):** integrates an existing email-sending system
  (SMTP/API provider) — not built from scratch.
  - `email.draft_create/edit/discard`: `EXACT`.
  - `email.send`: `IRREVERSIBLE`; requires `confirmations[irreversible_ack]`;
    record stores provider message-id as provenance of the external effect.
- Adapters declare, per action type: reversibility class, undo ops, and precondition
  checks. The executor core is adapter-agnostic.

## 6. Undo semantics

- **EXACT:** post-undo state hash-equals pre-action state for every `data_inputs` entry
  (verified, not assumed).
- **COMPENSABLE:** a counter-action restores semantic state (e.g. trash restore,
  field-restore); the undo is itself an action record chained into the log.
- **IRREVERSIBLE:** no undo path exists; `undo_status=impossible`; the record and the
  pre-execution confirmation are the audit trail.
- Undo of an undone action is a no-op with a kept record. Undo ordering is unrestricted:
  each undo restores its own action's captured pre-state; conflicts (target modified
  after the action) are detected via `post_hash` mismatch → undo refuses with reason
  rather than silently overwriting (limit probe A-3 in the experiment plan).

## 7. Audit & verification (spine)

`audit/verify_chain.py` is a thin wrapper over `qafiya_core_chain.verify(...)` on
`datasets/action_log/history.jsonl` and reports any break. `audit/renarrate.py` renders a complete human-readable narrative
from a record alone — the Track C instrument. `experiments/run_all.py` recomputes all
headline numbers from frozen raw artifacts; if it fails, the number does not go in the
paper (Qafiya discipline).

## 8. Layer-2 mock interface

Until the renderer spec freezes: `render_confirmation(action_record) -> bool` and
`render_audit_view(action_record) -> html` behind a stub interface; production wiring
uses the frozen Layer 2 spec only (contract rule 3 of the master instructions).

## 9. What this spec provably does not guarantee (honesty section, draft)

- Irreversible actions cannot be undone — only gated and recorded.
- Chained-undo conflicts are detected and refused, not auto-resolved.
- The gate contains actions **as normalized**; it does not guarantee the normalization
  (intent parsing) matched the user's meaning — that is Layer 5's problem, stated in
  the paper.
- Tamper-evidence detects modification of history; it does not prevent deletion of the
  entire store (mitigation: replication/backup, future work).

## 10. Experiment mapping

| Spec mechanism | Experiment |
|---|---|
| §6 undo semantics, EXACT verification | Track A — reversibility rate (target 100% data actions) |
| §4 gate + §2 I1–I3 | Track B — permission containment via defect injection |
| §3 record completeness, hash chain, §7 tools | Track C — re-narratability + tamper detection |

Frozen artifacts, spine script, and negative-results reporting follow Qafiya spec v1.1.
