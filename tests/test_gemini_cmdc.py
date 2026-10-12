#!/usr/bin/env python3
"""Unit tests for ax gemini / cmdc providers using synthetic fixtures."""
import hashlib
import importlib.machinery as machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

import ax_test_support  # noqa: F401  (scrubs store-redirecting env vars)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_gemini_cmdc_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader(
            "ax_gemini_cmdc_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestGeminiCmdc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_gemini_cmdc_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        for src, dst in [("gemini", ".gemini"),
                         ("commandcode", ".commandcode")]:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        # gemini projectHash = sha256(cwd): resolve the placeholder dir name
        # to the hash of a real dir under the fake HOME
        gem_proj = os.path.join(cls.tmp, "gem-proj")
        os.makedirs(gem_proj, exist_ok=True)
        cls.gem_hash = hashlib.sha256(gem_proj.encode()).hexdigest()
        tmp_root = os.path.join(cls.tmp, ".gemini", "tmp")
        ph = os.path.join(tmp_root, "HASH_GEM_PROJ")
        if os.path.isdir(ph):
            os.rename(ph, os.path.join(tmp_root, cls.gem_hash))
        s1 = os.path.join(tmp_root, cls.gem_hash, "chats",
                          "session-2026-01-15T10-00-gem1.json")
        with open(s1) as fh:
            sj = json.load(fh)
        sj["projectHash"] = cls.gem_hash
        with open(s1, "w") as fh:
            json.dump(sj, fh)
        # pin cmdc session mtimes (epochs derive from mtime)
        p1 = os.path.join(
            cls.tmp, ".commandcode", "projects", "home-alice-cmdc-proj",
            "aaaabbbb-0000-0000-0000-0000000000c1.jsonl")
        p2 = os.path.join(
            cls.tmp, ".commandcode", "projects", "home-alice-cmdc-proj2",
            "bbbbcccc-0000-0000-0000-0000000000c2.jsonl")
        os.utime(p1, (1700000000, 1700000000))
        os.utime(p2, (1700000010, 1700000010))
        cls.mod = load_ax(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        os.chdir(cls._orig_cwd)
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

    # ---------------- gemini ----------------
    def test_list_gemini(self):
        rows = self.mod.list_gemini(50)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(len(rows), 2)  # stale checkpoint deduped
        self.assertEqual(set(by_id), {"gem-1", "gem-2"})
        self.assertEqual(by_id["gem-1"]["agent"], "gemini")
        self.assertEqual(by_id["gem-1"]["cwd"],
                         os.path.join(self.tmp, "gem-proj"))
        self.assertEqual(by_id["gem-1"]["title"],
                         "Refactor the gemini search")
        self.assertEqual(by_id["gem-1"]["epoch"],
                         self.mod._epoch_from_ts(
                             "2026-01-15T10:05:00.000Z", utc=True))
        # unresolvable hash falls back to "?"
        self.assertEqual(by_id["gem-2"]["cwd"], "?")

    def test_preview_gemini(self):
        text = self.mod.preview_gemini("gem-1")
        self.assertIn("--- gemini gem-1", text)
        self.assertIn("Refactor the gemini search", text)
        self.assertIn("I'll refactor the gemini search", text)
        # non user/gemini record types must not leak
        self.assertNotIn("internal notice", text)

    def test_preview_gemini_not_found(self):
        self.assertIn("not found", self.mod.preview_gemini("zzz"))

    def test_grep_gemini(self):
        rows = self.mod.grep_sessions("migration", ["gemini"], 50)
        self.assertEqual({r["id"] for r in rows}, {"gem-2"})

    def test_grep_gemini_info_excluded(self):
        rows = self.mod.grep_sessions("internal notice", ["gemini"], 50)
        self.assertEqual(rows, [])

    def test_lookup_gemini(self):
        row = self.mod._lookup_gemini("gem-1")
        self.assertEqual(row["cwd"], os.path.join(self.tmp, "gem-proj"))
        self.assertIsNone(self.mod._lookup_gemini("zzz"))

    def test_store_info_gemini(self):
        info = self.mod.store_info_gemini()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- cmdc ----------------
    def test_list_cmdc(self):
        by_id = {r["id"]: r for r in self.mod.list_cmdc(50)}
        self.assertEqual(set(by_id), {"cmdc-1", "cmdc-2"})
        self.assertEqual(by_id["cmdc-1"]["agent"], "cmdc")
        self.assertEqual(by_id["cmdc-1"]["cwd"], "/home/alice/cmdc-proj")
        self.assertEqual(by_id["cmdc-1"]["title"],
                         "Refactor the cmdc search")
        self.assertEqual(by_id["cmdc-1"]["epoch"], 1700000000)
        self.assertEqual(by_id["cmdc-2"]["cwd"], "/home/alice/cmdc-proj2")

    def test_preview_cmdc(self):
        text = self.mod.preview_cmdc("cmdc-1")
        self.assertIn("--- cmdc cmdc-1", text)
        self.assertIn("Refactor the cmdc search", text)
        self.assertIn("I'll refactor the cmdc search", text)
        # thinking / tool_result / compaction must not leak
        self.assertNotIn("internal thought", text)
        self.assertNotIn("should not leak", text)
        self.assertNotIn("compaction summary", text)

    def test_preview_cmdc_not_found(self):
        self.assertIn("not found", self.mod.preview_cmdc("zzz"))

    def test_cmdc_unique_prefix(self):
        """cmdc --session accepts a unique id prefix; ax does too."""
        text = self.mod.preview_cmdc("aaaabbbb-0000-0000-0000-0000000000c1")
        self.assertIn("Refactor the cmdc search", text)
        row = self.mod._lookup_cmdc("aaaabbbb")
        self.assertEqual(row["id"], "cmdc-1")

    def test_grep_cmdc(self):
        rows = self.mod.grep_sessions("migration", ["cmdc"], 50)
        self.assertEqual({r["id"] for r in rows}, {"cmdc-2"})

    def test_grep_cmdc_tool_result_excluded(self):
        rows = self.mod.grep_sessions("should not leak", ["cmdc"], 50)
        self.assertEqual(rows, [])
        rows = self.mod.grep_sessions("compaction summary", ["cmdc"], 50)
        self.assertEqual(rows, [])

    def test_lookup_cmdc(self):
        row = self.mod._lookup_cmdc("cmdc-1")
        self.assertEqual(row["cwd"], "/home/alice/cmdc-proj")
        self.assertIsNone(self.mod._lookup_cmdc("zzz"))

    def test_store_info_cmdc(self):
        info = self.mod.store_info_cmdc()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)


if __name__ == "__main__":
    unittest.main()
