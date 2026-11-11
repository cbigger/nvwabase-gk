#!/usr/bin/env bash
# watchdog — keep the fleet commander loop alive until a deadline.
#
# The commander (`fleet command --loop`) owns the tempo; the watchdog owns the
# buzzer. It relaunches a crashed commander until the overall deadline, so the
# commander "resumes as its own successor" — continuity comes from the
# commander-state.json the loop persists each cycle (doctrine §5). On a clean
# stop (the commander decided to stop) it exits without relaunching.
#
# Exit codes it reads from `fleet command --loop`:
#   0  loop ended cleanly (max-cycles / deadline)  -> stop
#   10 commander signalled a stop decision         -> stop
#   *  crash                                        -> relaunch until deadline
#
# Env:
#   FLEET_ROOT              fleet dir (default: .fleet)
#   WATCHDOG_DEADLINE_MIN   overall deadline in minutes (default: 60)
#   WATCHDOG_INTERVAL       seconds between commander cycles (default: 30)
#   WATCHDOG_MAX_RESTARTS   give up after this many crashes (default: 100)
#   WATCHDOG_ROTATE_HOOK    shell run after a crash (e.g. rotate FG_TIERS keys)
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
FLEET="${FLEET_ROOT:-.fleet}"
DEADLINE_MIN="${WATCHDOG_DEADLINE_MIN:-60}"
INTERVAL="${WATCHDOG_INTERVAL:-30}"
MAX_RESTARTS="${WATCHDOG_MAX_RESTARTS:-100}"

log() { printf '[watchdog] %s\n' "$*" >&2; }

end=$(( $(date +%s) + DEADLINE_MIN * 60 ))
restarts=0

while (( $(date +%s) < end )); do
  remaining_min=$(( (end - $(date +%s)) / 60 + 1 ))
  log "launching commander (remaining ~${remaining_min}m, restart #${restarts})"
  python3 "$SCRIPT_DIR/lib/fleet.py" command --fleet "$FLEET" --loop \
    --interval "$INTERVAL" --deadline-min "$remaining_min"
  rc=$?
  case $rc in
    10) log "commander signalled stop — done"; exit 0 ;;
    0)  log "commander loop exited cleanly — done"; exit 0 ;;
    *)  restarts=$(( restarts + 1 ))
        log "commander died (rc=$rc), relaunch #${restarts}"
        if (( restarts >= MAX_RESTARTS )); then
          log "max restarts (${MAX_RESTARTS}) reached — giving up"
          exit 1
        fi
        if [[ -n "${WATCHDOG_ROTATE_HOOK:-}" ]]; then
          log "running rotate hook"
          eval "$WATCHDOG_ROTATE_HOOK" || log "rotate hook failed (continuing)"
        fi
        sleep 2 ;;
  esac
done

log "deadline (${DEADLINE_MIN}m) reached — stopping"
exit 0
