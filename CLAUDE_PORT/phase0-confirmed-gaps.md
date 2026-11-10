# Phase 0 — Confirmed gaps (audit of nvwabase)

Locks the scope of Phases 1–4 in `sapper-to-nvwabase.md`. This replaces the
plan's README-only guesses with a line-by-line audit of the actual code. Target
of the audit: `cbigger/nvwabase-gk` @ `3b2a991` (a fork of
`N1nEmAn/nvwabase` @ `6a55bf5`), whose `lib/fg.py` is byte-identical to upstream.

## Contribution model (decided)

`cbigger/nvwabase-gk` **is** the fork. Its `lib/fg.py`, `nvwa`, `templates/`,
`SKILL.md`, etc. are the clean upstream nvwabase; the only addition on top is the
`CLAUDE_PORT/` doc set (one commit). So the plan's "fork vs upstream PR" question
is already answered: we build on this fork, and code lands on branch
`claude/project-thread-qn1735` as reviewable PRs. No further forking needed.

## Command surface as it actually exists

Upstream renamed the orchestration CLI `nuwa` → `nvwa`. The graph CLI is `fgc`
(`lib/fg.py`); `nvwa` delegates every non-orchestration verb to it transparently.

**`fgc` (per-graph engine) — present:**
`init · status · graph · frontier · pick · fact · intent · hint · peers · send ·
capture · show · doc · recall · claim · release · done · complete · confirm ·
dispatch · brainstorm-pick · setup · teardown · view · auto`

- `dispatch <reason|verify|blindspot|brainstorm|INTENT_ID>` runs one commander/
  executor step through the `claude` CLI. (`INTENT_ID` → explore.)
- `auto` drives **one** graph forward: reason → explore → verify → repeat, with
  `--max-steps` / `--max-explore` caps.

**`nvwa` (orchestration layer) — present:**
`spawn · say · listen · list · kill · board` + pass-through to `fgc`.
One agent per tmux pane, `send-keys -l`, submission-verified. `board` shows the
roster plus **one** graph's status.

So the plan's assumption holds: **the per-graph loop and single-worker
orchestration already exist.** Phase 1's template/doctrine port and Phases 2–4
are the real work.

## The gaps, confirmed

### Gap 1 — Model tiering: mechanism partly present, the *system* absent
- `--model` **already exists** on `fgc dispatch` and `fgc auto` (default
  `FG_MODEL` env, else `sonnet`). So the thin "pick a model per step" mechanism
  is done for the single-graph path.
- `nvwa spawn` takes `--agent` (which CLI to launch) but **no `--model`/`--tier`**.
- **Absent:** any role→tier map (commander/senior/verifier/worker/scout/chore),
  the strong/cheap split, a max-concurrent-strong cap, and a key-pool / backup
  provider pool. There is no `SAPPER_KEY_POOL` equivalent anywhere.
- **Phase 2 scope shrinks:** the work is (a) a `--model`/`--tier` flag on
  `nvwa spawn`, and (b) the role→tier policy map + strong-concurrency cap +
  optional key-pool reader. The per-step `--model` plumbing is already there.

### Gap 2 — Multi-graph commander: fully absent (confirmed)
- `auto` and `board` each operate on exactly **one** graph.
- **Absent:** sapper's `command` (LLM allocates the next slice across many
  graphs), `fleet` (launch/stop the formation), `sweep` (round-robin `auto`
  across per-unit graphs). No cross-graph board, no allocation loop, no
  per-graph worker spawn/kill at the orchestration layer.
- No `command.md` template ships (`templates/` has only reason, explore, verify,
  brainstorm, blindspot — see Gap 5). The neutral `command.md` in `CLAUDE_PORT/`
  is the prompt this phase needs.
- **Phase 3 is the biggest code phase, as the plan expected.** It builds a thin
  orchestrator over the existing per-graph `auto`; reuse `nvwa spawn`, don't
  reinvent the worker layer.

### Gap 3 — Self-management (state file + watchdog): absent
- No watchdog script, no handover/STATE-file convention, no `--continue`
  relaunch. (`grep` for watchdog/handover/--continue → nothing.)
- Phase 4 ports both: the STATE/compaction protocol (markdown, already in the
  neutral doctrine §5) and a small keep-alive watchdog script (code).

### Gap 4 — Knowledge base: absent
- No `kb` subcommand, no `lib/kb.py`, no `kb/` data. (sapper had all three;
  nvwabase never carried them.)
- Minor live mismatch: the shipped `explore.md` template mentions an optional
  `<cli> kb search` the engine doesn't provide. Harmless (optional path), worth a
  note when Phase 5 lands or the template is revised.
- Phase 5 therefore means **porting the engine**, not generalizing an existing
  one — and it stays low priority; the system runs without it.

### Gap 5 — Phase 1 is smaller than written, with one compatibility catch
- `templates/` **already ships 5 of the 6** neutral prompts (reason, explore,
  verify, brainstorm, blindspot), and they are already domain-neutral with
  injection guards. The `CLAUDE_PORT/` copies are lightly reworded variants of
  the same files — `blindspot.md` is byte-identical; the other four differ only
  in wording.
- Genuinely missing from `templates/`: **`command.md`** (pairs with Phase 3) and
  a home for the **commander doctrine** (`commander-doctrine-neutral.md`).
  nvwabase's `SKILL.md` / `skill/SKILL.md` are CLI manuals, not commander
  standing orders.
- **Compatibility catch:** `render_prompt()` (lib/fg.py:1062) substitutes only
  `origin, goal, graph_yaml, fact_ids, open_intents, hints, max_intents`. It does
  **not** inject `{time_budget}` — which the `CLAUDE_PORT` `reason.md` and
  `command.md` reference. Dropping those variants in as-is would leave
  `{time_budget}` (and `command.md`'s `{board}`) as literal text in the prompt.
  So a straight template swap is **not** free: either keep the existing neutral
  templates (recommended — they already render cleanly) or extend the renderer
  (code) to supply the new keys.

## Net effect on the plan

| Phase | Plan's assumption | Audit verdict |
|---|---|---|
| 1 doctrine+prompts | port 6 templates + doctrine (markdown) | 5 templates already present & neutral; only `command.md` + a doctrine home are new. Mind the `{time_budget}` renderer gap. |
| 2 tiering | new code + config | smaller: per-step `--model` exists; need `spawn --model/--tier` + policy map + strong-cap. |
| 3 multi-graph commander | new code, the big one | confirmed fully absent — the main build. |
| 4 state+watchdog | new code + markdown | confirmed absent; both pieces needed. |
| 5 knowledge base | mostly existing-neutral | **correction:** nvwabase has no KB at all — port the engine, don't generalize. |

## The code boundary

Phases 2, 3, 4-watchdog and 5-engine are code and are blocked until a message
contains the exact phrase "You are being asked to produce code." Phase 0 (this
note) and Phase 1 (markdown) do not trip it. The one decision owned by the
requester before Phase 1 fills the `<DOMAIN>` slots: **which first non-CTF target
domain** to prove the doctrine on (the plan suggests a research sweep or a
code-audit task).
