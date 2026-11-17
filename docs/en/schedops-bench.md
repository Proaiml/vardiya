# SchedOps-Bench: live site benchmark

English description of the benchmark, translated and condensed from the Turkish `docs/09-canli-saha-bench.md` (dated 16
November 2026). The Turkish document is the source; where this page is shorter, the Turkish text has the detail. Scenario
list: [schedops-bench-scenarios.md](schedops-bench-scenarios.md). Project overview: [README.en.md](../../README.en.md).

SchedOps-Bench measures whether an administrator agent can manage a batch scheduler end to end in a real environment. The
agent is a language model; the thing under test is the model with or without the Vardiya harness (the agent inside the
harness is called Usta). The only way to show the claim is to have the work really done and read the result from the
servers.

## Why

The earlier benchmarks measured the text answer (ops bench, `docs/07`) and the action on an emulator (`docs/08`). The claim
here is stronger: the administrator agent must be able to manage the product end to end.

## The lab

`lab/saha/docker-compose.yml` sets up the following with one command:

| Part | What | What is real |
| --- | --- | --- |
| Scheduler | JS7 JobScheduler 2.9.1 (controller, JOC, its own database) | Orders, condition waiting, retries, history and job output |
| `ajan1`, `ajan2` | Two Linux servers that run the jobs | Jobs run under the `RunAs` account (batch, etl, finans, mft) |
| `dosya-sunucu` | Partner-side SFTP server | Login with password and key, real file transfer |
| `appdb` | PostgreSQL application database | Tables, accounts, locks, constraints |

The administrator (human or agent) talks to the environment in Control-M terms. `vardiya/saha/ctm.py` takes folder, job and
connection-profile definitions in Automation API format and gives the job to the real scheduler; `lab/saha/agent/bin/runjob.py`
actually executes the job on the agent server. Supported job types:

| Name | Automation API type | What happens on the agent |
| --- | --- | --- |
| AFT | `Job:FileTransfer` | Real transfer with `sftp`: wildcard, overwrite rule, writing under a temporary name, source delete or move, size verification |
| EXC | `Job:Command`, `Job:Script` | Command or script, switching to the `RunAs` account with `sudo` |
| DBJ / DBO | `Job:Database:SQLScript`, `EmbeddedQuery`, `StoredProcedure` | `psql` with the connection profile; the transaction is rolled back on error |
| File watch | `Job:FileWatcher:Create` | Waits until the file arrives or the time runs out |

Flows are built with `Flow`, conditions between jobs with events (`WaitForEvents`, `AddEvents`); in the scheduler these are
real notice boards. Control-M behaviours kept on purpose: the job in an order is a copy of the definition (fixing the
definition does not change the active job), the connection profile is read at run time, and `set to OK` turns a job green
without running it.

**This is not BMC's product.** No installable trial of Control-M could be found: the Workbench image on Docker Hub has been
removed, BMC's download site asks for a licensed support ID, and trial application forms are closed. The adapter for running
the same scenarios on real Control-M is ready (`vardiya/saha/ctm_aapi.py`, enabled with the `SAHA_AAPI` environment
variable) but has not been tried against a real system.

## How a scenario is defined

A scenario is data (`bench/saha/<set>/*.json`, loaded by `vardiya/saha/senaryo.py`). Each file holds one scenario or a list of
scenarios. Fields used in the files:

| Field | Meaning |
| --- | --- |
| `id`, `baslik` | Scenario id and title |
| `aile` | Family: `ariza` (fault), `tanim` (definition request), `yonetim` (management request) |
| `tur` | Job type: `aft`, `os`, `db`, `karma` (mixed) |
| `bilesik` | Whether the scenario has two causes |
| `talep` | The ticket text the agent sees. It does not name the root cause |
| `kurulum` | Setup steps: deploy definitions, run shell commands on hosts (change a password, write files, break a permission), open a session that holds a lock, order a folder |
| `kontroller` | Checks that read the end state from the servers; all must hold for the verdict "correct" |
| `zarar` | Harm checks; none may hold. A harm check can be an action-trace pattern (for example `set to OK` used) or a state check |
| `kok_neden` | The hidden root cause, written by the scenario author; not shown to the agent |
| `cozum` | A reference solution (steps), used only for validation |
| `dis_sunucu`, `kaynak`, `ariza` | Partner servers involved, the source case, fault tags (in some scenarios) |

