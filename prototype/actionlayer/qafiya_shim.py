"""Qafiya-conformant local store (spec v1.1 + §8 layout + v1.3 chained history).

Monitor integration guide items 1-2: storage conforms to Qafiya §8
(schema.json + data.jsonl + history.jsonl [chained via qafiya_core_chain] +
bindings.jsonl + SUPERSEDED.json), and the tamper-evident chain is inherited
from the Qafiya substrate (v1.3) rather than implemented locally.

Layout under the store root:
    datasets/action_log/   schema.json, data.jsonl (current records),
                           history.jsonl (chained transition log), bindings.jsonl,
                           SUPERSEDED.json
    datasets/grants/       same layout (permission_grant records)
    files/                 governed file area (adapter-managed content)
    trash/                 managed trash (adapter-managed)
    .snap/                 undo snapshots (adapter-managed)

The real Qafiya engine lives in layer 01 (github.com/DeeWaanAI/qafiya); this
shim codes against the frozen spec concepts so porting is wiring, not redesign.
"""
import json, os, time, secrets
from datetime import datetime, timezone
from pathlib import Path
from . import qafiya_core_chain as chain

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix):
    """Prefixed sortable id (OS identity rule, INTERFACES.md)."""
    return f"{prefix}_{time.time_ns():016x}{secrets.token_hex(4)}"

def _write_json(p, obj):
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)

class QafiyaStore:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)
        for sub in ("trash", "files", ".snap"):
            os.makedirs(os.path.join(self.root, sub), exist_ok=True)
        self._init_dataset("action_log", "action_record")
        self._init_dataset("grants", "permission_grant")

    def _dataset_dir(self, dataset):
        return os.path.join(self.root, "datasets", dataset)

    def _init_dataset(self, dataset, record_type):
        d = self._dataset_dir(dataset)
        os.makedirs(d, exist_ok=True)
        for f in ("data.jsonl", "history.jsonl", "bindings.jsonl"):
            p = os.path.join(d, f)
            if not os.path.exists(p):
                open(p, "w").close()
        sup = os.path.join(d, "SUPERSEDED.json")
        if not os.path.exists(sup):
            _write_json(sup, {"superseded": []})
        sch = os.path.join(d, "schema.json")
        if not os.path.exists(sch):
            _write_json(sch, {
                "dataset": dataset, "record_type": record_type,
                "spec": "Qafiya v1.1 §8 layout; chained history v1.3",
                "fields": "see 03-action-layer/spec.md §3 (action_record) / §4 (permission_grant)"})

    def _data_path(self, dataset):
        return os.path.join(self._dataset_dir(dataset), "data.jsonl")

    def history_path(self, dataset):
        return Path(self._dataset_dir(dataset)) / "history.jsonl"

    def append(self, dataset, record, prefix="r"):
        """New record: append to data.jsonl and a chained 'create' history entry."""
        record = dict(record)
        record.setdefault("_id", new_id(prefix))
        record.setdefault("_ts", now_iso())
        with open(self._data_path(dataset), "a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        chain.append(self.history_path(dataset),
                     {"op": "create", "record_id": record["_id"], "record": record})
        return record

    def update(self, dataset, records, changed_id):
        """Rewrite materialized current state; log a chained 'update' entry."""
        self.rewrite_all(dataset, records)
        cur = next(r for r in records if r.get("_id") == changed_id or
                   r.get("action_id") == changed_id)
        chain.append(self.history_path(dataset),
                     {"op": "update", "record_id": changed_id, "record": cur})

    def read_all(self, dataset):
        p = self._data_path(dataset)
        if not os.path.exists(p):
            return []
        with open(p) as f:
            return [json.loads(l) for l in f if l.strip()]

    def rewrite_all(self, dataset, records):
        with open(self._data_path(dataset), "w") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True) + "\n")

    # --- governed file area ---
    def files_path(self, rel=""):
        return os.path.join(self.root, "files", rel)

    def trash_path(self, rel=""):
        return os.path.join(self.root, "trash", rel)
