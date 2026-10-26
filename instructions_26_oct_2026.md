# Layer 3 (Khatt) — Revision instructions · 26 Oct 2026

**Source:** external audit (DeeWaanAI-OS-audit-2026-10-26.md). Text repairs + one small stub; do not re-run the frozen battery.

1. **Abstract defect label.** "caught 15/15 injected over-broad intents" → "injected permission and precondition defects". The 15 include path traversal, expired/missing grants, unknown action types, failed preconditions, missing confirmations — only some are over-broad intents. (This is the taxonomy's own S2 wrong-label class; fix it with care.)
2. **Mock interface claim vs code.** The paper says the renderer is mocked behind `render_confirmation` / `render_audit_view`, but those names exist only in the spec and guide, not in the prototype. **Add a small stub + one test** asserting the interface exists and is called on the confirmation path (preferred — L6 needs it), or remove the claim. Tell the monitor which you chose so INTERFACES.md can be updated.
3. **Reframe 37/37.** Exact reversibility is true by construction for EXACT actions. Present it as a correctness check; lead with the interesting results: classification before commitment, refusal on external modification, irreversibility gating. Keep the honest "floor, not ceiling" line.
4. **Reference year.** "Permission Manifests" is dated 2025 in the bibliography but is arXiv 2601 (January 2026). Fix.
5. **Spec freeze (administrative).** Your spec header still says "v0.1 (DRAFT)" although the monitor verified conformance on 2026-10-20. Change the header to **v0.1 FROZEN (date)** and note it in the decision log; the monitor will mark it frozen in INTERFACES.md. This is required before L6 can consume your contract.
6. **AI disclosure** — keep it; it is the best in the series. Optionally move the three oversight episodes to an appendix for conservative venues; do not delete the disclosure itself.

## Acceptance

Abstract label corrected; the stub exists and is tested (or the claim removed); spec header frozen; claim map and spine still exit 0; .tex compiles clean.