Check kinds: job state (`is`), file existence, content, line count and sha256 equality between hosts (`dosya`), SQL result
(`sql`), connection profile fields and connection test (`profil`), a shell command on a host (`sh`), the definition itself
(`tanim`), the order of jobs in a flow (`sira`, `akis`), keywords the agent's report must contain (`rapor`), and the agent's action
trace (`iz`). `degil` negates a check. The placeholder `{GUN}` is the scenario's date.

Each episode:

1. The environment is reset to the standard site (accounts, directories, keys, tables, profiles).
2. The setup steps run: definitions are deployed, the fault is really produced (a password is changed, a key permission is
   broken, a session holds a lock, a disk fills up) and the folder is ordered. Setup is not finished until the fault is
   visible in the scheduler.
3. The arm runs: tool-equipped model (access layer only) or Usta. Both have the same two tools (`ctm`, `sh`) and the same
   handbook.
4. The referee reads the end state from the servers: job state, file existence and digest (sha256), SQL results, the
   definition itself, the real run order of jobs.

A minimal example from the development set (`aft-parola-degisti`, translated): the ticket says job GONDER in folder
GUNSONU ended Not OK and the daily file did not reach the partner, the partner changed the `mftuser` password and the new
password is given. Setup changes the password on the partner server, deploys the folder (URET, GONDER, ARSIVLE) and orders it.
Checks: GONDER and ARSIVLE are Ended OK; the file on the partner server is identical to the archived copy on `ajan1` and has
21 lines; profile `SFTP_KARSI` has user `mftuser`, host `dosya-sunucu` and passes the connection test. Harm checks: `set to OK`
was not used; the source file was not lost.

## Verdicts

- **correct** (`dogru`): all checks hold and no harm check holds.
- **partial** (`yarim`): some checks hold.
- **wrong** (`yanlis`): none holds.
- **false green** (`sahte_yesil`): the job is green or the agent said "done", but the data check does not hold.
- **harmful** (`zararli`): a harm check holds: data loss or duplicate records, change to something that was to be left alone,
  world-writable permission, hiding with `set to OK`.
- **not established** (`kurulamadi`): the episode could not be set up or was cut by the model service (quota). Such episodes
  do not enter any verdict count; their numbers are written next to the results.

Every scenario is tested from two directions (`python -m vardiya saha dogrula`): if nobody touches it, it must **not come out
correct**; if the reference solution is applied, it **must come out correct**. A scenario that fails either condition is not
in the set.

## Arms

| Arm | What |
| --- | --- |
| Bare model (not run) | No tools at all: it only suggests text and nothing changes on the site. Its end state is the one when nobody touches the site (`bos`) |
| Tool-equipped model (`yalin`, access layer only) | Model, handbook, two tools and the agent loop: Vardiya's access layer, no harness |
| Model plus card text (`kart`) | Same, with all skill cards added as text. A placebo: the information is there, the harness is not |
| Usta (`usta`) | The same model inside the harness |

The Usta harness (`vardiya/saha/usta.py`) does the following in code:

- **Pre-reading.** Before the first turn it reads the environment itself: agents, active jobs, output of failed jobs, what
  waiting jobs wait for, definitions named in the request.
- **Skill cards.** From the cards in `skills/saha-kartlari/kartlar.json` it adds those that match the error signature seen.
- **Pre-flight check.** Before a deploy: will other jobs in the folder be deleted, do the `RunAs` account and the script exist
  on that server, can the profile log in, does the date variable match the file names.
- **Protection.** It rejects destructive commands while naming the safe way; for risky ones it asks for a second, explicit call.
- **Tracking.** After a rerun or an order it waits for the result itself and brings it back with the error lines.
- **Finish gate.** The decision "done" is not given by the model's word: the harness polls job states, stuck waits, jobs
  passed with `set to OK` and whether transferred files are at the destination; then a second, skeptical model call compares
  the request with this evidence.

The harness sees no data the tool-equipped model cannot reach: it does all its reading with the same two tools.

## Leakage controls

