"""Adapters: file executor (over Qafiya store), calendar, email.

Each adapter declares per action type:
  - TARGETS(normalized)      -> paths the gate must scope-check
  - PRECONDITIONS            -> checks run at ARMED
  - classify()               -> EXACT | COMPENSABLE | IRREVERSIBLE
  - capture_undo()           -> executable undo recipe, captured BEFORE execution
  - execute()                -> perform; returns (ok, log_steps, data_inputs)
  - undo(recipe)             -> apply recipe; returns (ok, detail)
"""
import os, shutil, uuid, json
from ..model import file_hash
from ..qafiya_shim import now_iso

# ---------------- File executor ----------------

FILE_ACTIONS = {"file.create", "file.move", "file.rename", "file.edit",
                "file.delete", "dir.create", "dir.delete", "trash.purge"}

def file_targets(n):
    p = n["params"]
    t = []
    for k in ("src", "dst", "path"):
        if p.get(k):
            t.append(p[k])
    return t

def file_classify(n):
    if n["action_type"] in ("trash.purge",):
        return "IRREVERSIBLE"
    if n["action_type"] in ("file.delete", "dir.delete"):
        return "COMPENSABLE"      # via managed trash restore
    return "EXACT"

def file_preconditions(n, store):
    p = n["params"]
    checks = []
    def need_exists(path, name):
        ap = store.files_path(path)
        checks.append({"check": name, "params": {"path": path},
                       "result": "pass" if os.path.exists(ap) else "fail"})
    if n["action_type"] in ("file.move", "file.rename", "file.edit", "file.delete",
                            "dir.delete"):
        need_exists(p.get("src") or p.get("path"), "target_exists")
    if n["action_type"] in ("file.move", "file.rename"):
        dst = store.files_path(p["dst"])
        checks.append({"check": "dst_free", "params": {"dst": p["dst"]},
                       "result": "pass" if not os.path.exists(dst) else "fail"})
    if n["action_type"] == "trash.purge":
        tp = store.trash_path(p["trash_id"])
        checks.append({"check": "trash_entry_exists", "params": {"trash_id": p["trash_id"]},
                       "result": "pass" if os.path.exists(tp) else "fail"})
    return checks

def file_capture_undo(n, store):
    """Runs at ARMED, before execution (spec I2)."""
    p = n["params"]
    at = n["action_type"]
    if at == "file.create":
        return {"ops": [{"op": "remove", "path": p["path"]}]}
    if at == "dir.create":
        return {"ops": [{"op": "remove_dir", "path": p["path"]}]}
    if at in ("file.move", "file.rename"):
        return {"ops": [{"op": "move", "src": p["dst"], "dst": p["src"]}]}
    if at == "file.edit":
        ap = store.files_path(p["path"])
        snap = os.path.join(store.root, ".snap", str(uuid.uuid4()))
        os.makedirs(os.path.dirname(snap), exist_ok=True)
        shutil.copy2(ap, snap)
        return {"ops": [{"op": "restore_snapshot", "path": p["path"], "snapshot": snap}]}
    if at in ("file.delete", "dir.delete"):
        return None  # captured at execution: trash_id known only after move
    if at == "trash.purge":
        return None  # IRREVERSIBLE: no recipe exists; classification is the receipt
    return None

