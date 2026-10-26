#!/usr/bin/env python3
"""audit/renarrate.py — render a complete narrative from a record ALONE (Track C).
Usage: python -m audit.renarrate <store_root> <action_id>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "prototype"))
from actionlayer.qafiya_shim import QafiyaStore

REQUIRED = ["intent", "actor", "authority", "permission_scope", "preconditions",
            "reversibility_class", "execution_log", "outcome"]

def renarrate(rec):
    n = rec["intent"]["normalized"]
    lines = [
        f"Action {rec['action_id']}",
        f"  Asked:   \"{rec['intent']['verbatim']}\"",
        f"  Parsed:  {n['action_type']} {n.get('params', {})} "
        f"(parser={rec['intent']['parser']} v{rec['intent']['parser_version']})",
        f"  Actor:   agent={rec['actor']['agent_id']} session={rec['actor']['session_id']}",
        f"  Authority: user={rec['authority']['user_id']} grant={rec['authority']['grant_id']}",
        f"  Scope:   types={rec['permission_scope'].get('action_types')} "
        f"pattern={rec['permission_scope'].get('target_pattern')}",
        f"  Class:   {rec['reversibility_class']}",
        f"  Preconditions: " + ", ".join(f"{c['check']}={c['result']}"
                                         for c in rec["preconditions"]) or "  Preconditions: none",
        f"  Steps:   " + " | ".join(f"{s['step']}({s['result']})"
                                    for s in rec["execution_log"]),
        f"  Outcome: {rec['outcome']['status']} {rec['outcome']['reason']}",
        f"  Undo:    status={rec['undo_status']} "
        f"recipe={'yes' if rec.get('undo_recipe') else 'none'}",
        f"  Confirmations: {[c['kind'] for c in rec.get('confirmations', [])]}",
    ]
    return "\n".join(lines)

def completeness(rec):
    required = list(REQUIRED)
    if rec["outcome"]["status"] == "refused" and "gate" in \
            " ".join(s["step"] for s in rec["execution_log"]):
        # refused at the gate: no classification was ever reached — refusal reason
        # in the log is the complete narrative
        required.remove("reversibility_class")
    missing = [k for k in required if k not in rec or rec.get(k) is None
               or (k != "preconditions" and rec.get(k) in ("", [], {}))]
    if rec.get("reversibility_class") in ("EXACT", "COMPENSABLE") and \
       rec["outcome"]["status"] == "success" and not rec.get("undo_recipe"):
        missing.append("undo_recipe")
    return missing

def main(root, action_id=None):
    store = QafiyaStore(root)
    records = store.read_all("action_log")
    sel = [r for r in records if action_id in (None, r["action_id"])]
    full = 0
    for r in sel:
        print(renarrate(r))
        miss = completeness(r)
        print(f"  Re-narratable from record alone: {'YES' if not miss else 'NO — missing: ' + str(miss)}")
        print()
        if not miss:
            full += 1
    print(f"re_narratable={full}/{len(sel)}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
