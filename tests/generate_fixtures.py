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
                "message": {"content": "ΟΔΟΣ του αλγορίθμου"},
                "timestamp": "2025-01-15T10:00:30.000Z",
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "η οδος είναι σαφής (clear path) "
                                "マイグレーション計画"
                            )
                        }
                    ]
                },
                "timestamp": "2025-01-15T10:00:45.000Z",
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
                        {"type": "text", "text": "Done. Validation errors now render inline."}
                    ]
                },
                "timestamp": "2025-01-15T10:02:00.000Z",
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
        "CREATE TABLE session (id TEXT, directory TEXT, title TEXT, "
        "time_updated INTEGER, parent_id TEXT)"
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
        "INSERT INTO session VALUES (?, ?, ?, ?, ?)",
        ("oc-1", "/home/alice/opencode", "open test one", 1700000200000, None),
    )
    con.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?)",
        ("oc-2", "/home/alice/opencode2", "open test two", 1700000300000, None),
    )
    # legacy (v1-only, absent from session_v2) child row: hidden from listings
    con.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?)",
        ("oc-legacy-child", "/home/alice/opencode", "legacy child",
         1700000350000, "oc-1"),
    )
    # opencode v2.0.x schema (kv migration.v1-v2 = completed): sessions live
    # in session_v2 and messages in session_message (content embedded in
    # data). part/message stay for pre-migration sessions only.
    con.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)")
    con.execute(
        "INSERT INTO kv VALUES ('migration.v1-v2', '{\"phase\":\"completed\"}')"
    )
    con.execute(
        "CREATE TABLE session_v2 (id TEXT PRIMARY KEY, project_id TEXT, "
        "workspace_id TEXT, parent_id TEXT, fork_session_id TEXT, "
        "fork_boundary INTEGER, slug TEXT, directory TEXT, path TEXT, "
        "title TEXT, version TEXT, share_url TEXT, summary_additions REAL, "
        "summary_deletions REAL, summary_files INTEGER, summary_diffs REAL, "
        "metadata TEXT, cost REAL, tokens_input INTEGER, tokens_output INTEGER, "
        "tokens_reasoning INTEGER, tokens_cache_read INTEGER, "
        "tokens_cache_write INTEGER, revert TEXT, permission TEXT, agent TEXT, "
        "model TEXT, time_created INTEGER, time_updated INTEGER, "
        "time_compacting INTEGER, time_archived INTEGER, time_suspended INTEGER, "
        "resume_attempts INTEGER, time_idle INTEGER, time_viewed INTEGER, "
        "idle_outcome TEXT)"
    )
    con.execute(
        "CREATE TABLE session_message (id TEXT PRIMARY KEY, session_id TEXT, "
        "type TEXT, seq INTEGER, time_created INTEGER, time_updated INTEGER, "
        "data TEXT)"
    )
    con.execute(
        "INSERT INTO session_v2 (id, directory, title, time_created, "
        "time_updated) VALUES (?, ?, ?, ?, ?)",
        ("oc-v2-1", "/home/alice/opencode3", "v2 session one",
         1700000400000, 1700000400000),
    )
    # top-level parent + fork/subagent child (child hidden from listings)
    con.execute(
        "INSERT INTO session_v2 (id, parent_id, directory, title, "
        "time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?)",
        ("oc-v2-parent", None, "/home/alice/opencode4", "v2 parent",
         1700000500000, 1700000500000),
    )
    con.execute(
        "INSERT INTO session_v2 (id, parent_id, directory, title, "
        "time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?)",
        ("oc-v2-child", "oc-v2-parent", "/home/alice/opencode4", "v2 child",
         1700000600000, 1700000600000),
    )
    # issue #40: column-missing rows must not crash listings
    con.execute(
        "INSERT INTO session_v2 (id, parent_id, directory, title, "
        "time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?)",
        ("oc-v2-null", None, None, None, None, None),
    )
    con.execute(
        "INSERT INTO session_message VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ocv2m-1", "oc-v2-1", "user", 4, 1700000400000, 1700000400000,
         json.dumps({"time": {"created": 1700000400000},
                     "text": "v2 user question"})),
    )
    con.execute(
        "INSERT INTO session_message VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ocv2m-2", "oc-v2-1", "assistant", 5, 1700000400100, 1700000400100,
         json.dumps({"time": {"created": 1700000400100},
                     "content": [{"type": "text",
                                  "text": "v2 assistant answer"}]})),
    )
    # child-only marker: greppable via preview, not via list/grep
    con.execute(
        "INSERT INTO session_message VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ocv2m-child-1", "oc-v2-child", "user", 4, 1700000600000,
         1700000600000,
         json.dumps({"time": {"created": 1700000600000},
                     "text": "child-only-marker-xyz question"})),
    )
    # issue #40 companion message for the NULL-column row
    con.execute(
        "INSERT INTO session_message VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ocv2m-null-1", "oc-v2-null", "user", 4, 1700000700000,
         1700000700000,
         json.dumps({"time": {"created": 1700000700000},
                     "text": "null-row-marker-xyz question"})),
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
        ("ocp-gr", "ocm-1", "oc-1", "ΟΔΟΣ του αλγορίθμου", 1700000200200),
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
        "CREATE TABLE sessions (id TEXT, working_directory TEXT, title TEXT, "
        "last_activity_at INTEGER, hidden INTEGER, main_chain_id INTEGER, model TEXT)"
    )
    con.execute(
        "CREATE TABLE message_nodes ("
        "row_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "session_id TEXT NOT NULL, "
        "node_id INTEGER NOT NULL, "
        "parent_node_id INTEGER, "
        "chat_message TEXT NOT NULL, "
        "created_at INTEGER NOT NULL, "
        "metadata TEXT)"
    )
    con.execute(
        "CREATE INDEX idx_message_nodes_session ON message_nodes(session_id)"
    )
    sessions = [
        ("dev-1", "/home/alice/devin", "devin test one", 1700000400, 0, 3, "devin-test"),
        ("dev-2", "/home/alice/devin2", "devin test two", 1700000500, 0, 3, "devin-test"),
        ("dev-hidden", "/home/alice/hidden", "hidden", 1700000600, 1, None, "devin-test"),
        ("dev-cloud", "/home/alice/devin", "cloud session via db", 1700000300, 1, 3, "devin-test"),
        ("dev-net", "/home/alice/devin", "cloud session via network", 1700000200, 1, None, "devin-test"),
    ]
    con.executemany(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)", sessions
    )

    # message node chains for dev-1, dev-2, dev-cloud
    chains = [
        ("dev-1", [
            (0, None, "system", "system prompt"),
            (1, 0, "system", "context"),
            (2, 1, "user", "Build a landing page"),
            (3, 2, "assistant", "I will build a landing page"),
        ]),
        ("dev-2", [
            (0, None, "system", "system prompt"),
            (1, 0, "system", "context"),
            (2, 1, "user", "Refactor the auth flow"),
            (3, 2, "assistant", "I will refactor the auth flow"),
        ]),
        ("dev-cloud", [
            (0, None, "system", "system prompt"),
            (1, 0, "system", "context"),
            (2, 1, "user", "Plan the migration from db"),
            (3, 2, "assistant", "I will plan the migration from db"),
        ]),
    ]
    for sid, nodes in chains:
        for node_id, parent_id, role, content in nodes:
            con.execute(
                "INSERT INTO message_nodes (session_id, node_id, parent_node_id, chat_message, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (sid, node_id, parent_id, json.dumps({"role": role, "content": content}), 1700000000),
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


def generate_aider():
    base = os.path.join(FIXTURES, "fixtures", "aider")
    write_text(
        os.path.join(base, "proj-one", ".aider.chat.history.md"),
        """\
# aider chat started at 2026-01-10 09:00:00

#### Refactor the parser
#### in two steps

I'll refactor the parser now.

> Applied edit to parser.py

# aider chat started at 2026-01-12 15:30:00

#### Fix the lexer bug

Here is the fix for the lexer bug.

```python
#### not a user line inside a fence
```
""",
    )
    write_text(
        os.path.join(base, "proj-two", ".aider.chat.history.md"),
        """\
# aider chat started at 2026-01-11 12:00:00

#### Update the README

Done updating the README.
""",
    )


def generate_goose():
    base = os.path.join(FIXTURES, "fixtures", "local", "share", "goose",
                        "sessions")
    os.makedirs(base, exist_ok=True)
    dbp = os.path.join(base, "sessions.db")
    if os.path.exists(dbp):
        os.remove(dbp)
    con = sqlite3.connect(dbp)
    con.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, working_dir TEXT, "
        "name TEXT, description TEXT, session_type TEXT, created_at TEXT, "
        "updated_at TEXT, message_count INTEGER, archived_at TEXT)")
    con.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, "
        "role TEXT, content_json TEXT, timestamp INTEGER)")
    con.executemany(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("g-1", "/home/alice/gooseproj", "goose test one", "", "user",
             "2026-01-15 09:00:00", "2026-01-15 10:00:00", 2, None),
            ("g-2", "/home/alice/gooseproj2", "goose test two", "", "user",
             "2026-01-14 09:00:00", "2026-01-14 10:00:00", 2, None),
        ])
    con.executemany(
        "INSERT INTO messages (session_id, role, content_json, timestamp) "
        "VALUES (?, ?, ?, ?)",
        [
            ("g-1", "user",
             json.dumps([{"type": "text", "text": "Explain the indexer"}]),
             1700000500),
            ("g-1", "assistant",
             json.dumps([{"type": "text",
                          "text": "Here is how the indexer works"}]),
             1700000501),
            ("g-2", "user",
             json.dumps([{"type": "text", "text": "Tune the scheduler"}]),
             1700000400),
        ])
    con.commit()
    con.close()

    # legacy pre-1.10 jsonl file (not imported into the db)
    write_jsonl(
        os.path.join(base, "20260101_1.jsonl"),
        [
            {"description": "legacy goose session",
             "working_dir": "/home/alice/legacy",
             "created_at": "2026-01-01 09:00:00",
             "updated_at": "2026-01-01 09:30:00"},
            {"id": "m1", "role": "user", "created": 1700000100,
             "content": [{"type": "text", "text": "Legacy user message"}]},
            {"id": "m2", "role": "assistant", "created": 1700000101,
             "content": [{"type": "text", "text": "Legacy reply"}]},
        ],
    )