def file_execute(n, store):
    p = n["params"]
    at = n["action_type"]
    log, inputs = [], []
    def step(name, result="ok"):
        log.append({"ts": now_iso(), "step": name, "result": result})
    try:
        if at == "file.create":
            ap = store.files_path(p["path"])
            os.makedirs(os.path.dirname(ap), exist_ok=True)
            with open(ap, "w") as f:
                f.write(p.get("content", ""))
            step(f"create {p['path']}")
        elif at == "dir.create":
            os.makedirs(store.files_path(p["path"]), exist_ok=False)
            step(f"mkdir {p['path']}")
        elif at in ("file.move", "file.rename"):
            src, dst = store.files_path(p["src"]), store.files_path(p["dst"])
            inputs.append({"qafiya_ref": p["src"], "role": "write",
                           "pre_hash": file_hash(src), "post_hash": None})
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            inputs[-1]["post_hash"] = file_hash(dst)
            step(f"move {p['src']} -> {p['dst']}")
        elif at == "file.edit":
            ap = store.files_path(p["path"])
            inputs.append({"qafiya_ref": p["path"], "role": "write",
                           "pre_hash": file_hash(ap), "post_hash": None})
            with open(ap, "w") as f:
                f.write(p.get("content", ""))
            inputs[-1]["post_hash"] = file_hash(ap)
            step(f"edit {p['path']}")
        elif at in ("file.delete", "dir.delete"):
            src = store.files_path(p.get("src") or p.get("path"))
            tid = str(uuid.uuid4())
            tp = store.trash_path(tid)
            inputs.append({"qafiya_ref": p.get("src") or p.get("path"), "role": "write",
                           "pre_hash": file_hash(src), "post_hash": None})
            shutil.move(src, tp)
            # trash entry carries provenance to the delete action (owner decision 2)
            with open(tp + ".prov.json", "w") as f:
                json.dump({"trash_id": tid, "original_path": p.get("src") or p.get("path"),
                           "deleted_at": now_iso()}, f)
            step(f"delete -> trash/{tid}")
            return True, log, inputs, {"ops": [{"op": "restore_trash",
                                                "trash_id": tid,
                                                "dst": p.get("src") or p.get("path")}]}
        elif at == "trash.purge":
            tp = store.trash_path(p["trash_id"])
            if os.path.isdir(tp):
                shutil.rmtree(tp)
            else:
                os.remove(tp)
            prov = tp + ".prov.json"
            if os.path.exists(prov):
                os.remove(prov)
            step(f"purge trash/{p['trash_id']} (IRREVERSIBLE)")
        else:
            return False, log + [{"ts": now_iso(), "step": at, "result": "unknown_action"}], inputs, None
        return True, log, inputs, None
    except Exception as e:
        step(f"{at} failed: {e}", "error")
        return False, log, inputs, None

def _prune_empty_parents(store, path):
    """Remove empty parent dirs left behind, up to (not incl.) the files root."""
    root = store.files_path()
    d = path if os.path.isdir(path) else os.path.dirname(path)
    while d and d != root and d.startswith(root) and os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
        d = os.path.dirname(d)

def file_undo(recipe, store):
    for op in recipe["ops"]:
        if op["op"] == "remove":
            ap = store.files_path(op["path"])
            if os.path.exists(ap):
                os.remove(ap)
            _prune_empty_parents(store, ap)
        elif op["op"] == "remove_dir":
            shutil.rmtree(store.files_path(op["path"]), ignore_errors=True)
            _prune_empty_parents(store, store.files_path(op["path"]))
        elif op["op"] == "move":
            src, dst = store.files_path(op["src"]), store.files_path(op["dst"])
            if not os.path.exists(src):
                return False, f"undo source missing: {op['src']}"
            shutil.move(src, dst)
            _prune_empty_parents(store, src)
        elif op["op"] == "restore_snapshot":
            shutil.copy2(op["snapshot"], store.files_path(op["path"]))
        elif op["op"] == "restore_trash":
            tp = store.trash_path(op["trash_id"])
            dst = store.files_path(op["dst"])
            if not os.path.exists(tp):
                return False, f"trash entry missing: {op['trash_id']}"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(tp, dst)
            prov = tp + ".prov.json"
            if os.path.exists(prov):
                os.remove(prov)
        else:
            return False, f"unknown undo op: {op['op']}"
    return True, "ok"

# ---------------- Calendar adapter (in-memory events DB in store) ----------------

def _cal_db(store):
    return os.path.join(store.root, "calendar.json")

