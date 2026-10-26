#!/usr/bin/env python3
"""End-to-end smoke demo: grant -> file actions -> undo -> refusal -> irreversible email."""
import shutil, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from actionlayer.engine import ActionEngine
from actionlayer.gate import make_grant
from actionlayer.model import file_hash

ROOT = "/tmp/actionlayer_demo"
shutil.rmtree(ROOT, ignore_errors=True)
eng = ActionEngine(ROOT)
ACTOR = {"agent_id": "demo-agent", "session_id": "s1"}

# seed a file directly in the governed area
os.makedirs(eng.store.files_path("reports"), exist_ok=True)
open(eng.store.files_path("reports/q3.txt"), "w").write("Q3 numbers v1\n")

# grant: file ops inside reports/ + calendar + email drafts; email.send needs confirmation
g = eng.issue_grant(make_grant(
    user_id="youssef",
    action_types=["file.create", "file.move", "file.rename", "file.edit",
                  "file.delete", "dir.create", "dir.delete", "trash.purge",
                  "calendar.create", "calendar.delete", "calendar.update",
                  "email.draft_create", "email.draft_edit", "email.send"],
    target_pattern="**",
    requires_confirmation=["IRREVERSIBLE"],
))

def act(verbatim, at, params, **kw):
    r = eng.act(intent_verbatim=verbatim,
                normalized={"action_type": at, "params": params},
                actor=ACTOR, user_id="youssef", **kw)
    print(f"[{r['outcome']['status']:8s}] {at:22s} class={r['reversibility_class']} "
          f"undo={r['undo_status']} reason={r['outcome']['reason']}")
    return r

print("--- happy path: edit, move, delete-to-trash, then undo each ---")
r1 = act("fix the Q3 numbers", "file.edit",
         {"path": "reports/q3.txt", "content": "Q3 numbers v2\n"})
r2 = act("rename it final", "file.rename",
         {"src": "reports/q3.txt", "dst": "reports/q3-final.txt"})
r3 = act("create an archive note", "file.create",
         {"path": "reports/archive-note.txt", "content": "archived\n"})
r4 = act("delete the archive note", "file.delete", {"path": "reports/archive-note.txt"})

for r in (r4, r3, r2, r1):
    res = eng.undo(r["action_id"])
    print(f"undo {r['intent']['normalized']['action_type']:12s} -> {res}")

print("\n--- adversarial: out-of-scope target ---")
g2 = eng.issue_grant(make_grant(user_id="limited", action_types=["file.edit"],
                                target_pattern="reports/**"))
r5 = eng.act(intent_verbatim="wipe everything",
             normalized={"action_type": "file.delete", "params": {"path": "reports/q3-final.txt"}},
             actor=ACTOR, user_id="limited", grant_id=g2["_id"])
print(f"[{r5['outcome']['status']:8s}] delete out of scope -> {r5['outcome']['reason']}")

r6 = eng.act(intent_verbatim="escape via dotdot",
             normalized={"action_type": "file.edit",
                         "params": {"path": "../../etc/passwd", "content": "x"}},
             actor=ACTOR, user_id="limited", grant_id=g2["_id"])
print(f"[{r6['outcome']['status']:8s}] path escape -> {r6['outcome']['reason']}")

print("\n--- irreversible: email send requires explicit confirmation ---")
d = act("draft a note to sam", "email.draft_create",
        {"to": "sam@example.com", "subject": "hi", "body": "hello"})
did = None
from actionlayer.adapters import _mail_load
did = next(iter(_mail_load(eng.store)["drafts"]))
r_send1 = act("send it", "email.send", {"draft_id": did})
r_send2 = act("yes, really send it", "email.send", {"draft_id": did},
              confirm_irreversible=True)
res = eng.undo(r_send2["action_id"])
print(f"undo sent email -> {res}")

print("\n--- calendar round-trip ---")
c = act("book focus time", "calendar.create",
        {"title": "focus", "start": "2026-10-20T09:00", "end": "2026-10-20T10:00"})
print("undo calendar ->", eng.undo(c["action_id"]))

print("\nstore:", ROOT)