def generate_omp():
    base = os.path.join(FIXTURES, "fixtures", "omp", "agent", "sessions")
    # current layout: 256-byte title slot line, then the session header
    d1 = os.path.join(base, "-home-alice-ws")
    os.makedirs(d1, exist_ok=True)
    p1 = os.path.join(d1, "20260216_102030_ompid1.jsonl")
    slot = json.dumps({"type": "title", "title": "omp test one",
                       "source": "auto"})
    slot = slot + " " * max(0, 255 - len(slot))
    with open(p1, "w") as f:
        f.write(slot + "\n")
        for obj in [
            {"type": "session", "version": 3, "id": "ompid1",
             "timestamp": "2026-02-16T10:20:30.000Z",
             "cwd": "/home/alice/ws"},
            {"type": "message", "id": "a1", "parentId": None,
             "timestamp": "2026-02-16T10:21:00.000Z",
             "message": {"role": "user",
                         "content": [{"type": "text",
                                      "text": "Fix the tokenizer"}]}},
            {"type": "message", "id": "a2", "parentId": "a1",
             "timestamp": "2026-02-16T10:22:00.000Z",
             "message": {"role": "assistant",
                         "content": [{"type": "text",
                                      "text": "I'll fix the tokenizer"}]}},
            {"type": "message", "id": "a3", "parentId": "a2",
             "timestamp": "2026-02-16T10:23:00.000Z",
             "message": {"role": "toolResult", "toolName": "exec",
                         "content": [{"type": "text",
                                      "text": "tool output ignored"}]}},
        ]:
            f.write(json.dumps(obj) + "\n")
    # legacy header-first layout (no title slot)
    write_jsonl(
        os.path.join(base, "-tmp-x", "20260217_090000_ompid2.jsonl"),
        [
            {"type": "session", "version": 1, "id": "ompid2",
             "timestamp": "2026-02-17T09:00:00.000Z", "cwd": "/home/bob/tmp"},
            {"type": "message", "id": "b1", "parentId": None,
             "timestamp": "2026-02-17T09:01:00.000Z",
             "message": {"role": "user",
                         "content": [{"type": "text",
                                      "text": "Second omp session"}]}},
            {"type": "message", "id": "b2", "parentId": "b1",
             "timestamp": "2026-02-17T09:02:00.000Z",
             "message": {"role": "assistant",
                         "content": [{"type": "text",
                                      "text": "Second omp reply"}]}},
        ],
    )