def _cal_load(store):
    if os.path.exists(_cal_db(store)):
        return json.load(open(_cal_db(store)))
    return {}

def _cal_save(store, db):
    json.dump(db, open(_cal_db(store), "w"), indent=1)

def calendar_targets(n):
    return ["calendar"]

def calendar_classify(n):
    return {"calendar.create": "EXACT", "calendar.delete": "COMPENSABLE",
            "calendar.update": "COMPENSABLE"}[n["action_type"]]

def calendar_preconditions(n, store):
    db = _cal_load(store)
    p = n["params"]
    if n["action_type"] in ("calendar.delete", "calendar.update"):
        ok = p["event_id"] in db
        return [{"check": "event_exists", "params": {"event_id": p["event_id"]},
                 "result": "pass" if ok else "fail"}]
    return []

def calendar_capture_undo(n, store):
    p = n["params"]
    at = n["action_type"]
    if at == "calendar.create":
        return {"ops": [{"op": "cal_delete", "event_id": "__FROM_EXEC__"}]}
    if at == "calendar.delete":
        db = _cal_load(store)
        ev = db.get(p["event_id"])
        return {"ops": [{"op": "cal_restore", "event": ev}]} if ev else None
    if at == "calendar.update":
        db = _cal_load(store)
        ev = db.get(p["event_id"])
        return {"ops": [{"op": "cal_restore", "event": dict(ev)}]} if ev else None
    return None

def calendar_execute(n, store):
    db = _cal_load(store)
    p = n["params"]
    at = n["action_type"]
    log = [{"ts": now_iso(), "step": at, "result": "ok"}]
    recipe = None
    if at == "calendar.create":
        eid = str(uuid.uuid4())
        db[eid] = {"event_id": eid, "title": p["title"], "start": p["start"],
                   "end": p["end"], "created_at": now_iso()}
        recipe = {"ops": [{"op": "cal_delete", "event_id": eid}]}
    elif at == "calendar.delete":
        del db[p["event_id"]]
    elif at == "calendar.update":
        db[p["event_id"]].update(p.get("fields", {}))
    else:
        return False, [{"ts": now_iso(), "step": at, "result": "unknown_action"}], [], None
    _cal_save(store, db)
    return True, log, [{"qafiya_ref": "calendar", "role": "write",
                        "pre_hash": None, "post_hash": None}], recipe

def calendar_undo(recipe, store):
    db = _cal_load(store)
    for op in recipe["ops"]:
        if op["op"] == "cal_delete":
            db.pop(op["event_id"], None)
        elif op["op"] == "cal_restore":
            db[op["event"]["event_id"]] = op["event"]
    _cal_save(store, db)
    return True, "ok"

# ---------------- Email adapter (external sending system, dry-run default) ----------------
# Owner decision 1: sending is done through an existing email system, not built here.
# The adapter shells out to a configured provider command; DRY-RUN is the default so
# experiments never send real mail. email.send is IRREVERSIBLE by construction.

def email_targets(n):
    return ["email"]

def email_classify(n):
    return {"email.draft_create": "EXACT", "email.draft_edit": "EXACT",
            "email.draft_discard": "EXACT", "email.send": "IRREVERSIBLE"}[n["action_type"]]

def _mail_db(store):
    return os.path.join(store.root, "mail.json")

def _mail_load(store):
    if os.path.exists(_mail_db(store)):
        return json.load(open(_mail_db(store)))
    return {"drafts": {}, "sent": []}

def _mail_save(store, db):
    json.dump(db, open(_mail_db(store), "w"), indent=1)

def email_preconditions(n, store):
    db = _mail_load(store)
    p = n["params"]
    if n["action_type"] in ("email.draft_edit", "email.draft_discard", "email.send"):
        ok = p["draft_id"] in db["drafts"]
        return [{"check": "draft_exists", "params": {"draft_id": p["draft_id"]},
                 "result": "pass" if ok else "fail"}]
    if n["action_type"] == "email.draft_create":
        to = p.get("to", "")
        ok = "@" in to
        return [{"check": "recipient_wellformed", "params": {"to": to},
                 "result": "pass" if ok else "fail"}]
    return []

