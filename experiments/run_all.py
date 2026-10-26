#!/usr/bin/env python3
"""experiments/run_all.py — the spine script.

Runs the frozen battery + defect injection against fresh stores, and recomputes
every headline number from the raw artifacts it produces. Qafiya discipline:
if this script fails, the number does not go in the paper.

Usage: python experiments/run_all.py
Outputs: experiments/out/<track>/... raw stores + logs
         experiments/out/results.json  headline numbers
"""
import json, os, shutil, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "prototype"))
sys.path.insert(0, os.path.join(ROOT, "audit"))

from actionlayer.engine import ActionEngine
from actionlayer.gate import make_grant
from actionlayer.model import file_hash
from actionlayer import qafiya_core_chain as chain
from actionlayer.qafiya_shim import QafiyaStore
from renarrate import completeness

OUT = os.path.join(HERE, "out")
BIG = ("lorem ipsum dolor sit amet — 数据 " * 800) + "\n"
ACTOR = {"agent_id": "experiment-agent", "session_id": "frozen-run"}

def state_hash(store):
    """Semantic content hash of everything the actions can touch.
    Missing DB files are hashed as their empty defaults so create-then-undo
    is identical to never-created."""
    h = hashlib.sha256()
    for base in (store.files_path(), store.trash_path()):
        fh = file_hash(base)
        h.update(fh.encode() if fh else b"EMPTY")
    defaults = {"calendar.json": {}, "mail.json": {"drafts": {}, "sent": []}}
    for f, default in defaults.items():
        p = os.path.join(store.root, f)
        data = json.load(open(p)) if os.path.exists(p) else default
        h.update(json.dumps(data, sort_keys=True).encode())
    return h.hexdigest()

def seed(store, seeds):
    for s in seeds:
        ap = store.files_path(s["path"])
        os.makedirs(os.path.dirname(ap), exist_ok=True)
        open(ap, "w").write(s["content"])

def issue_grants(eng):
    g = {}
    g["main"] = eng.issue_grant(make_grant(
        user_id="youssef",
        action_types=["file.create", "file.move", "file.rename", "file.edit",
                      "file.delete", "dir.create", "dir.delete", "trash.purge",
                      "calendar.create", "calendar.delete", "calendar.update",
                      "email.draft_create", "email.draft_edit",
                      "email.draft_discard", "email.send"],
        target_pattern="**", requires_confirmation=["IRREVERSIBLE"]))
    g["limited"] = eng.issue_grant(make_grant(
        user_id="limited", action_types=["file.edit"], target_pattern="reports/**"))
    g["expired"] = eng.issue_grant(make_grant(
        user_id="ghost", action_types=["file.create", "file.edit", "file.delete"],
        target_pattern="**", expires_at="2020-01-01T00:00:00+00:00"))
    return g

def resolve(params, artifacts):
    out = {}
    for k, v in params.items():
        if isinstance(v, str) and v.startswith("@"):
            out[k] = artifacts[v[1:]]
        elif v == "__BIG__":
            out[k] = BIG
        else:
            out[k] = v
    return out

def run_action(eng, grants, grant_name, action_type, params, verbatim,
               confirm=False, artifacts=None):
    params = resolve(params, artifacts or {})
    user = {"main": "youssef", "limited": "limited", "expired": "ghost", "none": "nobody"}[grant_name]
    gid = grants[grant_name]["_id"] if grant_name != "none" else None
    return eng.act(intent_verbatim=verbatim,
                   normalized={"action_type": action_type, "params": params},
                   actor=ACTOR, user_id=user, grant_id=gid,
                   confirm_irreversible=confirm)

def capture_artifacts(eng, rec):
    """Extract produced ids (event/draft/trash) from a setup action's record."""
    arts = {}
    recipe = rec.get("undo_recipe") or {}
    for op in recipe.get("ops", []):
        if op["op"] == "cal_delete":
            arts["event"] = op["event_id"]
        if op["op"] == "draft_remove":
            arts["draft"] = op["draft_id"]
        if op["op"] == "restore_trash":
            arts["trash"] = op["trash_id"]
    return arts

# ---------------- Track A ----------------