def generate_vibe():
    base = os.path.join(FIXTURES, "fixtures", "vibe", "logs", "session")
    for name, sid, title, wd, first in [
        ("session_20260216_103000_vb001", "vb001", "vibe test one",
         "/home/alice/vibeproj", "Summarize the logs"),
        ("session_20260217_090000_vb002", "vb002", None,
         "/home/alice/vibeproj2", "Plan the deploy"),
    ]:
        d = os.path.join(base, name)
        os.makedirs(d, exist_ok=True)
        meta = {"session_id": sid,
                "environment": {"working_directory": wd},
                "origin_directory": wd,
                "total_messages": 2,
                "updated_at": "2026-02-17T09:00:00Z"}
        if title:
            meta["title"] = title
        with open(os.path.join(d, "meta.json"), "w") as f:
            json.dump(meta, f)
        write_jsonl(
            os.path.join(d, "messages.jsonl"),
            [
                {"role": "system", "content": "system prompt ignored"},
                {"role": "user", "content": first},
                {"role": "assistant",
                 "content": [{"type": "text",
                              "text": f"Reply to: {first}"}]},
            ],
        )
        os.utime(os.path.join(d, "messages.jsonl"),
                 (1700000600, 1700000600))


def generate_hermes():
    base = os.path.join(FIXTURES, "fixtures", "hermes")
    os.makedirs(base, exist_ok=True)
    dbp = os.path.join(base, "state.db")
    if os.path.exists(dbp):
        os.remove(dbp)
    con = sqlite3.connect(dbp)
    con.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, "
        "title TEXT, cwd TEXT, model TEXT, started_at REAL, ended_at REAL, "
        "message_count INTEGER)")
    con.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, "
        "role TEXT, content TEXT, active INTEGER, timestamp REAL)")
    con.executemany(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("h-1", "cli", "hermes test one", "/home/alice/hproj",
             "hermes-4", 1700000700.0, 1700003600.0, 3),
            ("h-2", "cli", None, "/home/alice/hproj2",
             "hermes-4", 1700000800.0, None, 2),
        ])
    con.executemany(
        "INSERT INTO messages (session_id, role, content, active, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("h-1", "user", "Check the gateway", 1, 1700000700.0),
            ("h-1", "assistant", "Gateway is running", 1, 1700000701.0),
            ("h-1", "user", "old inactive message", 0, 1700000600.0),
            ("h-2", "user", "Restart the worker", 1, 1700000800.0),
            ("h-2", "assistant",
             "\x00json:" + json.dumps(
                 [{"type": "text", "text": "Worker restarted"}]),
             1, 1700000801.0),
        ])
    con.commit()
    con.close()


