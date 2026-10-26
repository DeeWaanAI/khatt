"""The action engine: lifecycle state machine (spec §2).

PROPOSED -> GATED -> ARMED -> EXECUTING -> DONE/FAILED -> UNDOING -> UNDONE
Invariants I1-I4 enforced here. The record is written at every transition;
an action whose record cannot be written does not run.
"""
from .qafiya_shim import QafiyaStore, now_iso
from .model import make_record, file_hash
from .gate import check_grant, needs_confirmation, has_confirmation
from .adapters import adapter_for
from . import renderer

class ActionEngine:
    def __init__(self, store_root):
        self.store = QafiyaStore(store_root)

    # -- grants --
    def issue_grant(self, grant):
        return self.store.append("grants", grant, prefix="g")

    def _latest_grants(self):
        return self.store.read_all("grants")

    def find_grant(self, grant_id=None, user_id=None):
        gs = self._latest_grants()
        if grant_id:
            for g in gs:
                if g.get("grant_id") == grant_id or g.get("_id") == grant_id:
                    return g
        if user_id:
            for g in reversed(gs):
                if g.get("user_id") == user_id:
                    return g
        return None

    # -- record persistence (every transition) --
    # Tamper-evidence is inherited from the substrate: every commit appends a
    # chained entry to datasets/action_log/history.jsonl (Qafiya v1.3).
    def _commit(self, record):
        records = self.store.read_all("action_log")
        existing = [r for r in records if r.get("action_id") == record["action_id"]]
        record["execution_log"] = record.get("execution_log", [])
        if not existing:
            self.store.append("action_log", record, prefix="a")
        else:
            # update bookkeeping fields; content fields frozen at first commit
            for r in records:
                if r.get("action_id") == record["action_id"]:
                    r["execution_log"] = record["execution_log"]
                    r["outcome"] = record["outcome"]
                    r["undo_status"] = record["undo_status"]
                    r["undo_recipe"] = record["undo_recipe"]
                    r["data_inputs"] = record["data_inputs"]
                    r["preconditions"] = record["preconditions"]
                    r["reversibility_class"] = record["reversibility_class"]
                    r["confirmations"] = record.get("confirmations", [])
            self.store.update("action_log", records, record["action_id"])
        return record

    def _log(self, record, step, result="ok"):
        record["execution_log"].append({"ts": now_iso(), "step": step, "result": result})

    # -- main entry --
    def act(self, *, intent_verbatim, normalized, actor, user_id,
            grant_id=None, confirm_irreversible=False):
        adapter = adapter_for(normalized["action_type"])
        grant = self.find_grant(grant_id=grant_id, user_id=user_id)
        record = make_record(
            intent_verbatim=intent_verbatim, normalized=normalized,
            actor=actor, authority={"user_id": user_id,
                                    "grant_id": (grant or {}).get("_id")},
            permission_scope=grant or {},
        )
        if adapter is None:
            record["outcome"] = {"status": "refused", "reason": "unknown_action_type"}
            self._commit(record)
            return record

        # GATED (invariant I1)
        targets = adapter["targets"](normalized)
        ok, reason = check_grant(grant, normalized, targets,
                                 self.store.files_path())
        self._log(record, f"gate: {reason}", "ok" if ok else "refused")
        if not ok:
            record["outcome"] = {"status": "refused", "reason": reason}
            self._commit(record)
            return record

        # ARMED: preconditions, undo recipe, classification (invariant I2)
        pre = adapter["preconditions"](normalized, self.store)
        record["preconditions"] = pre
        if any(c["result"] == "fail" for c in pre):
            failed = [c["check"] for c in pre if c["result"] == "fail"]
            self._log(record, f"preconditions failed: {failed}", "refused")
            record["outcome"] = {"status": "refused",
                                 "reason": "preconditions_failed:" + ",".join(failed)}
            self._commit(record)
            return record
        record["reversibility_class"] = adapter["classify"](normalized)
        record["undo_recipe"] = adapter["capture_undo"](normalized, self.store)
        self._log(record, f"armed: class={record['reversibility_class']}")
        self._commit(record)  # record exists before any state change

        # confirmation gate for IRREVERSIBLE / listed actions
        if record["reversibility_class"] == "IRREVERSIBLE" or \
           needs_confirmation(grant, record["reversibility_class"],
                              normalized["action_type"]):
            if confirm_irreversible:
                renderer.render_confirmation(record)  # Layer-2 display path (stub)
                record["confirmations"].append(
                    {"kind": "irreversible_ack", "ts": now_iso(), "user_id": user_id})
                self._log(record, "user confirmed irreversible action")
            else:
                self._log(record, "confirmation required, not given", "refused")
                record["outcome"] = {"status": "refused",
                                     "reason": "confirmation_required"}
                self._commit(record)
                return record

        # EXECUTING
        res = adapter["execute"](normalized, self.store)
        ok, steps, inputs, late_recipe = res
        record["execution_log"].extend(steps)
        record["data_inputs"] = inputs
        if late_recipe:
            record["undo_recipe"] = late_recipe
        record["outcome"] = {"status": "success" if ok else "failed",
                             "reason": "" if ok else "executor_error"}
        if ok and record["reversibility_class"] != "IRREVERSIBLE":
            record["undo_status"] = "available"
        elif ok:
            record["undo_status"] = "impossible"
        self._commit(record)
        return record

    # -- undo --
    def undo(self, action_id):
        records = self.store.read_all("action_log")
        rec = next((r for r in records if r.get("action_id") == action_id), None)
        if rec is None:
            return {"ok": False, "detail": "unknown action_id"}
        if rec["outcome"]["status"] != "success":
            return {"ok": False, "detail": "action did not succeed"}
        if rec["reversibility_class"] == "IRREVERSIBLE" or not rec.get("undo_recipe"):
            rec["undo_status"] = "impossible"
            self.store.update("action_log", records, action_id)
            return {"ok": False, "detail": "irreversible"}
        if rec.get("undo_status") == "executed":
            return {"ok": True, "detail": "already undone (no-op, record kept)"}
        # conflict detection: post-state must be untouched since execution
        for di in rec.get("data_inputs", []):
            if di.get("post_hash"):
                cur = file_hash(self.store.files_path(di["qafiya_ref"]))
                # for moves, current lives at dst; check via recipe target if needed
                if cur is not None and cur != di["post_hash"]:
                    rec["undo_status"] = "available"
                    return {"ok": False,
                            "detail": f"conflict: {di['qafiya_ref']} modified after action"}
        adapter = adapter_for(rec["intent"]["normalized"]["action_type"])
        rec["undo_status"] = "executed"
        ok, detail = adapter["undo"](rec["undo_recipe"], self.store)
        if not ok:
            rec["undo_status"] = "available"
        self.store.update("action_log", records, action_id)
        return {"ok": ok, "detail": detail}

    # -- queries --
    def records(self):
        return self.store.read_all("action_log")
