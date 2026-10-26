#!/usr/bin/env python3
import json, os, re
from collections import defaultdict
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
rows = json.load(open(os.path.join(RAW, "combined.json")))

# keyword boosts for topical relevance to a PERMISSIONED, REVERSIBLE,
# PROVENANCE-CARRYING ACTION LAYER for LLM operating systems
BOOST = {
 "tool_use": ["tool use","tool learning","function calling","api call","tool-augmented","toolbench","gorilla","tool","agent"],
 "agent_os": ["operating system","agent","aios","llm os","framework","orchestrat","model context protocol","personal agent"],
 "permissions": ["permission","sandbox","capabilit","least privilege","prompt injection","consent","authoriz","access control","privilege","defen"],
 "reversibility": ["undo","reversib","compensat","saga","transaction","rollback","recover","irreversib"],
 "audit": ["audit","accountab","log","traceab","provenance","record","transparen","attribut"],
 "human_loop": ["human-in-the-loop","human oversight","approval","confirm","delegat","autonomy","control","intervention"],
 "agent_bench": ["osworld","webarena","workarena","tau-bench","tau2","swe-bench","benchmark","environment","computer use"],
}

def score(r):
    txt = ((r.get("title") or "") + " " + (r.get("abstract") or "")).lower()
    s = 0
    for k in BOOST.get(r["theme"], []):
        if k.lower() in txt: s += 2
    if r.get("cited_by"): s += min(r["cited_by"], 200)/20.0
    return s

by_theme = defaultdict(list)
for r in rows:
    r["_score"] = score(r)
    by_theme[r["theme"]].append(r)

themes = ["tool_use","agent_os","permissions","reversibility","audit","human_loop","agent_bench"]
passed = 0
for theme in themes:
    lst = sorted(by_theme.get(theme, []), key=lambda x: x["_score"], reverse=True)
    npass = sum(1 for r in lst if r["_score"] >= 4)
    passed += npass
    print(f"\n===== {theme}  (candidates={len(lst)}, passed={npass}) =====")
    for r in lst[:20]:
        if r["_score"] < 4: break
        ident = r.get("doi") or ("arXiv:"+r["arxiv"] if r.get("arxiv") else r.get("oa_id",""))
        print(f"[{r['_score']:.1f}] {r.get('year')} | {r.get('venue') or '?'} | {r.get('title')} | {ident} | cites={r.get('cited_by')}")
print(f"\nTOTAL passed screen (score>=4): {passed}")