def email_capture_undo(n, store):
    p = n["params"]
    at = n["action_type"]
    if at == "email.draft_create":
        return {"ops": [{"op": "draft_remove", "draft_id": "__FROM_EXEC__"}]}
    if at == "email.draft_edit":
        db = _mail_load(store)
        d = db["drafts"].get(p["draft_id"])
        return {"ops": [{"op": "draft_restore", "draft": dict(d)}]} if d else None
    if at == "email.draft_discard":
        db = _mail_load(store)
        d = db["drafts"].get(p["draft_id"])
        return {"ops": [{"op": "draft_restore", "draft": dict(d)}]} if d else None
    if at == "email.send":
        return None  # IRREVERSIBLE: physically cannot unsend (spec §6)
    return None

def email_execute(n, store, provider=None):
    db = _mail_load(store)
    p = n["params"]
    at = n["action_type"]
    log = [{"ts": now_iso(), "step": at, "result": "ok"}]
    recipe = None
    inputs = []
    if at == "email.draft_create":
        did = str(uuid.uuid4())
        db["drafts"][did] = {"draft_id": did, "to": p["to"], "subject": p["subject"],
                             "body": p["body"], "created_at": now_iso()}
        recipe = {"ops": [{"op": "draft_remove", "draft_id": did}]}
    elif at == "email.draft_edit":
        db["drafts"][p["draft_id"]].update(p.get("fields", {}))
    elif at == "email.draft_discard":
        del db["drafts"][p["draft_id"]]
    elif at == "email.send":
        draft = db["drafts"][p["draft_id"]]
        # Provider handoff: an external sending system owns actual delivery.
        msg_id = (provider or (lambda d: "DRYRUN-" + str(uuid.uuid4())))(draft)
        db["sent"].append({"draft": draft, "provider_message_id": msg_id,
                           "sent_at": now_iso()})
        del db["drafts"][p["draft_id"]]
        inputs.append({"qafiya_ref": "provider:" + msg_id, "role": "write",
                       "pre_hash": None, "post_hash": None})
        log.append({"ts": now_iso(), "step": f"provider handoff id={msg_id}",
                    "result": "ok"})
    else:
        return False, [{"ts": now_iso(), "step": at, "result": "unknown_action"}], [], None
    _mail_save(store, db)
    return True, log, inputs, recipe

def email_undo(recipe, store):
    db = _mail_load(store)
    for op in recipe["ops"]:
        if op["op"] == "draft_remove":
            db["drafts"].pop(op["draft_id"], None)
        elif op["op"] == "draft_restore":
            db["drafts"][op["draft"]["draft_id"]] = op["draft"]
    _mail_save(store, db)
    return True, "ok"

ADAPTERS = {
    "file":  {"actions": FILE_ACTIONS, "targets": file_targets,
              "classify": file_classify, "preconditions": file_preconditions,
              "capture_undo": file_capture_undo, "execute": file_execute,
              "undo": file_undo},
    "calendar": {"actions": {"calendar.create", "calendar.delete", "calendar.update"},
              "targets": calendar_targets, "classify": calendar_classify,
              "preconditions": calendar_preconditions,
              "capture_undo": calendar_capture_undo, "execute": calendar_execute,
              "undo": calendar_undo},
    "email": {"actions": {"email.draft_create", "email.draft_edit",
                          "email.draft_discard", "email.send"},
              "targets": email_targets, "classify": email_classify,
              "preconditions": email_preconditions,
              "capture_undo": email_capture_undo, "execute": email_execute,
              "undo": email_undo},
}

def adapter_for(action_type):
    prefix = action_type.split(".")[0]
    if prefix in ("dir", "trash"):
        prefix = "file"
    return ADAPTERS.get(prefix)
