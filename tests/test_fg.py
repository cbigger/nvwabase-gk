import contextlib
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import fg  # noqa: E402

SETTINGS_PATH = ROOT / "lib" / "_settings_patch.py"
_spec = importlib.util.spec_from_file_location("settings_patch_for_tests", SETTINGS_PATH)
settings_patch = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(settings_patch)


class GraphIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = fg.Store(Path(self.tmp.name) / ".fg")
        self.store.init("test", "ship it")

    def tearDown(self):
        self.tmp.cleanup()

    def test_corrupt_node_is_skipped_and_reported_by_validate(self):
        (self.store.facts_dir / "f001.json").write_text('{"id":"f001"}\n', encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rendered = fg.render_graph_text(self.store)
        self.assertIn("goal: ship it", rendered)
        self.assertIn("missing string 'description'", stderr.getvalue())
        errors = fg.validate_graph(self.store)
        self.assertTrue(any("f001.json" in error for error in errors))

    def test_init_refuses_non_empty_directory(self):
        root = Path(self.tmp.name) / "new-store"
        root.mkdir()
        (root / "unrelated.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(fg.FGError, "non-empty directory"):
            fg.Store(root).init("", "goal")
        self.assertTrue((root / "unrelated.txt").exists())

    def test_validate_detects_goal_metadata_drift(self):
        goal = self.store.facts_dir / "goal.json"
        data = json.loads(goal.read_text(encoding="utf-8"))
        data["description"] = "different goal"
        goal.write_text(json.dumps(data), encoding="utf-8")
        errors = fg.validate_graph(self.store)
        self.assertIn("goal fact description does not match project goal", errors)

    def test_validate_detects_intent_state_mismatch(self):
        seed = self.store.add_fact("seed", "test", None)
        intent = self.store.add_intent([seed["id"]], "work", "test")
        path = self.store.intents_dir / f"{intent['id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "done"
        path.write_text(json.dumps(data), encoding="utf-8")
        errors = fg.validate_graph(self.store)
        self.assertTrue(any("completed status requires a target" in error for error in errors))

    def test_confirmation_is_enforced_at_write_boundary(self):
        fact = self.store.add_fact("starting point", "test", None)
        intent = self.store.add_intent(
            [fact["id"]], "delete data", "test", requires_confirmation=True
        )
        with self.assertRaisesRegex(fg.FGError, "requires confirmation"):
            self.store.conclude_with_new_fact(intent["id"], "must not run", "test")
        self.store.confirm_intent(intent["id"])
        self.store.claim_intent(intent["id"], "owner")
        with self.assertRaisesRegex(fg.FGError, "claimed by owner"):
            self.store.conclude_with_new_fact(intent["id"], "wrong worker", "other")
        result, concluded = self.store.conclude_with_new_fact(
            intent["id"], "approval was recorded", "owner"
        )
        self.assertEqual(concluded["to"], result["id"])

    def test_lookup_ids_cannot_escape_store(self):
        with self.assertRaisesRegex(fg.FGError, "invalid fact id"):
            self.store.get_fact("../../outside")

    def test_stale_counter_never_overwrites_existing_node(self):
        first = self.store.add_fact("first", "test", None)
        project = self.store.load_project()
        project["counters"]["fact"] = 0
        self.store.save_project(project)
        second = self.store.add_fact("second", "test", None)
        self.assertEqual(first["id"], "f001")
        self.assertEqual(second["id"], "f002")
        self.assertEqual(self.store.get_fact("f001")["description"], "first")

    def test_fact_from_intent_closes_the_intent_atomically(self):
        seed = self.store.add_fact("seed", "test", None)
        intent = self.store.add_intent([seed["id"]], "observe", "test")
        fact = self.store.add_fact("observed", "test", intent["id"])
        self.assertEqual(self.store.get_intent(intent["id"])["to"], fact["id"])
        self.assertEqual(fg.validate_graph(self.store), [])

    def test_linking_existing_fact_sets_its_source_edge(self):
        seed = self.store.add_fact("seed", "test", None)
        result = self.store.add_fact("already observed", "test", None)
        intent = self.store.add_intent([seed["id"]], "link result", "test")
        self.store.conclude_intent(intent["id"], result["id"], "test")
        self.assertEqual(self.store.get_fact(result["id"])["source_intent"], intent["id"])
        self.assertEqual(fg.validate_graph(self.store), [])

    def test_pick_claim_skips_another_workers_lease(self):
        seed = self.store.add_fact("seed", "test", None)
        first = self.store.add_intent([seed["id"]], "first", "test")
        second = self.store.add_intent([seed["id"]], "second", "test")
        self.store.claim_intent(first["id"], "other-worker")
        args = type("Args", (), {
            "store": str(self.store.root), "claim": True,
            "worker": "my-worker", "any": False,
        })()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            fg.cmd_pick(args)
        self.assertEqual(output.getvalue().strip(), second["id"])

    def test_static_view_escapes_script_terminators(self):
        self.store.add_fact("</script><script>alert(1)</script>", "test", None)
        html = fg._render_static_html(self.store)
        self.assertNotIn("</script><script>", html)
        self.assertIn(r"\u003c/script\u003e", html)

    def test_prompt_substitution_does_not_rewrite_inserted_braces(self):
        self.store.add_fact("literal {goal} marker", "test", None)
        prompt = fg.render_prompt(self.store, "{graph_yaml}\nGOAL={goal}")
        self.assertIn("literal {goal} marker", prompt)
        self.assertTrue(prompt.endswith("GOAL=ship it"))

    def test_brainstorm_template_token_does_not_rewrite_graph_text(self):
        self.store.add_fact("literal {max_options} marker", "test", None)
        args = type("Args", (), {
            "max_options": 2, "dry_run": True,
        })()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            fg._dispatch_brainstorm(
                self.store, ROOT / "templates", "sonnet", 10, False, ROOT, args
            )
        self.assertIn("literal {max_options} marker", output.getvalue())

    def test_verify_payload_requires_actionable_issues_on_failure(self):
        with self.assertRaisesRegex(fg.FGError, "explain"):
            fg._parse_verify_payload({"verified": False, "issues": ""})
        with self.assertRaisesRegex(fg.FGError, "leave 'issues' empty"):
            fg._parse_verify_payload({"verified": True, "issues": "warning"})

    def test_dispatch_verify_returns_failure_status(self):
        seed = self.store.add_fact("seed", "test", None)
        intent = self.store.add_intent([seed["id"]], "check", "test")
        result, _ = self.store.conclude_with_new_fact(intent["id"], "result", "test")
        args = type("Args", (), {
            "intent": intent["id"], "dry_run": False,
        })()
        with mock.patch.object(
            fg,
            "run_claude",
            return_value={"result": '{"accepted": true, "data": {"verified": false, "issues": "mismatch"}}'},
        ):
            rc = fg._dispatch_verify(
                self.store, ROOT / "templates", "sonnet", 10, False, ROOT, args
            )
        self.assertEqual(rc, 1)

    def test_completed_graph_validates_and_duplicate_completion_is_rejected(self):
        fact = self.store.add_fact("evidence", "test", None)
        self.store.complete_project([fact["id"]], "finish", "test")
        self.assertEqual(self.store.load_project()["status"], "completed")
        self.assertEqual(fg.validate_graph(self.store), [])
        with self.assertRaisesRegex(fg.FGError, "already completed"):
            self.store.complete_project([fact["id"]], "finish again", "test")

    def test_brainstorm_batches_are_unique(self):
        seed = self.store.add_fact("seed", "test", None)
        payload = {
            "accepted": True,
            "data": {
                "options": [
                    {"from": [seed["id"]], "title": "one", "description": "first"}
                ]
            },
        }
        fg._apply_brainstorm(self.store, payload)
        fg._apply_brainstorm(self.store, payload)
        docs = [i["doc"] for i in self.store.list_intents()]
        self.assertEqual(len(docs), 2)
        tags = [line for doc in docs for line in doc.splitlines() if line.startswith("[brainstorm batch:")]
        self.assertEqual(len(set(tags)), 2)

    def test_brainstorm_pick_preserves_abandoned_edges(self):
        seed = self.store.add_fact("seed", "test", None)
        payload = {
            "accepted": True,
            "data": {"options": [
                {"from": [seed["id"]], "title": "one", "description": "first"},
                {"from": [seed["id"]], "title": "two", "description": "second"},
            ]},
        }
        fg._apply_brainstorm(self.store, payload)
        picked = self.store.list_intents()[0]
        args = type("Args", (), {"store": str(self.store.root), "id": picked["id"], "purge": False})()
        fg.cmd_brainstorm_pick(args)
        intents = self.store.list_intents()
        self.assertEqual(sum(i["to"] is None for i in intents), 1)
        self.assertEqual(sum(i["to"] is not None for i in intents), 1)
        self.assertEqual(fg.validate_graph(self.store), [])


class SettingsPatchTests(unittest.TestCase):
    def test_settings_patch_is_atomic_and_preserves_unrelated_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(
                json.dumps({"hooks": {"SessionStart": [{"matcher": "x", "hooks": [
                    {"type": "command", "command": "echo keep"
                    }
                ]}]}}),
                encoding="utf-8",
            )
            changed, _ = settings_patch.add(path, "/tmp/fg-hook.py")
            self.assertTrue(changed)
            data = json.loads(path.read_text(encoding="utf-8"))
            commands = [
                h["command"]
                for groups in data["hooks"].values()
                for group in groups
                for h in group.get("hooks", [])
            ]
            self.assertIn("echo keep", commands)
            self.assertEqual(sum("fg-hook.py" in command for command in commands), 2)
            settings_patch.remove(path, "/tmp/fg-hook.py")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["hooks"]["SessionStart"][0]["hooks"][0]["command"], "echo keep")

    def test_settings_patch_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                settings_patch.add(path, "/tmp/fg-hook.py")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                settings_patch.remove(path, "/tmp/fg-hook.py")

    def test_settings_validation_catches_malformed_event_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"hooks": {"SessionStart": {}}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hooks.SessionStart"):
                settings_patch.validate(path)


class PeerConfigTests(unittest.TestCase):
    def test_malformed_peer_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fg.Store(Path(tmp) / ".fg")
            store.init("", "peers")
            (store.root / fg.PEERS_FILE).write_text(
                json.dumps({"version": 1, "channel": "x", "peers": {"bad name": {"target": "x"}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(fg.FGError, "invalid peer name"):
                fg._load_peers(store)

    def test_setup_preflights_invalid_settings_before_creating_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".claude").mkdir()
            (project / ".claude" / "settings.json").write_text("[]", encoding="utf-8")
            old_cwd = Path.cwd()
            try:
                import os
                os.chdir(project)
                args = type("Args", (), {
                    "store": ".fg", "goal": "should not initialize",
                    "origin": "", "agents": False, "force": False,
                })()
                with self.assertRaisesRegex(fg.FGError, "JSON object"):
                    fg.cmd_setup(args)
            finally:
                os.chdir(old_cwd)
            self.assertFalse((project / ".fg" / "project.json").exists())


class TierTests(unittest.TestCase):
    def test_default_map_resolves_every_role_to_default_model(self):
        cfg = fg.load_tier_config(raw=None)
        for role in ("commander", "senior", "verifier", "worker", "scout", "chore"):
            self.assertEqual(
                fg.resolve_model(cfg, role=role), fg._default_model(),
                f"role {role} should resolve to the default model with no config",
            )

    def test_fg_model_env_sets_the_default(self):
        with mock.patch.dict(fg.os.environ, {"FG_MODEL": "my-model"}, clear=False):
            cfg = fg.load_tier_config(raw=None)
            self.assertEqual(fg.resolve_model(cfg, role="worker"), "my-model")

    def test_configured_map_routes_roles_to_tiers(self):
        raw = json.dumps({
            "tiers": {"strong": {"model": "opus"}, "cheap": {"model": "haiku"}},
        })
        cfg = fg.load_tier_config(raw=raw)
        self.assertEqual(fg.resolve_model(cfg, role="commander"), "opus")
        self.assertEqual(fg.resolve_model(cfg, role="verifier"), "opus")
        self.assertEqual(fg.resolve_model(cfg, role="worker"), "haiku")
        self.assertEqual(fg.resolve_model(cfg, role="scout"), "haiku")

    def test_explicit_model_and_tier_override_role(self):
        raw = json.dumps({"tiers": {"strong": {"model": "opus"}, "cheap": {"model": "haiku"}}})
        cfg = fg.load_tier_config(raw=raw)
        self.assertEqual(fg.resolve_model(cfg, role="worker", model="forced"), "forced")
        self.assertEqual(fg.resolve_model(cfg, role="worker", tier="strong"), "opus")

    def test_default_role_is_worker(self):
        raw = json.dumps({"tiers": {"strong": {"model": "opus"}, "cheap": {"model": "haiku"}}})
        cfg = fg.load_tier_config(raw=raw)
        self.assertEqual(fg.resolve_tier(cfg), "cheap")
        self.assertEqual(fg.resolve_model(cfg), "haiku")

    def test_partial_tier_config_keeps_default_model(self):
        # adding only an endpoint to strong must not drop its default model
        raw = json.dumps({"tiers": {"strong": {"base_url": "https://x/v1"}}})
        cfg = fg.load_tier_config(raw=raw)
        self.assertEqual(fg.resolve_model(cfg, tier="strong"), fg._default_model())
        self.assertEqual(fg.tier_connection(cfg, "strong"), {"base_url": "https://x/v1"})

    def test_unknown_role_and_tier_error(self):
        cfg = fg.load_tier_config(raw="{}")
        with self.assertRaisesRegex(fg.FGError, "unknown role"):
            fg.resolve_tier(cfg, role="nope")
        with self.assertRaisesRegex(fg.FGError, "unknown tier"):
            fg.resolve_tier(cfg, tier="nope")

    def test_invalid_json_and_non_object_error(self):
        with self.assertRaisesRegex(fg.FGError, "invalid tier config JSON"):
            fg.load_tier_config(raw="{not json")
        with self.assertRaisesRegex(fg.FGError, "must be a JSON object"):
            fg.load_tier_config(raw="[1,2,3]")

    def test_tier_with_empty_model_rejected(self):
        with self.assertRaisesRegex(fg.FGError, "non-empty model"):
            fg.load_tier_config(raw=json.dumps({"tiers": {"cheap": {"model": ""}}}))

    def test_config_from_file_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tiers.json"
            p.write_text(json.dumps({"tiers": {"cheap": {"model": "from-file"}}}), encoding="utf-8")
            cfg = fg.load_tier_config(raw=str(p))
            self.assertEqual(fg.resolve_model(cfg, role="worker"), "from-file")

    def test_missing_config_file_errors(self):
        with self.assertRaisesRegex(fg.FGError, "tier config file not found"):
            fg.load_tier_config(raw="/no/such/tiers.json")

    def test_strong_cap_default_and_override(self):
        self.assertEqual(fg.strong_cap(fg.load_tier_config(raw="{}")), 3)
        cfg = fg.load_tier_config(raw=json.dumps({"limits": {"max_strong_concurrent": 1}}))
        self.assertEqual(fg.strong_cap(cfg), 1)

    def test_can_spawn_enforces_strong_cap(self):
        raw = json.dumps({"limits": {"max_strong_concurrent": 2}})
        env = {"FG_TIERS": raw}
        with mock.patch.dict(fg.os.environ, env, clear=False):
            under = type("A", (), {"tier_action": "can-spawn", "role": "commander",
                                   "tier": None, "model": None, "active_strong": 1})()
            self.assertEqual(fg.cmd_tier(under), 0)
            at_cap = type("A", (), {"tier_action": "can-spawn", "role": "commander",
                                    "tier": None, "model": None, "active_strong": 2})()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = fg.cmd_tier(at_cap)
            self.assertEqual(rc, 3)
            self.assertIn("strong-tier cap reached", stderr.getvalue())
            # cheap tier is never capped
            cheap = type("A", (), {"tier_action": "can-spawn", "role": "worker",
                                   "tier": None, "model": None, "active_strong": 99})()
            self.assertEqual(fg.cmd_tier(cheap), 0)


if __name__ == "__main__":
    unittest.main()
