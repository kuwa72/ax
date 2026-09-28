#!/usr/bin/env python3
"""opencode child sessions (fork/subagent) are hidden from listings (issue #36)."""
import importlib.machinery as machinery
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import ax_test_support  # noqa: F401

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_oc_child_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_oc_child_mod", loader,
                                               origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestOpencodeChildSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_oc_child_")
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

    def _run_ok(self):
        m = mock.Mock()
        m.returncode = 0
        return m

    def _capture(self, fn, *args):
        import io
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        try:
            rc = fn(*args)
            return rc, sys.stdout.getvalue(), sys.stderr.getvalue()
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    def test_list_hides_v2_child_shows_parent(self):
        rows = self.mod.list_opencode(400, no_cache=True)
        by_id = {r["id"] for r in rows}
        self.assertIn("oc-v2-parent", by_id)
        self.assertNotIn("oc-v2-child", by_id)

    def test_list_hides_v1_legacy_child(self):
        rows = self.mod.list_opencode(400, no_cache=True)
        by_id = {r["id"] for r in rows}
        self.assertNotIn("oc-legacy-child", by_id)

    def test_grep_hides_child(self):
        rows = self.mod.grep_sessions("child-only-marker-xyz",
                                      ["opencode"], 50, no_cache=True)
        ids = {r["id"] for r in rows}
        self.assertNotIn("oc-v2-child", ids)

    def test_preview_child_still_works(self):
        text = self.mod.preview_opencode("oc-v2-child", 10)
        self.assertIn("oc-v2-child", text)
        self.assertIn("child-only-marker-xyz", text)

    def test_rm_parent_still_found(self):
        with mock.patch("subprocess.run",
                        return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(self.mod.cmd_rm,
                                     ["opencode", "oc-v2-parent", "--yes"])
        self.assertEqual(rc, 0)
        argv = mrun.call_args[0][0]
        self.assertEqual(argv,
                         ["opencode", "session", "delete", "oc-v2-parent"])

    def test_rm_child_not_found(self):
        with mock.patch("subprocess.run",
                        return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(self.mod.cmd_rm,
                                     ["opencode", "oc-v2-child", "--yes"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)


if __name__ == "__main__":
    unittest.main()
