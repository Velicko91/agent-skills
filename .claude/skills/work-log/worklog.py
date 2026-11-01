#!/usr/bin/env python3
"""Keeps the work log of /implement-ticket.

Usage:
  worklog.py status                     Reconcile with GitHub, age finished entries, print open work
                                        and the work that waits for a dev or prod test.
  worklog.py show <ticket>              Print the entries of one ticket as JSON.
  worklog.py add --ticket T --title T --branch B --session S --session-id ID [--worktree P]
  worklog.py update --branch B [--pr URL] [--status S] [--worktree P] [--session-id ID]
  worklog.py merged --branch B          Read the PR state of one entry. Print yes, no, or closed.
  worklog.py clean --confirmed          Empty readyToDelete. Only after the user said so.

Options:
  --file <path>   Use another log file. Tests use it.

The log is at ~/.claude/skills/work-log/data.json.
/sweep-pr-comments and /open-claude-session read it there. The script keeps every
field it does not know, for example sweepLockedAt from /sweep-pr-comments.

--session-id also sets sessionCwd: the folder that owns the session. `claude --resume`
finds a session only from that folder.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_FILE = Path.home() / ".claude/skills/work-log/data.json"
PROJECTS_DIR = Path.home() / ".claude/projects"
STATUSES = ("in-progress", "in-review", "merged", "dev-tested", "prod-tested", "abandoned")
OPEN = ("in-progress", "in-review")
VERIFY = {"merged": ("mergedAt", "dev test"), "dev-tested": ("devTestedAt", "prod test")}
FINISHED = ("prod-tested", "abandoned")
STATUS_DATE = {"merged": "mergedAt", "dev-tested": "devTestedAt", "prod-tested": "prodTestedAt"}
AGE_DAYS = 30
EMPTY_LOG = {
    "version": 1,
    "_comment": "Work log for /implement-ticket. Local state. Never committed.",
    "active": [],
    "readyToDelete": [],
}


def today() -> date:
    return datetime.now(timezone.utc).date()


def session_cwd(session_id: str) -> str | None:
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
    return None


def set_session(entry: dict, session_id: str) -> bool:
    cwd = session_cwd(session_id)
    if cwd is None:
        print(f"No session file for id {session_id} under {PROJECTS_DIR}.", file=sys.stderr)
        return False
    entry["sessionId"] = session_id
    entry["sessionCwd"] = cwd
    return True


def load(path: Path) -> dict:
    if not path.exists():
        save(path, EMPTY_LOG)
        print(f"Created an empty work log: {path}")
    return json.loads(path.read_text())


def save(path: Path, log: dict) -> None:
    # Write to a temporary file and move it over the log, so a crash never leaves half a file.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(log, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def pr_state(pr: str) -> dict | None:
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "state,mergedAt,closedAt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def reconcile(log: dict) -> list[str]:
    warnings = []
    for entry in log["active"]:
        if not entry.get("pr") or entry.get("status") not in OPEN:
            continue
        state = pr_state(entry["pr"])
        if state is None:
            warnings.append(f"⚠️  Could not read {entry['pr']}. Entry {entry['ticket']} is unchanged.")
            continue
        apply_state(entry, state)
    return warnings


def apply_state(entry: dict, state: dict) -> None:
    if state["state"] == "MERGED":
        entry["status"] = "merged"
        entry["mergedAt"] = state["mergedAt"][:10]
    elif state["state"] == "CLOSED":
        entry["status"] = "abandoned"
        entry["mergedAt"] = None
        entry["closedAt"] = (state.get("closedAt") or today().isoformat())[:10]


def merged(log: dict, branch: str) -> str | None:
    """Return yes, no, or closed for the PR of one entry. Return None if the entry has no PR.

    A gh failure returns no, so a network error does not stop the hourly check.
    """
    matches = [e for e in log["active"] if e["branch"] == branch]
    if not matches or not matches[0].get("pr"):
        return None
    entry = matches[0]
    if entry.get("status") not in OPEN:
        return "closed" if entry.get("status") == "abandoned" else "yes"
    state = pr_state(entry["pr"])
    if state is None:
        print(f"Could not read {entry['pr']}.", file=sys.stderr)
        return "no"
    apply_state(entry, state)
    return {"MERGED": "yes", "CLOSED": "closed"}.get(state["state"], "no")


def finished_on(entry: dict) -> date | None:
    """A merged entry is not finished until its prod test, so only these dates count."""
    stamp = entry.get("prodTestedAt") or entry.get("closedAt")
    return date.fromisoformat(stamp[:10]) if stamp else None


def age(log: dict) -> int:
    keep, moved = [], 0
    for entry in log["active"]:
        done = finished_on(entry)
        if entry.get("status") in FINISHED and done and (today() - done).days > AGE_DAYS:
            entry["movedAt"] = today().isoformat()
            log["readyToDelete"].append(entry)
            moved += 1
        else:
            keep.append(entry)
    log["active"] = keep
    return moved


def print_status(log: dict, warnings: list[str], moved: int) -> None:
    open_work = [e for e in log["active"] if e.get("status") in OPEN]
    if open_work:
        print("📋 Open work")
        for e in open_work:
            days = (today() - date.fromisoformat(e["createdAt"][:10])).days
            print(f"  {e['ticket']:<10}{e['title'][:42]:<44}{e['status']:<13}{days} days")
            resume = f"claude --resume \"{e.get('sessionId') or e['session']}\""
            if e.get("sessionCwd"):
                resume = f"cd \"{e['sessionCwd']}\" && {resume}"
            print(f"  {'':<10}resume: {resume}     PR: {e.get('pr') or '—'}")
    else:
        print("📋 Open work: none")
    verify = [e for e in log["active"] if e.get("status") in VERIFY]
    if verify:
        print("\n🧪 Waiting for a test")
        for e in verify:
            field, step = VERIFY[e["status"]]
            print(f"  {e['ticket']:<10}{e['title'][:42]:<44}{e['status']:<13}since {e.get(field) or '—'}   next: {step}")
    for w in warnings:
        print(w)
    if moved:
        print(f"Moved {moved} finished entries to readyToDelete.")
    ready = log["readyToDelete"]
    if ready:
        print(f"\n🗑️  {len(ready)} entries in readyToDelete, all finished over {AGE_DAYS} days ago:")
        for e in ready:
            print(f"    {e['ticket']:<10}{e['status']} {finished_on(e) or '—'}")
        print('\nSay "clean the work log" to remove them. I will not delete anything otherwise.')


def main() -> int:
    parser = argparse.ArgumentParser(description="Work log of /implement-ticket")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    show = sub.add_parser("show")
    show.add_argument("ticket")
    add = sub.add_parser("add")
    for name in ("--ticket", "--title", "--branch", "--session"):
        add.add_argument(name, required=True)
    add.add_argument("--worktree")
    add.add_argument("--session-id", required=True)
    update = sub.add_parser("update")
    update.add_argument("--branch", required=True)
    update.add_argument("--pr")
    update.add_argument("--status", choices=STATUSES)
    update.add_argument("--worktree")
    update.add_argument("--session-id")
    check = sub.add_parser("merged")
    check.add_argument("--branch", required=True)
    clean = sub.add_parser("clean")
    clean.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()

    log = load(args.file)

    if args.cmd == "status":
        warnings = reconcile(log)
        moved = age(log)
        save(args.file, log)
        print_status(log, warnings, moved)
    elif args.cmd == "show":
        print(json.dumps([e for e in log["active"] if e["ticket"] == args.ticket], indent=2))
    elif args.cmd == "add":
        if any(e["branch"] == args.branch for e in log["active"]):
            print(f"An entry for branch {args.branch} exists already. Use update.", file=sys.stderr)
            return 1
        entry = {
            "ticket": args.ticket, "title": args.title, "branch": args.branch,
            "worktree": args.worktree, "session": args.session, "pr": None,
            "status": "in-progress", "createdAt": today().isoformat(), "mergedAt": None,
        }
        if not set_session(entry, args.session_id):
            return 1
        log["active"].append(entry)
        save(args.file, log)
        print(f"Added {args.ticket} ({args.branch}).")
    elif args.cmd == "update":
        matches = [e for e in log["active"] if e["branch"] == args.branch]
        if not matches:
            print(f"No active entry for branch {args.branch}.", file=sys.stderr)
            return 1
        for field in ("pr", "status", "worktree"):
            if getattr(args, field) is not None:
                matches[0][field] = getattr(args, field)
        stamp = STATUS_DATE.get(args.status)
        if stamp and not matches[0].get(stamp):
            matches[0][stamp] = today().isoformat()
        if args.session_id and not set_session(matches[0], args.session_id):
            return 1
        save(args.file, log)
        print(f"Updated {matches[0]['ticket']} ({args.branch}).")
    elif args.cmd == "merged":
        answer = merged(log, args.branch)
        if answer is None:
            print(f"No active entry with a PR for branch {args.branch}.", file=sys.stderr)
            return 1
        save(args.file, log)
        print(answer)
    elif args.cmd == "clean":
        if not args.confirmed:
            print("Refused: clean needs --confirmed, given only after the user asked.", file=sys.stderr)
            return 1
        removed = len(log["readyToDelete"])
        log["readyToDelete"] = []
        save(args.file, log)
        print(f"Removed {removed} entries from readyToDelete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
