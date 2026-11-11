import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import kb  # noqa: E402


class KBTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = kb.KB(Path(self.tmp.name) / "kb")

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_get_list_roundtrip(self):
        e = self.kb.add("Build Checklist", body="step one", tags=["build", "ci"])
        self.assertEqual(e["id"], "build-checklist")
        got = self.kb.get("build-checklist")
        self.assertEqual(got["title"], "Build Checklist")
        self.assertEqual(got["tags"], ["build", "ci"])
        self.assertEqual([x["id"] for x in self.kb.list()], ["build-checklist"])

    def test_add_explicit_id_and_overwrite_guard(self):
        self.kb.add("A", entry_id="x", body="first")
        with self.assertRaisesRegex(kb.KBError, "already exists"):
            self.kb.add("A2", entry_id="x")
        self.kb.add("A2", entry_id="x", overwrite=True, body="second")
        self.assertEqual(self.kb.get("x")["body"], "second")

    def test_empty_title_and_bad_tags_rejected(self):
        with self.assertRaisesRegex(kb.KBError, "title cannot be empty"):
            self.kb.add("   ")
        with self.assertRaisesRegex(kb.KBError, "tags must be a list"):
            self.kb.add("t", tags="nope")  # type: ignore[arg-type]

    def test_invalid_id_rejected(self):
        with self.assertRaisesRegex(kb.KBError, "invalid entry id"):
            self.kb.get("../etc/passwd")

    def test_search_ranks_title_over_body(self):
        self.kb.add("Cache benchmark", tags=["perf"], body="measure throughput")
        self.kb.add("Noise", body="a cache is mentioned once in the body")
        results = self.kb.search("cache")
        self.assertEqual(results[0]["id"], "cache-benchmark")  # title hit wins
        self.assertEqual(results[0]["score"], 3)

    def test_search_empty_query_returns_nothing(self):
        self.kb.add("x", body="y")
        self.assertEqual(self.kb.search("   "), [])

    def test_search_limit(self):
        for i in range(5):
            self.kb.add(f"source entry {i}", body="source")
        self.assertEqual(len(self.kb.search("source", limit=2)), 2)

    def test_damaged_entry_is_skipped_not_fatal(self):
        self.kb.add("good", body="findable token zebra")
        (self.kb.entries_dir / "broken.json").write_text("{not json", encoding="utf-8")
        # list and search tolerate the broken file
        self.assertEqual([e["id"] for e in self.kb.list()], ["good"])
        self.assertEqual(self.kb.search("zebra")[0]["id"], "good")

    def test_resolve_root_precedence(self):
        self.assertEqual(kb.resolve_kb_root("/explicit"), Path("/explicit"))
        with mock.patch.dict(kb.os.environ, {"FG_KB": "/from/env"}, clear=False):
            self.assertEqual(kb.resolve_kb_root(None), Path("/from/env"))
        with mock.patch.dict(kb.os.environ, {}, clear=True):
            self.assertEqual(kb.resolve_kb_root(None), ROOT / "kb")


class ShippedEntriesTests(unittest.TestCase):
    def test_repo_kb_loads_cleanly(self):
        # The base ships no domain entries; the shipped KB must still load.
        store = kb.KB(ROOT / "kb")
        self.assertIsInstance(store.list(), list)


if __name__ == "__main__":
    unittest.main()
