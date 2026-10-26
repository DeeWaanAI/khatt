#!/usr/bin/env python3
"""audit/verify_chain.py — thin wrapper over the Qafiya v1.3 substrate chain
(monitor integration guide §1). Recomputes datasets/action_log/history.jsonl.
Usage: python audit/verify_chain.py <store_root>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "prototype"))
from actionlayer.qafiya_shim import QafiyaStore
from actionlayer import qafiya_core_chain as chain

def main(root):
    store = QafiyaStore(root)
    ok, detail = chain.verify(store.history_path("action_log"))
    print(f"chain_ok={ok} ({detail})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
