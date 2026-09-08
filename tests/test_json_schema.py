#!/usr/bin/env python3
"""Tests for --json schema contract and SKILL.md documentation."""
import importlib.machinery as machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_schema_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_schema_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestJsonSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_schema_test_home_")
        for src, dst in [("claude", ".claude"), ("codex", ".codex"),
                         ("gemini", ".gemini"), ("local", ".local")]:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        cls.mod = load_ax(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        shutil.rmtree(cls.tmp)

    def _capture_stdout(self, fn, *args, **kwargs):
        old = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            result = fn(*args, **kwargs)
        finally:
            sys.stdout = old
        return result, buf.getvalue()

    def test_list_json_has_all_required_keys(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--json"])
        rows = json.loads(out)
        self.assertIsInstance(rows, list)
        self.assertTrue(rows)
        required = {"agent", "id", "epoch", "cwd", "title"}
        for r in rows:
            missing = required - set(r)
            self.assertFalse(missing, f"list row missing keys: {missing}: {r!r}")
            self.assertIn(r["agent"], self.mod.ALL_AGENTS)
            self.assertIsInstance(r["id"], str)
            self.assertIsInstance(r["epoch"], int)
            self.assertIsInstance(r["cwd"], str)
            self.assertIsInstance(r["title"], str)

    def test_list_json_empty_is_valid_array(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--json", "--agent", "no-such-agent"])
        rows = json.loads(out)
        self.assertEqual(rows, [])

    def test_list_grep_json_has_match_field(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--json", "--grep", "Refactor"])
        rows = json.loads(out)
        self.assertTrue(rows)
        required = {"agent", "id", "epoch", "cwd", "title", "match"}
        for r in rows:
            missing = required - set(r)
            self.assertFalse(missing, f"grep row missing keys: {missing}: {r!r}")
            self.assertIsInstance(r["match"], str)
            self.assertNotIn("\t", r["match"])
            self.assertNotIn("\n", r["match"])

    def test_preview_json_has_all_required_keys(self):
        _, out = self._capture_stdout(self.mod.cmd_preview, ["claude", "sess-c1a2b3", "--json"])
        obj = json.loads(out)
        required = {"agent", "id", "preview"}
        missing = required - set(obj)
        self.assertFalse(missing, f"preview missing keys: {missing}: {obj!r}")
        self.assertEqual(obj["agent"], "claude")
        self.assertEqual(obj["id"], "sess-c1a2b3")
        self.assertIsInstance(obj["preview"], str)

    def test_preview_json_not_found_still_has_schema(self):
        _, out = self._capture_stdout(self.mod.cmd_preview, ["claude", "no-such-id", "--json"])
        obj = json.loads(out)
        self.assertIn("preview", obj)
        self.assertIsInstance(obj["preview"], str)
        self.assertIn("not found", obj["preview"].lower())

    def test_skill_md_exists_and_documents_schema(self):
        skill = os.path.join(REPO_ROOT, ".agents", "skills", "ax", "SKILL.md")
        self.assertTrue(os.path.isfile(skill), f"SKILL.md not found: {skill}")
        text = open(skill, encoding="utf-8").read()
        self.assertIn("name: ax", text)
        for k in ("agent", "id", "epoch", "cwd", "title", "match", "preview"):
            self.assertIn(k, text, f"SKILL.md does not document key: {k}")
        for cmd in ("ax list --json", "ax preview --json", "ax resume"):
            self.assertIn(cmd, text, f"SKILL.md does not mention: {cmd}")


if __name__ == "__main__":
    unittest.main()
