# Reversible Agency: A Permissioned, Provenance-Carrying Action Layer for LLM Operating Systems — A Structured Literature Review

**Scope:** the *action layer* only — how LLM agents invoke tools and take real-world actions, how those actions are permissioned, whether they can be undone, and whether they can be audited. Memory across sessions, model routing/planning, and the shell UI are explicitly out of scope (reserved for Layers 4, 5, 6).
**Review type:** structured thematic review (scoping + targeted synthesis), run in the same verified style as the Qafiya data-layer review.
**Date searched:** 2026-10-19 (Asia/Bangkok). **Window:** 2018-01-01 to 2026-12-31.
**Databases:** OpenAlex (primary), arXiv (preprints). All 38 included citations verified programmatically against the OpenAlex DOI resolver / arXiv API (`verify.py`, `raw/included_verified.json`).

---

## Abstract

An LLM operating system becomes useful — and dangerous — at the point where it stops *rendering* and starts *acting*: moving files, sending messages, scheduling, purchasing. This review maps the six research literatures that a permissioned, reversible, provenance-carrying action layer must stand on: (1) tool use and function calling, (2) LLM agent operating systems and tool protocols, (3) agent action environments and benchmarks, (4) permissioning, capability security, and prompt-injection defense, (5) reversibility, undo, and transactional compensation, and (6) auditability, action provenance, and human-in-the-loop approval. From 805 deduplicated records, 438 passed the relevance screen and 38 verified works were synthesised. The central finding is that the field has solved *invocation* and is beginning to solve *containment*, but has not addressed *recourse*: tool-calling research measures whether an action succeeds, permission research asks whether it should proceed, and transaction research compensates failed workflows — yet no surveyed system treats an executed action as a **bound record** (intent, authority, data inputs, execution log) carrying a **first-class undo recipe**, so that what an agent did can always be re-narrated and, where physically possible, reversed. We state that gap as the action layer's novelty claim.

## 1. Introduction and research questions

Layer 3 of DeeWaanAI OS must let agents act under two guarantees no current agent OS offers: every action is a bound record (what was asked, what was done, on whose authority, with what data), and every action is reversible or explicitly marked irreversible. This review reorganises the literature around that target.

**Primary RQ.** *What prior work exists toward an action layer in which every agent action is permissioned before execution, recorded as a provenance-carrying artifact, and reversible by construction — and where is the integration gap?*

Sub-questions:

- **RQ1 (invocation).** How do LLMs select and call tools, and what structure do tool calls carry?
- **RQ2 (agent OS substrate).** How do LLM agent operating systems and tool protocols (AIOS, MCP) model actions, and do they permission or record them?
- **RQ3 (evaluation).** How are agent actions benchmarked, and do benchmarks measure containment or reversibility?
- **RQ4 (permissioning).** What mechanisms constrain *which* actions an agent may take (capabilities, least privilege, injection defenses)?
- **RQ5 (reversibility).** What prior art exists for undoing/compensating executed actions, in distributed systems and in agent systems?
- **RQ6 (audit & oversight).** How are agent actions logged, made auditable, and gated by human approval?

## 2. Methods

### 2.1 Search strategy

Two reachable databases were queried programmatically on 2026-10-19 using the same stdlib-only pipeline as the Qafiya review: **OpenAlex** `title_and_abstract.search` and **arXiv** `abs:`/`ti:` field queries, restricted to 2018–2026. Six concept blocks were used; representative strings:

| Block | Example query strings |
|---|---|
| Tool use | `"tool use" "large language model"`, `"function calling"`, `tool learning language model` |
| Agent OS & protocols | `"large language model" agent "operating system"`, `"AIOS"`, `"Model Context Protocol"` |
| Permissions & security | `capability-based security agent`, `"least privilege" agent tool`, `"prompt injection" defense` |
| Reversibility | `undo actions "software agent"`, `compensating transaction saga`, `"reversibility" software system` |
| Audit | `audit log "software agent"`, `accountability autonomous agents`, `provenance agent actions` |
| Human-in-the-loop | `"human-in-the-loop" agent approval`, `"human oversight" autonomous system` |

A seventh arXiv-only block targeted named action environments (`OSWorld`, `WebArena`, `τ-bench`, `SWE-bench`).

### 2.2 Screening and inclusion

