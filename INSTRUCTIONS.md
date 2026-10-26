# Layer 3 — Action Layer · INSTRUCTIONS

**Paper working title:** *Reversible Agency: A Permissioned, Provenance-Carrying Action Layer for LLM Operating Systems*

## Mission

Let agents *act* — move, delete, send, schedule, purchase — with two guarantees no
current agent OS offers: every action is a **bound record** (what was asked, what was
done, on whose authority, with what data), and every action is **reversible** or
explicitly marked irreversible.

## What to build (in order)

1. **Design brief** — the action record: intent, preconditions, permission scope,
   execution log, undo recipe. Position against AIOS [6], generative file systems
   [2, 3], and tool-use/agent literature (fresh mini-review required — the Qafiya
   review does not cover tool-use; run a small verified search in the same style).
   Stop for owner confirmation.
2. **Prototype** — an action executor over Qafiya stores first (file-level actions),
   then 2–3 external actions (e.g. calendar, email draft) behind permission scopes.
3. **Experiments (frozen):**
   - Reversibility rate: share of a scripted action battery that can be undone
     exactly (target: 100% for data actions; report what can't be, e.g. sent email).
   - Permission containment: injected over-broad intents must be caught before
     execution (defect-injection style, mirroring the Qafiya integrity track).
   - Auditability: every action re-narratable from its record alone.

## Contracts you build on

- Qafiya spec v1.1 (actions are stored as bindings/records in Qafiya datasets).
- Layer 2 renderer (action confirmations and audit views render through it) — code
  against its frozen spec once it exists; until then, mock it.

## Deliverables

`brief.md` → `spec.md` → prototype → frozen experiments → paper draft (.tex).

## Out of scope

Memory across sessions (Layer 4), which model plans the action (Layer 5), the shell
UI (Layer 6).
