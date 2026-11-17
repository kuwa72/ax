#!/usr/bin/env python3
"""Unit tests for ax cline / tau / continue / kilo / mimo / codewhale /
gptme / jcode / dsh providers using synthetic fixtures."""
import importlib.machinery as machinery
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

import ax_test_support  # noqa: F401  (scrubs store-redirecting env vars)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

try:
    import compression.zstd  # noqa: F401
    HAVE_ZSTD = True
except ImportError:
    HAVE_ZSTD = False


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_batch2_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader(
            "ax_batch2_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestBatch2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_batch2_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        for src, dst in [("cline", ".cline"), ("tau", ".tau"),
                         ("continue", ".continue"),
                         ("kilo", os.path.join(".local", "share", "kilo")),
                         ("mimocode", os.path.join(".local", "share",
                                                   "mimocode")),
                         ("codewhale", ".codewhale"),
                         ("gptme", os.path.join(".local", "share", "gptme")),
                         ("jcode", ".jcode"), ("dsh", ".dsh")]:
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

    # ---------------- cline ----------------
    def test_list_cline(self):
        by_id = {r["id"]: r for r in self.mod.list_cline(50)}
        self.assertEqual(set(by_id), {"1793000000000_c1", "1792990000000_c2"})
        self.assertEqual(by_id["1793000000000_c1"]["agent"], "cline")
        self.assertEqual(by_id["1793000000000_c1"]["cwd"],
                         "/home/alice/cline-proj")
        self.assertEqual(by_id["1793000000000_c1"]["title"],
                         "Refactor the cline search")

    def test_preview_cline(self):
        text = self.mod.preview_cline("1793000000000_c1")
        self.assertIn("--- cline 1793000000000_c1", text)
        self.assertIn("Refactor the cline search", text)
        self.assertIn("I'll refactor the cline search", text)
        self.assertNotIn("should not leak", text)
        self.assertNotIn("user_input", text)

    def test_preview_cline_not_found(self):
        self.assertIn("not found", self.mod.preview_cline("zzz"))

    def test_grep_cline(self):
        rows = self.mod.grep_sessions("migration", ["cline"], 50)
        self.assertEqual({r["id"] for r in rows}, {"1792990000000_c2"})
        rows = self.mod.grep_sessions("should not leak", ["cline"], 50)
        self.assertEqual(rows, [])

    def test_lookup_cline(self):
        self.assertEqual(self.mod._lookup_cline("1793000000000_c1")["cwd"],
                         "/home/alice/cline-proj")
        self.assertIsNone(self.mod._lookup_cline("zzz"))

    def test_store_info_cline(self):
        info = self.mod.store_info_cline()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- tau ----------------
    def test_list_tau(self):
        by_id = {r["id"]: r for r in self.mod.list_tau(50)}
        self.assertEqual(set(by_id), {"tau-1", "tau-2"})
        self.assertEqual(by_id["tau-1"]["cwd"], "/home/alice/tau-proj")
        self.assertEqual(by_id["tau-1"]["title"], "Refactor the tau search")
        self.assertEqual(by_id["tau-1"]["epoch"], 1700000300)
        self.assertEqual(by_id["tau-2"]["title"], "Plan the migration")

    def test_preview_tau(self):
        text = self.mod.preview_tau("tau-1")
        self.assertIn("--- tau tau-1", text)
        self.assertIn("Refactor the tau search", text)
        self.assertIn("I'll refactor the tau search", text)
        self.assertNotIn("should not leak", text)

    def test_preview_tau_not_found(self):
        self.assertIn("not found", self.mod.preview_tau("zzz"))

    def test_grep_tau(self):
        rows = self.mod.grep_sessions("migration", ["tau"], 50)
        self.assertEqual({r["id"] for r in rows}, {"tau-2"})
        rows = self.mod.grep_sessions("should not leak", ["tau"], 50)
        self.assertEqual(rows, [])

    def test_lookup_tau(self):
        self.assertEqual(self.mod._lookup_tau("tau-1")["cwd"],
                         "/home/alice/tau-proj")
        self.assertIsNone(self.mod._lookup_tau("zzz"))

    def test_store_info_tau(self):
        info = self.mod.store_info_tau()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- continue ----------------
    def test_list_continue(self):
        by_id = {r["id"]: r for r in self.mod.list_continue(50)}
        self.assertEqual(set(by_id), {"cont-1", "cont-2"})
        self.assertEqual(by_id["cont-1"]["cwd"],
                         "/home/alice/continue-proj")
        self.assertEqual(by_id["cont-1"]["title"],
                         "Refactor the continue search")

    def test_preview_continue(self):
        text = self.mod.preview_continue("cont-1")
        self.assertIn("--- continue cont-1", text)
        self.assertIn("Refactor the continue search", text)
        self.assertIn("I'll refactor the continue search", text)

    def test_preview_continue_not_found(self):
        self.assertIn("not found", self.mod.preview_continue("zzz"))

    def test_grep_continue(self):
        rows = self.mod.grep_sessions("migration", ["continue"], 50)
        self.assertEqual({r["id"] for r in rows}, {"cont-2"})

    def test_lookup_continue(self):
        self.assertEqual(self.mod._lookup_continue("cont-1")["cwd"],
                         "/home/alice/continue-proj")
        self.assertIsNone(self.mod._lookup_continue("zzz"))

    def test_store_info_continue(self):
        info = self.mod.store_info_continue()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- kilo ----------------
    def test_list_kilo(self):
        by_id = {r["id"]: r for r in self.mod.list_kilo(50)}
        self.assertEqual(set(by_id), {"kilo-1", "kilo-2"})
        self.assertEqual(by_id["kilo-1"]["cwd"], "/home/alice/kilo-proj")
        self.assertEqual(by_id["kilo-1"]["title"],
                         "Refactor the kilo search")
        self.assertEqual(by_id["kilo-1"]["epoch"], 1700000300)

    def test_preview_kilo(self):
        text = self.mod.preview_kilo("kilo-1")
        self.assertIn("--- kilo kilo-1", text)
        self.assertIn("Refactor the kilo search", text)
        self.assertIn("I'll refactor the kilo search", text)
        self.assertNotIn("should not leak", text)

    def test_preview_kilo_not_found(self):
        self.assertIn("not found", self.mod.preview_kilo("zzz"))

    def test_grep_kilo(self):
        rows = self.mod.grep_sessions("migration", ["kilo"], 50)
        self.assertEqual({r["id"] for r in rows}, {"kilo-2"})
        rows = self.mod.grep_sessions("should not leak", ["kilo"], 50)
        self.assertEqual(rows, [])

    def test_lookup_kilo(self):
        self.assertEqual(self.mod._lookup_kilo("kilo-1")["cwd"],
                         "/home/alice/kilo-proj")
        self.assertIsNone(self.mod._lookup_kilo("zzz"))

    def test_store_info_kilo(self):
        info = self.mod.store_info_kilo()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- mimo ----------------
    def test_list_mimo(self):
        by_id = {r["id"]: r for r in self.mod.list_mimo(50)}
        self.assertEqual(set(by_id), {"mimo-1", "mimo-2"})
        self.assertEqual(by_id["mimo-1"]["cwd"], "/home/alice/mimo-proj")
        self.assertEqual(by_id["mimo-1"]["title"],
                         "Refactor the mimo search")

    def test_preview_mimo(self):
        text = self.mod.preview_mimo("mimo-1")
        self.assertIn("--- mimo mimo-1", text)
        self.assertIn("Refactor the mimo search", text)
        self.assertIn("I'll refactor the mimo search", text)

    def test_preview_mimo_not_found(self):
        self.assertIn("not found", self.mod.preview_mimo("zzz"))

    def test_grep_mimo(self):
        rows = self.mod.grep_sessions("migration", ["mimo"], 50)
        self.assertEqual({r["id"] for r in rows}, {"mimo-2"})

    def test_lookup_mimo(self):
        self.assertEqual(self.mod._lookup_mimo("mimo-1")["cwd"],
                         "/home/alice/mimo-proj")
        self.assertIsNone(self.mod._lookup_mimo("zzz"))

    def test_store_info_mimo(self):
        info = self.mod.store_info_mimo()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- codewhale ----------------
    def test_list_codewhale(self):
        by_id = {r["id"]: r for r in self.mod.list_codewhale(50)}
        self.assertEqual(set(by_id), {"cw-1", "cw-2"})
        self.assertEqual(by_id["cw-1"]["cwd"],
                         "/home/alice/codewhale-proj")
        self.assertEqual(by_id["cw-1"]["title"],
                         "Refactor the codewhale search")

    def test_preview_codewhale(self):
        text = self.mod.preview_codewhale("cw-1")
        self.assertIn("--- codewhale cw-1", text)
        self.assertIn("Refactor the codewhale search", text)
        self.assertIn("I'll refactor the codewhale search", text)

    def test_preview_codewhale_not_found(self):
        self.assertIn("not found", self.mod.preview_codewhale("zzz"))

    def test_grep_codewhale(self):
        rows = self.mod.grep_sessions("migration", ["codewhale"], 50)
        self.assertEqual({r["id"] for r in rows}, {"cw-2"})

    def test_lookup_codewhale(self):
        self.assertEqual(self.mod._lookup_codewhale("cw-1")["cwd"],
                         "/home/alice/codewhale-proj")
        self.assertIsNone(self.mod._lookup_codewhale("zzz"))

    def test_store_info_codewhale(self):
        info = self.mod.store_info_codewhale()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- gptme ----------------
    def test_list_gptme(self):
        by_id = {r["id"]: r for r in self.mod.list_gptme(50)}
        self.assertEqual(set(by_id), {"2026-01-15-refactor-gptme",
                                      "2026-01-14-plan-migration"})
        self.assertEqual(by_id["2026-01-15-refactor-gptme"]["cwd"],
                         "/home/alice/gptme-proj")
        self.assertEqual(by_id["2026-01-15-refactor-gptme"]["title"],
                         "Refactor the gptme search")

    def test_preview_gptme(self):
        text = self.mod.preview_gptme("2026-01-15-refactor-gptme")
        self.assertIn("--- gptme 2026-01-15-refactor-gptme", text)
        self.assertIn("Refactor the gptme search", text)
        self.assertIn("I'll refactor the gptme search", text)
        self.assertNotIn("system prompt should not leak", text)

    def test_preview_gptme_not_found(self):
        self.assertIn("not found", self.mod.preview_gptme("zzz"))

    def test_grep_gptme(self):
        rows = self.mod.grep_sessions("migration", ["gptme"], 50)
        self.assertEqual({r["id"] for r in rows},
                         {"2026-01-14-plan-migration"})
        rows = self.mod.grep_sessions("should not leak", ["gptme"], 50)
        self.assertEqual(rows, [])

    def test_lookup_gptme(self):
        self.assertEqual(
            self.mod._lookup_gptme("2026-01-15-refactor-gptme")["cwd"],
            "/home/alice/gptme-proj")
        self.assertIsNone(self.mod._lookup_gptme("zzz"))

    def test_store_info_gptme(self):
        info = self.mod.store_info_gptme()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- jcode ----------------
    def test_list_jcode(self):
        by_id = {r["id"]: r for r in self.mod.list_jcode(50)}
        self.assertEqual(set(by_id), {"session_dove_1700000000000_j1",
                                      "session_herb_1699990000000_j2"})
        self.assertEqual(by_id["session_dove_1700000000000_j1"]["cwd"],
                         "/home/alice/jcode-proj")
        self.assertEqual(by_id["session_dove_1700000000000_j1"]["title"],
                         "Refactor the jcode search")

    def test_preview_jcode(self):
        text = self.mod.preview_jcode("session_dove_1700000000000_j1")
        self.assertIn("--- jcode session_dove_1700000000000_j1", text)
        self.assertIn("Refactor the jcode search", text)
        self.assertIn("I'll refactor the jcode search", text)
        self.assertNotIn("should not leak", text)

    def test_preview_jcode_not_found(self):
        self.assertIn("not found", self.mod.preview_jcode("zzz"))

    def test_grep_jcode(self):
        rows = self.mod.grep_sessions("migration", ["jcode"], 50)
        self.assertEqual({r["id"] for r in rows},
                         {"session_herb_1699990000000_j2"})
        rows = self.mod.grep_sessions("should not leak", ["jcode"], 50)
        self.assertEqual(rows, [])

    def test_lookup_jcode(self):
        self.assertEqual(
            self.mod._lookup_jcode("session_dove_1700000000000_j1")["cwd"],
            "/home/alice/jcode-proj")
        self.assertIsNone(self.mod._lookup_jcode("zzz"))

    def test_store_info_jcode(self):
        info = self.mod.store_info_jcode()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)  # .bak not counted

    # ---------------- dsh ----------------
    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_list_dsh(self):
        by_id = {r["id"]: r for r in self.mod.list_dsh(50)}
        self.assertEqual(set(by_id), {"session-dsh-1", "session-dsh-2"})
        self.assertEqual(by_id["session-dsh-1"]["cwd"],
                         "/home/alice/dsh-proj")
        self.assertEqual(by_id["session-dsh-1"]["title"],
                         "Refactor the dsh search")

    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_preview_dsh(self):
        text = self.mod.preview_dsh("session-dsh-1")
        self.assertIn("--- dsh session-dsh-1", text)
        self.assertIn("Refactor the dsh search", text)
        self.assertIn("I'll refactor the dsh search", text)
        self.assertNotIn("should not leak", text)

    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_preview_dsh_not_found(self):
        self.assertIn("not found", self.mod.preview_dsh("zzz"))

    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_grep_dsh(self):
        rows = self.mod.grep_sessions("migration", ["dsh"], 50)
        self.assertEqual({r["id"] for r in rows}, {"session-dsh-2"})
        rows = self.mod.grep_sessions("should not leak", ["dsh"], 50)
        self.assertEqual(rows, [])

    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_lookup_dsh(self):
        self.assertEqual(self.mod._lookup_dsh("session-dsh-1")["cwd"],
                         "/home/alice/dsh-proj")
        self.assertIsNone(self.mod._lookup_dsh("zzz"))

    @unittest.skipUnless(HAVE_ZSTD, "compression.zstd not available")
    def test_store_info_dsh(self):
        info = self.mod.store_info_dsh()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- resume commands ----------------
    def test_resume_cmds_registered(self):
        self.assertEqual(self.mod.RESUME_CMD["cline"]("x"),
                         ["cline", "--id", "x"])
        self.assertEqual(self.mod.RESUME_CMD["tau"]("x"),
                         ["tau", "--session", "x"])
        self.assertEqual(self.mod.RESUME_CMD["continue"]("x"),
                         ["cn", "--resume"])
        self.assertEqual(self.mod.RESUME_CMD["kilo"]("x"),
                         ["kilo", "-s", "x"])
        self.assertEqual(self.mod.RESUME_CMD["mimo"]("x"),
                         ["mimo", "-s", "x"])
        self.assertEqual(self.mod.RESUME_CMD["codewhale"]("x"),
                         ["codewhale", "--resume", "x"])
        self.assertEqual(self.mod.RESUME_CMD["gptme"]("x"),
                         ["gptme", "--name", "x"])
        self.assertEqual(self.mod.RESUME_CMD["jcode"]("x"),
                         ["jcode", "--resume", "x"])
        self.assertEqual(self.mod.RESUME_CMD["dsh"]("x"),
                         ["dsh", "--profile", "headless",
                          "--session-id", "x"])


if __name__ == "__main__":
    unittest.main()
