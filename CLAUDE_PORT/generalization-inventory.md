# Full-project generalization inventory

A file-by-file map of what in `sapper-v2-gk` is pentest-specific and what is
already domain-neutral machinery, so a "generalize everything, keep the
functionality" pass has a complete target list. Based on a scan of every tracked
file (excluding `docs/assets/` images).

## The headline answer to "is it only markdown?"

**No — almost, but not quite.** If you set aside the Docker/competition wiring,
the pentest-specific additions over nvwabase's neutral core are *mostly*
markdown, but there are three non-markdown exceptions:

1. **`lib/arena.py`** (212 lines of Python) — the TSecBench platform API client.
   This is arguably "competition wiring" itself, just written in Python instead
   of Docker, so whether it counts depends on where you draw that line.
2. **`lib/sapper.py` has pentest code paths baked in**, not in separate files.
   The CTF subcommands — `flag`, `arena`, `bench`, `command`, `fleet`, `sweep` —
   live inside the one 4,726-line monolith (112 mentions of "challenge", 103 of
   "flag", 51 each of "arena"/"bench"). nvwabase never had these; it split the
   neutral core (`fgc`) from orchestration (`nuwa`) and stopped there. So "the
   only thing added is markdown *files*" is true at the file level but misses
   that the shared Python file itself carries pentest logic.
3. **56 `kb/entries/*.json`** — the offline knowledge base content (SQLi,
   privesc, CVE ladders). This is the cleanest exception: not markdown, not
   Docker, genuinely pentest data. The *loader* (`lib/kb.py`) is domain-neutral;
   its *contents* are the pentest part.

So the accurate statement is: **the markdown is where almost all the
pentest-specific *behavior* lives, but generalizing the project also means
touching Python (`sapper.py`, `arena.py`), swapping JSON data (the kb entries),
and updating the tests that cover those.**

## Classification table

Legend: **NEUTRAL** = already domain-agnostic machinery, keep as-is ·
**MD-DONE** = pentest markdown, neutral draft already written ·
**MD-TODO** = pentest markdown, still needs a neutral pass (allowed — markdown) ·
**CODE** = generalizing this means editing code/data (blocked by your no-code
rule until you say so) · **WIRING** = Docker/competition runtime you're excluding ·
**NARRATIVE** = the "out there" story text, optional to rewrite.

| File / group | Class | Notes |
|---|---|---|
| `lib/sapper.py` — graph core (Store, fact/intent, frontier, pick, claim, done, dispatch, auto, recall, view, setup) | NEUTRAL (but entangled) | the general engine; shares the file with the CTF verbs below |
| `lib/sapper.py` — CTF verbs (`flag`, `arena`, `bench`, `command`, `fleet`, `sweep`) | CODE | extract behind a domain/platform interface, or delete, to generalize |
| `lib/arena.py` | CODE / WIRING | TSecBench API client; drop, or turn into a pluggable "platform adapter" |
| `lib/kb.py` | NEUTRAL | knowledge-base engine, domain-agnostic |
| `kb/entries/kb0*.json` (×56) | CODE (data) | pentest techniques/CVEs; replace with your domain's KB, or ship empty |
| `lib/_settings_patch.py`, `lib/sapper-hook.py` | NEUTRAL | Claude Code hook wiring |
| `lib/view_template.html` | NEUTRAL | graph visualization |
| `tests/test_sapper.py` | CODE (mixed) | `ArenaClientTests`, `FlagLedgerTests`, parts of `CommanderTests`/`FleetTests` cover CTF features; the graph-core tests are neutral |
| `templates/reason.md`, `explore.md`, `verify.md`, `command.md` | MD-DONE | neutral drafts in `doctrine/templates-neutral/` |
| `templates/brainstorm.md`, `blindspot.md` | MD-DONE | were already ~neutral; copied over, brainstorm got a one-line tweak |
| `docker/commander/SKILL.md` (426-line doctrine) | MD-DONE | neutral template = `doctrine/commander-doctrine-neutral.md` Part A |
| `SKILL.md` (root), `skill/SKILL.md` | MD-TODO | CLI manuals; neutralizing them depends on the CODE decisions above (which verbs survive) |
| `docker/commander/SPEC.md` | MD-TODO | architecture contract, pentest-flavored prose |
| `docker/ENV.md` | MD-TODO / WIRING | config checklist; half neutral (tiering), half competition |
| `docker/Dockerfile*`, `entrypoint*.sh`, `watchdog.sh`, `worker.sh`, `build.sh`, `export.sh`, `local-sim.sh`, `tmux-drive.sh`, `config.toml` | WIRING | competition runtime you're excluding |
| `docker/nuclei.zip` | WIRING (binary) | pentest tool pack |
| `README.md`/`.zh-CN`, `BATTLE-REPORT.md`/`.zh-CN`, `CHANGELOG.md`, `docs/events-*.md` | NARRATIVE | the Nüwa/competition story; rewrite only if you want a neutral public face |
| `DISCLAIMER.md`, `LICENSE` | KEEP | the disclaimer is security-testing-specific; keep or soften |
| `install.sh`, `.gitignore`, `.dockerignore` | NEUTRAL | installer + ignores |

## What a "full pass" actually requires, in order

1. **Markdown (allowed now):** the four template rewrites (done) + root `SKILL.md`,
   `skill/SKILL.md`, and `SPEC.md`. The three TODO manuals are easiest to do
   *after* the code decisions, since they document the command surface.
2. **Code decisions (needs your go-ahead):** decide the fate of the CTF verbs and
   `arena.py` — the clean design is to extract them behind a small "platform
   adapter" + "domain fact-kinds" interface so the core stays verb-stable and a
   domain plugs in its own platform/KB. That is a real refactor of `sapper.py`
   and its tests.
3. **Data:** replace or empty the 56 kb entries; the engine stays.

## The boundary I'm holding

Steps 2 and 3 are code/data edits. Your standing rule is no code edits unless the
request contains the exact phrase "You are being asked to produce code," and none
of your messages so far has. So I've done all the markdown (reversible drafts in
the shared folder) and stopped at the code line. When you want the `sapper.py` /
`arena.py` / tests / kb refactor executed, include that phrase and I'll do it on
the `claude/project-thread-va6ygw` branch as a reviewable PR.
