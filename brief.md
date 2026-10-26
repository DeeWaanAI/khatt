# Layer 3 — Action Layer · Design Brief

**Working title:** *Reversible Agency: A Permissioned, Provenance-Carrying Action Layer for LLM Operating Systems*
**Author:** Youssef Hariri · **Product:** DeeWaanAI · **Status:** DRAFT — awaiting owner confirmation before any building.
**Builds on:** Qafiya spec v1.1 (frozen). Layer 2 renderer mocked until its spec is frozen.
**Prior work feeding this brief:** `litreview/review.md` (38 verified works, searched 2026-10-19).

---

## 1. The idea in one paragraph

The action layer turns "the agent did something" into "the agent did something *on the record*."
Every action the system takes — moving a file, drafting an email, creating a calendar event —
is executed only inside an explicit permission scope and is stored, in the Qafiya substrate, as a
single bound artifact: the **action record**. The record carries what was asked, what was done,
on whose authority, with what data — and a **recipe to undo it**, or an honest machine-readable
label that it cannot be undone. The literature review confirms this artifact does not exist:
tool-use work keeps no receipt, agent-OS work enforces no authority, saga work compensates
failures but never gives the user recourse, and audit work logs fragments. Our contribution is
the integration — permission, record, and undo as one object in the data substrate.

## 2. The action record (core design)

Every action, before, during, and after execution, is one record with these fields:

| Field | Content | Set when |
|---|---|---|
| `action_id` | Unique ID; content-hash chained to prior record (tamper-evident log) | Creation |
| `intent` | The user's request, verbatim, plus the normalized action the system derived from it | Creation |
| `actor` | Who/what acts: the agent identity and the session it runs in | Creation |
| `authority` | On whose authority: the user, and the **permission scope** granted | Creation |
| `permission_scope` | Structured grant: allowed action type, target pattern, expiry, constraints (e.g. "move files within `/Documents/reports`, today only") | Creation — checked again at commit |
| `preconditions` | Machine-checkable statements that must hold before execution (target exists, disk space, scope still valid) | Checked at commit |
| `data_inputs` | Provenance links (Qafiya record refs) to every data item the action reads or writes | At execution |
| `execution_log` | Ordered steps actually taken, with timestamps and results | At execution |
| `outcome` | success / failed / refused / partial, with reason | At completion |
| `reversibility_class` | `EXACT` (byte-for-byte undoable) / `COMPENSABLE` (undoable by counter-action, e.g. delete sent-to-trash) / `IRREVERSIBLE` (e.g. sent email) | Classified **before** execution, shown to user |
| `undo_recipe` | An executable recipe (not prose): the operations that restore prior state, stored alongside | Captured **before/at** execution |
| `undo_status` | not_requested / available / executed / expired / impossible | Lifecycle |

Two design decisions to flag for your approval:

1. **Reversibility is classified before execution, not after.** The user sees "this can be
   undone exactly" or "this cannot be undone" *before* confirming. Irreversible actions
   require an explicit, separate confirmation — the honest handling of the "sent email"
   problem that the literature skips entirely.
2. **The undo recipe is captured at execution time, not reconstructed later.** For a file
   move, that means storing source path + pre-action hash. For a delete, it means moving to
   a managed trash area, never unlinking. If a recipe cannot be captured, the action is
   automatically classified IRREVERSIBLE and gated accordingly. **An action that cannot
   produce a receipt cannot run** — this is the enforcement core the agent-OS literature omits.

## 3. Architecture (prototype scope)

```
user request → Intent Parser → Action Proposal
                                    │
                    ┌───────────────▼────────────────┐
                    │  Permission Gate (deterministic)│  ← scope check at commit, not advisory
                    └───────────────┬────────────────┘
                                    │ granted
                    ┌───────────────▼────────────────┐
                    │  Precondition Check + Undo      │
                    │  Recipe Capture + Classify      │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  Executor (adapters)            │
                    │  · Qafiya file actions          │
                    │  · calendar (mock or real)      │
                    │  · email draft (draft only)     │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────▼────────────────┐
                    │  Action Record → Qafiya store   │  ← the receipt, always written
                    └────────────────────────────────┘
```

- **Executor over Qafiya stores first**: create, move, rename, edit, delete (to trash) —
  all file-level actions, all EXACT or COMPENSABLE reversible.
