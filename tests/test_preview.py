#!/usr/bin/env python3
"""Tests for the human-readable block format of `ax preview` (issue #9)."""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

from test_ax import FIXTURES, load_ax

CASES = [
    ("claude", "sess-c1a2b3"),
    ("codex", "codex-1"),
    ("agy", "agy-1"),
    ("opencode", "oc-1"),
    ("devin", "dev-1"),
]

ROLE_RE = re.compile(r"^\s*\[(user|ai|msg|[a-z_]+)\]( \S.*)?$")


class TestPreviewFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_preview_home_")
        for src, dst in [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
        ]:
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

    def _capture_stdout(self, fn, *args):
        old = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            result = fn(*args)
        finally:
            sys.stdout = old
        return result, buf.getvalue()

    def test_block_layout_all_agents(self):
        for agent, sid in CASES:
            with self.subTest(agent=agent):
                text = self.mod.PREVIEWERS[agent](sid)
                lines = text.splitlines()
                self.assertTrue(
                    lines[0].startswith(f"--- {agent} {sid}"),
                    f"missing session header: {lines[0]!r}",
                )
                role_lines = [l for l in lines if ROLE_RE.match(l)]
                self.assertTrue(
                    any(l.lstrip().startswith("[user]") for l in role_lines),
                    f"no [user] role header for {agent}",
                )
                self.assertTrue(
                    any(l.lstrip().startswith("[ai]") for l in role_lines),
                    f"no [ai] role header for {agent}",
                )
                # turn blocks are separated from the header by a blank line
                self.assertIn("\n\n[", text)

    def test_role_header_is_own_line_body_follows(self):
        text = self.mod.preview_claude("sess-c1a2b3")
        lines = text.splitlines()
        idx = next(i for i, l in enumerate(lines) if l.lstrip().startswith("[user]"))
        self.assertEqual(lines[idx + 1].lstrip(), "Refactor the login form")

    def test_long_body_wraps_at_width(self):
        old = os.environ.get("AX_PREVIEW_WIDTH")
        os.environ["AX_PREVIEW_WIDTH"] = "40"
        try:
            text = self.mod.preview_claude("sess-c1a2b3")
        finally:
            if old is None:
                os.environ.pop("AX_PREVIEW_WIDTH", None)
            else:
                os.environ["AX_PREVIEW_WIDTH"] = old
        body = [l for l in text.splitlines()
                if l and not l.startswith(("[", "---"))]
        self.assertTrue(body)
        for l in body:
            self.assertLessEqual(
                len(l), 40, f"body line exceeds width: {l!r}")
        # the long fixture message must actually span multiple lines
        self.assertGreater(len(body), 4)

    def test_default_wrap_never_exceeds_80(self):
        os.environ.pop("AX_PREVIEW_WIDTH", None)
        text = self.mod.preview_claude("sess-c1a2b3")
        body = [l for l in text.splitlines()
                if l and not l.startswith(("[", "---"))]
        self.assertTrue(body)
        for l in body:
            self.assertLessEqual(len(l), 80, f"body line too long: {l!r}")

    def test_original_newlines_preserved(self):
        os.environ.pop("AX_PREVIEW_WIDTH", None)
        text = self.mod.preview_claude("sess-c1a2b3")
        lines = text.splitlines()
        # fixture message has a hard newline before "Also keep ..."
        self.assertTrue(
            any(l.lstrip().startswith("Also keep the submit button") for l in lines),
            "original newline was not preserved",
        )
        # and the two paragraphs were not squashed onto one line
        self.assertNotIn("field. Also", text)

    def test_wrap_body_helper(self):
        out = self.mod.wrap_body("alpha beta gamma delta epsilon zeta", 20)
        self.assertTrue(all(len(l) <= 20 for l in out))
        self.assertGreater(len(out), 1)
        out2 = self.mod.wrap_body("one\n\nthree", 20)
        self.assertEqual(out2, ["one", "", "three"])

    def test_cmd_preview_json_keeps_preview_field(self):
        _, out = self._capture_stdout(
            self.mod.cmd_preview, ["claude", "sess-c1a2b3", "--json"])
        obj = json.loads(out)
        self.assertEqual(obj["agent"], "claude")
        self.assertEqual(obj["id"], "sess-c1a2b3")
        self.assertIsInstance(obj["preview"], str)
        self.assertIn("--- claude sess-c1a2b3", obj["preview"])

    def test_devin_keeps_resume_and_model_lines(self):
        text = self.mod.preview_devin("dev-1")
        self.assertIn("resume: devin -r dev-1", text)
        self.assertIn("model=", text)

    def test_tool_rows_filtered(self):
        text = self.mod.render_preview(
            "claude", "test",
            [("user", "Start the process\n[tool: exec]\nEnd the process")],
            width=60, total=1)
        self.assertIn("Start the process", text)
        self.assertIn("End the process", text)
        self.assertNotIn("[tool: exec]", text)
        self.assertNotIn("[tool:", text)

    def test_ai_turn_is_right_aligned(self):
        os.environ.pop("AX_PREVIEW_WIDTH", None)
        text = self.mod.preview_claude("sess-c1a2b3")
        lines = text.splitlines()
        ai_lines = [l for l in lines
                    if l.lstrip().startswith("[ai]") and l != l.lstrip()]
        self.assertTrue(ai_lines, "ai header should be right-aligned (indented)")

    def test_not_found_still_readable(self):
        self.assertIn("not found", self.mod.preview_claude("no-such-id"))
        self.assertIn("not found", self.mod.preview_agy("no-such-id"))


class TestAgyPlannerResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_agy_planner_home_")
        for src, dst in [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
        ]:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        cls.mod = load_ax(cls.tmp)
        # write a synthetic agy transcript with a PLANNER_RESPONSE
        cid = "agy-planner"
        p = os.path.join(cls.mod.AGY_HOME, "brain", cid,
                         ".system_generated", "logs", "transcript.jsonl")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(json.dumps({"type": "USER_INPUT",
                                "content": "<USER_REQUEST>plan the migration</USER_REQUEST> extra text",
                                "timestamp": 1700000000000}) + "\n")
            f.write(json.dumps({"type": "PLANNER_RESPONSE",
                                "content": "I will plan the migration step by step.",
                                "timestamp": 1700000001000}) + "\n")

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        shutil.rmtree(cls.tmp)

    def test_agy_planner_response_is_ai(self):
        text = self.mod.preview_agy("agy-planner", 10)
        self.assertIn("[user]", text)
        self.assertIn("plan the migration", text)
        self.assertIn("[ai]", text)
        self.assertIn("I will plan the migration step by step.", text)


if __name__ == "__main__":
    unittest.main()