Records were deduplicated by DOI (normalised-title fallback), screened by a keyword-relevance score over title+abstract against the action-layer topic (threshold ≥ 4), then manually curated to works that materially inform the design. **Exclusion:** domain-specific autonomy work (robotics teaming, weapons oversight) retained only where the control/approval idea transfers; pure coding-benchmark papers without an action-model angle excluded; vendor white papers and self-published Zenodo/SSRN records excluded unless the mechanism was directly on-point.

### 2.3 PRISMA-style flow

| Stage | n |
|---|---|
| Identified — OpenAlex | 679 |
| Identified — arXiv | 188 |
| After deduplication | 805 |
| Passed relevance screen | 438 |
| **Included in synthesis** | **38** |

### 2.4 Citation verification and a cautionary finding

Every included identifier was resolved against the arXiv API (arXiv IDs) or OpenAlex (DOIs), and canonical metadata retrieved programmatically. One screening hit is worth reporting as a data-integrity finding: OpenAlex returns a record titled *"Distributing Accountability, Not Capability…"* carrying ReAct's arXiv DOI (10.48550/arXiv.2210.03629) and a record titled *"Counterfactually Auditable Lifecycle Certification for Autonomous Agents"* carrying ToolLLM's DOI (10.48550/arXiv.2307.16789) — registry records squatting on well-known identifiers. Both were dropped, and all arXiv-sourced citations here were verified against the arXiv API rather than OpenAlex. Author lists are registry-derived and should be spot-checked at final typesetting.

## 3. Results — thematic synthesis

### 3.1 Tool use and function calling (RQ1)

The foundational pattern is established: **Toolformer** [1] self-supervises API calls; **ReAct** [2] interleaves reasoning and acting; **Gorilla** [3] and **ToolLLM/ToolBench** [4] scale to thousands of real APIs; **HuggingGPT** [5] orchestrates models as tools; **WebGPT** [6] grounds browsing with human feedback. Surveys consolidate the field [7, 8], and benchmark hardening (StableToolBench [9]) shows evaluation itself is fragile.

