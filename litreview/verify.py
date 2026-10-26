#!/usr/bin/env python3
import json, os, re, time, urllib.parse, urllib.request
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
UA = {"User-Agent": "lit-review-action-layer/1.0"}
def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode("utf-8","replace")
        except Exception:
            time.sleep(1.5*(i+1))
    return None

# Curated included set for the ACTION LAYER review.
INC = [
 # A. Tool use & function calling
 ("toolformer2023", {"arxiv":"2302.04761"}),
 ("react2023", {"arxiv":"2210.03629"}),
 ("gorilla2023", {"arxiv":"2305.15334"}),
 ("toolllm2023", {"arxiv":"2307.16789"}),
 ("hugginggpt2023", {"arxiv":"2303.17580"}),
 ("webgpt2021", {"arxiv":"2112.09332"}),
 ("toollearning_survey2025", {"doi":"10.1007/s11704-024-40678-2"}),
 ("agenticllm_survey2025", {"doi":"10.1613/jair.1.18675"}),
 ("stabletoolbench2024", {"doi":"10.18653/v1/2024.findings-acl.664"}),
 # B. Agent operating systems & tool protocols
 ("aios2024", {"arxiv":"2403.16971"}),
 ("llmos2023", {"arxiv":"2312.03815"}),
 ("mcp_landscape2026", {"doi":"10.1145/3796519"}),
 ("litecua2025", {"arxiv":"2505.18829"}),
 ("agents_survey2024", {"doi":"10.1007/s11704-024-40231-1"}),
 # C. Agent action environments & benchmarks
 ("osworld2024", {"arxiv":"2404.07972"}),
 ("webarena2023", {"arxiv":"2307.13854"}),
 ("taubench2024", {"arxiv":"2406.12045"}),
 ("workarena2024", {"arxiv":"2403.07718"}),
 ("agentdojo2024", {"arxiv":"2406.13352"}),
 ("sweagent2024", {"arxiv":"2405.15793"}),
 # D. Permissions, capability security, injection defense
 ("camel2025", {"arxiv":"2503.18813"}),
 ("mcpsecure2026", {"doi":"10.1109/ojcs.2026.3664314"}),
 ("miniscope2025", {"arxiv":"2512.11147"}),
 ("permmanifests2025", {"arxiv":"2601.02371"}),
 ("adaptiveattacks2025", {"doi":"10.18653/v1/2025.findings-naacl.395"}),
 ("privacyasst2024", {"doi":"10.1109/tdsc.2024.3372777"}),
 # E. Reversibility, undo, transactions
 ("saga2019", {"doi":"10.5220/0007918704830490"}),
 ("sagallm2025", {"doi":"10.14778/3750601.3750611"}),
 ("reversiblesurvey2020", {"doi":"10.1007/978-3-030-47361-7_2"}),
 # F. Auditability & action provenance
 ("agenttrace2026", {"arxiv":"2602.10133"}),
 ("provagent2025", {"doi":"10.1109/escience65000.2025.00093"}),
 ("provsensitivity2026", {"arxiv":"2607.20827"}),
 ("preactionauthz2026", {"doi":"10.5281/zenodo.21270299"}),
 ("continuousaudit2022", {"doi":"10.1007/s44206-022-00022-2"}),
 # G. Human-in-the-loop approval & oversight
 ("magenticui2025", {"arxiv":"2507.22358"}),
 ("actioncard2026", {"arxiv":"2609.18411"}),
 ("loopjacking2026", {"arxiv":"2609.21081"}),
 ("oversight2024", {"doi":"10.1016/j.nbt.2024.12.003"}),
]

def oa_by_doi(doi):
    txt = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    if not txt: return None
    try: w = json.loads(txt)
    except: return None
    if w.get("error"): return None
    return canon(w)

def arxiv_by_id(aid):
    txt = get("http://export.arxiv.org/api/query?id_list="+aid)
    if not txt: return None
    m = re.search(r"<entry>(.*?)</entry>", txt, re.S)
    if not m: return None
    e = m.group(1)
    def tag(t):
        mm = re.search(rf"<{t}>(.*?)</{t}>", e, re.S); return re.sub(r"\s+"," ",mm.group(1).strip()) if mm else ""
    return {"title":tag("title"), "year":tag("published")[:4],
            "authors":re.findall(r"<name>(.*?)</name>", e)[:8],
            "venue":"arXiv", "doi":"10.48550/arXiv."+aid, "arxiv":aid, "source":"arxiv"}

def canon(w):
    auth = [a.get("author",{}).get("display_name") for a in w.get("authorships",[])][:8]
    doi = (w.get("doi") or "").replace("https://doi.org/","")
    return {"title":w.get("title"), "year":w.get("publication_year"),
            "authors":auth, "venue":((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "doi":doi, "arxiv":None, "cited_by":w.get("cited_by_count"), "source":"openalex"}

out = {}
for key, spec in INC:
    rec = None
    if "arxiv" in spec: rec = arxiv_by_id(spec["arxiv"])
    elif "doi" in spec: rec = oa_by_doi(spec["doi"])
    status = "OK" if rec and rec.get("title") else "MISS"
    out[key] = {"status":status, "spec":spec, "rec":rec}
    t = (rec or {}).get("title") if rec else None
    print(f"[{status}] {key}: {t} ({(rec or {}).get('year')}) | {(rec or {}).get('venue')} | doi={(rec or {}).get('doi')}")
    time.sleep(0.3)

json.dump(out, open(os.path.join(RAW,"included_verified.json"),"w"), indent=1)
miss = [k for k,v in out.items() if v["status"]=="MISS"]
print("\nTOTAL", len(out), "OK", len(out)-len(miss), "MISS", len(miss), miss)
