#!/usr/bin/env python3
"""opencode NULL-column rows are listed robustly (issue #40)."""
import importlib.machinery as machinery
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

import ax_test_support  # noqa: F401

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_oc_null_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_oc_null_mod", loader,
                                               origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestOpencodeNullRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_test_ocnull_")
        for src, dst in (("local", ".local"),):
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

    def test_list_null_row_defaults(self):
        rows = self.mod.list_opencode(400, no_cache=True)
        by_id = {r["id"]: r for r in rows}
        self.assertIn("oc-v2-null", by_id)
        row = by_id["oc-v2-null"]
        self.assertEqual(row["cwd"], "?")
        self.assertEqual(row["epoch"], 0)
        self.assertEqual(row["title"], "(untitled)")

    def test_preview_null_row(self):
        text = self.mod.preview_opencode("oc-v2-null", 10)
        self.assertIn("oc-v2-null", text)
        self.assertIn("null-row-marker-xyz", text)

    def test_grep_null_row(self):
        rows = self.mod.grep_sessions("null-row-marker-xyz",
                                      ["opencode"], 50, no_cache=True)
        ids = {r["id"] for r in rows}
        self.assertIn("oc-v2-null", ids)

    def test_extra_column_does_not_break_list(self):
        dbp = os.path.join(self.tmp, ".local", "share",
                           "opencode", "opencode.db")
        con = sqlite3.connect(dbp)
        try:
            con.execute("ALTER TABLE session_v2 ADD COLUMN future_col TEXT")
            con.commit()
        finally:
            con.close()
        try:
            rows = self.mod.list_opencode(400, no_cache=True)
        finally:
            # restore the pristine fixture copy for the remaining tests
            shutil.rmtree(os.path.join(self.tmp, ".local"))
            shutil.copytree(os.path.join(FIXTURES, "local"),
                            os.path.join(self.tmp, ".local"))
        self.assertIn("oc-v2-null", {r["id"] for r in rows})


if __name__ == "__main__":
    unittest.main()
