#!/usr/bin/env python3
"""Generate synthetic fixtures for ax tests."""
import json
import os
import sqlite3

FIXTURES = os.path.dirname(os.path.abspath(__file__))


def write_jsonl(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def touch_epoch(path, epoch):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "a").close()
    os.utime(path, (epoch, epoch))


def write_text(path, text, epoch=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if epoch is not None:
        os.utime(path, (epoch, epoch))


def generate_claude():
    base = os.path.join(FIXTURES, "fixtures", "claude", "projects")
    write_jsonl(
        os.path.join(base, "webapp", "sess-c1a2b3.jsonl"),
        [
            {"cwd": "/home/alice/projects/webapp"},
            {
                "type": "user",
                "message": {"content": "Refactor the login form"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "I'll help you refactor the login form. What framework is it using?",
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": (
                        "Please handle validation errors gracefully and show inline "
                        "error messages right next to each form field.\n"
                        "Also keep the submit button disabled while the request is "
                        "in flight so users cannot trigger duplicate submissions."
                    ),
                },
                "timestamp": "2025-01-15T10:01:00.000Z",
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Done. Validation errors now render inline.",
                        }
                    ],
                },
                "timestamp": "2025-01-15T10:02:00.000Z",
            },
        ],
    )
    write_jsonl(
        os.path.join(base, "api", "sess-d4e5f6.jsonl"),
        [
            {"cwd": "/home/alice/projects/api"},
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Write tests for the new endpoint",
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Here is a test outline."}
                    ]
                },
            },
        ],
    )
    os.utime(os.path.join(base, "webapp", "sess-c1a2b3.jsonl"), (1700000000, 1700000000))
    os.utime(os.path.join(base, "api", "sess-d4e5f6.jsonl"), (1700000020, 1700000020))


def generate_codex():
    base = os.path.join(FIXTURES, "fixtures", "codex", "sessions")
    p1 = os.path.join(base, "2025", "01", "15", "sess-codex-1.jsonl")
    write_jsonl(
        p1,
        [
            {"type": "session_meta", "payload": {"id": "codex-1", "cwd": "/home/bob/codex"}},
            {
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "Review this function"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "The function looks okay."}
                    ],
                },
            },
        ],
    )
    p2 = os.path.join(base, "2025", "01", "14", "sess-codex-2.jsonl")
    write_jsonl(
        p2,
        [
            {"type": "session_meta", "payload": {"id": "codex-2", "cwd": "/home/bob/codex2"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Optimize the query"}
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Try adding an index."}
                    ],
                },
            },
        ],
    )
    os.utime(p1, (1700000010, 1700000010))
    os.utime(p2, (1700000030, 1700000030))


def generate_agy():
    base = os.path.join(FIXTURES, "fixtures", "gemini", "antigravity-cli")
    write_jsonl(
        os.path.join(base, "history.jsonl"),
        [
            {
                "conversationId": "agy-1",
                "display": "Plan the migration",
                "workspace": "/home/alice/ws",
                "timestamp": 1700000000000,
            },
            {
                "conversationId": "agy-2",
                "display": "/system",
                "workspace": "?",
                "timestamp": 1700000100000,
            },
        ],
    )
    for cid, workspace in [("agy-1", "?"), ("agy-2", "/home/alice/ws2")]:
        dbp = os.path.join(base, "conversations", f"{cid}.db")
        os.makedirs(os.path.dirname(dbp), exist_ok=True)
        if os.path.exists(dbp):
            os.remove(dbp)
        con = sqlite3.connect(dbp)
        con.execute("CREATE TABLE trajectory_metadata_blob (data BLOB)")
        if workspace != "?":
            con.execute(
                "INSERT INTO trajectory_metadata_blob (data) VALUES (?)",
                (b"workspace: file:///home/alice/ws2",),
            )
        con.commit()
        con.close()
        os.utime(dbp, (1600000000, 1600000000))

    # agy-1 title comes from history; agy-2 falls back to transcript.
    for cid, first in [
        ("agy-1", "Plan the migration"),
        ("agy-2", "Optimize database"),
    ]:
        p = os.path.join(
            base, "brain", cid, ".system_generated", "logs", "transcript.jsonl"
        )
        write_jsonl(
            p,
            [
                {
                    "type": "USER_INPUT",
                    "content": f"{first}",
                },
                {
                    "type": "AGENT_OUTPUT",
                    "content": f"Okay, let's start with {first.lower()}.",
                },
            ],
        )


