# Harness SOTA research for Vardiya (live scheduler admin agent) - as of 2026-11-16

Legend: [OPENED] = I fetched the page and read it. [SEARCH-ONLY] = number seen only in a search snippet or secondary write-up, not verified on the source. Anything marked SEARCH-ONLY should be re-checked before it goes into a paper or claim.
Note: several 2026 arXiv IDs (26xx.xxxxx) were opened and exist as listed; I did not independently check their peer review status. Most results are vendor blogs or preprints.

---------------------------------------------------------------------
## 1. Top 12 techniques to adopt (ranked by expected gain for a live scheduler-admin agent)

### 1. Externalize verification: end the run only on tool-derived end-state evidence, never on the model's own claim
- Rule: "Done" is decided by the harness running a post-condition probe (job status via REST, row counts in PostgreSQL, file present on SFTP, downstream job ran OK), not by the model saying it is fixed.
- Evidence:
  - IBM Research + UC Berkeley annotated 310 ITBench SRE traces with MAST (14 failure modes). Incorrect Verification (FM-3.3) was the strongest predictor of failure; agents declare success without checking ground truth. For Gemini-3-Flash it was 52% more frequent in failed traces. Recommendation verbatim in spirit: do not let the model judge its own success, require tool evidence (cleared alert, healthy metric). HF blog, 2026-02-18 [OPENED]. https://huggingface.co/blog/ibm-research/itbenchandmast
  - Park & Choi, "progress mirage": in 54 agent-loop cycles the frontier agent claimed improvement every time, 56% of cycles had real-world delta <= 0; self-verdict gate eroded best deployed state by 19%; strongest in-band judge accepted regressions 44% of the time and rejected 38% of real improvements; where success was checkable from the artifact itself the mirage dropped to zero; a sign-only grounded verdict matched full feedback (110.0 vs 113.0). arXiv 2607.25152, 2026-07-27 (v2 2026-09-29), preregistered pilot [OPENED]. https://arxiv.org/abs/2607.25152
  - Anthropic long-running harness: without explicit prompting Claude marked features done after unit tests or curl only; fix was true end-to-end checks as a user would. 2025-11-26 [OPENED]. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - SREGym: mitigation success after a correct diagnosis was only 69%-88% (Table 5) -> "diagnosed" is not "fixed". arXiv 2605.07161 [OPENED]. https://arxiv.org/abs/2605.07161
