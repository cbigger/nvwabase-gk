# nvwabase-gk

A shared **fact-intent graph** for long-horizon, multi-agent work, plus a thin
orchestration layer that runs many agents and many graphs at once. Pure Python
standard library, zero dependencies, opt-in per project.

The model is simple: **facts** are confirmed observations (nodes), **intents**
are units of work (edges from the facts they depend on toward the fact they
will produce), and an intent that points at the goal completes it. State lives
in the graph's structure, not a state machine. Many agents share one graph;
individual agent sessions can end while the graph — and the work — persists.

This fork generalizes the proven *design* of an autonomous multi-agent harness
into a domain-neutral base and builds three things on top of the graph engine:
a **commander doctrine**, **model tiering**, and a **multi-graph commander**.
The first worked domain is defensive **incident response** — see
[docs/ir-platform.md](docs/ir-platform.md).

## The two CLIs

- **`fgc`** — the single-graph engine (`lib/fg.py`): create a graph, record
  facts and intents, dispatch reason/explore/verify/brainstorm/blindspot steps
  through the `claude` CLI, drive one graph to its goal with `auto`, search
  prior work with `recall`, and render an interactive HTML DAG with `view`.
- **`nvwa`** — orchestration: spawn/‌message/‌read AI agents (one per tmux pane),
  a cross-graph board, and the multi-graph commander. Every `fgc` command
  passes through `nvwa` transparently.

## What's inside

- **Layered memory** — each node has a title, a one-line description, and an
  optional detailed doc; prompts get the summary layer, depth is opt-in via
  `fgc doc <id>`, so context stays lean.
- **Typed facts, neutral mechanism** — `fgc fact "<obs>" -k <kind> -d key=value`
  records a node with an optional domain `kind` (a free-form slug) and a bag of
  `key=value` attributes, so the commander can count and correlate on them
  (`fgc graph -k indicator`). The engine never enumerates kinds — it stores
  arbitrary strings; a domain's doctrine supplies the vocabulary (incident
  response uses `alert`, `indicator`, `host`, `account`, `timeline`, `finding`,
  `containment`). Untyped facts default to `note`, so the feature is opt-in.
- **Sub-agent dispatch** — `fgc dispatch reason|explore|verify|brainstorm|blindspot`:
  a commander proposes, executors work, verifiers check; every conclusion is
  written back into the graph. `fgc auto` runs the loop to the goal or budget.
- **Model tiering** — a role→tier→model map (`FG_TIERS`): a strong model for the
  commander and hard/high-stakes steps, a cheap model for the worker mass, with
  a strong-concurrency cap. Degrades to a single model when unconfigured.
  See [doctrine/commander-doctrine.md](doctrine/commander-doctrine.md) Part B.
- **Multi-graph commander** — a **fleet** is a directory of per-unit graphs.
  `nvwa command` runs one LLM allocation step across the board (work/hire/fire/
  stop), `nvwa sweep` round-robins a slice over open units, and
  `fleet up`/`down` manage the formation. `fleet command --loop` plus
  `watchdog.sh` keep a commander alive to a deadline, resuming from a persisted
  state file (doctrine §5).
- **Knowledge base** — `fgc kb search|list|show|add`: a static reference shelf
  the workers look things up in, distinct from the live graph.
- **Concurrency-safe** — one JSON file per node, flock + atomic writes; many
  agents, one graph, no corruption, and `git diff`-friendly.
- **Project hooks** — `fgc setup` injects graph state into every session turn.

## Quick start

```bash
bash install.sh      # installs fgc + nvwa (stdlib only, zero deps)
```

Then follow [docs/quickstart.md](docs/quickstart.md), which walks a single
graph through setup → fact → intent → auto, then scales up to a multi-graph
fleet with the commander. Drive it with your own Claude Code: `fgc`/`nvwa`
default to the `claude` CLI and your Anthropic account; the full multi-agent
path also needs `tmux`.

## Documentation

- [docs/quickstart.md](docs/quickstart.md) — end-to-end walkthrough.
- [docs/ir-platform.md](docs/ir-platform.md) — using nvwabase-gk as an incident-response platform.
- [doctrine/commander-doctrine.md](doctrine/commander-doctrine.md) — the neutral commander standing orders + model tiering (fill-in template).
- [doctrine/incident-response.md](doctrine/incident-response.md) — the IR instantiation of the doctrine.
- [doctrine/state-and-watchdog.md](doctrine/state-and-watchdog.md) — the state file + watchdog mechanism.
- [SKILL.md](SKILL.md) — the full `fgc` command reference.

## Credits

Built on [nvwabase](https://github.com/N1nEmAn/nvwabase) by N1nEmAn · VarFusion
Lab, which extracted the domain-neutral fact-intent graph engine. This fork adds
the generalized commander doctrine, model tiering, and multi-graph
orchestration. Thanks to [Cairn by Lèxiào](https://github.com/oritera/Cairn) for
the original approach to recording history for AI agents.

**License**: MIT
