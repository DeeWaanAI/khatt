"""Action record content model (spec §3).

The tamper-evident chain is NOT implemented here: it is inherited from the
Qafiya substrate (v1.3, qafiya_core_chain) and lives on each dataset's
history.jsonl. This module defines record content, ids, and content hashing
of governed files.
"""
import hashlib, json, os
from .qafiya_shim import now_iso, new_id

CONTENT_FIELDS = [
    "action_id", "created_at", "intent", "actor", "authority",
    "permission_scope", "preconditions", "reversibility_class", "undo_recipe",
    "data_inputs", "execution_log", "outcome", "confirmations",
]

def content_hash(record):
    return hashlib.sha256(json.dumps(
        {k: record.get(k) for k in CONTENT_FIELDS},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def make_record(*, intent_verbatim, normalized, actor, authority, permission_scope,
                parser="scripted", parser_version="0.1"):
    return {
        "action_id": new_id("a"),   # prefixed sortable id (OS identity rule)
        "created_at": now_iso(),
        "intent": {"verbatim": intent_verbatim, "normalized": normalized,
                   "parser": parser, "parser_version": parser_version},
        "actor": actor,
        "authority": authority,
        "permission_scope": permission_scope,
        "preconditions": [],
        "reversibility_class": None,   # set by adapter at ARMED
        "undo_recipe": None,           # captured before execution (spec I2)
        "data_inputs": [],
        "execution_log": [],
        "outcome": {"status": "proposed", "reason": ""},
        "undo_status": "not_requested",
        "confirmations": [],
    }

def file_hash(path):
    if not os.path.exists(path):
        return None
    if os.path.isdir(path):
        h = hashlib.sha256()
        for root, dirs, files in sorted(os.walk(path)):
            for d in sorted(dirs):
                h.update(b"dir:" + os.path.join(root, d).encode())
            for fn in sorted(files):
                fp = os.path.join(root, fn)
                h.update(b"file:" + fp.encode() + b":" + (file_hash(fp) or "").encode())
        return h.hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