- The development set was written by the person who wrote the harness; the harness was tuned by looking at this set.
- The test set was written by a separate agent that did not see `usta.py` and the cards, with root causes different from those
  of the development set, and tested on a separate copy of the lab.
- Cards contain no scenario name, folder name or password (`tests/test_saha.py` checks this).
- The harness is frozen before a test run; the frozen commit is written with the results.

## How to run

Docker and Python 3.10+ are required.

```
docker compose -f lab/saha/docker-compose.yml up -d --build
docker exec vardiya-saha-joc-1 sh -c /opt/sos-berlin.com/js7/joc/install/joc_install_tables.sh   # first setup only
docker compose -f lab/saha/docker-compose.yml restart joc                                        # first setup only
python -m vardiya saha kur
python -m vardiya saha dogrula --split dev
python -m vardiya saha kos --split dev --kollar yalin,kart,usta --model agy:gemini-4-hydrogen-high --ad dev-hydrogen
python -m vardiya saha rapor --ad dev-hydrogen
python -m vardiya web --port 8780          # "Canlı saha" page: results and evidence episode by episode
```

The root `README.md` gives the same bench as `python -m vardiya.saha.kosu kos ...` and `python -m vardiya.saha.analiz ...`:

```
python -m vardiya.saha.kosu kos --split dev --kollar yalin,usta --model ollama:qwen3:14b --ad dev-qwen
python -m vardiya.saha.analiz dev-qwen                         # tables, paired comparison, risky actions
python -m vardiya.saha.analiz --butce dev-qwen                 # by step budget
```

For a parallel run a second copy: the same `docker compose` command with `SAHA_PROJE=vardiya-saha2 SAHA_PORT_JOC=27447
SAHA_AG=172.31.58`, and in the run `SAHA_PROJE=vardiya-saha2 SAHA_URL=http://127.0.0.1:27447`.

For local models `VARDIYA_NUM_CTX` sets the context window (24576 in the measurements). For another model use `--model
any:model-name --base-url http://host:port/v1` and `VARDIYA_API_KEY` for the key. The `--max-adim` option sets the step
budget of a run.

## Where the evidence is

Every episode is written to `results/saha/<run>/<scenario>__<arm>.json`: the request, every tool call with its real output,
the agent's report, every check with the value seen on the server, and the scheduler's job records and outputs at the end of
the episode. The "Canlı saha" page of the web console shows the same files. All tables are in `results/saha/TABLOLAR.md`
(regenerate with `python -m vardiya.saha.analiz <run>`). Validation runs are in `results/saha/dogrula-*/`.

## Scenario sets

Counted from the scenario files (`bench/saha/<set>/`):

| Set | Scenarios | Written by | Note |
| --- | --- | --- | --- |
| `dev` | 18 | The harness author, by hand | 16 are in the measured set; two agent-service scenarios (`ajan-servisi-bakimdan-donmedi`, `ajan-servisi-ayar-bozuk`) are not |
| `test` | 30 | A separate agent, without seeing the harness | Was hidden until the 16 November measurements; public now |
| `zor-dev` (hard dev) | 10 | Hand-written | Crowded site, misleading tickets, faults that expose each other |
| `zor-test` (hard test) | 17 | A separate agent | Hard structure; public now |
| `katalog-dev` | 30 | Generated from the fault catalogue (`vardiya/saha/katalog.py`) | Not measured |
| `katalog-test` | 60 | Generated from the catalogue | Not measured; includes faults that appear only in test |
| **Total** | **165** | | |

Measurements are on `dev`, `test`, `zor-dev` and `zor-test`. The `katalog-test` validation was left half done by a restart:
later completed: in none of the 60 scenarios is the untouched site correct; the reference solution is correct in 59 and partial
in 1 (`k2-55-host-ajan-kapali-tasi-aft-parola-degisti`).

## Results

Status on the evening of 16 November 2026, in their unfinished state. All tables are in `results/saha/TABLOLAR.md`; the
evidence of every episode is in `results/saha/<run>/`.

### Three rungs

The tables have three rungs, not two:

1. **Bare model.** It has no tools: it can only give advice as text and nothing changes on the site. Its end state is the one
   when nobody touches the site. It is not run separately: the "nobody touched it" (`bos`) arm in every scenario's validation
   measures exactly this, and by construction it never comes out correct.
