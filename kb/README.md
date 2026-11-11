# Knowledge base

The domain **reference shelf** the agent swarm looks things up in — distinct
from the fact graph. The graph is live per-run working memory (what a run
produces); the KB is static reference (checklists, methods, playbooks) that
workers consult *before* improvising or escalating a tier.

The engine (`lib/kb.py`) is domain-agnostic; the contents are the domain part.
One JSON file per entry under `entries/`:

```json
{"id": "slug", "title": "...", "tags": ["..."], "body": "markdown text"}
```

Use it:

```
fgc kb search "<keywords>"      # keyword search (title/tags weighted over body)
fgc kb list                     # all entries
fgc kb show <id>
fgc kb add --title "..." --tags "a,b" --body "..."
```

The engine is domain-agnostic; the contents are the domain part. Fill the KB
with your own playbooks, or leave it empty — nothing in the base depends on a
particular entry.
