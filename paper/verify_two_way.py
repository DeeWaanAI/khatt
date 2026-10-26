#!/usr/bin/env python3
"""verify_two_way.py — two-way claim-map verifier (datapoints-v2 schema).

Per entry in paper/claim_map/datapoints.json:
  (a) the frozen artifact's value at `path` equals `expect`
      (paths: dotted key path | '@file_len' | '@len:<keypath>' |
       '@distinct_action_types' for the battery fixture)
  (b) the entry's `marker` text appears verbatim in paper/paper.tex,
      near `paper_line` (±3 lines) if given, else anywhere in the draft.
Exit 0 only when every entry passes BOTH directions.
"""
import json, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, "paper", "claim_map", "datapoints.json")
DRAFT = os.path.join(ROOT, "paper", "paper.tex")

entries = json.load(open(MAP))["datapoints"]
draft = open(DRAFT).read()
draft_lines = draft.splitlines()
fails = []

def get_by_path(obj, dotted):
    for seg in dotted.split("."):
        obj = obj[int(seg)] if isinstance(obj, list) else obj[seg]
    return obj

for e in entries:
    src = os.path.join(ROOT, e["source"])
    # (a) artifact value == expect
    if not os.path.exists(src):
        fails.append((e["id"], "missing source " + e["source"]))
    else:
        data = json.load(open(src))
        path = e["path"]
        try:
            if path == "@file_len":
                val = len(data)
            elif path.startswith("@len:"):
                val = len(get_by_path(data, path[5:]))
            elif path == "@distinct_action_types":
                val = len({a["action_type"] for a in data["actions"]})
            else:
                val = get_by_path(data, path)
            exp = e["expect"]
            ok = (abs(float(val) - float(exp)) < 1e-9) if isinstance(exp, (int, float)) \
                 else (str(val) == str(exp))
            if not ok:
                fails.append((e["id"], f"artifact value {val!r} != expect {exp!r}"))
        except Exception as ex:
            fails.append((e["id"], f"path error: {ex}"))
    # (b) marker appears in the draft
    marker = e["marker"]
    if marker not in draft:
        fails.append((e["id"], "marker not in draft: " + marker[:60]))
    elif e.get("paper_line"):
        lo, hi = e["paper_line"] - 3, e["paper_line"] + 3
        window = "\n".join(draft_lines[max(0, lo - 1):hi])
        if marker not in window:
            fails.append((e["id"], f"marker moved from line {e['paper_line']}"))

if fails:
    for f in fails:
        print("FAIL", *f)
    sys.exit(1)
print(f"OK: {len(entries)} datapoints verified both directions "
      f"(frozen artifact value == expect AND marker present in draft)")