def track_a(battery):
    results = []
    for a in battery["actions"]:
        sroot = os.path.join(OUT, "trackA", a["id"])
        shutil.rmtree(sroot, ignore_errors=True)
        eng = ActionEngine(sroot)
        seed(eng.store, battery["meta"]["seeds"])
        grants = issue_grants(eng)
        artifacts = {}
        for s in a.get("setup", []):
            srec = run_action(eng, grants, "main", s["action_type"], s["params"],
                              "setup:" + s["name"])
            assert srec["outcome"]["status"] == "success", f"{a['id']} setup failed: {srec['outcome']}"
            produced = capture_artifacts(eng, srec)
            if produced:
                artifacts[s["name"]] = list(produced.values())[0]
        s0 = state_hash(eng.store)
        rec = run_action(eng, grants, "main", a["action_type"], a["params"],
                         a["verbatim"], confirm=a.get("confirm", False),
                         artifacts=artifacts)
        exp = a["expect"]
        row = {"id": a["id"], "action_type": a["action_type"],
               "status": rec["outcome"]["status"],
               "class": rec["reversibility_class"],
               "expect": exp, "undo_detail": None, "exact_restore": None}
        row["status_ok"] = rec["outcome"]["status"] == exp["status"]
        row["class_ok"] = rec["reversibility_class"] == exp["class"]
        if a.get("post_modify"):
            pm = a["post_modify"]
            open(eng.store.files_path(pm["path"]), "w").write(pm["content"])
        if exp["undo"] == "exact":
            u = eng.undo(rec["action_id"])
            row["undo_detail"] = u
            s2 = state_hash(eng.store)
            row["exact_restore"] = (s0 == s2) and u["ok"]
        elif exp["undo"] == "impossible":
            u = eng.undo(rec["action_id"])
            row["undo_detail"] = u
            row["exact_restore"] = (not u["ok"]) and u["detail"] == "irreversible"
        elif exp["undo"] == "conflict":
            u = eng.undo(rec["action_id"])
            row["undo_detail"] = u
            row["exact_restore"] = (not u["ok"]) and "conflict" in u["detail"]
        elif exp["undo"] == "idempotent":
            u1 = eng.undo(rec["action_id"])
            u2 = eng.undo(rec["action_id"])
            row["undo_detail"] = [u1, u2]
            s2 = state_hash(eng.store)
            row["exact_restore"] = u1["ok"] and u2["ok"] and \
                "already undone" in u2["detail"] and s0 == s2
        results.append(row)
    return results

# ---------------- Track B ----------------

def track_b(defects):
    results = []
    for d in defects["defects"]:
        sroot = os.path.join(OUT, "trackB", d["id"])
        shutil.rmtree(sroot, ignore_errors=True)
        eng = ActionEngine(sroot)
        seed(eng.store, defects["meta"]["seeds"])
        grants = issue_grants(eng)
        artifacts = {}
        for s in d.get("setup", []):
            srec = run_action(eng, grants, "main", s["action_type"], s["params"],
                              "setup:" + s["name"])
            produced = capture_artifacts(eng, srec)
            if produced:
                artifacts[s["name"]] = list(produced.values())[0]
        s0 = state_hash(eng.store)
        if "chain" in d:
            rows = []
            for step in d["chain"]:
                rec = run_action(eng, grants, d["grant"], step["action_type"],
                                 step["params"], d["verbatim"])
                rows.append({"status": rec["outcome"]["status"],
                             "reason": rec["outcome"]["reason"]})
            final = rows[-1]
            caught = final["status"] == "refused" and \
                     final["reason"].startswith(d["chain"][-1]["expect_reason"])
            results.append({"id": d["id"], "rows": rows, "caught": caught,
                            "state_unchanged_by_refused": None})
            # state must reflect ONLY the legal first action
            ref = open(eng.store.files_path("notes/todo.txt")).read()
            results[-1]["state_unchanged_by_refused"] = (ref == "todo v1\n")
            continue
        rec = run_action(eng, grants, d["grant"], d["action_type"], d["params"],
                         d["verbatim"], artifacts=artifacts)
        s1 = state_hash(eng.store)
        caught = rec["outcome"]["status"] == "refused" and \
                 rec["outcome"]["reason"].startswith(d["expect_reason"])
        results.append({"id": d["id"], "status": rec["outcome"]["status"],
                        "reason": rec["outcome"]["reason"],
                        "expected": d["expect_reason"], "caught": caught,
                        "state_unchanged": s0 == s1})
    return results

# ---------------- Track C ----------------

