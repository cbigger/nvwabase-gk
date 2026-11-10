# Handoff brief — porting sapper's lessons onto nvwabase

You are picking up a project that was scoped in a separate thread. This document
introduces the task, summarizes the conclusions reached there, and points you at
the detailed plan and reference files. Read this first, then the port plan.

## The task in one sentence

Fork **nvwabase** and build onto it a generalized, domain-neutral version of the
three things **sapper-v2** added on top of a fact-graph engine: a commander
doctrine, model tiering, and multi-graph orchestration — keeping the proven
*design* without inheriting sapper's pentest-specific *tangle*.

## Background (what these two projects are)

- **sapper-v2** (`github.com/cbigger/sapper-v2-gk`, a hard fork we translated to
  English) is an autonomous multi-agent orchestration harness that won a CTF
  competition. It is a legion model: one AI commander reads a shared fact/intent
  graph and dispatches worker agents in parallel; workers divide labor, pass
  intel through the graph, and a watchdog keeps them alive. Its interesting
  emergent behaviors (a self-invented "signalman" role, performance reviews of
  unproductive workers, inherited playbooks) came from four things: a tight
  command loop, a durable state/handover file, an escalation ladder with real
  stop-loss, and the commander's permission to reorganize its own workforce.
- **nvwabase** (`github.com/N1nEmAn/nvwabase`) is the domain-agnostic *base* the
  same author extracted from that work: the fact/intent graph engine
  (`fgc`) plus worker orchestration primitives (`nuwa` spawn/say/listen),
  pure-Python stdlib, with the pentest doctrine stripped out.

## Why we chose "build onto nvwabase," not "edit sapper down"

Both paths were considered. We chose nvwabase as the foundation and sapper as
the reference spec, because:

1. sapper's logic is a 4,726-line monolith (`lib/sapper.py`) with pentest
   concepts woven through the core (112 mentions of "challenge", 103 of "flag",
   plus CTF-coupled tests). Subtracting from it risks regressions in the engine
   we want to keep, and leaves us owning a monolith.
2. nvwabase is already the clean extraction — `fgc`/`nuwa` split, no pentest
   doctrine. Additive work on a clean base is reviewable; subtractive surgery on
   someone else's monolith is not.
3. What we actually want from sapper is mostly non-code (doctrine + tiering, now
   generalized into drop-in markdown) plus two code-shaped capabilities that
   nvwabase appears to lack anyway — tiering and multi-graph orchestration — so
   that code gets written either way. Better onto a clean base.
4. Both are MIT, same author lineage, so lifting generalized lessons is clean.

## What was already produced (carry these into the new project)

All of the following live in the **previous project's shared folder** and must
be copied into this project's init — a different project cannot read the old
one's files. Paths as they were written:

| File | What it is |
|---|---|
| `port-plan/sapper-to-nvwabase.md` | **The authoritative plan.** Seven phases, each with an exit criterion; says which lessons are markdown vs new code and the order to do them. START HERE after this brief. |
| `port-plan/handoff-brief.md` | This document. |
| `doctrine/commander-doctrine-neutral.md` | Domain-neutral commander standing orders (Part A) + model-tiering rules and a config stub (Part B). The generalized form of sapper's 426-line doctrine. Phase 1 + Phase 2 input. |
| `doctrine/generalization-inventory.md` | File-by-file classification of the whole sapper repo: neutral machinery vs pentest code vs data vs wiring vs narrative. Reference for what maps where. |
| `doctrine/templates-neutral/reason.md` | Neutral commander "what to dispatch next" prompt. Phase 1. |
| `doctrine/templates-neutral/explore.md` | Neutral worker "advance one unit" prompt. Phase 1. |
| `doctrine/templates-neutral/verify.md` | Neutral result-verification prompt. Phase 1. |
| `doctrine/templates-neutral/command.md` | Neutral multi-unit allocation prompt. Phase 1 + Phase 3. |
| `doctrine/templates-neutral/brainstorm.md` | Neutral brainstorm prompt (was already near-neutral). Phase 1. |
| `doctrine/templates-neutral/blindspot.md` | Neutral blindspot-analysis prompt (was already neutral). Phase 1. |
| `testing/running-and-reusing-sapper.md` | How to run sapper's 48-test suite and local sim, plus a plain-language explainer of the engine for non-CTF use. Orientation/background only. |

## Your first move

1. Read `port-plan/sapper-to-nvwabase.md` in full.
2. Execute **Phase 0** (investigation, no code): fork nvwabase, audit its actual
   `fgc`/`nuwa` command surface and template locations, and confirm the two
   key gaps the plan assumes — no model tiering, no multi-graph commander. The
   plan's code estimates firm up only after this. Produce the "confirmed gaps"
   note the plan calls for.
3. Then Phase 1 (port the neutral doctrine + templates, markdown only).

## One constraint carried over

The requester's standing rule: **do not write or edit code unless the
instructing message contains the exact phrase "You are being asked to produce
code."** Phase 0 (investigation), Phase 1, and Phase 6 (markdown) do not trip
this; Phases 2–5 do. Get explicit go-ahead with that phrase before writing code,
and when you do, work on a feature branch and open reviewable PRs.