def generate_pi():
    base = os.path.join(FIXTURES, "fixtures", "pi", "agent", "sessions")
    # cwd "/home/alice/pi-proj" sanitized to a dash-wrapped dir name
    p1 = os.path.join(base, "--home-alice-pi-proj--",
                      "2026-01-15T10-00-00-000Z_pi-1.jsonl")
    write_jsonl(
        p1,
        [
            {"type": "session", "version": 3, "id": "pi-1",
             "timestamp": "2026-01-15T10:00:00.000Z",
             "cwd": "/home/alice/pi-proj"},
            {"type": "model_change", "id": "mm1", "parentId": None,
             "timestamp": "2026-01-15T10:00:00.100Z",
             "provider": "commandcode",
             "modelId": "poolside/laguna-s-2.1-free"},
            {"type": "message", "id": "u1", "parentId": "mm1",
             "timestamp": "2026-01-15T10:00:01.000Z",
             "message": {"role": "user",
                         "content": [{"type": "text",
                                      "text": "Refactor the pi search"}]}},
            # thinking parts must not leak into preview/grep
            {"type": "message", "id": "a1", "parentId": "u1",
             "timestamp": "2026-01-15T10:00:02.000Z",
             "message": {"role": "assistant",
                         "content": [
                             {"type": "thinking",
                              "thinking": "internal thought"},
                             {"type": "text",
                              "text": "I'll refactor the pi search"}]}},
            {"type": "message", "id": "t1", "parentId": "a1",
             "timestamp": "2026-01-15T10:00:03.000Z",
             "message": {"role": "toolResult",
                         "content": [{"type": "text", "text": "ok"}]}},
        ],
    )
    p2 = os.path.join(base, "--home-alice-pi-proj2--",
                      "2026-01-14T09-00-00-000Z_pi-2.jsonl")
    write_jsonl(
        p2,
        [
            {"type": "session", "version": 3, "id": "pi-2",
             "timestamp": "2026-01-14T09:00:00.000Z",
             "cwd": "/home/alice/pi-proj2"},
            {"type": "message", "id": "u2", "parentId": None,
             "timestamp": "2026-01-14T09:00:01.000Z",
             "message": {"role": "user",
                         "content": [{"type": "text",
                                      "text": "Plan the migration"}]}},
            {"type": "message", "id": "a2", "parentId": "u2",
             "timestamp": "2026-01-14T09:00:02.000Z",
             "message": {"role": "assistant",
                         "content": [{"type": "text",
                                      "text":
                                          "Migration plan: add an index"}]}},
        ],
    )
    os.utime(p1, (1700000000, 1700000000))
    os.utime(p2, (1700000010, 1700000010))


