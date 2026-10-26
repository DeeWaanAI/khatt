# Integration guide — Layer 3 (action layer)

**From:** monitor · **Date:** 2026-10-20 · **Nothing here changes your published results; this is conformance + substrate sharing.**

## 1. Hash chain → consume Qafiya v1.3 (when owner confirms the bump)

- Replace the local chain code behind your §3 (`record_hash`/`prev_hash`) with
  `qafiya_core.chain` (reference impl: `00-monitor/packages/qafiya-v1.3-hash-chain/chain.py`,
  tests pass). Your `audit/verify_chain.py` becomes a thin wrapper calling
  `chain.verify(...)` per store.
- Paper edit (one sentence): "the tamper-evident chain is inherited from the Qafiya
  substrate (v1.3)" — cite the Qafiya paper. Stronger story: mechanism proven at the
  substrate, applied at the action layer.

## 2. Storage layout → conform to Qafiya §8

Your action stores currently use `records.jsonl` + `grants.jsonl`. Conform:

```
datasets/action_log/   schema.json  data.jsonl (the action records)  history.jsonl  bindings.jsonl  SUPERSEDED.json
datasets/grants/       schema.json  data.jsonl (permission_grant records)  …
```

- Write a two-section `schema.json` per dataset (fields are already documented in
  your spec §3/§4 — mechanical transcription).
- Keep `files/`, `trash/`, `.snap/` as adapter-managed content addressed by records
  (that's fine — media/blobs live outside datasets in Qafiya too).
- If any field genuinely doesn't fit Qafiya §8, write an `EXTENSION.md` (versioned)
  instead of drifting silently.

## 3. Identity rule

`action_id`/`grant_id`: switch uuid4 → prefixed sortable ids (`a_*`, `g_*`, ULID or
sortable uuid payload). One-line change in your id factory; see INTERFACES.md.
Paper: replace "uuid-v4" with "prefixed sortable identifier (OS identity rule)".

## 4. Layer-2 mock → real

When the dvr/1.0 contract is confirmed frozen (INTERFACES.md), rewire
`render_confirmation` / `render_audit_view` from the stub to the real renderer.
Your experiment artifacts don't change — only the demo path.