def generate_opencode():
    base = os.path.join(FIXTURES, "fixtures", "local", "share", "opencode")
    os.makedirs(base, exist_ok=True)
    dbp = os.path.join(base, "opencode.db")
    if os.path.exists(dbp):
        os.remove(dbp)
    con = sqlite3.connect(dbp)
    con.execute(
        "CREATE TABLE session (id TEXT, directory TEXT, title TEXT, time_updated INTEGER)"
    )
    # mirror the real schema: part.message_id -> message.id, role in message.data
    con.execute(
        "CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, "
        "time_created INTEGER, time_updated INTEGER, data TEXT)"
    )
    con.execute(
        "CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, "
        "session_id TEXT, time_created INTEGER, time_updated INTEGER, data TEXT)"
    )
    con.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?)",
        ("oc-1", "/home/alice/opencode", "open test one", 1700000200000),
    )
    con.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?)",
        ("oc-2", "/home/alice/opencode2", "open test two", 1700000300000),
    )
    msgs = [
        ("ocm-1", "oc-1", "user", 1700000200000),
        ("ocm-2", "oc-1", "assistant", 1700000200100),
        ("ocm-3", "oc-2", "user", 1700000300000),
    ]
    for mid, sid, role, ts in msgs:
        con.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            (mid, sid, ts, ts, json.dumps({"role": role})),
        )
    parts = [
        ("ocp-1", "ocm-1", "oc-1", "Explain this code", 1700000200000),
        ("ocp-2", "ocm-2", "oc-1", "Here is an explanation", 1700000200100),
        ("ocp-3", "ocm-3", "oc-2", "Plan the feature", 1700000300000),
    ]
    for pid, mid, sid, text, ts in parts:
        con.execute(
            "INSERT INTO part VALUES (?, ?, ?, ?, ?, ?)",
            (pid, mid, sid, ts, ts,
             json.dumps({"type": "text", "text": text})),
        )
    con.commit()
    con.close()


def generate_devin():
    base = os.path.join(FIXTURES, "fixtures", "local", "share", "devin", "cli")
    os.makedirs(os.path.join(base, "transcripts"), exist_ok=True)
    dbp = os.path.join(base, "sessions.db")
    if os.path.exists(dbp):
        os.remove(dbp)
    con = sqlite3.connect(dbp)
    con.execute(
        "CREATE TABLE sessions (id TEXT, working_directory TEXT, title TEXT, last_activity_at INTEGER, hidden INTEGER)"
    )
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        ("dev-1", "/home/alice/devin", "devin test one", 1700000400, 0),
    )
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        ("dev-2", "/home/alice/devin2", "devin test two", 1700000500, 0),
    )
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        ("dev-hidden", "/home/alice/hidden", "hidden", 1700000600, 1),
    )
    con.commit()
    con.close()

    for sid, prompt in [
        ("dev-1", "Build a landing page"),
        ("dev-2", "Refactor the auth flow"),
    ]:
        p = os.path.join(base, "transcripts", f"{sid}.json")
        with open(p, "w") as f:
            json.dump(
                {
                    "agent": {"model_name": "devin-test"},
                    "steps": [
                        {"source": "user", "message": prompt},
                        {"source": "assistant", "message": f"I will {prompt.lower()}"},
                        {"source": "system", "message": "this should be ignored"},
                    ],
                },
                f,
            )


if __name__ == "__main__":
    generate_claude()
    generate_codex()
    generate_agy()
    generate_opencode()
    generate_devin()
    print("fixtures generated in", os.path.join(FIXTURES, "fixtures"))
