#!/usr/bin/env python3
"""Devin preview tests covering ATIF parsing, --export fallback and local DB fallback."""
import importlib.machinery as machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
FAKE_DEVIN = os.path.join(FIXTURES, "bin")


def load_ax(home, path):
    os.environ["HOME"] = home
    os.environ["PATH"] = path
    loader = machinery.SourceFileLoader("ax_devin_mod", AX_PATH)
    spec = importlib.util.spec_from_loader("ax_devin_mod", loader, origin=AX_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDevinPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls._orig_path = os.environ.get("PATH")
        cls.tmp = tempfile.mkdtemp(prefix="ax_devin_test_")
        mapping = [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
        ]
        for src, dst in mapping:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        # an empty dir to simulate missing devin binary
        cls.empty_bin = os.path.join(cls.tmp, "empty_bin")
        os.makedirs(cls.empty_bin, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        if cls._orig_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = cls._orig_path
        shutil.rmtree(cls.tmp)

    def _mod(self, with_devin=True):
        if with_devin:
            py_dir = os.path.dirname(sys.executable)
            path = FAKE_DEVIN + os.pathsep + py_dir
        else:
            path = self.empty_bin
        return load_ax(self.tmp, path)

    def test_preview_local_transcript(self):
        mod = self._mod()
        text = mod.preview_devin("dev-1", 10)
        self.assertIn("--- devin dev-1", text)
        self.assertIn("[user]", text)
        self.assertIn("Build a landing page", text)
        self.assertIn("[ai]", text)
        self.assertIn("I will build a landing page", text)
        self.assertIn("source=local", text)

    def test_preview_falls_back_to_devin_export(self):
        mod = self._mod()
        # dev-net has no transcript and no message_nodes
        text = mod.preview_devin("dev-net", 10)
        self.assertIn("--- devin dev-net", text)
        self.assertIn("[user]", text)
        self.assertIn("Cloud user request", text)
        self.assertIn("[ai]", text)
        self.assertIn("Cloud agent response", text)
        self.assertIn("source=export", text)
        # sentinel prompt should be trimmed, not shown
        self.assertNotIn("/_ax_preview", text)

    def test_preview_falls_back_to_message_nodes(self):
        mod = self._mod(with_devin=False)
        # dev-cloud has message_nodes but no transcript and no devin binary
        text = mod.preview_devin("dev-cloud", 10)
        self.assertIn("--- devin dev-cloud", text)
        self.assertIn("[user]", text)
        self.assertIn("Plan the migration from db", text)
        self.assertIn("[ai]", text)
        self.assertIn("I will plan the migration from db", text)
        self.assertIn("source=db", text)

    def test_preview_unknown_session_falls_back_to_title(self):
        mod = self._mod(with_devin=False)
        text = mod.preview_devin("no-such-session", 10)
        self.assertIn("--- devin no-such-session", text)
        self.assertIn("(no local transcript)", text)

    def test_preview_agent_source_atif(self):
        mod = self._mod()
        atif = {
            "schema_version": "ATIF-v1.7",
            "session_id": "dev-agent",
            "agent": {"model_name": "devin-agent"},
            "steps": [
                {"source": "user", "message": "Hello"},
                {"source": "agent", "message": "Hi there", "tool_calls": [{"function_name": "exec"}]},
                {"source": "tool", "message": "tool exec result"},
            ],
        }
        p = os.path.join(self.tmp, ".local", "share", "devin", "cli", "transcripts", "dev-agent.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(atif, f)
        text = mod.preview_devin("dev-agent", 10)
        self.assertIn("[user]", text)
        self.assertIn("Hello", text)
        self.assertIn("[ai]", text)
        self.assertIn("Hi there", text)
        self.assertNotIn("[tools:", text)
        self.assertNotIn("tool exec result", text)


if __name__ == "__main__":
    unittest.main()
