# Unattended fleet: state file + watchdog

The concrete mechanism behind the unattended allocation loop (`nvwa fleet
command --loop`, [quickstart §5](../docs/quickstart.md)). Two pieces: a durable
**state file** for continuity and a **watchdog** for liveness. This is the
scripted allocator, not the agentic commander of
[commander-doctrine.md](commander-doctrine.md) — the doctrine's STATE.md is the
prose counterpart an LLM commander keeps by hand.

## The state file

`nvwa fleet command --loop` persists `<fleet>/commander-state.json` every cycle:

```json
{"iterations": 7, "history": [{"cycle": 7, "action": "hire", "target": "u03", "note": "fresh lead"}], "stopped": false, "stop_reason": ""}
```

On start the loop *reads* this file, so a relaunched loop resumes its iteration
count and recent decision history instead of starting cold. `history` is trimmed
to the last 20 decisions to stay small.

## The watchdog

`watchdog.sh` keeps the allocation loop alive until a deadline. The loop owns the
tempo; the watchdog owns the buzzer:

```
WATCHDOG_DEADLINE_MIN=90 FLEET_ROOT=.fleet ./watchdog.sh
```

- Relaunches a crashed loop until `WATCHDOG_DEADLINE_MIN`, recomputing the
  remaining deadline each relaunch so the overall budget is honored.
- Exits without relaunching on a clean stop (rc 0) or a stop decision (rc 10).
- `WATCHDOG_ROTATE_HOOK` runs after a crash — wire it to rotate `FG_TIERS` keys
  or swap to a backup provider pool, so a quota/auth wall becomes a reroute
  rather than a halt. Continuity is preserved by the shared graphs and the state
  file.

Nothing here is domain-specific; it is the same keep-alive loop for any fleet.
