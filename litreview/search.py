#!/usr/bin/env python3
"""Systematic multi-database search for the 'permissioned, provenance-carrying,
reversible action layer for LLM operating systems' review.
Same pipeline style as the Qafiya data-layer review: stdlib only (urllib),
OpenAlex (primary, has DOIs) + arXiv (recent preprints).
Writes raw JSON per source and a combined, deduplicated candidate list."""
import json, time, urllib.parse, urllib.request, re, sys, os

OUT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "lit-review-action-layer/1.0 (research; mailto:youssef.hariri@example.org)"}
YEAR_FROM, YEAR_TO = 2018, 2026

def get(url, tries=4, sleep=1.5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            code = getattr(e, "code", None)
            if code == 429:
                time.sleep(sleep * (i + 2)); continue
            time.sleep(sleep)
    return None

# ---- Concept queries (action-layer focused) ----
# Themes:
#  tool_use      — LLM tool use / function calling / tool benchmarks
#  agent_os      — LLM agent operating systems & agent frameworks
#  permissions   — permissioning, sandboxing, capability security, consent for agents
#  reversibility — undo, compensation, transactional/saga recovery for actions
#  audit         — action logging, auditability, accountability of agents
#  human_loop    — human-in-the-loop approval / confirmation for agent actions
OPENALEX_QUERIES = {
 "tool_use": ['"tool use" "large language model"', '"function calling" "large language model"',
              'tool learning language model', '"tool-augmented" language model',
              '"ToolBench"', '"API" "language model" agent tool'],
 "agent_os": ['"large language model" agent "operating system"', '"LLM agent" framework',
              '"AIOS" agent operating system', 'autonomous agent "large language model" survey',
              '"Model Context Protocol"'],
 "permissions": ['"sandbox" agent "language model"', 'capability-based security agent',
                 'permission "language model" agent', '"least privilege" agent tool',
                 '"prompt injection" defense tool agent'],
 "reversibility": ['undo actions "software agent"', 'compensating transaction saga',
                   '"reversibility" software system actions', '"undo" "human-computer interaction"',
                   'reversible computing system recovery'],
 "audit": ['audit log "software agent"', 'accountability autonomous agents',
           '"action logging" agent', 'provenance agent actions',
           'auditability "artificial intelligence" system'],
 "human_loop": ['"human-in-the-loop" agent approval', '"human oversight" autonomous system',
                'confirmation dialog agent action', '"human-AI" delegation authority',
                'agent autonomy control human'],
}

def openalex_search():
    all_rows = {}
    for theme, queries in OPENALEX_QUERIES.items():
        for q in queries:
            params = {
                "filter": f"title_and_abstract.search:{q},from_publication_date:{YEAR_FROM}-01-01,to_publication_date:{YEAR_TO}-12-31",
                "per-page": "25", "sort": "relevance_score:desc",
            }
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
            txt = get(url)
            if not txt:
                print(f"[openalex] FAIL {theme} :: {q}", file=sys.stderr); continue
            try:
                data = json.loads(txt)
            except Exception:
                print(f"[openalex] JSONERR {theme} :: {q}", file=sys.stderr); continue
            for w in data.get("results", []):
                doi = (w.get("doi") or "").replace("https://doi.org/", "")
                key = doi or w.get("id")
                inv = w.get("abstract_inverted_index") or {}
                pos = {}
                for word, idxs in inv.items():
                    for i in idxs: pos[i] = word
                abstract = " ".join(pos[i] for i in sorted(pos))[:600]
                all_rows[key] = {
                    "source": "openalex", "theme": theme, "query": q,
                    "title": w.get("title"), "year": w.get("publication_year"),
                    "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                    "doi": doi, "arxiv": None,
                    "cited_by": w.get("cited_by_count"),
                    "abstract": abstract,
                    "oa_id": w.get("id"),
                }
            time.sleep(0.4)
    return all_rows

def arxiv_search():
    rows = {}
    arq = {
      "tool_use": 'abs:"tool use" AND abs:"large language model" OR abs:"function calling" OR abs:"ToolBench" OR abs:"Gorilla" AND abs:"API"',
      "agent_os": 'abs:"LLM agent operating system" OR abs:"AIOS" OR abs:"agent operating system" OR abs:"Model Context Protocol"',
      "permissions": 'abs:"prompt injection" AND abs:"agent" OR abs:"sandbox" AND abs:"LLM agent" OR abs:"permission" AND abs:"LLM agent"',
      "reversibility": 'abs:"undo" AND abs:"agent" AND abs:"action" OR abs:"compensating transaction" OR abs:"saga" AND abs:"microservice"',
      "audit": 'abs:"audit" AND abs:"LLM agent" OR abs:"accountability" AND abs:"autonomous agent" OR abs:"action provenance"',
      "human_loop": 'abs:"human-in-the-loop" AND abs:"agent" AND abs:"tool" OR abs:"human oversight" AND abs:"AI agent"',
      "agent_bench": 'abs:"OSWorld" OR abs:"WebArena" OR abs:"tau-bench" OR abs:"SWE-bench" OR abs:"WorkArena"',
    }
    for theme, q in arq.items():
        url = "http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&start=0&max_results=30"
        txt = get(url)
        if not txt:
            print(f"[arxiv] FAIL {theme}", file=sys.stderr); continue
        entries = re.findall(r"<entry>(.*?)</entry>", txt, re.S)
        for e in entries:
            def tag(t):
                m = re.search(rf"<{t}>(.*?)</{t}>", e, re.S); return m.group(1).strip() if m else ""
            idurl = tag("id")
            m = re.search(r"arxiv.org/abs/([\d.v]+)", idurl)
            aid = m.group(1) if m else idurl
            title = re.sub(r"\s+", " ", tag("title"))
            summ = re.sub(r"\s+", " ", tag("summary"))[:600]
            pub = tag("published")[:10]
            yr = int(pub[:4]) if pub[:4].isdigit() else None
            authors = re.findall(r"<name>(.*?)</name>", e)
            if yr and yr < YEAR_FROM: continue
            rows["arxiv:"+aid] = {
                "source": "arxiv", "theme": theme, "query": q,
                "title": title, "year": yr, "venue": "arXiv",
                "doi": "", "arxiv": aid, "cited_by": None,
                "abstract": summ, "authors": authors[:6],
            }
        time.sleep(1.0)
    return rows

def main():
    oa = openalex_search()
    ax = arxiv_search()
    with open(os.path.join(RAW, "openalex.json"), "w") as f: json.dump(list(oa.values()), f, indent=1)
    with open(os.path.join(RAW, "arxiv.json"), "w") as f: json.dump(list(ax.values()), f, indent=1)
    combined = {}
    for r in list(oa.values()) + list(ax.values()):
        t = re.sub(r"[^a-z0-9 ]", "", (r["title"] or "").lower()).strip()
        key = t[:60]
        if key in combined:
            if r.get("arxiv") and not combined[key].get("arxiv"):
                combined[key]["arxiv"] = r["arxiv"]
        else:
            combined[key] = dict(r)
    with open(os.path.join(RAW, "combined.json"), "w") as f: json.dump(list(combined.values()), f, indent=1)
    print(f"openalex_raw={len(oa)} arxiv_raw={len(ax)} deduped={len(combined)}")
    from collections import Counter
    print("by_theme:", dict(Counter(r['theme'] for r in combined.values())))

if __name__ == "__main__":
    main()
