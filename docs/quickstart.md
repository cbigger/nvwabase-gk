# Quickstart

A walkthrough from one graph to a multi-graph fleet, using a defensive
incident-response task as the running example. Everything runs on your own
Claude Code and Anthropic account.

## 0. Install

```bash
bash install.sh        # puts fgc + nvwa on your PATH (stdlib only, zero deps)
```

Requirements: the `claude` CLI on your PATH (that's what dispatch and workers
call). The multi-agent path (`nvwa spawn`, `fleet`) also needs `tmux`. A single
graph needs only `claude`.

## 1. A single graph

Create a graph for one incident and inspect it:

```bash
fgc init --goal "triage the alert on host web-01"
fgc status                     # project + the ready-to-work frontier
```

Record a confirmed observation (a **fact**), then a **unit of work** (an
**intent**) that depends on it:

```bash
fgc fact "web-01 is running the alerted process" --title "process confirmed"
#   -> f001
fgc intent --from f001 "pull auth logs for web-01 around the alert time"
#   -> i001
fgc graph                      # facts + intents
fgc frontier                   # intents ready to work
```

Facts carry a one-line description plus an optional `--title` and `--doc`
(or `--doc-file`). Intents depend on one or more fact ids via `--from`
(the special `goal` fact can't be a dependency — seed a fact first, as above).
Use `--confirm` on an intent that must not run without human sign-off.

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

A **fleet** is a directory of per-unit graphs — one incident per unit. Create a
couple and watch the board:

```bash
fleet init u01 --goal "triage alert on host web-01"
fleet init u02 --goal "reconstruct the timeline for account svc-deploy"
fleet status --budget 60m      # cross-graph board: status / facts / open / ready / worker
```

Advance them. `sweep` is a no-LLM round-robin; `command` is one LLM allocation
step that decides which unit to work/hire/fire next:

```bash
fleet sweep --rounds 2                       # one auto slice over each open unit
fleet command --budget 60m                    # commander (strong tier) allocates the next slice
fleet up                                      # hire a worker on each open unit (needs tmux + claude)
fleet down                                     # stop all fleet workers
```

(`nvwa fleet …`, `nvwa command …`, `nvwa sweep …` route to the same thing.)

## 5. Run it unattended

`fleet command --loop` is the commander's tempo loop; `watchdog.sh` keeps it
alive to a deadline and relaunches it from its persisted state if it dies:

```bash
WATCHDOG_DEADLINE_MIN=90 FLEET_ROOT=.fleet ./watchdog.sh
```

See [doctrine/state-and-watchdog.md](../doctrine/state-and-watchdog.md).

## 6. Knowledge base

A static reference shelf the workers consult (distinct from the live graph):

```bash
fgc kb search "triage alert"
fgc kb show ir-triage-checklist
fgc kb add --title "Containment playbook" --tags "containment,ir" --body "isolate, preserve, eradicate"
```

## Where next

- [docs/ir-platform.md](ir-platform.md) — the incident-response domain in depth.
- [doctrine/commander-doctrine.md](../doctrine/commander-doctrine.md) — how a commander should allocate and escalate.
- [SKILL.md](../SKILL.md) — the full `fgc` command reference.
