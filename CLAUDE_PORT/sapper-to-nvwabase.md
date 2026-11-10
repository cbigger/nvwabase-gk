# Port plan: sapper lessons → nvwabase

**Decision (settled):** nvwabase is the foundation; sapper is the reference spec.
We build the commander + tiering + orchestration onto nvwabase's clean
`fgc`/`nuwa` split rather than carving the pentest logic out of sapper's
4,726-line monolith.

This plan lists each sapper lesson, what it becomes on nvwabase, whether it's
markdown/config or genuinely new code, and the order to do it in.

## Confidence note (read first)

The "what nvwabase already has" column is based on nvwabase's README/SKILL
command surface, not a line-by-line audit — GitHub rate-limited the deeper
read. So **Phase 0 is a real audit step**, and the new-code estimates below
firm up only after it. Treat anything marked *(assumed absent)* as a
hypothesis to confirm, not a fact.

Known from the README:
- `nuwa`: `setup` · `status` · `spawn` · `say` · `listen` · `dispatch reason` · `fact`
- `fgc`: `fact` · `doc` · `dispatch reason|explore|verify|brainstorm|blindspot` · `auto` · `recall` · `view` · `setup`

So the **per-graph loop and single-worker orchestration already exist** on
nvwabase. What appears missing is the **multi-graph commander** (sapper's
`command`/`fleet`/`sweep`) and **model tiering** — which is exactly the
high-value, code-shaped part of this port.

## Phasing at a glance

| Phase | Lesson from sapper | Becomes on nvwabase | Type | Depends on |
|---|---|---|---|---|
| 0 | — | Audit nvwabase's real surface + pick a fork/contribution model | investigation | — |
| 1 | Generalized prompts + commander doctrine | drop-in markdown (already drafted) | markdown | 0 |
| 2 | Model tiering (§4.9) | role→model map + key-pool reader | **new code** + config | 0, 1 |
| 3 | Multi-graph commander (`command`/`fleet`/`sweep`) | an orchestrator over many graphs | **new code** | 0, 2 |
| 4 | Self-management: state file + watchdog | handover-file convention + keep-alive loop | **new code** (watchdog) + markdown (protocol) | 1, 3 |
| 5 | Knowledge base (`kb`) | neutral KB engine, empty/other data | mostly already-neutral code + data | 0 |
| 6 | Narrative/docs | neutral README + quickstart | markdown | 1–5 |

## Phase 0 — Audit + setup (investigation, no code)
- Confirm nvwabase's actual `fgc`/`nuwa` command surface and where its prompt
  templates live (does it already ship `reason.md`/`explore.md` equivalents we
  should diff against, or inline prompts?).
- Confirm whether any tiering/multi-graph support exists that the README omits.
- Decide the contribution model: a hard fork we own, or upstream PRs to
  nvwabase. (Both MIT, same author — either is clean. A fork is lower-friction
  for iterating; upstreaming is better if the author wants it.)
- Output: a one-page "confirmed gaps" note that locks the Phase 2–4 scope.

## Phase 1 — Doctrine + prompts (markdown, no new code)
The lowest-risk, highest-leverage phase, and already mostly drafted.
- Port the six generalized prompt templates (`doctrine/templates-neutral/`) into
  nvwabase's template location, diffing against whatever it already ships.
- Port the neutral commander doctrine (`doctrine/commander-doctrine-neutral.md`
  Part A) as nvwabase's commander SKILL/standing-orders.
- Fill the `<DOMAIN>` slots for a first real target domain (pick one — a
  research sweep or a code-audit task is a good non-CTF proof).
- Exit criterion: nvwabase runs a single-graph task end-to-end driven by the
  neutral doctrine, no pentest vocabulary anywhere.

## Phase 2 — Model tiering (new code + config)
*(tiering assumed absent on nvwabase)*
- Add a tier map: roles (`commander`/`senior`/`verifier`/`worker`/`scout`/`chore`)
  → model/endpoint, plus a max-concurrent-strong limit and a backup pool. The
  config stub is in `commander-doctrine-neutral.md` Part B; it mirrors sapper's
  existing `SAPPER_KEY_POOL` JSON shape.
- Wire `spawn`/`dispatch` to accept a tier (or a `--model`) and default workers
  to the cheap tier.
- Degrades to plain retry with a single key, so it ships safely before a second
  provider exists.
- Smallest viable version: just `--model` on `spawn` + a default — tiering
  *policy* lives in the doctrine (Phase 1), the *mechanism* is this thin flag.

## Phase 3 — Multi-graph commander (new code, the big one)
*(multi-graph orchestration assumed absent on nvwabase)*
- This is sapper's `command` (LLM allocates the next work slice across many
  graphs), `fleet` (launch/stop the formation), and `sweep` (round-robin `auto`
  across per-unit graphs). nvwabase today drives *one* graph; this adds the
  layer that runs *many*.
- Design it as a thin orchestrator over nvwabase's existing per-graph `auto`:
  a board view across graphs, the allocation loop from `command.md` (already
  generalized), and spawn/kill of per-graph workers. Reuse nvwabase's `spawn`
  primitives; don't reinvent the worker layer.
- This is where most of the new code is. Scope it against Phase 0's findings —
  if nvwabase has any sweep primitive, this shrinks a lot.

## Phase 4 — Self-management: state file + watchdog (new code + markdown)
- The handover-file convention and compaction protocol are markdown (already in
  the neutral doctrine §5) — port as-is.
- The watchdog (relaunch a dead commander with `--continue`, rotate keys, wrap
  up at the deadline) is a small standalone script, domain-neutral already in
  sapper. Port it adapted to nvwabase's process model. This is what gives you
  the "commander resumes as its own successor" behavior.

## Phase 5 — Knowledge base (mostly existing-neutral)
- sapper's `kb.py` engine is already domain-agnostic; only its 56 JSON entries
  are pentest. If nvwabase lacks a KB, port the engine and ship it empty (or
  with domain-appropriate entries). Low priority — the system runs without it.

## Phase 6 — Docs (markdown)
- Neutral README + a quickstart that walks a non-CTF domain through
  setup→fact→intent→auto→commander. Replace the Nüwa/competition narrative with
  a plain "shared graph + many workers + scheduler" framing. Do this last, once
  the surface is stable.

## Critical path & sequencing logic
- **1 → 2 → 3** is the spine: doctrine first (proves the design on one graph),
  then the tiering mechanism it assumes, then the multi-graph layer that the
  commander doctrine is written for. Doing 3 before 1 would mean building
  orchestration with no doctrine to drive it.
- Phases 4, 5, 6 are parallelizable once 1–3 land.
- Each phase has a standalone exit criterion, so it's shippable incrementally
  rather than one big-bang port.

## The code boundary (unchanged)
Phases 2, 3, 4-watchdog, and 5-engine are **code**. Under your standing rule I
won't write code until a message includes the exact phrase "You are being asked
to produce code." Phase 0 (investigation) and Phases 1 and 6 (markdown) I can do
without it. When you're ready to start the code phases, say the phrase and name
the phase, and I'll do it on the `claude/project-thread-va6ygw` branch (or a new
nvwabase repo, per Phase 0's fork decision) as reviewable PRs.

## Immediate next action
Phase 0 is investigation-only and within what I can do now: audit nvwabase's
real command surface and produce the confirmed-gaps note that locks Phase 2–3
scope. Say the word and I'll run it — it also de-risks every code estimate above.