*Synthesis.* A tool call in this literature is a **transient function invocation**: arguments in, result out, measured by task success. What was asked (the user's intent), on whose authority the call ran, and what data flowed into it are not part of the call's record. The field optimised the *verb* and discarded the *receipt*.

### 3.2 Agent operating systems and tool protocols (RQ2)

**AIOS** [10] and the "LLM as OS" vision [11] frame LLM agents as processes on an OS-like kernel; the companion semantic file system was treated in the Qafiya review. **MCP** has become the de-facto tool protocol, and its security threat landscape is now actively mapped [12]; AIOS extensions route computer use through MCP [13]. Broad agent surveys [14] catalogue architectures without addressing action governance.

*Synthesis.* The OS metaphor has been applied to *scheduling and context*, not to *authority*. Classic operating systems exist precisely to mediate what a process may do (permissions, capabilities, audit); the LLM-OS line reuses the vocabulary while omitting the enforcement and accountability core. MCP standardises the wire format of a tool call — it does not standardise a permission grant, an action record, or an undo channel.

### 3.3 Agent action environments and benchmarks (RQ3)

Realistic action environments now exist: **WebArena** [16], **WorkArena** [18], **OSWorld** [15] (real computers), **τ-bench** [17] (tool-agent-user dialogues with policy conformance), **SWE-agent** [19] interfaces, and **AgentDojo** [20] for injection attacks/defenses.

*Synthesis.* Benchmarks score **task completion and, recently, attack resistance** — but never *recourse*. No environment asks: after the agent acted, could the state be restored? Can a third party reconstruct *why* the action was permitted? τ-bench's policy conformance is the closest neighbour to permission checking, but the policy is the benchmark's, not the user's authority record. Reversibility and auditability are unmeasured properties — which means they are unresearched properties. This absence directly motivates this layer's frozen experiments (reversibility rate; permission containment; re-narratability).

### 3.4 Permissioning, capability security, and injection defense (RQ4)

This is the fastest-moving block. **CaMeL** [21] shows prompt injection can be defeated *by design* with capability-style policies separating control and data flow. Runtime access control for MCP tooling exists (**MCP-Secure** [22]), as do least-privilege authorisation (**MiniScope** [23]) and **Permission Manifests** for web agents [24]. Privacy-specific tool-use guards exist (**PrivacyAsst** [26]). The sobering counterweight: **adaptive attacks break deployed defenses** [25], and AgentDojo [20] shows defense evaluation must be dynamic.

*Synthesis.* Permissioning is converging on the right abstractions — capabilities, least privilege, manifests — but grants live **outside the action**: they are filters in front of the model, not fields of a durable record. And the strongest results are *negative*: defenses degrade under adaptive attack. For our design this has two consequences: (a) permission scope must be a structural field of the action record, checked deterministically at commit time, not an advisory classifier; (b) the permission-containment experiment must be run defect-injection style, expecting and reporting bypasses.

### 3.5 Reversibility, undo, and transactional compensation (RQ5)

The mature prior art lives in distributed systems: the **saga pattern** — forward actions paired with compensating transactions — is well characterised [27], and **SagaLLM** [28] ports transaction guarantees and validation to multi-agent LLM planning. Reversible-computing and reversible-software surveys [29] formalise invertibility at a deeper level.

*Synthesis.* Compensation is a proven, formalised idea — but it is applied to *workflow failure*, not to *user recourse*, and it assumes the developer hand-writes compensations per service. No agent system executes an action while **simultaneously deriving and storing its undo recipe**, classifying the action as exactly-reversible / compensable / irreversible, and reporting that classification to the user before commitment. The "sent email" class — physically irreversible actions that must be marked and gated, not hidden — does not appear in this literature at all. This is the review's sharpest gap and the layer's clearest contribution.

### 3.6 Auditability, action provenance, and human approval (RQ6)

Post-hoc observability is arriving: **AgentTrace** [30] structured logging, **PROV-AGENT** [31] W3C-PROV lineage of agent interactions, audits of whether agents attend to provenance when choosing actions [32], and pre-action authorization bound to provenance evaluated on AgentDojo [33]; continuous-audit frameworks for AI predate agents [34]. On the approval side, **Magentic-UI** [35] makes human-in-the-loop control the interface, the **Verifiable Action Card** [36] binds approval to an inspectable action description, and **Loopjacking** [37] demonstrates that approval gates themselves are an attack surface; the feasibility limits of human oversight are argued broadly [38].

*Synthesis.* Logging captures *what happened*; provenance work captures *what data flowed*; approval work captures *who consented*. None fuses the three into a single **action record sufficient to re-narrate the action without rerunning anything** — intent, permission scope, data inputs, execution log, and undo recipe in one durable, provenance-carrying artifact. Auditability in the surveyed work means "a log exists"; the target here is stronger: the record *is* the audit.

## 4. The gap and the layer's novelty claim

The six literatures each solve one facet and leave the seams open:

- Tool use invokes actions but keeps no receipt [1–9].
- Agent OS/protocols standardise invocation but not authority or recourse [10–14].
- Benchmarks measure success and attack resistance, never reversibility or auditability [15–20].
- Permission systems gate actions but the grant is not bound to the record, and defenses degrade adaptively [20–26].
- Sagas compensate failures but assume hand-written compensation and never classify irreversibility for the user [27–29].
- Audit/approval work logs, traces, or gates — separately; no fused, self-sufficient action record exists [30–38].

**Novelty claim (defensible).** *We propose an action layer in which every agent action is executed only inside an explicit permission scope and is stored — in the Qafiya substrate — as a bound, provenance-carrying record carrying intent, authority, data inputs, execution log, and a first-class undo recipe with an explicit reversibility class (exactly-reversible / compensable / irreversible), so that every action is permissioned before execution, re-narratable from its record alone, and reversible by construction where physically possible.* The contribution is the **integration — permission, record, and undo as one artifact in the data substrate** — not any one mechanism.

**Closest neighbours to differentiate explicitly:** [10]/[11] (LLM OS — no permission or record semantics for actions), [21] (CaMeL — capability defense at the model, no durable action record or undo), [28] (SagaLLM — transaction guarantees for planning, no user-facing reversibility classes or per-action undo recipes), [23]/[24] (least-privilege grants — grants not bound to provenance-carrying records), [31]/[33] (provenance tracking / pre-action authorization — closest in spirit; no reversibility, and records are not first-class substrate entities), [36] (verifiable approval — human gate without an executable undo channel).

## 5. Evidence required to defend the claim (next steps)

Consistent with the layer instructions, the paper is credible with: (a) a **formal spec** of the action record (intent, preconditions, permission scope, execution log, undo recipe, reversibility class) expressed as Qafiya records/bindings; (b) a **prototype** executing file-level actions over Qafiya stores plus 2–3 external actions (calendar, email draft) behind scopes; (c) **frozen experiments** — reversibility rate over a scripted action battery (target 100% for data actions; irreversible ones like sent email reported, not hidden), permission containment via defect injection of over-broad intents (mirroring the Qafiya integrity track, and informed by the adaptive-attack findings [25]), and re-narratability: every action reconstructed from its record alone.

## 6. Limitations of this review

Single-pass automated search on two databases (Semantic Scholar excluded per the Qafiya precedent); relevance screening used a keyword score plus manual curation, so recall is bounded by the query strings. The tool-security literature is moving weekly; several 2026 items are preprints not yet peer-reviewed. Non-archival venues (Zenodo/SSRN) were largely excluded by design, which may under-count recent practitioner mechanisms. Author metadata is registry-derived. These bound completeness, not the direction of the gap, which is corroborated independently across all six themes.

## 7. References

1. Schick, T., Dwivedi-Yu, J., Dessì, R., et al. (2023). *Toolformer: Language Models Can Teach Themselves to Use Tools.* arXiv. https://doi.org/10.48550/arXiv.2302.04761
2. Yao, S., Zhao, J., Yu, D., et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models.* arXiv. https://doi.org/10.48550/arXiv.2210.03629
3. Patil, S. G., Zhang, T., Wang, X., et al. (2023). *Gorilla: Large Language Model Connected with Massive APIs.* arXiv. https://doi.org/10.48550/arXiv.2305.15334
4. Qin, Y., Liang, S., Ye, Y., et al. (2023). *ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs.* arXiv. https://doi.org/10.48550/arXiv.2307.16789
5. Shen, Y., Song, K., Tan, X., et al. (2023). *HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face.* arXiv. https://doi.org/10.48550/arXiv.2303.17580
6. Nakano, R., Hilton, J., Balaji, S., et al. (2021). *WebGPT: Browser-assisted question-answering with human feedback.* arXiv. https://doi.org/10.48550/arXiv.2112.09332
7. Qu, C., Dai, S., Wei, X., et al. (2025). *Tool learning with large language models: a survey.* Frontiers of Computer Science. https://doi.org/10.1007/s11704-024-40678-2
8. Plaat, A., van Duijn, M. J., van Stein, B., et al. (2025). *Agentic Large Language Models, a Survey.* Journal of Artificial Intelligence Research. https://doi.org/10.1613/jair.1.18675
9. Guo, Z., Cheng, S., Wang, H., et al. (2024). *StableToolBench: Towards Stable Large-Scale Benchmarking on Tool Learning of Large Language Models.* ACL Findings. https://doi.org/10.18653/v1/2024.findings-acl.664
10. Mei, K., Zhu, X., Xu, W., et al. (2024). *AIOS: LLM Agent Operating System.* arXiv. https://doi.org/10.48550/arXiv.2403.16971
11. Ge, Y., Ren, Y., Hua, W., et al. (2023). *LLM as OS, Agents as Apps: Envisioning AIOS, Agents and the AIOS-Agent Ecosystem.* arXiv. https://doi.org/10.48550/arXiv.2312.03815
12. Hou, X., Zhao, Y., Wang, S., et al. (2026). *Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions.* ACM TOSEM. https://doi.org/10.1145/3796519
13. Mei, K., Zhu, X., Gao, H., et al. (2025). *LiteCUA: Computer as MCP Server for Computer-Use Agent on AIOS.* arXiv. https://doi.org/10.48550/arXiv.2505.18829
14. Wang, L., Ma, C., Feng, X., et al. (2024). *A survey on large language model based autonomous agents.* Frontiers of Computer Science. https://doi.org/10.1007/s11704-024-40231-1
15. Xie, T., Zhang, D., Chen, J., et al. (2024). *OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments.* arXiv. https://doi.org/10.48550/arXiv.2404.07972
16. Zhou, S., Xu, F. F., Zhu, H., et al. (2023). *WebArena: A Realistic Web Environment for Building Autonomous Agents.* arXiv. https://doi.org/10.48550/arXiv.2307.13854
17. Yao, S., Shinn, N., Razavi, P., et al. (2024). *τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.* arXiv. https://doi.org/10.48550/arXiv.2406.12045
18. Drouin, A., Gasse, M., Caccia, M., et al. (2024). *WorkArena: How Capable Are Web Agents at Solving Common Knowledge Work Tasks?* arXiv. https://doi.org/10.48550/arXiv.2403.07718
19. Yang, J., Jimenez, C. E., Wettig, A., et al. (2024). *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering.* arXiv. https://doi.org/10.48550/arXiv.2405.15793
20. Debenedetti, E., Zhang, J., Balunović, M., et al. (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.* arXiv. https://doi.org/10.48550/arXiv.2406.13352
21. Debenedetti, E., Shumailov, I., Fan, T., et al. (2025). *Defeating Prompt Injections by Design (CaMeL).* arXiv. https://doi.org/10.48550/arXiv.2503.18813
22. Singh, G., Madisetti, V. K. (2026). *MCP-Secure: A Runtime Access Control Layer for Privilege-Aware LLM Agent Tooling.* IEEE Open Journal of the Computer Society. https://doi.org/10.1109/ojcs.2026.3664314
23. Zhu, J., Huang, X., Tseng, K., et al. (2025). *MiniScope: Authorizing Agents with Least-Privilege Permissions.* arXiv. https://doi.org/10.48550/arXiv.2512.11147
24. Marro, S., Chan, A., Ren, X., et al. (2025). *Permission Manifests for Web Agents.* arXiv. https://doi.org/10.48550/arXiv.2601.02371
25. Zhan, Q., Fang, R., Panchal, H. S., et al. (2025). *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents.* NAACL Findings. https://doi.org/10.18653/v1/2025.findings-naacl.395
26. Zhang, X., Xu, H., Ba, Z., et al. (2024). *PrivacyAsst: Safeguarding User Privacy in Tool-Using Large Language Model Agents.* IEEE TDSC. https://doi.org/10.1109/tdsc.2024.3372777
27. Štefanko, M., Chaloupka, O., Rossi, B. (2019). *The Saga Pattern in a Reactive Microservices Environment.* ICSOFT. https://doi.org/10.5220/0007918704830490
28. Chang, E. Y., Geng, L. (2025). *SagaLLM: Context Management, Validation, and Transaction Guarantees for Multi-Agent LLM Planning.* PVLDB. https://doi.org/10.14778/3750601.3750611
29. Mezzina, C. A., Schlatte, R., Glück, R., et al. (2020). *Software and Reversible Systems: A Survey of Recent Activities.* LNCS. https://doi.org/10.1007/978-3-030-47361-7_2
30. AlSayyad, A., Huang, K. Y., Pal, R. (2026). *AgentTrace: A Structured Logging Framework for Agent System Observability.* arXiv. https://doi.org/10.48550/arXiv.2602.10133
31. de Souza, R. P., Gueroudji, A., DeWitt, S. J., et al. (2025). *PROV-AGENT: Unified Provenance for Tracking AI Agent Interactions in Agentic Workflows.* IEEE eScience. https://doi.org/10.1109/escience65000.2025.00093
32. Liao, J. (2026). *Auditing Provenance Sensitivity in LLM Agent Action Selection.* arXiv. https://doi.org/10.48550/arXiv.2607.20827
33. Grice, D. (2026). *Provenance-Based Pre-Action Authorization for LLM Agents: A Structural Defense Evaluated on AgentDojo with AgentLock.* Zenodo. https://doi.org/10.5281/zenodo.21270299
34. Minkkinen, M., Laine, J., Mäntymäki, M. (2022). *Continuous Auditing of Artificial Intelligence: a Conceptualization and Assessment of Tools and Frameworks.* Digital Society. https://doi.org/10.1007/s44206-022-00022-2
35. Mozannar, H., Bansal, G., Tan, C., et al. (2025). *Magentic-UI: Towards Human-in-the-loop Agentic Systems.* arXiv. https://doi.org/10.48550/arXiv.2507.22358
36. Irshad, H., Mughees, A., Mughees, N., et al. (2026). *The Verifiable Action Card: Trustworthy Human-in-the-Loop Control for Secure Autonomous Agents.* arXiv. https://doi.org/10.48550/arXiv.2609.18411
37. Kumar, A. A. (2026). *Loopjacking: Hijacking Human-in-the-Loop Approval.* arXiv. https://doi.org/10.48550/arXiv.2609.21081
38. Holzinger, A., Zatloukal, K., Müller, H. (2024). *Is human oversight to AI systems still possible?* New Biotechnology. https://doi.org/10.1016/j.nbt.2024.12.003

---
*Reproducibility artifacts:* `search.py` (queries), `raw/openalex.json`, `raw/arxiv.json`, `raw/combined.json`, `screen.py`, `verify.py`, `raw/included_verified.json` (canonical metadata for all 38). Generated 2026-10-19.
