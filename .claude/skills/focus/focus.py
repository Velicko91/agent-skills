#!/usr/bin/python3
"""Ranks open work and incidents, flags idle items, and pings for them.

Usage:
  focus.py                       Print the ranked list of open items.
  focus.py --idle                Print only the items that need attention.
  focus.py --ping                Send a cmux notification for each item that needs attention
                                 and was not pinged in the last repingHours, at most pingMax items,
                                 highest rank first. For the loop job.
  focus.py pause <key> <dur>     Hide an item for a duration: 30m, 4h, 2d, 1w.
  focus.py resume <key>          End a pause now.
  focus.py pauses                List the active pauses.

<key> is a ticket key (PROJ-1234) or an incident reference (INC-123).

Sources, all read-only:
  ~/.claude/skills/work-log/worklog.py list --open           work sessions
  ~/.claude/skills/investigate-incident/incident-log.local.md resolved incidents
  cmux workspaces                                            sessions and their last activity
  cmux sessions + Claude transcripts                         reminders set with CronCreate

The script writes only its own data.json: the pauses and the last ping times.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("FOCUS_DATA", HERE / "data.json"))
EXAMPLE = HERE / "data.example.json"
WORKLOG = Path(os.environ.get("FOCUS_WORKLOG", Path.home() / ".claude/skills/work-log/worklog.py"))
INCIDENT_LOG = Path(os.environ.get(
    "FOCUS_INCIDENT_LOG", Path.home() / ".claude/skills/investigate-incident/incident-log.local.md"))
CMUX = os.environ.get("FOCUS_CMUX") or shutil.which("cmux") or "/Applications/cmux.app/Contents/Resources/bin/cmux"
# Written by cmux-pause in this folder: workspace id -> {"until": ISO time}
PAUSE_STATE = Path(os.environ.get("CMUX_PAUSE_STATE", Path.home() / ".local/state/cmux-pause/pauses.json"))

INCIDENT_RE = re.compile(r"^(INC-\d+)\b", re.I)
KEY_RE = re.compile(r"^([A-Z][A-Z0-9]+-\d+)\b")
PAUSED_RE = re.compile(r"\bpaused\b", re.I)  # the word in a workspace title pauses the item
# The CronCreate result, for example: Scheduled one-shot task a95d2060 (0 10 2 11 *). Next run: Nov 2 9:59am.
SCHEDULED_RE = re.compile(rb"Scheduled [\w -]*?task ([0-9a-f]{8}) \([^)]*\)\. Next run: (\w{3} \d{1,2} \d{1,2}:\d{2}[ap]m)")
CRON_DELETE_RE = re.compile(rb'"name":\s*"CronDelete",\s*"input":\s*\{[^}]*"id":\s*"([0-9a-f]{8})"')
NEEDS_INPUT = ("Needs input", "Waiting")
OPEN_STATUSES = ("in-progress", "in-review", "merged", "dev-tested")
TEST_WAIT = {"merged": "dev test", "dev-tested": "prod test"}

NOW = datetime.now(timezone.utc)


def die(msg):
    print(f"error: {msg}")
    sys.exit(1)


def load_data():
    if not DATA.exists():
        die(f"{DATA} is missing. Copy {EXAMPLE.name} to data.json and set config.boards.")
    data = json.loads(DATA.read_text())
    data.setdefault("state", {}).setdefault("pauses", {})
    data["state"].setdefault("pinged", {})
    return data


def save_data(data):
    fd, tmp = tempfile.mkstemp(dir=DATA.parent, prefix=".data.", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, DATA)


def parse_time(value):
    if not value:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_duration(text):
    m = re.fullmatch(r"(\d+)([mhdw])", text.strip().lower())
    if not m:
        die(f"bad duration '{text}': use 30m, 4h, 2d, or 1w")
    n = int(m.group(1))
    return {"m": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n), "w": timedelta(weeks=n)}[m.group(2)]


def age(dt):
    if dt is None:
        return "?"
    s = int((NOW - dt).total_seconds())
    if s < 3600:
        return f"{max(s // 60, 0)}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def cmux_json(*args):
    try:
        out = subprocess.run([CMUX, "--json", *args], capture_output=True, text=True, timeout=20,
                             env={**os.environ, "CMUX_QUIET": "1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        die(f"cmux failed: {e}")
    if out.returncode != 0:
        die(f"cmux {' '.join(args)} failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def workspaces():
    """title -> {ref, last (datetime or None), state, paused, remind, until (datetime or None)}"""
    result = {}
    remind = reminders()
    until = cmux_pauses()
    for w in cmux_json("workspace", "list").get("workspaces", []):
        title = w.get("custom_title") or w.get("title") or ""
        result[title] = {"ref": w.get("ref"), "id": w.get("id"),
                         "last": parse_time(w.get("latest_submitted_at")), "state": "",
                         "paused": bool(PAUSED_RE.search(title)),
                         "remind": remind.get((w.get("id") or "").upper()),
                         "until": until.get((w.get("id") or "").upper())}
    try:
        out = subprocess.run([CMUX, "top", "--all", "--format", "tsv"], capture_output=True,
                             text=True, timeout=20, env={**os.environ, "CMUX_QUIET": "1"}).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    tags = {}
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) > 6 and f[3] == "tag" and ":tag:" in f[4]:
            owner, key = f[4].rsplit(":tag:", 1)
            if key in ("claude_code", "agent"):
                tags.setdefault(owner.split(":", 1)[-1], []).append(f[6])
    for w in result.values():
        states = tags.get(w["id"], [])
        w["state"] = next((s for s in NEEDS_INPUT if s in states), "")
    return result


def cmux_pauses():
    """workspace id -> the end of its cmux-pause pause, for pauses that have not ended."""
    try:
        state = json.loads(PAUSE_STATE.read_text())
    except (FileNotFoundError, ValueError):
        return {}
    ends = {ws.upper(): parse_time(e.get("until")) for ws, e in state.items()}
    return {ws: t for ws, t in ends.items() if t and t > NOW}


def next_run(text):
    """'Nov 2 9:59am' in local time -> the next such datetime in UTC."""
    local = datetime.now().astimezone()
    t = datetime.strptime(f"{local.year} {text}", "%Y %b %d %I:%M%p").replace(tzinfo=local.tzinfo)
    if t < local - timedelta(days=180):  # a December run read in January
        t = t.replace(year=t.year + 1)
    return t.astimezone(timezone.utc)


def reminders():
    """workspace id -> the earliest future run of a CronCreate reminder of a live session in it.

    A CronCreate job lives only in its Claude process, so only sessions with a live pid count.
    The run time is the one CronCreate printed, so a recurring job counts until that first run.
    """
    try:
        sessions = cmux_json("sessions", "list", "--agent", "claude").get("sessions", [])
    except SystemExit:
        return {}
    result = {}
    for s in sessions:
        path, ws_id = s.get("transcript_path"), (s.get("workspace_id") or "").upper()
        if not (path and ws_id and s.get("stored_pid_exists")) or not os.path.exists(path):
            continue
        # Search the raw bytes: a transcript can be tens of MB, and most have no reminder.
        text = Path(path).read_bytes()
        if b"Next run:" not in text:
            continue
        runs = {job.decode(): when.decode() for job, when in SCHEDULED_RE.findall(text)}
        deleted = {j.decode() for j in CRON_DELETE_RE.findall(text)}
        future = [t for job, when in runs.items() if job not in deleted
                  for t in [next_run(when)] if t > NOW]
        if future:
            result[ws_id] = min([*future, result.get(ws_id, future[0])])
    return result


def resolved_incidents():
    if not INCIDENT_LOG.exists():
        return set()
    return {m.upper() for m in re.findall(r"^## [^·]*·\s*(INC-\d+)", INCIDENT_LOG.read_text(), re.M)}


def work_branches():
    """Return (item title, branch) for each branch of the open items. Only worklog.py reads the log."""
    try:
        out = subprocess.run([str(WORKLOG), "list", "--open"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        die(f"cannot run {WORKLOG}: {e}")
    if out.returncode != 0:
        die(f"{WORKLOG} list --open failed: {out.stderr.strip()}")
    return [(item.get("title"), branch) for item in json.loads(out.stdout) for branch in item["branches"]]


def board_of(ticket, boards):
    prefix = ticket.split("-", 1)[0].upper()
    return prefix if prefix in boards else "other"


def collect(config):
    idle = config["idle"]
    boards = [b.upper() for b in config["boards"]]
    ws = workspaces()
    items = []

    resolved = resolved_incidents()
    for title, w in ws.items():
        m = INCIDENT_RE.match(title)
        if not m or m.group(1).upper() in resolved:
            continue
        key = m.group(1).upper()
        if any(i["key"] == key for i in items):
            continue
        items.append({"key": key, "tier": "incident", "title": title, "status": "open",
                      "ref": w["ref"], "last": w["last"], "state": w["state"], "paused": w["paused"],
                      "remind": w["remind"], "until": w["until"],
                      "limit": timedelta(hours=idle["incidentHours"]), "why": "no activity"})

    for title, e in work_branches():
        status = e.get("status")
        if status not in OPEN_STATUSES:
            continue
        ticket = e.get("key") or ""
        w = ws.get(e.get("session") or "") or next(
            (v for t, v in ws.items() if t == ticket or t.startswith((ticket + "-", ticket + " "))), None)
        item = {"key": ticket, "title": title or e.get("branch"), "status": status,
                "ref": w["ref"] if w else None, "state": w["state"] if w else "",
                "paused": bool(w and w["paused"]), "remind": w["remind"] if w else None,
                "until": w["until"] if w else None}
        if status in TEST_WAIT:
            since = (e.get("transitions") or [{}])[-1].get("enteredAt")
            item.update(tier="prod-test", last=parse_time(since),
                        limit=timedelta(days=idle["testWaitDays"]), why=f"waits for a {TEST_WAIT[status]}")
        else:
            last = (w and w["last"]) or parse_time(e.get("createdAt"))
            item.update(tier=board_of(ticket, boards), last=last,
                        limit=timedelta(days=idle["sessionDays"]), why="no activity")
        items.append(item)

    wait = timedelta(minutes=idle["waitingMinutes"])
    for i in items:
        reasons = []
        if i["state"] and (i["last"] is None or NOW - i["last"] >= wait):
            reasons.append(f"session {i['state'].lower()}")
        if i["last"] is not None and NOW - i["last"] >= i["limit"]:
            reasons.append(f"{i['why']} for {age(i['last'])}")
        i["attention"] = "; ".join(reasons)

    order = {t.upper() if t not in ("incident", "prod-test", "other") else t: n
             for n, t in enumerate(config["tiers"])}
    items.sort(key=lambda i: (order.get(i["tier"], len(order)), 0 if i["attention"] else 1,
                              i["last"] or NOW))
    return items


def is_paused(item, pauses):
    return (item["paused"] or item["remind"] is not None or item["until"] is not None
            or item["key"] in pauses)


def active_pauses(state):
    pauses = state["pauses"]
    for key in [k for k, v in pauses.items() if parse_time(v) <= NOW]:
        del pauses[key]
    return pauses


def print_items(items, pauses):
    if not items:
        print("No open items.")
        return
    # Paused items go last, so the numbers at the top are the work to do.
    items = sorted(items, key=lambda i: is_paused(i, pauses))
    print(f"{'#':>2}  {'tier':<9} {'key':<10} {'status':<11} {'last':>5}  attention / title")
    for n, i in enumerate(items, 1):
        note = i["attention"] or i["title"]
        if i["paused"]:
            note = "paused (workspace title)"
        elif i["until"]:
            note = f"paused until {i['until'].astimezone().strftime('%Y-%m-%d %H:%M %Z')} (cmux-pause)"
        elif i["remind"]:
            note = f"paused: reminder at {i['remind'].astimezone().strftime('%Y-%m-%d %H:%M %Z')}"
        elif i["key"] in pauses:
            note = f"paused until {pauses[i['key']][:16].replace('T', ' ')} UTC"
        elif i["attention"]:
            note = f"!! {note} · /focus pause {i['key']} <30m|4h|2d|1w>"
        print(f"{n:>2}  {i['tier']:<9} {i['key']:<10} {i['status']:<11} {age(i['last']):>5}  {note}")


def ping(items, data):
    state = data["state"]
    pauses = active_pauses(state)
    repeat = timedelta(hours=data["config"]["repingHours"])
    sent = []
    due = [i for i in items if i["attention"] and not is_paused(i, pauses)]
    for i in due[:data["config"]["pingMax"]]:
        last = parse_time(state["pinged"].get(i["key"]))
        if last and NOW - last < repeat:
            continue
        args = [CMUX, "notify", "--title", f"focus: {i['key']} ({i['tier']})",
                "--body", f"{i['attention']}. Pause it: /focus pause {i['key']} <30m|4h|2d|1w>"]
        if i["ref"]:
            args += ["--workspace", i["ref"]]
        subprocess.run(args, capture_output=True, timeout=20, env={**os.environ, "CMUX_QUIET": "1"})
        state["pinged"][i["key"]] = NOW.isoformat(timespec="seconds")
        sent.append(f"pinged {i['key']} ({i['tier']}): {i['attention']}")
    live = {i["key"] for i in items if i["attention"]}
    state["pinged"] = {k: v for k, v in state["pinged"].items() if k in live}
    save_data(data)
    print("\n".join(sent) if sent else "nothing to ping")


def main(argv):
    data = load_data()
    state = data["state"]
    cmd = argv[0] if argv else ""

    if cmd == "pause":
        if len(argv) != 3:
            die("usage: focus.py pause <key> <30m|4h|2d|1w>")
        key = argv[1].upper()
        until = NOW + parse_duration(argv[2])
        state["pauses"][key] = until.isoformat(timespec="seconds")
        state["pinged"].pop(key, None)
        save_data(data)
        print(f"paused {key} until {until.astimezone().strftime('%Y-%m-%d %H:%M %Z')}")
        return
    if cmd == "resume":
        if len(argv) != 2:
            die("usage: focus.py resume <key>")
        key = argv[1].upper()
        print(f"resumed {key}" if state["pauses"].pop(key, None) else f"{key} was not paused")
        save_data(data)
        return
    if cmd == "pauses":
        pauses = active_pauses(state)
        save_data(data)
        for k, v in sorted(pauses.items(), key=lambda kv: kv[1]):
            print(f"{k:<10} until {parse_time(v).astimezone().strftime('%Y-%m-%d %H:%M %Z')}")
        if not pauses:
            print("no active pauses")
        return
    if cmd and cmd not in ("--idle", "--ping"):
        die(f"unknown command '{cmd}'. Use: (none), --idle, --ping, pause, resume, pauses")

    items = collect(data["config"])
    if cmd == "--ping":
        ping(items, data)
        return
    pauses = active_pauses(state)
    if cmd == "--idle":
        items = [i for i in items if i["attention"] and not is_paused(i, pauses)]
        if not items:
            print("Nothing needs attention.")
            return
    print_items(items, pauses)


if __name__ == "__main__":
    main(sys.argv[1:])