def track_c(battery):
    sroot = os.path.join(OUT, "trackC", "full_run")
    shutil.rmtree(sroot, ignore_errors=True)
    eng = ActionEngine(sroot)
    seed(eng.store, battery["meta"]["seeds"])
    grants = issue_grants(eng)
    records_skipped = []
    for a in battery["actions"]:
        artifacts = {}
        deps_ok = True
        for s in a.get("setup", []):
            srec = run_action(eng, grants, "main", s["action_type"], s["params"],
                              "setup:" + s["name"])
            if srec["outcome"]["status"] != "success":
                deps_ok = False  # e.g. earlier battery action consumed the target
            produced = capture_artifacts(eng, srec)
            if produced:
                artifacts[s["name"]] = list(produced.values())[0]
        try:
            resolve(a["params"], artifacts)
        except KeyError:
            deps_ok = False
        if not deps_ok:
            records_skipped.append(a["id"])
            continue
        run_action(eng, grants, "main", a["action_type"], a["params"],
                   a["verbatim"], confirm=a.get("confirm", False),
                   artifacts=artifacts)
    records = eng.records()
    ren = [r for r in records if not r["intent"]["verbatim"].startswith("setup:")]
    complete = sum(1 for r in ren if not completeness(r))
    ok_chain, _ = chain.verify(eng.store.history_path("action_log"))

    # tamper test 1: modify content of a history entry
    troot = os.path.join(OUT, "trackC", "tampered_content")
    shutil.rmtree(troot, ignore_errors=True)
    shutil.copytree(sroot, troot)
    p = os.path.join(troot, "datasets", "action_log", "history.jsonl")
    entries = [json.loads(l) for l in open(p)]
    entries[2]["record"]["intent"]["verbatim"] = "tampered"
    open(p, "w").write("".join(json.dumps(e) + "\n" for e in entries))
    ok_t1, _ = chain.verify(QafiyaStore(troot).history_path("action_log"))

    # tamper test 2: delete a history entry (history gap)
    troot2 = os.path.join(OUT, "trackC", "tampered_delete")
    shutil.rmtree(troot2, ignore_errors=True)
    shutil.copytree(sroot, troot2)
    p2 = os.path.join(troot2, "datasets", "action_log", "history.jsonl")
    entries2 = [json.loads(l) for l in open(p2)]
    del entries2[3]
    open(p2, "w").write("".join(json.dumps(e) + "\n" for e in entries2))
    ok_t2, _ = chain.verify(QafiyaStore(troot2).history_path("action_log"))

    return {"records_total": len(records), "battery_records": len(ren),
            "skipped_dependency_collisions": records_skipped,
            "re_narratable": complete, "chain_ok": ok_chain,
            "tamper_modify_detected": (not ok_t1),
            "tamper_delete_detected": (not ok_t2)}

# ---------------- spine ----------------

def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    battery = json.load(open(os.path.join(HERE, "frozen", "battery.json")))
    defects = json.load(open(os.path.join(HERE, "frozen", "defects.json")))

    A = track_a(battery)
    B = track_b(defects)
    C = track_c(battery)

    undoable = [r for r in A if r["expect"]["undo"] == "exact"]
    exact = [r for r in undoable if r["exact_restore"]]
    impossible_ok = [r for r in A if r["expect"]["undo"] == "impossible" and r["exact_restore"]]
    impossible_all = [r for r in A if r["expect"]["undo"] == "impossible"]
    special_ok = [r for r in A if r["expect"]["undo"] in ("conflict", "idempotent") and r["exact_restore"]]
    special_all = [r for r in A if r["expect"]["undo"] in ("conflict", "idempotent")]
    status_ok = all(r["status_ok"] and r["class_ok"] for r in A)

    caught = [d for d in B if d["caught"]]
    no_side_effects = all(d.get("state_unchanged", d.get("state_unchanged_by_refused"))
                          for d in B)

    results = {
        "trackA": {
            "battery_size": len(A),
            "all_statuses_and_classes_as_expected": status_ok,
            "undoable_actions": len(undoable),
            "undone_exactly": len(exact),
            "reversibility_rate": round(len(exact) / len(undoable), 4),
            "irreversible_actions_correctly_refusing_undo":
                f"{len(impossible_ok)}/{len(impossible_all)}",
            "limit_probes_passed": f"{len(special_ok)}/{len(special_all)}",
            "detail": A,
        },
        "trackB": {
            "injected_defects": len(B),
            "caught_before_execution": len(caught),
            "containment_rate": round(len(caught) / len(B), 4),
            "no_state_change_on_refusal": no_side_effects,
            "detail": B,
        },
        "trackC": C,
    }
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(results, f, indent=1)

    print("=== HEADLINE NUMBERS (recomputed from raw artifacts) ===")
    print(f"Track A reversibility rate : {len(exact)}/{len(undoable)} "
          f"= {results['trackA']['reversibility_rate']*100:.1f}% "
          f"(status/classes as expected: {status_ok})")
    print(f"Track A irreversible gated : {results['trackA']['irreversible_actions_correctly_refusing_undo']}")
    print(f"Track A limit probes       : {results['trackA']['limit_probes_passed']}")
    print(f"Track B containment        : {len(caught)}/{len(B)} "
          f"= {results['trackB']['containment_rate']*100:.1f}% "
          f"(no side effects: {no_side_effects})")
    print(f"Track C re-narratable      : {C['re_narratable']}/{C['battery_records']}")
    print(f"Track C chain ok           : {C['chain_ok']} | "
          f"tamper modify detected: {C['tamper_modify_detected']} | "
          f"tamper delete detected: {C['tamper_delete_detected']}")

if __name__ == "__main__":
    main()
