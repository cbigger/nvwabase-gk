# Self-management: state file + watchdog

The concrete mechanism behind the commander doctrine's §5 (self-management) and
§6 (failure awareness). Two pieces: a durable **state file** for continuity and
a **watchdog** for liveness.

## The state file

`fleet command --loop` persists `<fleet>/commander-state.json` every cycle:

```json
{"iterations": 7, "history": [{"cycle": 7, "action": "hire", "target": "u03", "note": "fresh lead"}], "stopped": false, "stop_reason": ""}
```

On start the loop *reads* this file, so a relaunched commander resumes its
iteration count and recent decision history instead of starting cold — the
"commander resumes as its own successor" behavior. `history` is trimmed to the
last 20 decisions to stay small.

This is the machine-maintained counterpart to the doctrine's STATE.md, which an
LLM commander keeps in prose (allocation table, parked list, intel log, queue).
Use both: STATE.md for the reasoning, `commander-state.json` for the loop's
bookkeeping.

## The watchdog

`watchdog.sh` keeps the commander loop alive until a deadline. The commander
owns the tempo; the watchdog owns the buzzer:

```
WATCHDOG_DEADLINE_MIN=90 FLEET_ROOT=.fleet ./watchdog.sh
```

- Relaunches a crashed commander until `WATCHDOG_DEADLINE_MIN`, recomputing the
  remaining deadline each relaunch so the overall budget is honored.
- Exits without relaunching on a clean stop (rc 0) or a commander stop decision
  (rc 10).
- `WATCHDOG_ROTATE_HOOK` runs after a crash — wire it to rotate `FG_TIERS` keys
  or swap to a backup provider pool (doctrine Part B), so a quota/auth wall
  becomes a reroute rather than a halt. Continuity is preserved by the shared
  graphs and the state file.

Nothing here is domain-specific; it is the same keep-alive loop for any fleet.