- **External actions** behind scopes, via adapter systems (we integrate, we do not rebuild):
  calendar (adapter over an existing calendar API) and **email — including real send —
  via an existing email-sending system** (e.g. an SMTP/API provider). Per owner decision,
  send is supported and classified `IRREVERSIBLE`, gated by the explicit separate
  confirmation; drafts are `EXACT`/`COMPENSABLE`.
- **Layer 2 renderer mocked**: a minimal stub renders confirmation prompts and audit
  views from action records; replaced by the real renderer when its spec freezes.
- **Permission gate is deterministic code**, not an LLM judgment — the adaptive-attacks
  finding [litreview ref 25] shows advisory classifiers degrade; structural checks hold.

## 4. Test plan — functional and limits

All experiments follow the Qafiya discipline: data frozen before runs, a spine script
recomputes every headline number from raw artifacts, and negative results are reported
as results. Three experiment tracks, matching the layer instructions:

### Track A — Reversibility rate (functional + limits)

A scripted **action battery**: a fixed list of ~40 actions across categories
(file create/move/rename/edit/delete; folder ops; calendar create/update/delete;
email draft create/edit/discard; plus deliberately irreversible stubs).

- **Measure:** share of actions that can be undone *exactly* — verified by content-hash
  comparison of pre-action vs. post-undo state, not by "it looked right."
- **Target:** 100% for data actions. External/compensable actions reported separately.
- **Honesty clause:** anything that cannot be undone exactly (e.g. a simulated sent email)
  is reported in its own class, mirroring the Qafiya paper's 0%-recall classes.
- **Limit probes:** undo after intermediate modifications; undo after system restart;
  undo ordering (undo action #5 while #6–#9 exist); undo of a partial/failed action;
  expired undo window.

### Track B — Permission containment (limits / adversarial)

Defect-injection, mirroring the Qafiya integrity track and informed by the
adaptive-attack literature:

- Inject **over-broad intents**: the derived action exceeds the granted scope
  (wrong folder, wrong action type, expired grant, escalated target such as
  "delete all" when "delete draft" was granted, path-escape attempts like `../`).
- **Measure:** share caught **before execution** — at the gate, deterministically.
  Any execution of an out-of-scope action is a reported failure, full stop.
- **Limit probes:** scope-bypass attempts via malformed intents, chained actions that
  are individually in-scope but jointly out-of-scope, replay of an expired grant,
  tampered action records (hash-chain must catch them).

### Track C — Auditability / re-narratability (functional)

- For every executed action in the battery: reconstruct a full narrative
  (what was asked, by whom, on what authority, what data, what happened, how to undo)
  **from the record alone** — no reruns, no logs outside the record.
- **Measure:** share of actions fully re-narratable from record only (target 100%);
  plus a tamper check: modified records must be detectable via the hash chain.
- **Before/after examples** in the paper: one file move shown end-to-end
  (request → gate → execute → record → undo), one refused over-broad intent,
  one irreversible action correctly gated — per the project's plain-English,
  show-the-system-operating rule.

### What we explicitly do NOT test (out of scope)

Which model plans the action (Layer 5), memory across sessions (Layer 4),
the shell UI (Layer 6). Intent parsing in the prototype is scripted/simple;
the paper claims the *record and enforcement*, not NL understanding quality.

## 5. Deliverables and order

1. This brief → **your confirmation** (stop here).
2. `spec.md` — formal spec of the action record, permission scopes, gate semantics,
   undo recipes, and the Qafiya binding.
3. Prototype (Python, AGPL-3.0, DeeWaanAI org).
4. Frozen experiments + spine script (`run_all.py` recomputes all headline numbers).
5. Paper draft (.tex), HBR register, with the honesty section: what the layer provably
   cannot do (irreversible actions, chained-undo limits, whatever Track B bypasses we find).

## 6. Owner decisions (2026-10-19) — design locked

1. **Email:** send is in scope, executed through an existing email-sending system
   (adapter over an external provider — we do not build the sending system).
   Send is classified `IRREVERSIBLE` and gated accordingly; drafts remain reversible.
2. **Trash:** deletes go to a managed trash **inside the Qafiya store**, replacing any
   reliance on OS-native trash. Trash contents are provenance-carrying records and
   purge is itself a recorded, irreversible-classified action.
3. **Tamper-evidence:** the action log is **hash-chained from v1** — each record
   embeds the hash of its predecessor, so any modification or deletion of history is
   detectable. Verified in Track C.
