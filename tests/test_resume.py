#!/usr/bin/env python3
"""Unit tests for `ax resume` cwd resolution (issue #38).

resume must resolve the target session's cwd with a single lookup against
the target provider's own store (or one bounded list call) instead of
enumerating every session via collect([agent], 2000). Unknown ids must
still resume without cd. picker/grep -> resume handoff must keep working.
All tests run against a synthetic fixture HOME; subprocess/execvp are mocked.
"""
import importlib.machinery as machinery
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import ax_test_support  # noqa: F401  (scrubs HERMES_HOME for the test run)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_resume_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_resume_test_mod", loader,
                                               origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


# agent -> (known id, expected cwd). All synthetic fixture data.
KNOWN = {
    "claude": ("sess-c1a2b3", "/home/alice/projects/webapp"),
    "codex": ("codex-1", "/home/bob/codex"),
    "agy": ("agy-1", "/home/alice/ws"),
    "opencode": ("oc-1", "/home/alice/opencode"),
    "devin": ("dev-1", "/home/alice/devin"),
    "goose": ("g-1", "/home/alice/gooseproj"),
    "hermes": ("h-1", "/home/alice/hproj"),
    "vibe": ("vb001", "/home/alice/vibeproj"),
    "omp": ("ompid1", "/home/alice/ws"),
}


class TestResumeLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_resume_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        mapping = [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
            ("aider", "aiderws"),
            ("omp", ".omp"),
            ("vibe", ".vibe"),
            ("hermes", ".hermes"),
        ]
        for src, dst in mapping:
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

    def setUp(self):
        if os.path.exists(self.mod.TITLES_PATH):
            os.remove(self.mod.TITLES_PATH)

    def _capture(self, fn, *args, **kwargs):
        old_out, old_err = sys.stdout, sys.stderr
        out, err = io.StringIO(), io.StringIO()
        sys.stdout, sys.stderr = out, err
        try:
            rc = fn(*args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        return rc, out.getvalue(), err.getvalue()

    # ---------- single lookup, no full enumeration ----------
    def test_find_session_does_not_enumerate(self):
        with mock.patch.object(
                self.mod, "collect",
                side_effect=AssertionError("must not enumerate")):
            for agent, (sid, cwd) in KNOWN.items():
                with self.subTest(agent=agent):
                    r = self.mod._find_session(agent, sid)
                    self.assertIsNotNone(r, agent)
                    self.assertEqual(r["cwd"], cwd, agent)

    def test_find_session_does_not_call_provider_listers(self):
        blocks = {a: mock.patch.object(
            self.mod, f"list_{a}",
            side_effect=AssertionError(f"list_{a} must not run"))
            for a in KNOWN}
        with mock.patch.object(
                self.mod, "collect",
                side_effect=AssertionError("must not enumerate")):
            for cm in blocks.values():
                cm.start()
            try:
                for agent, (sid, _) in KNOWN.items():
                    with self.subTest(agent=agent):
                        self.assertIsNotNone(
                            self.mod._find_session(agent, sid), agent)
            finally:
                for cm in blocks.values():
                    cm.stop()

    def test_find_session_unknown_id_returns_none(self):
        with mock.patch.object(
                self.mod, "collect",
                side_effect=AssertionError("must not enumerate")):
            for agent in KNOWN:
                with self.subTest(agent=agent):
                    self.assertIsNone(
                        self.mod._find_session(agent, "no-such-id"), agent)

    def test_find_session_opencode_v2_and_child_hidden(self):
        with mock.patch.object(
                self.mod, "collect",
                side_effect=AssertionError("must not enumerate")):
            r = self.mod._find_session("opencode", "oc-v2-1")
            self.assertIsNotNone(r)
            self.assertEqual(r["cwd"], "/home/alice/opencode3")
            # fork/subagent children stay hidden, as in list (#36)
            self.assertIsNone(self.mod._find_session("opencode", "oc-v2-child"))

    def test_find_session_aider_resolves_by_path(self):
        aide_rows = self.mod.list_aider()
        self.assertTrue(aide_rows)
        sid = aide_rows[0]["id"]
        with mock.patch.object(
                self.mod, "collect",
                side_effect=AssertionError("must not enumerate")):
            r = self.mod._find_session("aider", sid)
            self.assertIsNotNone(r)
            self.assertEqual(r["cwd"], os.path.dirname(sid))

    # ---------- cmd_resume behaviour ----------
    def _run_resume(self, args):
        seen = {}

        def _execvp(prog, argv):
            seen["argv"] = [prog] + list(argv[1:])
            raise SystemExit(99)

        with mock.patch.object(self.mod, "collect",
                               side_effect=AssertionError(
                                   "resume must not enumerate")), \
                mock.patch("os.path.isdir", return_value=True), \
                mock.patch("os.chdir",
                           side_effect=lambda d: seen.update(chdir=d)), \
                mock.patch.object(self.mod.os, "execvp", side_effect=_execvp):
            try:
                self._capture(self.mod.cmd_resume, args)
            except SystemExit as e:
                seen["exit"] = e.code
        return seen

    def test_resume_cds_before_exec(self):
        seen = self._run_resume(["devin", "dev-1"])
        self.assertEqual(seen.get("chdir"), "/home/alice/devin")
        self.assertEqual(seen.get("argv"), ["devin", "-r", "dev-1"])
        self.assertEqual(seen.get("exit"), 99)

    def test_resume_unknown_id_still_execs_without_cd(self):
        seen = self._run_resume(["devin", "no-such-id"])
        self.assertNotIn("chdir", seen)
        self.assertEqual(seen.get("argv"), ["devin", "-r", "dev-1"][:2]
                         + ["no-such-id"])
        self.assertEqual(seen.get("exit"), 99)

    def test_resume_unknown_agent_usage(self):
        rc, _, err = self._capture(self.mod.cmd_resume, ["nope", "x"])
        self.assertNotEqual(rc, 0)
        self.assertIn("unknown agent", err)

    # ---------- picker -> resume handoff intact ----------
    def test_picker_hands_agent_and_id_to_resume(self):
        rows = [{"agent": "devin", "id": "dev-1", "epoch": 1, "cwd": "?",
                 "title": "t"}]

        class _Proc:
            returncode = 0
            stdout = "devin\tdev-1\t1\tnow\t?\t?\tt\n"

        resumed = {}
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(self.mod, "collect", return_value=rows), \
                mock.patch("subprocess.run",
                           return_value=_Proc()), \
                mock.patch.object(
                    self.mod, "cmd_resume",
                    side_effect=lambda a: resumed.update(args=a) or 0):
            rc = self.mod.cmd_picker()
        self.assertEqual(rc, 0)
        self.assertEqual(resumed["args"], ["devin", "dev-1"])


if __name__ == "__main__":
    unittest.main()