def _make_crush_db(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        os.remove(p)
    con = sqlite3.connect(p)
    con.execute(
        "CREATE TABLE sessions (id TEXT, parent_session_id TEXT, "
        "title TEXT, message_count INTEGER, prompt_tokens INTEGER, "
        "completion_tokens INTEGER, cost REAL, updated_at INTEGER, "
        "created_at INTEGER, summary_message_id TEXT, todos TEXT, "
        "channel TEXT)")
    con.execute(
        "CREATE TABLE messages (id TEXT, session_id TEXT, role TEXT, "
        "parts TEXT, model TEXT, created_at INTEGER, updated_at INTEGER, "
        "finished_at TEXT, provider TEXT, is_summary_message INTEGER, "
        "prism_model_id TEXT, prism_model_name TEXT, "
        "prism_hypercredit_savings REAL, prism_dollar_savings REAL)")
    return con


def generate_crush():
    base = os.path.join(FIXTURES, "fixtures", "crush", "share", "crush")
    os.makedirs(base, exist_ok=True)
    # data_dir uses a placeholder; tests rewrite it to the
    # copied location under the temporary HOME (the fixture
    # must not bake in the generating machine's paths)
    with open(os.path.join(base, "projects.json"), "w") as f:
        json.dump({"projects": [
            {"path": "/home/alice/crush-proj",
             "data_dir": "CRUSH_FIXTURE_ROOT/proj/.crush",
             "last_accessed": "2026-01-15T10:00:00Z"},
            {"path": "/home/alice/crush-proj2",
             "data_dir": "CRUSH_FIXTURE_ROOT/proj2/.crush",
             "last_accessed": "2026-01-14T09:00:00Z"},
        ]}, f)
    con = _make_crush_db(os.path.join(base, "proj", ".crush", "crush.db"))
    con.executemany(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("crush-1", None, "crush test one", 2, 0, 0, 0.0,
             1700000000, 1700000000, None, None, None),
            # subagent session: hidden from listings
            ("crush-child", "crush-1", "child", 1, 0, 0, 0.0,
             1700000100, 1700000100, None, None, None),
        ])
    con.executemany(
        "INSERT INTO messages VALUES "
        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("m1", "crush-1", "user",
             json.dumps([{"type": "text",
                          "data": {"text": "Plan the migration"}}]),
             "", 1700000000, 1700000000, None, None, 0,
             None, None, None, None),
            ("m2", "crush-1", "assistant",
             json.dumps([{"type": "text",
                          "data": {"text": "I will plan the migration"}}]),
             "", 1700000010, 1700000010, None, None, 0,
             None, None, None, None),
            ("mc1", "crush-child", "user",
             json.dumps([{"type": "text", "data": {"text": "child only"}}]),
             "", 1700000100, 1700000100, None, None, 0,
             None, None, None, None),
        ])
    con.commit()
    con.close()
    con = _make_crush_db(os.path.join(base, "proj2", ".crush", "crush.db"))
    con.executemany(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("crush-2", None, "crush test two", 1, 0, 0, 0.0,
             1700000020, 1700000020, None, None, None),
        ])
    con.executemany(
        "INSERT INTO messages VALUES "
        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("m3", "crush-2", "user",
             json.dumps([{"type": "text",
                          "data": {"text": "Check the lexer"}}]),
             "", 1700000020, 1700000020, None, None, 0,
             None, None, None, None),
        ])
    con.commit()
    con.close()


if __name__ == "__main__":
    generate_claude()
    generate_codex()
    generate_agy()
    generate_opencode()
    generate_devin()
    generate_aider()
    generate_goose()
    generate_omp()
    generate_vibe()
    generate_hermes()
    generate_pi()
    generate_crush()
    print("fixtures generated in", os.path.join(FIXTURES, "fixtures"))