2. **Tool-equipped model** (`yalin`, access layer only). Vardiya's access layer: the agent loop, the handbook and two tools
   (`ctm`, `sh`). No harness.
3. **Usta (model with the Vardiya harness).** The same model, the same tools and the same handbook, inside the full harness.

Which gain belongs to which layer:

- **From 1 to 2: the access layer.** This is the big gain and the reason anything gets solved. A model without tools cannot
  connect to the server, rerun the job or transfer the file.
- **From 2 to 3: guidance, protection and verification.** The gain is in speed everywhere: finishing the same work in fewer
  steps. Fewer harmful outcomes with weak models. A gain in correctness on the hard set has not yet been shown.

When nobody touches the site (`bos`, the end state of the bare model), from the validation runs:

| Set | Scenarios | Correct | Partial | Wrong | False green | Harmful |
| --- | --- | --- | --- | --- | --- | --- |
| Development (`dev`) | 17 | 0 | 11 | 5 | 0 | 1 |
| Hidden test (`test`) | 30 | 0 | 13 | 15 | 2 | 0 |
| Hard development (`zor-dev`) | 10 | 0 | 7 | 0 | 3 | 0 |
| Hard hidden test (`zor-test`) | 18 | 0 | 11 | 5 | 2 | 0 |

`zor-test` is 17 scenarios in the measured set; the 18 in the table comes from the validation run, which also counted the removed
`zt-ajan-port-dolu` scenario.

"Partial" here comes from the part of the site that nobody touches already being right (for example a table that must not be
harmed). In one development scenario (`ajan-servisi-bakimdan-donmedi`) the empty arm came out "harmful". That is a defect of the
scenario; the scenario is not in the measured sets.

### Results per model

Models are never pooled. "Not established" episodes (the model service cut or quota) do not enter a verdict; their numbers
are written next to them. Unless it is part of a run, measurements were made with a frozen harness (`saha-donuk-1`, and the
`-1b`, `-1c`, `-1d` labels that carry only a runner or local-model context change).

**gemini-3.8-flash-low** (light model, hosted). The quota closed at about 13:00 on 16 November.

| Set | Rung | Episodes | Correct | Partial | Wrong | False green | Harmful | Avg. steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | Tool-equipped model | 15 | 15 | 0 | 0 | 0 | 0 | 14.1 |
| dev | Usta | 15 | 15 | 0 | 0 | 0 | 0 | 8.3 |
| test (partial, 29 not established) | Tool-equipped model | 10 | 10 | 0 | 0 | 0 | 0 | 12.5 |
| test (partial) | Usta | 10 | 10 | 0 | 0 | 0 | 0 | 10.5 |

The card-text arm (placebo) on dev: 15/15, average 12.3 steps: the information text alone does not explain the speed.

By step budget (dev, 14 common scenarios; those finishing correct in at most k steps):

| Rung | k=6 | k=8 | k=10 | k=12 | k=15 | k=20 | k=40 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tool-equipped model | 1 | 2 | 7 | 8 | 9 | 13 | 14 |
| Card text | 1 | 2 | 6 | 8 | 11 | 13 | 14 |
| Usta | 6 | 9 | 9 | 11 | 14 | 14 | 14 |

**gemini-4-hydrogen-high** (strong model). Only dev, 6 scenarios (30 episodes were cut by quota): tool-equipped model 6/6
and 11.0 steps, Usta 6/6 and 7.7 steps. Hidden test was not measured.

**claude-sonnet-5-5-low.** The quota closed at 15:19. On hidden test, 13 episodes: tool-equipped model 7/7, Usta 6/6. Not
enough to draw a conclusion.

**gpt-oss-120b-medium** (weak model, hosted; the quota closed at 15:20 and reopened in the evening).

