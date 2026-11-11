import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import fg       # noqa: E402
import fleet    # noqa: E402


def _init_unit(fleet_root: Path, name: str, goal: str) -> fleet.Unit:
    fleet.cmd_init(argparse.Namespace(
        fleet=str(fleet_root), name=name, goal=goal, origin="",
    ))
    return fleet.Fleet(fleet_root).unit(name)


class FleetModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".fleet"

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_and_discovery(self):
        _init_unit(self.root, "u02", "second")
        _init_unit(self.root, "u01", "first")
        names = [u.name for u in fleet.Fleet(self.root).units()]
        self.assertEqual(names, ["u01", "u02"])  # sorted

    def test_empty_fleet_has_no_units(self):
        self.assertEqual(fleet.Fleet(self.root).units(), [])

    def test_board_counts_reflect_graph(self):
        u = _init_unit(self.root, "u01", "triage alert")
        seed = u.store.add_fact("web-01 has the alerted process", "test", None)
        u.store.add_intent([seed["id"]], "pull auth logs", "test")
        board = fleet.Fleet(self.root).board("60m")
        self.assertEqual(board["budget_left"], "60m")
        row = board["units"][0]
        self.assertEqual(row["unit"], "u01")
        self.assertEqual(row["open_intents"], 1)
        self.assertEqual(row["ready"], 1)
        self.assertEqual(row["worker"], "-")
        self.assertFalse(row["completed"])

    def test_render_board_includes_units_and_budget(self):
        _init_unit(self.root, "u01", "triage alert on web-01")
        text = fleet.Fleet(self.root).render_board("30m")
        self.assertIn("budget_left: 30m", text)
        self.assertIn("u01", text)
        self.assertIn("triage alert on web-01", text)

    def test_state_roundtrip(self):
        f = fleet.Fleet(self.root)
        f.save_state({"workers": {"u01": {"since": 1}}})
        self.assertEqual(f.load_state()["workers"], {"u01": {"since": 1}})

    def test_invalid_state_rejected(self):
        self.root.mkdir(parents=True)
        (self.root / fleet.STATE_NAME).write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(fleet.FleetError, "invalid fleet state"):
            fleet.Fleet(self.root).load_state()


class ParseDecisionTests(unittest.TestCase):
    def test_work_hire_fire_ok(self):
        for action in ("work", "hire", "fire"):
            d = fleet._parse_decision({"accepted": True, "data": {
                "action": action, "target": "u03", "note": "n"}})
            self.assertEqual(d["action"], action)
            self.assertEqual(d["target"], "u03")

    def test_stop_bare_and_nested(self):
        self.assertEqual(fleet._parse_decision({"action": "stop", "reason": "done"})["action"], "stop")
        self.assertEqual(
            fleet._parse_decision({"accepted": True, "data": {"action": "stop"}})["action"], "stop")

    def test_rejected_payload_errors(self):
        with self.assertRaisesRegex(fleet.FleetError, "rejected"):
            fleet._parse_decision({"accepted": False, "reason": "bad input"})

    def test_unknown_action_errors(self):
        with self.assertRaisesRegex(fleet.FleetError, "unknown action"):
            fleet._parse_decision({"accepted": True, "data": {"action": "nuke", "target": "u1"}})

    def test_missing_target_errors(self):
        with self.assertRaisesRegex(fleet.FleetError, "needs a target"):
            fleet._parse_decision({"accepted": True, "data": {"action": "work"}})


class CommandStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".fleet"
        _init_unit(self.root, "u01", "triage alert")
        _init_unit(self.root, "u02", "reconstruct timeline")
        self.fleet = fleet.Fleet(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _mock_claude(self, decision: dict):
        return mock.patch.object(
            fleet.fg, "run_claude",
            return_value={"result": json.dumps(decision), "is_error": False},
        )

    def test_hire_records_worker_and_spawns(self):
        decision = {"accepted": True, "data": {"action": "hire", "target": "u01", "note": "lead"}}
        with self._mock_claude(decision), \
             mock.patch.object(fleet, "spawn_worker") as spawn:
            out = self.fleet  # noqa
            d = fleet.command_step(self.fleet)
        self.assertEqual(d["action"], "hire")
        spawn.assert_called_once()
        self.assertIn("u01", self.fleet.load_state()["workers"])

    def test_hire_twice_is_noop(self):
        self.fleet.save_state({"workers": {"u01": {"since": 1}}})
        decision = {"accepted": True, "data": {"action": "hire", "target": "u01"}}
        with self._mock_claude(decision), \
             mock.patch.object(fleet, "spawn_worker") as spawn:
            fleet.command_step(self.fleet)
        spawn.assert_not_called()

    def test_fire_removes_worker_and_kills(self):
        self.fleet.save_state({"workers": {"u02": {"since": 1}}})
        decision = {"accepted": True, "data": {"action": "fire", "target": "u02"}}
        with self._mock_claude(decision), \
             mock.patch.object(fleet, "kill_worker") as kill:
            d = fleet.command_step(self.fleet)
        self.assertEqual(d["action"], "fire")
        kill.assert_called_once_with("u02")
        self.assertNotIn("u02", self.fleet.load_state()["workers"])

    def test_work_runs_a_slice(self):
        decision = {"accepted": True, "data": {"action": "work", "target": "u01", "minutes": 20}}
        with self._mock_claude(decision), \
             mock.patch.object(fleet, "run_unit_slice") as slice_:
            d = fleet.command_step(self.fleet)
        self.assertEqual(d["action"], "work")
        slice_.assert_called_once()
        self.assertEqual(slice_.call_args.args[0].name, "u01")

    def test_stop_decision(self):
        with self._mock_claude({"action": "stop", "reason": "all done"}):
            d = fleet.command_step(self.fleet)
        self.assertEqual(d["action"], "stop")

    def test_unknown_target_errors(self):
        decision = {"accepted": True, "data": {"action": "work", "target": "u99"}}
        with self._mock_claude(decision):
            with self.assertRaisesRegex(fleet.FleetError, "unknown unit"):
                fleet.command_step(self.fleet)

    def test_empty_fleet_errors(self):
        empty = fleet.Fleet(Path(self.tmp.name) / "nope")
        with self.assertRaisesRegex(fleet.FleetError, "empty"):
            fleet.command_step(empty)


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / ".fleet"

    def tearDown(self):
        self.tmp.cleanup()

    def test_sweep_skips_completed_units(self):
        u1 = _init_unit(self.root, "u01", "done unit")
        _init_unit(self.root, "u02", "open unit")
        seed = u1.store.add_fact("done", "test", None)
        u1.store.complete_project([seed["id"]], "finished", "test")
        with mock.patch.object(fleet, "run_unit_slice") as slice_:
            fleet.sweep(fleet.Fleet(self.root), rounds=1)
        sliced = [c.args[0].name for c in slice_.call_args_list]
        self.assertEqual(sliced, ["u02"])

    def test_sweep_empty_fleet_errors(self):
        with self.assertRaisesRegex(fleet.FleetError, "empty"):
            fleet.sweep(fleet.Fleet(self.root))


if __name__ == "__main__":
    unittest.main()
