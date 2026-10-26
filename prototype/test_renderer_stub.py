#!/usr/bin/env python3
"""Test: the Layer-2 renderer stub exists and is invoked on the confirmation path.
(Revision instructions 2026-10-26, item 2.)"""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from actionlayer.engine import ActionEngine
from actionlayer.gate import make_grant
from actionlayer import renderer

def main():
    assert hasattr(renderer, "render_confirmation"), "interface missing: render_confirmation"
    assert hasattr(renderer, "render_audit_view"), "interface missing: render_audit_view"

    root = tempfile.mkdtemp(prefix="khatt-renderer-test-")
    try:
        eng = ActionEngine(root)
        g = eng.issue_grant(make_grant(
            user_id="u", action_types=["email.draft_create", "email.send"],
            target_pattern="**", requires_confirmation=["IRREVERSIBLE"]))
        actor = {"agent_id": "t", "session_id": "t"}
        d = eng.act(intent_verbatim="draft", normalized={
            "action_type": "email.draft_create",
            "params": {"to": "sam@example.com", "subject": "s", "body": "b"}},
            actor=actor, user_id="u")
        from actionlayer.adapters import _mail_load
        did = next(iter(_mail_load(eng.store)["drafts"]))

        renderer.CALLS.clear()
        s = eng.act(intent_verbatim="send it", normalized={
            "action_type": "email.send", "params": {"draft_id": did}},
            actor=actor, user_id="u", confirm_irreversible=True)
        assert s["outcome"]["status"] == "success", s["outcome"]
        assert ("render_confirmation", s["action_id"]) in renderer.CALLS, \
            f"confirmation path did not call the renderer: {renderer.CALLS}"

        html = renderer.render_audit_view(s)
        assert isinstance(html, str) and s["action_id"] in html

        # and on the refusal path the renderer is NOT consulted (no confirmation given)
        d2 = eng.act(intent_verbatim="draft2", normalized={
            "action_type": "email.draft_create",
            "params": {"to": "sam@example.com", "subject": "s", "body": "b"}},
            actor=actor, user_id="u")
        did2 = next(k for k in _mail_load(eng.store)["drafts"] if k != did)
        renderer.CALLS.clear()
        r = eng.act(intent_verbatim="send without confirming", normalized={
            "action_type": "email.send", "params": {"draft_id": did2}},
            actor=actor, user_id="u")
        assert r["outcome"]["status"] == "refused"
        assert ("render_confirmation", r["action_id"]) not in renderer.CALLS
        print("PASS: renderer stub exists, called on confirmation path, "
              "not consulted on refusal path")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