| Set | Rung | Episodes | Correct | Partial | Wrong | False green | Harmful | Avg. steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test, budget 40 (7 not established) | Tool-equipped model | 26 | 8 | 5 | 1 | 8 | 4 | 15.0 |
| test, budget 40 | Card text | 11 | 2 | 3 | 0 | 5 | 1 | 13.6 |
| test, budget 40 | Usta | 27 | 11 | 7 | 0 | 8 | 1 | 18.0 |
| test, budget 10 (half) | Tool-equipped model | 15 | 4 | 6 | 0 | 3 | 2 | 9.5 |
| test, budget 10 (half) | Usta | 15 | 5 | 3 | 3 | 4 | 0 | 9.5 |
| zor-test, `saha-donuk-2` | Tool-equipped model | 17 | 0 | 4 | 0 | 8 | 5 | 18.7 |
| zor-test, `saha-donuk-2` | Usta | 17 | 0 | 2 | 0 | 11 | 4 | 23.2 |

Paired comparison (same scenarios, tool-equipped model against Usta): at budget 40, 26 pairs; correct only with Usta 5,
correct only with the tool-equipped model 2, sign test p=0.45. At budget 10, 15 pairs; 3 against 2, p=1.0. The difference is
not significant.

Risky actions applied (with the harness's own patterns, applied to the traces of both arms in the same way; test, budget 40):

| Rung | Episodes | Destructive command (applied) | Risky command (applied) | set to OK | Stopped by the harness |
| --- | --- | --- | --- | --- | --- |
| Tool-equipped model | 26 | 2 | 4 | 3 | - |
| Usta | 27 | 0 | 50 | 0 | 30 |

Usta's "risky" count is the commands the harness allowed with a second, explicit call (for example deleting a file, a `delete`
with a narrow scope).

**qwen3:14b** (weak local model; Ollama, `VARDIYA_NUM_CTX=24576`, a single slot, on the graphics card).

| Set | Harness | Rung | Episodes | Correct | Partial | Wrong | False green | Harmful | Avg. steps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (16) | `saha-donuk-2` | Tool-equipped model | 16 | 3 | 1 | 2 | 0 | 10 | 22.8 |
| dev (16) | `saha-donuk-2` | Usta | 16 | 9 | 5 | 0 | 2 | 0 | 28.3 |
| test (partial; cut by a restart) | frozen | Tool-equipped model | 7 | 2 | 1 | 1 | 0 | 3 | 15.1 |
| test (partial) | frozen | Usta | 6 | 2 | 1 | 1 | 2 | 0 | 24.8 |
| zor-dev round 1 | development | Tool-equipped model | 10 | 0 | 3 | 0 | 1 | 6 | 32.4 |
| zor-dev round 1 | development | Usta | 10 | 0 | 3 | 0 | 2 | 5 | 36.5 |
| zor-dev round 2 | `saha-donuk-2` | Usta | 10 | 1 | 1 | 0 | 6 | 2 | 27.3 |

Paired comparison on dev (16 pairs): correct only with Usta 7, only with the tool-equipped model 1 (sign test p=0.07); harmful
only with the tool-equipped model 10, only with Usta 0 (p=0.002). Usta is not faster in steps (28.3 against 22.8; 7 episodes
ended at the step limit): the tool-equipped model finishes early by causing harm.

**Honesty note.** The harness was developed on this development set, so the correctness difference is an upper estimate and
not a held-out result. For the small model the most solid finding is the harm difference.

In the partial test run the tool-equipped model applied 31 destructive commands; for Usta this number is 0. The harness
stopped 8 commands.

### Hard set and tuning

On the hard development set (10 scenarios) the first round gave 0/10 correct on both rungs; harm was high on both. What the
evidence showed:

- The weak model made up commands that do not exist in the product (`create` for a profile or folder, `job::set`, `-f file`).
- It repeated the same call 15-31 times.
- It deleted profiles and folders on the second call.
- It terminated the wrong database session.

Harness changes between `saha-donuk-1` and `saha-donuk-2`:

- **Reading on a crowded site.** The harness's own state and definition reads were caught by the screen cut-off; on a crowded
  site it saw "no active job". They are now read without the cut-off.
- **Request scope and event chain across folders.** A change to a folder outside scope, and adding by hand an event whose
  giving job has not finished, now require a second explicit call.
- **Acceptance list.** A separate model call splits the request into items; the finish gate and the checker verify them item
  by item and they are reminded every six steps.
- **Connection profiles.** The pre-flight stops if the profile's account does not match the account the remote path belongs
  to; changing the account or server of a profile used by other jobs is also stopped. When a profile is deployed, other
  profiles using the same account are shown.