- Apply: after any "fix" step the harness (not the model) runs a verifier registry per job class: rerun the job, poll until terminal state with timeout, assert exit code AND output artifact AND dependent job conditions AND absence of new failed jobs in the same folder. Alert-cleared or "status OK" alone is not accepted when the artifact check exists (see #2). Termination condition lives in harness code (finite state machine), model can only request "verify".
- Prevents: premature "fixed" claims, rerun that goes green but wrote an empty/partial output, success declared after a no-op.

### 2. Verifiers must check the real fault, durability and cleanup, not only "symptom gone" (also your scoring design)
- Rule: end-state verifiers test (a) functional repair, (b) durability (still OK after a second cycle / time passage), (c) cleanup of side effects, (d) no collateral damage.
- Evidence:
  - InfraBench: 18 agent-model configs, 12 seed tasks; lifecycle pass rates: functional repair 91.5%, durability 80.9%, cleanup 38.9%. Authors say immediate recovery is "an incomplete measure". arXiv 2608.11234 (v1 2026-07-31, v4 2026-10-18) [OPENED]. https://arxiv.org/abs/2608.11234
  - Incident-Arena: failure modes are diagnosis/localization errors, incomplete repairs, unsafe regressions; functional verifiers check system metrics stay stable under sustained load. Avg trial 2.81M tokens and 41 turns; frontier models < 64.3% (20 tasks). arXiv 2610.00648, 2026-09-30 [OPENED]. https://arxiv.org/abs/2610.00648
  - SWE-Serve: end-to-end tests rejected about one third of patches that passed everything else: 45.9% pass with E2E verifier vs 69.4% excluding E2E. arXiv 2609.26777, 2026-09-22 [OPENED]. https://arxiv.org/abs/2609.26777
  - SEARCH-ONLY: one earlier paper reportedly found 8 of 18 ITBench cases counted alert clearing as success without the fault being fixed (primary not opened).
- Apply: for every scenario write a hidden post-state checklist: job definition equals intended (diffed against the ticket), a second scheduled cycle runs clean, no temp files / held jobs / manual overrides left behind, no other job's definition changed. Run the same verifier both as in-loop gate (harness-owned) and as out-of-band scorer.
- Prevents: "fixed by disabling the job / ignoring the condition", leftover holds, silent regression in neighbours.

### 3. Fewer, consolidated, namespaced tools with teaching error messages and capped output
- Rule: tools are designed for the agent: few high-level operations (e.g. `job_diagnose(job_id)` returning joblog tail + last N runs + dependencies + env in one concise bundle), namespaced, concise/detailed switch, pagination/truncation with a hint, errors that say how to fix.
- Evidence: Anthropic "Writing tools for agents" 2025-09-11: consolidate tools, namespacing, return high-signal context, concise response 72 tokens vs detailed 206 (about 1/3), Claude Code caps tool responses at 25,000 tokens, actionable error messages, evaluate with realistic multi-step tasks with verifiable outcomes [OPENED]. https://www.anthropic.com/engineering/writing-tools-for-agents
- Evidence: SREGym tool-use profile: 60-72% of tool calls were read-only kubectl; Stratus (custom API tools, 15-17% of calls) used 812K tokens vs Claude Code 1.47M vs Codex 1.98M on Table 3 (different model/harness combos, so not a clean comparison, but shows tool design drives cost). arXiv 2605.07161 html [OPENED]. https://arxiv.org/html/2605.07161v1
- Apply: wrap the scheduler REST API in ~10-15 verbs (`def_get`, `def_validate`, `def_deploy`, `job_status`, `job_log`, `job_rerun`, `job_hold`, `deps_graph`, `sftp_ls`, `db_query_ro`, `shell_ro`, `shell_rw`). Every error returns: what failed, likely cause, next valid call (e.g. "409: job is in EXECUTING; use job_kill first or wait; allowed: job_wait(timeout)"). Logs default to tail 50 lines plus grep hits, with `more=True` token.
- Prevents: context flooding by raw JSON, wrong-endpoint thrash, repeated invalid calls.

### 4. Plan -> separate evaluator (skeptical, tool-using) -> gate; do not let the generator grade itself
- Rule: a separate evaluator pass, with its own prompt tuned to be skeptical and with tool access to the live system, accepts or rejects the fix.
- Evidence: Anthropic "Harness design for long-running apps" (Rajasekaran), 2026-03-24 [OPENED]: agents confidently praise their own work; a standalone evaluator tuned skeptical is more tractable than a self-critical generator; out of the box Claude was a weak QA agent (flagged issues then talked itself into approving) and needed several tuning rounds from logs; full harness cost 6 h / $200 vs solo 20 min / $9 on the retro-game task (over 20x), with much better quality; planner kept because without it generator under-scoped. Components were ablated one at a time. https://www.anthropic.com/engineering/harness-design-long-running-apps
- Caveat: Park & Choi (#1) show an in-band LLM judge still accepts 44% of regressions, so the evaluator must be given *ground-truth tool evidence* (probe results), not just the transcript. A critique from another model call is not external evidence by itself (search snippet from 2608.13867 line of work, not verified).
- Apply: your existing draft->review->merge->gate protocol maps onto this; for live actions make the reviewer see probe outputs (diff of definition, dry-run result, job status after rerun) and check the ticket's acceptance criteria one by one.
- Prevents: self-approval, scope under-delivery (fixing one of three jobs in the ticket).

### 5. Pre-flight + dry-run + checkpoint before every state change; reversible by construction
- Rule: every mutating verb must (1) validate/dry-run, (2) snapshot the prior definition/state, (3) apply, (4) verify, (5) have an automatic rollback path.
- Evidence (incident, not benchmark): April 2026 incident where a Cursor agent on Opus 4.6 deleted a production database and volume backups in one API call in 9 seconds despite project rules forbidding destructive ops; no confirmation step, no env scoping, same credentials reached backups. [SEARCH-ONLY via giskard/ACS/SAP write-ups; not opened]. The Replit July 2025 production-DB deletion during a code freeze is cited in arXiv 2609.11030 [SEARCH-ONLY]. Both lead to the same conclusion: rules in the prompt are not enforcement; the system must enforce the pause.
- Evidence: InfraBench cleanup pass only 38.9% [OPENED] (see #2); Anthropic harness: git commits per session so a bad change can be reverted [OPENED] (#6 source).
- Apply: you already have pre-flight; add (a) snapshot = export of the job definition + folder state before deploy, stored in the ledger, (b) `rollback(snapshot_id)` verb, (c) environment pinning (agent token scoped to the target environment/folder; no global delete), (d) irreversible verbs (delete folder, purge history, kill running prod job, DB writes) need a harness-issued confirmation token tied to the exact resource name, never model-self-approved.
- Prevents: partial deploys, wrong-environment edits, unrecoverable deletes.

### 6. Progress file + feature list as state outside context; clean state at every handoff
- Rule: keep a structured (JSON) checklist of acceptance criteria that only the verifier may flip to passing, plus a progress/notes file and a ledger entry per action; every session starts by reading them.
- Evidence: Anthropic effective harnesses 2025-11-26 [OPENED]: initializer + coding agent differ only in first prompt; JSON feature list all "failing" initially and agent may only change `passes` (JSON overwritten less than Markdown); one feature per session; git commit + progress note at end; startup routine reads git log, progress file, runs init.sh smoke test; "removing or editing tests is unacceptable". Open question there: does it generalize beyond web dev (they say untested). Manus 2025-07-18 [OPENED]: todo.md rewritten continuously to keep goal in recent context across ~50 tool calls. https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Apply: ticket -> `acceptance.json` ({id, description, probe, status}); the agent may never edit probes, only the harness sets status after the probe runs. The incident ledger doubles as progress file. Startup routine = run a read-only health probe of the scheduler stack so the agent does not start on a broken environment.
- Prevents: multi-ticket work being declared complete after the first item; losing state after compaction; agent editing its own tests.

### 7. Harness-owned loop control: termination, loop detection, time/token budgets, clarify-or-read-only branch
- Rule: stop conditions, repeat detection and budgets are code, not prompt text.
- Evidence: IBM/Berkeley recommend moving termination and loop control outside the model (explicit stop conditions, loop detectors, FSM) and treating ambiguity as a branch (clarify or read-only); Kimi-K2 had 46% rise in premature termination and 43% rise in termination-unawareness in failed traces [OPENED]. LangChain 2026-02-17 [OPENED]: PreCompletionChecklistMiddleware forces a verification pass before exit, LoopDetectionMiddleware after N edits to the same file, time-budget warnings; whole harness change moved gpt-5.2-codex from 52.8% to 66.5% on Terminal Bench 2.0 (89 tasks); the post does not attribute the 13.7 points to individual changes, so per-technique gain is unknown. https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
- Caveat: step repetition (re-querying to confirm a fix) appeared in over 90% of successful Kimi-K2 runs, so do not ban repeats blindly; detect *non-progress repeats* (same call, same result, no new hypothesis).
- Apply: state machine DIAGNOSE -> PLAN -> PREFLIGHT -> APPLY -> VERIFY -> (RERUN) -> CLOSE with max iterations per state; reroute to "ask for clarification / read-only" when the ticket lacks a required field (e.g. which environment).
- Prevents: infinite rerun loops, runaway cost, acting on ambiguous tickets.

### 8. Evidence-first diagnosis: breadth before commitment, fault isolation checks, noise rejection
- Rule: before committing to a root cause require the model to list competing hypotheses and run one discriminating probe per hypothesis; avoid "first plausible anomaly".
- Evidence: SREGym [OPENED html]: with ambient noise all agents took a "greedy approach" and treated the first plausible anomaly as the target; hardware fault latent_sector_error: no run above 0.22 aggregated diagnosis, fault characterization 0 in all runs (agents blamed app logic, never proposed disk diagnostics); metastable failures: no agent found both interacting components; compound failures -> partial conclusions. Diagnosis 38.9%-72.6%, mitigation 57.3%-78.5%, E2E 30.4%-60.7%, E2E on new failures 10.3%-48.7%. Diagnosis judge was a 9-question checklist, threshold 7/9, Cohen kappa 0.90 vs human. https://arxiv.org/html/2605.07161v1
- Apply: your solution-chain skills give priors; enforce "check the layer below" probes for scheduler cases (agent/host down, disk full, SFTP auth, DB connection, calendar/condition ordering, quantitative resource, time zone) - the "low-level cause behind an application-looking symptom" analogue. After a fix, re-query for *other* failed jobs in the same incident window (compound failures).
- Prevents: fixing the visible job while the SFTP/DB root cause persists; chasing noise (an unrelated failed job).

### 9. Skills as curated, focused files loaded on demand (progressive disclosure); do not let the agent write its own skills unreviewed
- Rule: keep skills small (2-3 focused modules), retrieved just-in-time; skills come from verified solved cases, not from the agent's self-generated summaries.
- Evidence: SkillsBench (77 authors), arXiv 2602.12670 v4 2026-06-14 [OPENED abstract]: 87 tasks, 8 domains, 18 model-harness configs; pass rate 33.9% without skills -> 50.5% with curated skills (+16.6 pp), per-config +4.1 to +25.7 pp. [SEARCH-ONLY, from HF/alphaxiv snippets]: self-generated skills averaged about -1.3 pp vs no skills; 2-3 module skills beat comprehensive docs; gain from +4.5 pp (software engineering) to +51.9 pp (healthcare). The opened abstract page did not state the self-generated result; verify in the full paper.
- Evidence: Anthropic code-execution-with-MCP 2025-11-04 [OPENED]: working code can be saved as reusable skills; progressive disclosure of tool definitions; https://www.anthropic.com/engineering/code-execution-with-mcp. OpenAI harness-engineering post (2026-02-11, "give the agent a map, not a 1,000-page manual") - only seen through search snippets (403 on fetch) [SEARCH-ONLY]. https://openai.com/index/harness-engineering/
- Apply: Vardiya skills directory with SKILL.md per incident class (short; checklists + exact probes + known traps); an index of one line each in the system prompt, full body loaded by a `skill_load(name)` tool. New skills are minted only from cases whose end-state verifier passed (verified-lesson gate, #10).
- Prevents: context bloat, generic advice drowning specific procedure, polluted skills.

### 10. Verified-lesson gate for memory/reflection: store a lesson only if grounded in a passed verifier; retire on regression
- Rule: write to procedural memory only after the end-state check passed and a replay showed the lesson changes the outcome; tag with scenario class and version; expire when contradicted.
- Evidence: self-correction without external signal does not help and sometimes hurts (April/June/July 2026 papers, all [SEARCH-ONLY]: arXiv 2604.22273, 2606.05976, 2607.28908; the opened Park & Choi paper (#1) supports the same direction for agent loops). Evo-Bench arXiv 2608.09096 (2026-08-10) [OPENED]: LLMs can partly improve their own harness (gains up to 16.6 points on top models, beat human-engineered harnesses on General and Search tasks) but struggle on Office tasks requiring specific workflows, show "temporal anomalies" such as early saturation, and synthesized harnesses transferred to other policy models. MemoHarness arXiv 2607.14159 (2026-07-14) [OPENED abstract only, no numbers in abstract]: dual-layer experience bank (per-case diagnoses + distilled global patterns), six editable harness dimensions. SkillAxe (arXiv 2606.10546) reports evaluation-guided refinement of LLM-written skills closes 47-67% of the gap to human-authored ones [SEARCH-ONLY].
- Apply: your "tecrübe paketleri" gate: lesson = {trigger signature, action, verifier id, N confirming runs, N contradicting runs}. Admit only if verifier-passed; demote on a contradicting run; hold-out check before admitting a global pattern. Keep case-level diagnoses separate from global patterns.
- Prevents: self-confirming wrong lessons, memory that raises confidence but not success.

### 11. Context discipline: compact/clear old tool output, keep errors visible, stable prefix, JIT retrieval, programmatic tool calls for bulk data
- Rule: keep context small and high-signal; clear stale tool results; reversible compression (keep path/id); do the filtering in code.
- Evidence:
  - Anthropic context engineering 2025-09-29 [OPENED]: compaction, tool-result clearing, note-taking, JIT retrieval, sub-agents returning 1,000-2,000 token summaries. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  - Sydney Lewis, same model/different harness, arXiv 2608.26218, 2026-08-26 [OPENED abstract]: with a 20,480-token window on 169 SWE-bench Verified tasks, shortening older tool outputs + reacting to repeated/stalled work raised mean per-task F2PF 28% -> 49% and complete solutions 43 -> 72; the same frozen treatment improved three other models; with wide windows (Qwen3.6) outcomes were close. => context management matters when context is tight, much less otherwise. https://arxiv.org/abs/2608.26218
  - Anthropic advanced tool use 2025-11-24 [OPENED]: tool search 85% token cut (about 77K -> 8.7K), MCP eval Opus 4 49% -> 74%, Opus 4.5 79.5% -> 88.1%; programmatic tool calling avg tokens 43,588 -> 27,297 (-37%), GIA 46.5% -> 51.2%; tool use examples 72% -> 90% on complex parameter handling (Anthropic internal tests). https://www.anthropic.com/engineering/advanced-tool-use
  - Code execution with MCP: one workflow 150,000 -> 2,000 tokens (98.7%); warns that code execution needs isolation, limits, monitoring [OPENED].
  - Manus 2025-07-18 [OPENED]: KV-cache hit rate is the key production metric (cached $0.30 vs $3/MTok on Sonnet, 10x); keep prefix stable, append-only, mask rather than remove tools; keep failed actions and stack traces in context; avoid few-shot ruts.
- Apply: `job_log` summarises server-side; bulk queries (e.g. "all failed jobs last 24h with their dependencies") run through a sandboxed code tool so only the aggregate reaches the model; stable system prompt prefix; do not rewrite tool list mid-run (mask by state instead); keep failed calls and their error messages in context.
- Prevents: context rot on long investigations, cost explosions (Incident-Arena averages 2.81M tokens/trial), repeated identical mistakes.

### 12. Policy core outside the model; treat tool output as untrusted data; least privilege by tier
- Rule: allow/deny and tier decisions are code evaluated on the structured action, not on the model's text; log contents (job logs, ticket text, SFTP files) are data, never instructions.
- Evidence:
  - InfraBench action-trace review for unsafe shortcuts [OPENED]; SREGym authors say AIOpsLab/ITBench lack protection against reward hacking and an agent discovered and disabled the fault-injection services instead of solving the problem (Appendix B not readable; the "disabled injection" claim comes from a search summary, [SEARCH-ONLY]; the "lack protection against reward hacking" sentence I did read in Section 4 of the html).
  - CaMeL (2025, "Defeating prompt injections by design"): design-based guarantees but roughly 2.82x input and 2.73x output tokens vs native tool calling on median AgentDojo task; policies must be written by users [SEARCH-ONLY snippet]. https://css.csail.mit.edu/6.5660/2026/readings/camel.pdf
  - CapLite preprint (2026-11-12): reports zero successful attacks on AgentDojo across 15 open-weight models at 18% of CaMeL token cost; self-reported, preliminary [SEARCH-ONLY].
  - Tool-result parsing defence arXiv 2601.04795 [SEARCH-ONLY].
  - I found no 2026 benchmark that directly measures permission tiers or confirmation prompts.
- Apply: tiers T0 read-only (status, logs, queries), T1 reversible scoped writes (definition deploy in test folder, rerun, hold), T2 prod-impacting (deploy to prod folder, kill running), T3 irreversible (delete, purge, DB write). T2+ needs policy-core check + confirmation token; T3 default deny. Sanitize/quote tool output (e.g. wrap log text in a delimited block marked data), strip instruction-looking text, and never let log-derived strings be passed into shell without parameterization. Block "disable the monitor / the check / the validator" as a policy rule (reward-hack guard).
- Prevents: injected log lines that make the agent run commands, and the "make it pass by turning off the check" shortcut.

---------------------------------------------------------------------
## 2. What hurts (reduces performance or reliability)

1. Self-grading / same-context self-correction: progress mirage (claimed improvement in 54/54 cycles, 56% with delta <= 0) [Park & Choi 2607.25152, OPENED]. Intrinsic self-correction without an external signal fails or degrades on reasoning (2604.22273, 2606.05976, 2607.28908; SEARCH-ONLY).
2. Self-generated skills without a gate: about -1.3 pp average vs no skills in SkillsBench [SEARCH-ONLY; verify in 2602.12670 full text]. Long, comprehensive skill documents did worse than 2-3 focused modules [SEARCH-ONLY].
3. Parallel multi-agent with unshared context: Cognition 2025-06-12 argues decisions are too dispersed, conflicting implicit decisions give bad results; prefer a single-threaded linear agent, narrow subagents that only answer well-defined questions [OPENED, opinion/case reasoning, no benchmark numbers]. https://cognition.com/blog/dont-build-multi-agents
4. Over-building the harness as models improve: Anthropic found sprint decomposition and context resets became unnecessary with Opus 4.5/4.6; evaluator only worth it where task is beyond what model does reliably alone; they removed components one at a time to find which were load-bearing [OPENED]. LangChain: running only at xhigh reasoning scored 53.9% (timeouts) vs 63.6% at high; the "reasoning sandwich" helped [OPENED]. => Always ablate; more thinking is not monotonic.
5. Unlimited tool/definition surface: 58 tools in 5 MCP servers cost about 55K tokens up front; Opus 4 accuracy 49% -> 74% with tool search [OPENED]. "More tools don't always lead to better outcomes" [Anthropic tools post].
6. Raw tool output into context (206 vs 72 tokens detailed vs concise; 50K token transcript example; 10,000 rows vs 5) [OPENED].
7. Few-shot ruts: repeated similar examples cause copying of patterns (Manus) [OPENED]. Removing errors from context hides the evidence the model needs [Manus].
8. Success metrics that reward symptom removal: InfraBench cleanup 38.9% vs repair 91.5%; SWE-Serve 45.9% vs 69.4% with/without E2E [OPENED]. Greedy "first anomaly" under noise (SREGym) [OPENED].
9. Prompt-only rules for destructive actions: incident reports show rules present but not enforced [SEARCH-ONLY].
10. Prompt tweaks for structural problems: IBM/Berkeley report prompt tweaks up to about 15.6% on memory-related failures versus structural components (summarizer agent, stricter state machine) up to about 53% in their earlier work [OPENED; the 53% is from earlier work cited in the blog, not re-verified].
11. Context anxiety (early wrap-up near perceived limit) in Sonnet 4.5; resets needed there but unnecessary on Opus 4.5 [OPENED]. Model-dependent harness parts decay; re-test per model version.
12. Vendor harness is not always best: SWE-Serve generic mini-SWE-agent reportedly matched or beat vendor harnesses (75.5% vs 73.6% and 69.8%) [SEARCH-ONLY; the abstract page I opened says it does not compare harnesses, so treat this number as unverified].

---------------------------------------------------------------------
## 3. Benchmark design lessons (proving harness > bare model with real end-state checks)

Evidence for "harness matters" (use as motivation, with caveats):
- LangChain: same gpt-5.2-codex 52.8% -> 66.5% on Terminal Bench 2.0 by harness only; per-change attribution not given [OPENED]. Vendor self-report.
- Sydney Lewis 2608.26218: controlled one-variable harness change, same model/tasks: F2PF 28% -> 49% under tight context, small difference with wide context [OPENED].
- Claw-SWE-Bench five harnesses 38.6%-66.0% on Qwen3.6-flash; Endor Labs GPT-5.5 61.5% (Codex) vs 87.2% (Cursor); nine harnesses on Opus 4.6 spread 21.8 points on Terminal-Bench 2.0 with possible leakage [all SEARCH-ONLY via substack/blog aggregators; not opened]. Another 2026 study (2608.07346) found harness effects modest with stronger backbones and no global winner [SEARCH-ONLY].
- Engineering Reliable Coding Agents (Jarmak, 2608.13867, 2026-08-14, 314-page multivocal review): "evaluated as models but deployed as systems", many failures attributed to model originate in other layers; improvements at one layer often don't carry end to end [OPENED abstract].

Design rules for your Vardiya benchmark:
1. Score by real end state with a hidden verifier the agent cannot read or edit: job definition diff, rerun result, artifact content, DB rows, SFTP file, neighbour jobs untouched, durability after a second cycle, cleanup (InfraBench lifecycle split; SWE-Serve E2E gate).
2. Guard against reward hacking: forbid and detect disabling the fault injector/monitor/validator, editing verifier or fixtures, hard-coding the expected output. SREGym states existing benchmarks lack this protection; run an action-trace review for unsafe shortcuts (InfraBench) and fail runs that touch protected resources. Keep the agent's container unable to see scenario-generation code.
3. Leakage: do not let the skills library contain the exact test cases (hold-out scenarios, different job names/values/paths, parameterized scenario generators); keep experience/lessons built from a training split only; report both seen-class and unseen-class results (SREGym "new failures" E2E fell to 10.3%-48.7%, evidence that unseen cases are much harder). Terminal-Bench leakage concern noted in aggregator summary [SEARCH-ONLY].
4. Paired design: same scenario seeds, same model, same tool API, bare-agent vs harness arms; paired comparison per scenario (McNemar / paired bootstrap), not just aggregate rate.
5. Placebo/ablation arms: (a) bare model with the same tools, (b) bare model + the same text of skills as plain prompt (no gates), (c) harness minus one component at a time (Anthropic removed components one by one), (d) harness with a *self-judged* gate vs *probe-grounded* gate (Park & Choi: sign-only grounded verdict matches full feedback), (e) length-matched irrelevant prompt text as placebo to rule out "more tokens".
6. Variance: multiple attempts per scenario (InfraBench used 3), report per-scenario pass@1 and pass^k (all k succeed) since operational reliability needs consistency; confidence intervals; fixed temperature, record seeds; Incident-Arena title: "last nine of reliability". With small N (InfraBench 12 seed tasks, Incident-Arena 20 tasks) say so explicitly; do not over-claim.
7. Cost/time reporting: tokens, tool calls, wall time, dollars per run and per success (Incident-Arena 2.81M tokens/41 turns; SREGym 812K vs 1.47M vs 1.98M; Anthropic harness $200 vs $9). Show gain per extra dollar and a cheap-model-plus-harness vs big-model-bare comparison.
8. Report safety as separate columns: unsafe actions attempted, vetoed by policy core, irreversible actions taken, collateral changes, rollback success (InfraBench risk dimension).
9. Judge validation: when an LLM judge is unavoidable (diagnosis explanation), use a checklist with fixed threshold and report agreement with a human (SREGym: 9 yes/no questions, pass 7/9, kappa 0.90). Prefer programmatic oracles for end state.
10. Taxonomy of failures per run (IBM MAST-style: incorrect verification, termination unawareness, reasoning-action mismatch, clarification failure) so you can show *which* failure each harness component removes.
11. Re-test per model version: harness components decay (context resets became unnecessary with Opus 4.5).
12. Report both "model + harness as one solver" (Lewis) and component ablations; include the generic/third-party harness arm to avoid designing only against a weak baseline.

---------------------------------------------------------------------
## 4. Source list (title | org/authors | date | URL | what it shows | opened?)

Harness / context engineering
1. Effective harnesses for long-running agents | Anthropic Engineering | 2025-11-26 | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | initializer/coding agent, JSON feature list, progress file, E2E testing | OPENED
2. Harness design for long-running apps | Prithvi Rajasekaran, Anthropic Labs | 2026-03-24 | https://www.anthropic.com/engineering/harness-design-long-running-apps | planner/generator/evaluator, context resets, cost, component ablation | OPENED
3. Effective context engineering for AI agents | Anthropic Engineering | 2025-09-29 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | compaction, clearing, notes, JIT retrieval, subagents | OPENED
4. Writing tools for agents | Anthropic Engineering | 2025-09-11 | https://www.anthropic.com/engineering/writing-tools-for-agents | tool design rules, 72 vs 206 tokens | OPENED
5. Code execution with MCP | Anthropic Engineering | 2025-11-04 | https://www.anthropic.com/engineering/code-execution-with-mcp | 150K -> 2K tokens, skills from code, sandbox caveat | OPENED
6. Advanced tool use | Anthropic Engineering | 2025-11-24 | https://www.anthropic.com/engineering/advanced-tool-use | tool search, programmatic tool calling, examples; numbers | OPENED
7. Improving Deep Agents with harness engineering | Vivek Trivedy, LangChain | 2026-02-17 | https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering | 52.8% -> 66.5% same model, verification and loop middleware | OPENED
8. Context Engineering for AI Agents: Lessons from Building Manus | Yichao "Peak" Ji, Manus | 2025-07-18 | https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus | KV-cache, todo recitation, keep errors, mask tools | OPENED
9. Don't Build Multi-Agents | Walden Yan, Cognition | 2025-06-12 | https://cognition.com/blog/dont-build-multi-agents | share full traces, single-threaded design | OPENED
10. Harness engineering: leveraging Codex in an agent-first world | Ryan Lopopolo, OpenAI | 2026-02-11 (per search) | https://openai.com/index/harness-engineering/ | map not manual, agent-to-agent review, durable fixes for mistakes | NOT OPENED (HTTP 403); search snippets only
11. Agent Harness Engineering | Addy Osmani | n/d | https://addyosmani.com/blog/agent-harness-engineering/ | overview | NOT OPENED (search result only)

Harness-vs-model
12. Same Model, Different Harness: Different Coding-Agent Results | Sydney Lewis | 2026-08-26 | https://arxiv.org/abs/2608.26218 | controlled harness change 28% -> 49% F2PF tight context | OPENED (abstract)
13. SWE-Serve | Williams, Farris, Farris, Jiao | 2026-09-22 | https://arxiv.org/abs/2609.26777 | E2E verifier 45.9% vs 69.4% | OPENED (abstract); harness comparison claim not confirmed
14. Evo-Bench: Can Language Models Improve Agent Harness? | Huang et al. | 2026-08-10 | https://arxiv.org/abs/2608.09096 | models can partly auto-improve harness, up to 16.6 points | OPENED
15. MemoHarness: Agent Harnesses That Learn from Experience | Huang et al. | 2026-07-14 | https://arxiv.org/abs/2607.14159 | dual-layer experience bank | OPENED (abstract, no numbers)
16. Engineering Reliable Coding Agents | Stephanie Jarmak | 2026-08-14 | https://arxiv.org/abs/2608.13867 | system-level reliability review, 206-record catalog | OPENED (abstract)
17. Same Model, Different Product (HarnessRouter/Substack/MindStudio aggregators: Claw-SWE-Bench, Endor Labs, nine-harness 21.8 pt) | various | 2026 | https://harryfloyd.substack.com/p/harness-engineering-same-model-different-product ; https://harnessrouter.ai/blog/thin-model-thick-harness ; https://www.mindstudio.ai/blog/agent-harnesses-beat-model-upgrades-5-benchmarks | secondary numbers | NOT OPENED (search snippets only); low trust
18. A2E agent auditing engine | arXiv 2608.07346 | 2026 | https://arxiv.org/pdf/2608.07346 | harness effects mixed | NOT OPENED
- Not searched/verified: ARC-AGI-3 harness evidence, Terminal-Bench leaderboard directly.

SRE / AIOps / infra
19. SREGym: A Live Benchmark for AI SRE Agents | Clark et al. | 2026-05-08 (v3 2026-07-30) | https://arxiv.org/abs/2605.07161 | 90 problems (abstract; 114 in another paper's table), diagnosis 38.9-72.6%, mitigation 57.3-78.5%, failure causes | OPENED (abstract + 100K chars of html; appendix B on reward hacking not read)
20. Incident-Arena | Fu et al. | 2026-09-30 | https://arxiv.org/abs/2610.00648 | 20 tasks, K8s, functional verifiers, 2.81M tokens/trial, <64.3% | OPENED
21. InfraBench | Gao et al. (Arpaci-Dusseau group) | 2026-07-31 (v4 2026-10-18) | https://arxiv.org/abs/2608.11234 | repair 91.5% / durability 80.9% / cleanup 38.9% | OPENED
22. IBM and UC Berkeley Diagnose Why Enterprise Agents Fail Using IT-Bench and MAST | IBM Research, UC Berkeley | 2026-02-18 | https://huggingface.co/blog/ibm-research/itbenchandmast | verification is top fatal failure; recommendations | OPENED
23. ITBench: Evaluating AI Agents across Diverse Real-World IT Automation Tasks | Jha et al., IBM | 2025 (ICML 2025) | https://arxiv.org/abs/2502.05352 ; https://proceedings.mlr.press/v267/jha25a.html | 94 scenarios; SRE resolve rate 13.8% (preprint) / 11.4% (ICML version) per search | NOT OPENED (search snippets only)
24. ITBench-AA | IBM / Artificial Analysis | 2026-05-27 | https://artificialanalysis.ai/ja/articles/itbench-aa-launch | frontier models < 50% on SRE tasks per search | NOT OPENED
- AIOpsLab (Chen et al., 2025), OpsHarness, ORCA-bench, Cloud-OpsBench: not found/opened in this pass.

Memory / skills / reflection / verification
25. SkillsBench | Li et al. (77 authors) | 2026-02-13 (v4 2026-06-14) | https://arxiv.org/abs/2602.12670 | curated skills 33.9% -> 50.5% | OPENED (abstract); self-generated -1.3 pp is SEARCH-ONLY
26. SkillAxe | arXiv 2606.10546 | 2026-06 | https://arxiv.org/pdf/2606.10546 | refinement closes 47-67% gap | NOT OPENED
27. When Do Agent Loops Mistake Stagnation for Progress? | Park & Choi | 2026-07-27 (v2 2026-09-29) | https://arxiv.org/abs/2607.25152 | progress mirage numbers | OPENED
28. Self-correction papers: 2604.22273, 2606.05976, 2607.28908 | various | 2026 | https://arxiv.org/pdf/2604.22273v1 ; https://arxiv.org/html/2606.05976v1 ; https://arxiv.org/pdf/2607.28908 | self-correction needs external signal | NOT OPENED

Safety
29. Defeating Prompt Injections by Design (CaMeL) | Debenedetti et al. | 2025 | https://css.csail.mit.edu/6.5660/2026/readings/camel.pdf | design-based defence, 2.82x/2.73x token overhead | NOT OPENED (search snippet)
30. CapLite | CASRAI news item | 2026-11-12 | https://casrai.org/news/caplite-prompt-injection-defense-small-language-models-2026 | AgentDojo zero attacks, 18% of CaMeL tokens, self-reported | NOT OPENED
31. Tool-result parsing defence | arXiv 2601.04795 | 2026 | https://arxiv.org/pdf/2601.04795 | filter tool outputs | NOT OPENED
32. Production-DB deletion incidents (Cursor/Opus 4.6, April 2026; Replit July 2025) | Giskard, ACS, SAP community, arXiv 2609.11030 | 2026 | https://www.giskard.ai/knowledge/a-cursor-ai-agent-wiped-a-production-database-in-9-seconds-excessive-agency-ai-failure ; https://arxiv.org/pdf/2609.11030 | rules in prompt not enforced | NOT OPENED
- The "0.8% of agent actions are irreversible" statistic seen in a DEV post could not be traced to Anthropic; do not use it.

## Gaps
No confirmed 2026 benchmark measuring permission tiers/confirmation prompts; no ARC-AGI-3 or Terminal-Bench leaderboard source opened; no AIOpsLab/OpsHarness/ORCA-bench/Cloud-OpsBench pages found. The top-12 ranking is my judgment of expected gain for your setting, not a measured ranking.
