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
fgc kb search "timeline"        # keyword search (title/tags weighted over body)
fgc kb list                     # all entries
fgc kb show timeline-reconstruction
fgc kb add --title "..." --tags "a,b" --body "..."
```

The two entries shipped here are neutral incident-response examples. Replace or
extend them with your own domain's playbooks; ship the KB empty if you prefer.