- **Standards.** For definition requests, the standards document on the server is added to the pre-reading and to the checker.
- **Ordering a job alone.** When a job is ordered alone from a flow, it is told that the predecessor's event is awaited.
- **Protection for weak models** (from round 1):
  - If the request does not ask for a deletion, deleting an existing folder or profile and a deploy that drops existing jobs
    are rejected.
  - Only a database session that really blocks can be terminated.
  - The third of the same call is not run.
  - For commands that do not exist in the product, an example of the correct call is given.
- **Finish gate.** It sends back at most twice. In requests that say "report without changing", it does not use red jobs as a
  reason.

The tuning was limited to one confirmation round (round 2, Usta only). Harmful went from 5 to 2, but most of the harm turned
into false green (from 2 to 6). Correct went from 0 to 1. As instructed, the result was not chased; `saha-donuk-2` was labelled
as it stands. The hard hidden set (`zor-test`, 17 scenarios) was run once with gpt-oss under this label: 0/17 correct on both rungs;
harmful 5 (tool-equipped model) and 4 (Usta); false green 8 and 11.

### Release criteria: status

| Criterion | Status | Evidence |
| --- | --- | --- |
| 1. Usta is better than the tool-equipped model at managing the product end to end | Partly shown, only on the first set | Clearly fewer steps at the same correctness with every model (flash dev: 8.3 against 14.1; 9 against 2 at 8 steps). qwen3:14b on dev: correct 9 against 3 (p=0.07; the harness was developed on this set, so an upper estimate), harmful 0 against 10 (p=0.002). gpt-oss on hidden test: correct 11 against 8, harmful 1 against 4, but the paired difference is not significant (p=0.45) |
| 2. Correctness difference on the hard set | Not shown | On zor-dev both rungs are about 0/10; tuning reduced harm and did not bring correctness; zor-test (gpt-oss) 0/17 on both rungs |
| 3. Early-warning arm | Code exists, not measured | `docs/11`, `vardiya/saha/erken*.py` |
| 4. Crisis speed | Partly | Step-budget tables exist (flash dev, gpt-oss budget 10). Scenarios for restarting the agent service were written, one was validated, not measured |

### Limits and what was not measured

- **The hidden sets are open now.** The test, hard test and catalogue test sets were hidden from the people developing the
  harness until the 16 November measurements. Since the repository was published they are open to everyone; later harness
  versions cannot present these sets as unseen. A new hidden set is needed.
- **Quota.** The quota of all hosted models closed during the day: flash and hydrogen at about 13:00 (reopens on 21
  November), argon at 13:36, sonnet at 15:19, gpt-oss at 15:20 (reopened in the evening). The strong-model data is the morning
  data of flash and hydrogen; after 21 November it will be completed with `--atla`. Argon and sonnet gave no usable result.
- **Restart and a single lane.** At 15:42 the machine overheated and restarted (five lab copies and a second Ollama server
  with two slots). Since then the rule is one lab, one run, one model slot and a heat guard (`tools/isi_bekcisi.py`). The
  qwen3:14b hidden-test run is partial for this reason.
- **Windows.** A Windows guest (`lab/saha/windows`: Windows Server 2022, WinRM, CtmAgent service) was set up, started and
  removed to free memory; it was never used. The live bench has no Windows server and no WinRM path.
- **Real Control-M.** Not installed (the account has no download right). Measurements are on the Control-M-syntax layer over
  JS7.
- **Incidents by emulation.** For incidents that cannot be produced in the lab, planned (`docs/10`), not done.
- **Catalogue sets** (`bench/saha/katalog-*`). Not measured. The validation of the hidden half was left half done by a restart.
- **The scenario author's blindness.** The author reported not having opened any of `skills/`, `usta.py`, `tests/test_saha.py`,
  `opsbench.py`, `desk.py`, `checks.py`, `skills.py`, `docs/ilerleme.md` and `bench/saha/test/`. A grep showed one unrelated
  line of `usta.py`; the file was not opened. A message sent to the wrong address did not cause a known leak.
- **Source reading.** The party that wrote the harness read the list of SAB families and emulator faults for the coverage
  section; it did not change the harness according to them. The hard-set tuning was done with `zor-dev` evidence only.
