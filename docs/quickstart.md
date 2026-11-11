# Quickstart

A walkthrough from one graph to a multi-graph fleet, using a library-evaluation
task as the running example. Everything runs on your own Claude Code and
Anthropic account.

## 0. Install

```bash
bash install.sh        # puts fgc + nvwa on your PATH (stdlib only, zero deps)
```

Requirements: the `claude` CLI on your PATH (that's what dispatch and workers
call). The multi-agent path (`nvwa spawn`, `fleet`) also needs `tmux`. A single
graph needs only `claude`.

## 1. A single graph

Create a graph for one goal and inspect it:

```bash
fgc init --goal "evaluate candidate caching libraries and recommend one"
fgc status                     # project + the ready-to-work frontier
```

Record a confirmed observation (a **fact**), then a **unit of work** (an
**intent**) that depends on it:

```bash
fgc fact "libfoo documents an async API and a 10k-star repo" --title "libfoo overview" \
    -k source -d name=libfoo -d url=example.com/libfoo
#   -> f001
fgc intent --from f001 "benchmark libfoo throughput against the baseline"
#   -> i001
fgc graph                      # facts + intents (kinds shown inline)
fgc graph -k source            # only facts/intents of kind 'source'
fgc frontier                   # intents ready to work
```

Facts carry a one-line description plus an optional `--title` and `--doc`
(or `--doc-file`). A fact can also be **typed**: `-k <kind>` tags it with a
free-form type and `-d key=value` (repeatable) attaches structured
attributes, which the commander can count and filter on (`fgc graph -k source`).
Kinds are arbitrary strings — the engine never enumerates them — and an untyped
fact defaults to the kind `note`. The neutral default vocabulary is `source`,
`finding`, `artifact`, `decision`, and `risk`; a specialized deployment can
define its own. `fgc done` and `fgc intent` take the same `-k`/`-d`. Intents depend on one or more fact ids via `--from` (the special
`goal` fact can't be a dependency — seed a fact first, as above). Use
`--confirm` on an intent that must not run without human sign-off.

## 2. Drive it with the LLM

A single dispatch step, or the whole loop:

```bash
fgc dispatch reason --skip-permissions      # commander proposes intents / completes
fgc dispatch i001 --skip-permissions        # an executor works that intent
fgc auto --skip-permissions                  # reason -> explore -> verify, to the goal or budget
```

`--skip-permissions` passes `--dangerously-skip-permissions` to the worker so
it can run its tools unattended; drop it to approve each tool call.

Visualize anytime:

```bash
fgc view                       # writes a self-contained HTML DAG and opens it
fgc view --serve               # live page that refreshes as the graph changes
```

## 3. Model tiering (optional)

By default every step uses one model (`FG_MODEL`, default `sonnet`) through your
Claude Code auth. To run the commander and verification on a strong model and
the worker mass on a cheap one, point `FG_TIERS` at a map (inline JSON or a
file — see [doctrine/tiers.example.json](../doctrine/tiers.example.json)):

```bash
export FG_TIERS='{"tiers":{"strong":{"model":"opus"},"cheap":{"model":"haiku"}}}'
fgc tier show                  # inspect the resolved role -> tier -> model map
fgc auto --skip-permissions    # reason=strong, explore=cheap, verify=strong, automatically
```

`base_url`/`token` per tier let you use a key pool; omit them to use your
ambient Anthropic environment. Unset `FG_TIERS` and everything runs on one
model — tiering is opt-in.

## 4. Many graphs: a fleet

A **fleet** is a directory of per-unit graphs — one goal per unit. Create a
couple and watch the board:

```bash
nvwa fleet init u01 --goal "evaluate caching libraries and recommend one"
nvwa fleet init u02 --goal "evaluate logging libraries and recommend one"
nvwa fleet status --budget 60m   # cross-graph board: status / facts / open / ready / worker
```

Advance them. `sweep` is a no-LLM round-robin; `command` is one scripted
allocation step that decides which unit to work/hire/fire next:

```bash
nvwa fleet sweep --rounds 2        # one auto slice over each open unit
nvwa fleet command --budget 60m    # the allocator picks the next slice (strong tier)
nvwa fleet up                      # hire a worker on each open unit (needs tmux + claude)
nvwa fleet down                    # stop all fleet workers
```

## 5. Run the allocator unattended

`nvwa fleet command --loop` is the fleet's scripted allocation loop — not the
agentic commander of [the doctrine](../doctrine/commander-doctrine.md), but a
simple work/hire/fire/stop decision repeated on a timer. `watchdog.sh` keeps it
alive to a deadline and relaunches it from its persisted state if it dies:

```bash
WATCHDOG_DEADLINE_MIN=90 FLEET_ROOT=.fleet ./watchdog.sh
```

See [doctrine/state-and-watchdog.md](../doctrine/state-and-watchdog.md).

## 6. Knowledge base

A static reference shelf the workers consult (distinct from the live graph):

```bash
fgc kb search "<keywords>"
fgc kb list
fgc kb add --title "Benchmark method" --tags "method,perf" --body "warm up, measure p50/p99, repeat 5x"
```

## Where next

- [doctrine/commander-doctrine.md](../doctrine/commander-doctrine.md) — how a commander should allocate and escalate.
- [SKILL.md](../SKILL.md) — the full `fgc` command reference.
