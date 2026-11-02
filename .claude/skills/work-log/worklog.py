#!/usr/bin/env python3
"""Keeps the work log: tickets and incidents, their branches, and the history of their states.

Usage:
  worklog.py status                     Reconcile with GitHub, print open work, the work that waits
                                        for a dev or prod test, and the open incidents.
  worklog.py show <key>                 Print one item as JSON.
  worklog.py list [--type T] [--key K] [--search TEXT] [--branch B] [--session-id ID]
                  [--open] [--status S] Print the matching items as JSON.
  worklog.py types                      Print the state machines as JSON.
  worklog.py add --ticket K --title T --branch B --session S --session-id ID [--worktree P]
                                        Add a branch. --key is the same as --ticket. The branch attaches
                                        to the item with that key, else to a new ticket.
  worklog.py update --branch B [--pr URL] [--status S] [--worktree P] [--session-id ID]
                    [--set K=V ...] [--force]
  worklog.py merged --branch B          Read the PR state of one branch. Print yes, no, or closed.
  worklog.py item add --type T --key K --title T [--set K=V ...]
  worklog.py item update --key K [--title T] [--status S] [--set K=V ...] [--force]
  worklog.py lock --branch B            Set sweepLockedAt. Exit 1 if another run holds a fresh lock.
  worklog.py unlock --branch B          Clear sweepLockedAt.

Options:
  --db <path>   Use another database. The env var WORKLOG_DB does the same. Tests use it.

The database is ~/.claude/work-log/worklog.db. Other skills read and write the log only through
this script, so the schema can change without a change to them.

A status change must be an edge of the state machine of the item or the branch (see `types`).
--force skips the edge check, but never the fields that a state requires.
--set K=V stores a field of another skill, for example sweepCheckedAt. An empty V removes it.

On the first run, the script imports ~/.claude/skills/work-log/data.json one time and renames it
to data.json.migrated.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME_DB = Path.home() / ".claude/work-log/worklog.db"
LEGACY_FILE = Path.home() / ".claude/skills/work-log/data.json"
PROJECTS_DIR = Path.home() / ".claude/projects"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
LOCK_STALE = timedelta(hours=2)

BRANCH_MACHINE = {
    "in-progress": ("in-review", "merged", "abandoned"),
    "in-review": ("in-progress", "merged", "abandoned"),
    "merged": ("dev-tested", "prod-tested"),
    "dev-tested": ("prod-tested", "merged"),
    "prod-tested": (),
    "abandoned": ("in-progress",),
}
BRANCH_OPEN = ("in-progress", "in-review")
BRANCH_FINISHED = ("prod-tested", "abandoned")
BRANCH_WAITING = {"merged": "dev test", "dev-tested": "prod test"}

# One entry for each item type. The first state of `transitions` is the initial state; `required` holds
# the fields a state needs, also with --force; `automatic` is (open, done) when branches set the status.
TYPES = {
    "ticket": {
        "transitions": {"open": ("done",), "done": ("open",)},
        "terminal": ("done",),
        "required": {},
        "automatic": ("open", "done"),
    },
    "incident": {
        "transitions": {
            "investigating": ("cause-found", "false-positive"),
            "cause-found": ("fixing", "investigating"),
            "fixing": ("monitoring", "cause-found"),
            "monitoring": ("resolved", "fixing"),
            "resolved": ("investigating",),
            "false-positive": ("investigating",),
        },
        "terminal": ("resolved", "false-positive"),
        "required": {"resolved": ("summary", "resolution")},
        "automatic": None,
    },
}

# The output puts the fields of `data` next to these names, so --set cannot use them.
RESERVED = {
    "type", "key", "title", "status", "createdAt", "branches", "transitions", "durations",
    "branch", "pr", "worktree", "session", "sessionId", "sessionCwd",
}

MIGRATIONS = [
    [
        """CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE COLLATE NOCASE,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            data TEXT NOT NULL DEFAULT '{}'
        )""",
        """CREATE TABLE branches (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES items(id),
            branch TEXT NOT NULL UNIQUE,
            pr TEXT,
            status TEXT NOT NULL,
            worktree TEXT,
            session TEXT,
            session_id TEXT,
            session_cwd TEXT,
            created_at TEXT NOT NULL,
            data TEXT NOT NULL DEFAULT '{}'
        )""",
        """CREATE TABLE transitions (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL REFERENCES items(id),
            branch_id INTEGER REFERENCES branches(id),
            status TEXT NOT NULL,
            entered_at TEXT NOT NULL
        )""",
        "CREATE INDEX transitions_owner ON transitions(item_id, branch_id, entered_at)",
    ],
]

LEGACY_DATES = (
    ("createdAt", "in-progress"),
    ("mergedAt", "merged"),
    ("devTestedAt", "dev-tested"),
    ("prodTestedAt", "prod-tested"),
    ("closedAt", "abandoned"),
)
LEGACY_DROP = {
    "ticket", "title", "branch", "pr", "status", "worktree", "session", "sessionId",
    "sessionCwd", "movedAt", "sweepLockedAt", *(field for field, _ in LEGACY_DATES),
}


class WorklogError(Exception):
    """A refused command. main prints the message and exits 1."""


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(moment: datetime) -> str:
    return moment.strftime(TIME_FORMAT)


def parse(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT).replace(tzinfo=timezone.utc)


def from_date(value: str | None) -> str | None:
    return f"{value[:10]}T00:00:00Z" if value else None


# --- Storage -------------------------------------------------------------------------------


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Hold the write lock from the first read, so a check and its write cannot interleave."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def migrate(conn: sqlite3.Connection) -> None:
    start = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, statements in enumerate(MIGRATIONS[start:], start=start + 1):
        with transaction(conn):
            if conn.execute("PRAGMA user_version").fetchone()[0] >= number:
                continue
            for statement in statements:
                conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {number}")


def add_transition(conn, item_id: int, branch_id: int | None, status: str, at: str) -> None:
    conn.execute(
        "INSERT INTO transitions (item_id, branch_id, status, entered_at) VALUES (?, ?, ?, ?)",
        (item_id, branch_id, status, at),
    )


def find_item(conn, key: str):
    return conn.execute("SELECT * FROM items WHERE key = ?", (key,)).fetchone()


def get_item(conn, key: str):
    item = find_item(conn, key)
    if item is None:
        raise WorklogError(f"No item with key {key}.")
    return item


def find_branch(conn, branch: str):
    return conn.execute(
        "SELECT b.*, i.key FROM branches b JOIN items i ON i.id = b.item_id WHERE b.branch = ?",
        (branch,),
    ).fetchone()


def get_branch(conn, branch: str):
    row = find_branch(conn, branch)
    if row is None:
        raise WorklogError(f"No entry for branch {branch}.")
    return row


def insert_item(conn, type_: str, key: str, title: str, at: str, data: dict) -> int:
    initial = next(iter(TYPES[type_]["transitions"]))
    item_id = conn.execute(
        "INSERT INTO items (type, key, title, status, created_at, data) VALUES (?, ?, ?, ?, ?, ?)",
        (type_, key, title, initial, at, json.dumps(data)),
    ).lastrowid
    add_transition(conn, item_id, None, initial, at)
    return item_id


# --- State machines ------------------------------------------------------------------------


def check_move(machine: dict, current: str, new: str, force: bool) -> None:
    if new not in machine:
        raise WorklogError(f"Unknown status {new}. Use one of: {', '.join(machine)}.")
    if force or new in machine[current]:
        return
    allowed = ", ".join(machine[current]) or "none, because it is a terminal state"
    raise WorklogError(f"{current} → {new} is not allowed. Next: {allowed}. Use --force to override.")


def check_required(type_: str, status: str, data: dict) -> None:
    missing = [field for field in TYPES[type_]["required"].get(status, ()) if not data.get(field)]
    if missing:
        raise WorklogError(
            f"{status} needs {', '.join(missing)}. Add them with --set {missing[0]}=<text>."
        )


def set_branch_status(conn, branch, status: str, force: bool = False) -> None:
    if branch["status"] == status:
        return
    check_move(BRANCH_MACHINE, branch["status"], status, force)
    at = stamp(now())
    conn.execute("UPDATE branches SET status = ? WHERE id = ?", (status, branch["id"]))
    add_transition(conn, branch["item_id"], branch["id"], status, at)
    refresh_item(conn, branch["item_id"], at)


def set_item_status(conn, item, status: str, force: bool) -> None:
    spec = TYPES[item["type"]]
    if spec["automatic"]:
        raise WorklogError(
            f"The status of a {item['type']} is automatic. Change the status of its branches."
        )
    if item["status"] == status:
        return
    check_move(spec["transitions"], item["status"], status, force)
    conn.execute("UPDATE items SET status = ? WHERE id = ?", (status, item["id"]))
    add_transition(conn, item["id"], None, status, stamp(now()))


def refresh_item(conn, item_id: int, at: str) -> None:
    """Set an automatic item to done when all its branches are finished, else to open."""
    item = conn.execute("SELECT type, status FROM items WHERE id = ?", (item_id,)).fetchone()
    automatic = TYPES[item["type"]]["automatic"]
    if not automatic:
        return
    statuses = [row[0] for row in conn.execute("SELECT status FROM branches WHERE item_id = ?", (item_id,))]
    open_state, done_state = automatic
    target = done_state if statuses and all(s in BRANCH_FINISHED for s in statuses) else open_state
    if target != item["status"]:
        conn.execute("UPDATE items SET status = ? WHERE id = ?", (target, item_id))
        add_transition(conn, item_id, None, target, at)


# --- Fields of other skills ----------------------------------------------------------------


def parse_set(pairs: list[str]) -> dict:
    changes = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not name:
            raise WorklogError(f"--set needs K=V, not {pair}.")
        if name in RESERVED:
            raise WorklogError(f"{name} is a column, not a field. Use its own option.")
        changes[name] = value or None
    return changes


def apply_set(data: dict, changes: dict) -> dict:
    for name, value in changes.items():
        if value is None:
            data.pop(name, None)
        else:
            data[name] = value
    return data


# --- Sessions and GitHub -------------------------------------------------------------------


def find_session_cwd(session_id: str) -> str:
    """Return the folder whose project directory holds the session file.

    The session can move to a worktree after it starts, so the first cwd in the
    file is not always the owner. The owner is the cwd that encodes to the name of
    the project directory.
    """
    for path in PROJECTS_DIR.glob(f"*/{session_id}.jsonl"):
        with path.open() as f:
            for line in f:
                try:
                    cwd = json.loads(line).get("cwd")
                except json.JSONDecodeError:
                    continue
                if cwd and re.sub(r"[^A-Za-z0-9]", "-", cwd) == path.parent.name:
                    return cwd
    raise WorklogError(f"No session file for id {session_id} under {PROJECTS_DIR}.")


def pr_state(pr: str) -> dict | None:
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "state,mergedAt,closedAt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def apply_pr_state(conn, branch_name: str, state: str) -> None:
    target = {"MERGED": "merged", "CLOSED": "abandoned"}.get(state)
    if target is None:
        return
    with transaction(conn):
        branch = get_branch(conn, branch_name)
        if branch["status"] in BRANCH_OPEN:
            set_branch_status(conn, branch, target)


def reconcile(conn) -> list[str]:
    """Read the PR state of each open branch. The gh calls run outside a transaction."""
    warnings = []
    rows = conn.execute(
        "SELECT b.branch, b.pr, i.key FROM branches b JOIN items i ON i.id = b.item_id "
        "WHERE b.pr IS NOT NULL AND b.status IN (?, ?)",
        BRANCH_OPEN,
    ).fetchall()
    for row in rows:
        state = pr_state(row["pr"])
        if state is None:
            warnings.append(f"⚠️  Could not read {row['pr']}. Entry {row['key']} is unchanged.")
            continue
        apply_pr_state(conn, row["branch"], state["state"])
    return warnings


def merged(conn, branch_name: str) -> str:
    """Return yes, no, or closed. A gh failure returns no, so a network error does not stop the hourly check."""
    branch = find_branch(conn, branch_name)
    if branch is None or not branch["pr"]:
        raise WorklogError(f"No entry with a PR for branch {branch_name}.")
    if branch["status"] not in BRANCH_OPEN:
        return "closed" if branch["status"] == "abandoned" else "yes"
    state = pr_state(branch["pr"])
    if state is None:
        print(f"Could not read {branch['pr']}.", file=sys.stderr)
        return "no"
    apply_pr_state(conn, branch_name, state["state"])
    return {"MERGED": "yes", "CLOSED": "closed"}.get(state["state"], "no")


# --- Import of data.json -------------------------------------------------------------------


def import_once(conn, path: Path) -> None:
    """Import the old JSON log if the database has no items yet, then rename the file."""
    if not path.exists():
        return
    try:
        log = json.loads(path.read_text())
        with transaction(conn):
            if conn.execute("SELECT 1 FROM items LIMIT 1").fetchone():
                return
            count = import_legacy(conn, log)
    except (KeyError, TypeError, ValueError) as error:
        raise WorklogError(
            f"Cannot import {path}: {error!r}. Fix the file, or move it away to start an empty log."
        ) from error
    path.rename(path.with_name(path.name + ".migrated"))
    print(f"Imported {count} branches from {path}.", file=sys.stderr)


def import_legacy(conn, log: dict) -> int:
    """Write the old entries as items, branches, and transitions. Run inside a transaction.

    The old history has no edge check, because old data can hold moves that the machine
    refuses. A current status with no date gets a transition at the time of the import.
    """
    imported_at = stamp(now())
    seen, entries = set(), []
    for entry, ready in [(e, False) for e in log.get("active", [])] + [(e, True) for e in log.get("readyToDelete", [])]:
        if entry["branch"] in seen:
            continue
        seen.add(entry["branch"])
        entry = dict(entry)
        if ready and entry["status"] == "merged":
            entry["status"] = "prod-tested"
            entry["prodTestedAt"] = entry.get("prodTestedAt") or entry.get("movedAt")
        entry["createdAt"] = from_date(entry.get("createdAt")) or imported_at
        entries.append(entry)
    first = {}
    for entry in entries:
        ticket = entry["ticket"].casefold()
        first[ticket] = min(first.get(ticket, entry["createdAt"]), entry["createdAt"])
    for entry in entries:
        item = find_item(conn, entry["ticket"])
        item_id = item["id"] if item else insert_item(
            conn, "ticket", entry["ticket"], entry.get("title") or entry["ticket"],
            first[entry["ticket"].casefold()], {})
        created = entry["createdAt"]
        data = {k: v for k, v in entry.items() if k not in LEGACY_DROP}
        branch_id = conn.execute(
            "INSERT INTO branches (item_id, branch, pr, status, worktree, session, session_id, "
            "session_cwd, created_at, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, entry["branch"], entry.get("pr"), entry["status"], entry.get("worktree"),
             entry.get("session"), entry.get("sessionId"), entry.get("sessionCwd"), created,
             json.dumps(data)),
        ).lastrowid
        history = sorted(
            ((from_date(entry[field]), status) for field, status in LEGACY_DATES if entry.get(field)),
            key=lambda pair: pair[0],
        )
        if not history or history[-1][1] != entry["status"]:
            history.append((imported_at, entry["status"]))
        for at, status in history:
            add_transition(conn, item_id, branch_id, status, at)
    for (item_id,) in conn.execute("SELECT id FROM items").fetchall():
        last = conn.execute(
            "SELECT max(entered_at) FROM transitions WHERE item_id = ? AND branch_id IS NOT NULL",
            (item_id,),
        ).fetchone()[0]
        refresh_item(conn, item_id, last)
    return len(entries)


# --- Reads ---------------------------------------------------------------------------------


def history(conn, item_id: int, branch_id: int | None) -> list[dict]:
    if branch_id is None:
        rows = conn.execute(
            "SELECT status, entered_at FROM transitions WHERE item_id = ? AND branch_id IS NULL "
            "ORDER BY entered_at, id",
            (item_id,),
        )
    else:
        rows = conn.execute(
            "SELECT status, entered_at FROM transitions WHERE branch_id = ? ORDER BY entered_at, id",
            (branch_id,),
        )
    return [{"status": row[0], "enteredAt": row[1]} for row in rows]


def durations(transitions: list[dict], terminal: tuple, at: datetime) -> dict:
    """Seconds in each state, summed over visits. A terminal last state does not count up."""
    totals = {}
    for index, step in enumerate(transitions):
        if index + 1 < len(transitions):
            end = parse(transitions[index + 1]["enteredAt"])
        elif step["status"] in terminal:
            break
        else:
            end = at
        seconds = int((end - parse(step["enteredAt"])).total_seconds())
        totals[step["status"]] = totals.get(step["status"], 0) + seconds
    return totals


def branch_json(conn, key: str, branch, at: datetime) -> dict:
    steps = history(conn, branch["item_id"], branch["id"])
    return {
        **json.loads(branch["data"]),
        "key": key,
        "branch": branch["branch"],
        "pr": branch["pr"],
        "status": branch["status"],
        "worktree": branch["worktree"],
        "session": branch["session"],
        "sessionId": branch["session_id"],
        "sessionCwd": branch["session_cwd"],
        "createdAt": branch["created_at"],
        "transitions": steps,
        "durations": durations(steps, BRANCH_FINISHED, at),
    }


def item_json(conn, item, at: datetime) -> dict:
    steps = history(conn, item["id"], None)
    branches = conn.execute(
        "SELECT * FROM branches WHERE item_id = ? ORDER BY created_at, id", (item["id"],)
    ).fetchall()
    return {
        **json.loads(item["data"]),
        "type": item["type"],
        "key": item["key"],
        "title": item["title"],
        "status": item["status"],
        "createdAt": item["created_at"],
        "transitions": steps,
        "durations": durations(steps, TYPES[item["type"]]["terminal"], at),
        "branches": [branch_json(conn, item["key"], b, at) for b in branches],
    }


def like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_items(conn, args) -> list:
    where, params = [], []
    if args.type:
        where.append("i.type = ?")
        params.append(args.type)
    if args.key:
        where.append("i.key = ? COLLATE NOCASE")
        params.append(args.key)
    if args.branch:
        where.append("b.branch = ?")
        params.append(args.branch)
    if args.session_id:
        where.append("b.session_id = ?")
        params.append(args.session_id)
    if args.status:
        where.append("(i.status = ? OR b.status = ?)")
        params += [args.status, args.status]
    if args.open:
        terminal = [(t, s) for t, spec in TYPES.items() for s in spec["terminal"]]
        # A finished item stays open while one of its branches is not finished.
        where.append("((i.type, i.status) NOT IN (VALUES " + ", ".join("(?, ?)" for _ in terminal)
                     + ") OR b.status NOT IN (" + ", ".join("?" for _ in BRANCH_FINISHED) + "))")
        params += [value for pair in terminal for value in pair] + list(BRANCH_FINISHED)
    if args.search:
        # json_tree reads values only, so a key name such as "summary" does not match.
        where.append(
            "(i.title LIKE ? ESCAPE '\\' "
            "OR EXISTS (SELECT 1 FROM json_tree(i.data) WHERE atom LIKE ? ESCAPE '\\') "
            "OR EXISTS (SELECT 1 FROM json_tree(b.data) WHERE atom LIKE ? ESCAPE '\\'))"
        )
        params += [like(args.search)] * 3
    sql = "SELECT DISTINCT i.* FROM items i LEFT JOIN branches b ON b.item_id = i.id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY i.created_at, i.id"
    return conn.execute(sql, params).fetchall()


def types_json() -> dict:
    machines = {
        "branch": {
            "transitions": {s: list(n) for s, n in BRANCH_MACHINE.items()},
            "terminal": list(BRANCH_FINISHED),
            "required": {},
            "automatic": None,
        }
    }
    for name, spec in TYPES.items():
        machines[name] = {
            "transitions": {s: list(n) for s, n in spec["transitions"].items()},
            "terminal": list(spec["terminal"]),
            "required": {s: list(f) for s, f in spec["required"].items()},
            "automatic": list(spec["automatic"]) if spec["automatic"] else None,
        }
    return machines


def print_status(conn, warnings: list[str]) -> None:
    at = now()
    rows = conn.execute(
        "SELECT b.*, i.key, i.title FROM branches b JOIN items i ON i.id = b.item_id "
        "ORDER BY b.created_at, b.id"
    ).fetchall()
    open_work = [r for r in rows if r["status"] in BRANCH_OPEN]
    if open_work:
        print("📋 Open work")
        for r in open_work:
            days = (at - parse(r["created_at"])).days
            print(f"  {r['key']:<10} {r['title'][:42]:<44}{r['status']:<13}{days} days")
            resume = f"claude --resume \"{r['session_id'] or r['session']}\""
            if r["session_cwd"]:
                resume = f"cd \"{r['session_cwd']}\" && {resume}"
            print(f"  {'':<10} resume: {resume}     PR: {r['pr'] or '—'}")
    else:
        print("📋 Open work: none")
    waiting = [r for r in rows if r["status"] in BRANCH_WAITING]
    if waiting:
        print("\n🧪 Waiting for a test")
        for r in waiting:
            since = history(conn, r["item_id"], r["id"])[-1]["enteredAt"][:10]
            step = BRANCH_WAITING[r["status"]]
            print(f"  {r['key']:<10} {r['title'][:42]:<44}{r['status']:<13}since {since}   next: {step}")
    incidents = [
        i for i in conn.execute("SELECT * FROM items WHERE type = 'incident' ORDER BY created_at, id")
        if i["status"] not in TYPES["incident"]["terminal"]
    ]
    if incidents:
        print("\n🚨 Open incidents")
        for i in incidents:
            days = (at - parse(i["created_at"])).days
            print(f"  {i['key']:<10} {i['title'][:42]:<44}{i['status']:<13}{days} days")
    for w in warnings:
        print(w)


# --- Commands ------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="The work log of tickets and incidents")
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("WORKLOG_DB") or HOME_DB))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("types")
    show = sub.add_parser("show")
    show.add_argument("key")
    found = sub.add_parser("list")
    found.add_argument("--type", choices=TYPES)
    found.add_argument("--key")
    found.add_argument("--search")
    found.add_argument("--branch")
    found.add_argument("--session-id")
    found.add_argument("--open", action="store_true")
    found.add_argument("--status")
    add = sub.add_parser("add")
    add.add_argument("--ticket", "--key", dest="key", required=True)
    for name in ("--title", "--branch", "--session", "--session-id"):
        add.add_argument(name, required=True)
    add.add_argument("--worktree")
    update = sub.add_parser("update")
    update.add_argument("--branch", required=True)
    update.add_argument("--pr")
    update.add_argument("--status", choices=BRANCH_MACHINE)
    update.add_argument("--worktree")
    update.add_argument("--session-id")
    update.add_argument("--set", dest="changes", action="append", default=[])
    update.add_argument("--force", action="store_true")
    for name in ("merged", "lock", "unlock"):
        sub.add_parser(name).add_argument("--branch", required=True)
    item = sub.add_parser("item").add_subparsers(dest="item_cmd", required=True)
    item_add = item.add_parser("add")
    item_add.add_argument("--type", choices=TYPES, required=True)
    item_add.add_argument("--key", required=True)
    item_add.add_argument("--title", required=True)
    item_add.add_argument("--set", dest="changes", action="append", default=[])
    item_update = item.add_parser("update")
    item_update.add_argument("--key", required=True)
    item_update.add_argument("--title")
    item_update.add_argument("--status")
    item_update.add_argument("--set", dest="changes", action="append", default=[])
    item_update.add_argument("--force", action="store_true")
    return parser


def cmd_add(conn, args) -> None:
    cwd = find_session_cwd(args.session_id)
    with transaction(conn):
        if find_branch(conn, args.branch):
            raise WorklogError(f"An entry for branch {args.branch} exists already. Use update.")
        at = stamp(now())
        item = find_item(conn, args.key)
        item_id = item["id"] if item else insert_item(conn, "ticket", args.key, args.title, at, {})
        branch_id = conn.execute(
            "INSERT INTO branches (item_id, branch, status, worktree, session, session_id, "
            "session_cwd, created_at) VALUES (?, ?, 'in-progress', ?, ?, ?, ?, ?)",
            (item_id, args.branch, args.worktree, args.session, args.session_id, cwd, at),
        ).lastrowid
        add_transition(conn, item_id, branch_id, "in-progress", at)
        refresh_item(conn, item_id, at)
    print(f"Added {args.key} ({args.branch}).")


def cmd_update(conn, args) -> None:
    cwd = find_session_cwd(args.session_id) if args.session_id else None
    changes = parse_set(args.changes)
    with transaction(conn):
        branch = get_branch(conn, args.branch)
        data = apply_set(json.loads(branch["data"]), changes)
        conn.execute(
            "UPDATE branches SET pr = COALESCE(?, pr), worktree = COALESCE(?, worktree), "
            "session_id = COALESCE(?, session_id), session_cwd = COALESCE(?, session_cwd), data = ? "
            "WHERE id = ?",
            (args.pr, args.worktree, args.session_id, cwd, json.dumps(data), branch["id"]),
        )
        if args.status:
            set_branch_status(conn, branch, args.status, args.force)
    print(f"Updated {branch['key']} ({args.branch}).")


def cmd_item_add(conn, args) -> None:
    data = apply_set({}, parse_set(args.changes))
    with transaction(conn):
        if find_item(conn, args.key):
            raise WorklogError(f"An item with key {args.key} exists already. Use item update.")
        insert_item(conn, args.type, args.key, args.title, stamp(now()), data)
    print(f"Added {args.type} {args.key}.")


def cmd_item_update(conn, args) -> None:
    changes = parse_set(args.changes)
    with transaction(conn):
        item = get_item(conn, args.key)
        data = apply_set(json.loads(item["data"]), changes)
        check_required(item["type"], args.status or item["status"], data)
        conn.execute(
            "UPDATE items SET title = COALESCE(?, title), data = ? WHERE id = ?",
            (args.title, json.dumps(data), item["id"]),
        )
        if args.status:
            set_item_status(conn, item, args.status, args.force)
    print(f"Updated {item['type']} {args.key}.")


def cmd_lock(conn, args) -> None:
    at = now()
    with transaction(conn):
        branch = get_branch(conn, args.branch)
        held = json.loads(branch["data"]).get("sweepLockedAt")
        try:
            fresh = held is not None and parse(held) > at - LOCK_STALE
        except ValueError:
            fresh = False
        if fresh:
            raise WorklogError(f"Branch {args.branch} is locked since {held}. Another run owns it.")
        conn.execute(
            "UPDATE branches SET data = json_set(data, '$.sweepLockedAt', ?) WHERE id = ?",
            (stamp(at), branch["id"]),
        )
    print("locked")


def cmd_unlock(conn, args) -> None:
    with transaction(conn):
        branch = get_branch(conn, args.branch)
        conn.execute(
            "UPDATE branches SET data = json_remove(data, '$.sweepLockedAt') WHERE id = ?",
            (branch["id"],),
        )
    print("unlocked")


def run(conn, args) -> int:
    if args.cmd == "status":
        print_status(conn, reconcile(conn))
    elif args.cmd == "types":
        print(json.dumps(types_json(), indent=2))
    elif args.cmd == "show":
        print(json.dumps(item_json(conn, get_item(conn, args.key), now()), indent=2))
    elif args.cmd == "list":
        at = now()
        print(json.dumps([item_json(conn, i, at) for i in list_items(conn, args)], indent=2))
    elif args.cmd == "add":
        cmd_add(conn, args)
    elif args.cmd == "update":
        cmd_update(conn, args)
    elif args.cmd == "merged":
        print(merged(conn, args.branch))
    elif args.cmd == "lock":
        cmd_lock(conn, args)
    elif args.cmd == "unlock":
        cmd_unlock(conn, args)
    elif args.item_cmd == "add":
        cmd_item_add(conn, args)
    else:
        cmd_item_update(conn, args)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        conn = connect(args.db)
        try:
            if args.db == HOME_DB:
                import_once(conn, LEGACY_FILE)
            return run(conn, args)
        finally:
            conn.close()
    except WorklogError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