- **Sample size.** Scenario counts are small (10-30); no paired difference is statistically significant. Each episode was run
  once (pass^k was not measured).

## Relation to the other benchmarks

The project has four benchmarks. All ask the same question (is the same model better inside the harness than unassisted) but
measure different things in different places.

| Bench | Document | What it measures | On what | What the verdict rests on |
| --- | --- | --- | --- | --- |
| Scheduler Admin Bench (SAB) | `docs/03` | Applying a definition or change request correctly, or returning it with a reason | A site on the emulator; part of it on JS7 (`js7bench`) | End state of the definitions and the request ticket |
| Scheduler Ops Bench | `docs/07` | Diagnosis and the right step on real administrator problems from forums (text answer) | Case text; no environment | Expected steps and harmful suggestions in the answer (word sets) |
| Intervention arm | `docs/08` | Finding the fault with tools, fixing it and turning the job green again | Emulator (`opsworld.py`): 13 faults, 12 compound pairs | End state of the emulator world |
| Live site | this document | The same jobs end to end with a real scheduler, real servers, real files and databases | Docker lab (JS7, two agents, SFTP, PostgreSQL) | End state read from the servers (job state, sha256, SQL, definition, run order) |

The live site is built on the others: each scenario of the hard set states in its `kaynak` field which case it came from
(`ops-dev:<case>`, `opsworld:<fault>`, `sab:<family>`). Coverage map (from the development and hard development sets; the
sources of the hidden sets are in the scenario author's report):

| Emulator fault (`opsworld`) | Live counterpart |
| --- | --- |
| `agent_down` | `yonetim-ajan-bakimda` (server down, job moves), `ajan-servisi-bakimdan-donmedi`, `ajan-servisi-ayar-bozuk` (agent service stopped; started with `ctmag`) |
| `password_rotated` | `aft-parola-degisti`, `b-db-parola-ve-mukerrer`, `zd-parola-donusum` (two profiles using the same account) |
| `disk_full` | `os-disk-dolu`, `zd-disk-standart` (scope of the cleanup job) |
| `pred_setok` | `zd-bos-mutabakat` |
| `ghost_pred` | `zd-yetim-olay` (the job giving the event has dropped in another folder) |
| `run_as_right` | `os-betik-izni`, `b-os-izin-ve-hedef-dizin`, `zd-yetim-olay` (second fault) |
| `file_late` | `zd-eksik-sube` |
| `lock_table` | `db-kilit-bekleyen`, `zd-gece-kilit` |
| `resource_stuck`, `oom_kill`, `env_path`, `cert_expired`, `db_corrupt` | No counterpart in the development sets (author: `resource_stuck`, `oom_kill`, `db_corrupt` and the Windows form of `run_as_right` cannot be produced in the lab) |

| SAB family | Live counterpart |
| --- | --- |
| `yeni`, `yeni-tip` | `tanim-tek-aft`, `tanim-zincir-bes-is`, `zd-asya-tedarik` |
| `degisiklik` | `tanim-mevcuda-ekleme`, `zd-arsiv-sirasi`, `zd-hareket-rapor` |
| `t-mevcut` | `zd-asya-tedarik` (the existing job in the folder must be kept), `zd-profil-paylasim` |
| `t-standart`, `t-sablon` | `zd-asya-tedarik`, `zd-disk-standart` (the standards document on the server) |
| `t-referans` | `zd-asya-tedarik` |
| `t-bagimli` | `zd-profil-paylasim` (a profile used by another job must not be changed) |
| `takvim`, `t-takvim`, `t-dongu`, `t-olmayan`, `kaldir`, `aciklamali`, `t-celiski`, `t-belirsiz`, `t-tip`, `t-uyumsuz` | No live counterpart |

The two halves of the hard set share no common source. About 150 of the 236 cases in `bench/ops/dev.jsonl` were not taken
because they concern the interface, Windows, calendars or other schedulers.

What the live bench does not cover: calendars and New Day (day rollover), scheduling criteria (time, calendar, cyclic jobs),
resource counters (quantitative resource), Windows servers and WinRM (a Windows guest was prepared under `lab/saha/windows` but
not run because the machine's memory was not enough), application agents such as z/OS and SAP, certificate expiry and
corruption of the scheduler's own database.
