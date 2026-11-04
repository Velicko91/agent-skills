#!/usr/bin/python3
"""Ranks the open cmux sessions, and pings for the ones that need you.

focus.sh in this folder switches cmux to a row of the table that this script stores.

Usage:
  focus                          Print the session table: active, then idle, then paused.
                                 Store it in board.tsv for focus.sh.
  focus items [--attention]      Print the ranked work log items. --attention: only the
                                 items that need attention and are not paused.
  focus --ping                   Send a cmux notification for each item that needs attention
                                 and was not pinged in the last repingHours, at most pingMax items,
                                 highest rank first. The daemon runs it.
  focus daemon install [<min>]   Run --ping every <min> minutes with launchd. Default: daemon.everyMinutes.
  focus daemon uninstall         Stop the daemon.
  focus daemon status            Show if the daemon is loaded.
  focus pause <key> <dur>        Hide an item for a duration: 30m, 4h, 2d, 1w.
  focus resume <key>             End a pause now.
  focus pauses                   List the active pauses.

<key> is a ticket key (PROJ-1234) or an incident reference (INC-123).

Sources, all read-only:
  ~/.claude/skills/work-log/worklog.py list --open           work sessions
  ~/.claude/skills/investigate-incident/incident-log.local.md resolved incidents
  cmux windows, workspaces, and groups                       sessions and their last activity
  cmux sessions + Claude transcripts                         reminders set with CronCreate

The script writes its own data.json (the pauses and the last ping times), the table of the
last print, and the launchd job of the daemon.
"""
import json
import os
import plistlib
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
# transcript path -> {"offset", "runs", "deleted"}, so each run reads only the new bytes
REMINDER_CACHE = Path(os.environ.get("FOCUS_CACHE", Path.home() / ".cache/focus/reminders.json"))
# The rows of the last printed table, so focus.sh switches to the row the user saw.
# One line for each row, tab-separated: n, section, needs input (1 or 0), ref, window, id, title
BOARD = REMINDER_CACHE.parent / "board.tsv"
# Written by cmux-pause in this folder: workspace id -> {"until": ISO time}
PAUSE_STATE = Path(os.environ.get("CMUX_PAUSE_STATE", Path.home() / ".local/state/cmux-pause/pauses.json"))
LABEL = "local.focus"
PLIST = Path.home() / f"Library/LaunchAgents/{LABEL}.plist"
LOG = Path.home() / "Library/Logs/focus.log"

INCIDENT_RE = re.compile(r"^(INC-\d+)\b", re.I)
KEY_RE = re.compile(r"^([A-Z][A-Z0-9]+-\d+)\b")
PAUSED_RE = re.compile(r"\bpaused\b", re.I)  # the word in a workspace title pauses the item
# The CronCreate result, for example: Scheduled one-shot task a95d2060 (0 10 2 11 *). Next run: Nov 2 9:59am.
SCHEDULED_RE = re.compile(rb"Scheduled [\w -]*?task ([0-9a-f]{8}) \([^)]*\)\. Next run: (\w{3} \d{1,2} \d{1,2}:\d{2}[ap]m)")
CRON_DELETE_RE = re.compile(rb'"name":\s*"CronDelete",\s*"input":\s*\{[^}]*"id":\s*"([0-9a-f]{8})"')
NEEDS_INPUT = ("Needs input", "Waiting")
ACTIVE = (*NEEDS_INPUT, "Running")
SECTIONS = ("active", "idle", "paused")
DEFAULT_GROUPS = ["incident", "work", "util"]
DEFAULT_DAEMON = {"everyMinutes": 30, "activeHours": "09:00-19:00", "days": "1-5"}
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


def write_json(path, value, indent=None):
    """Write a temporary file and move it, so a crash keeps the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, indent=indent)
        f.write("\n")
    os.replace(tmp, path)


def save_data(data):
    write_json(DATA, data, indent=2)


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


def local(dt):
    return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def cmux_run(*args):
    try:
        out = subprocess.run([CMUX, *args], capture_output=True, text=True, timeout=20,
                             env={**os.environ, "CMUX_QUIET": "1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        die(f"cmux failed: {e}")
    if out.returncode != 0:
        die(f"cmux {' '.join(args)} failed: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout


def cmux_json(*args):
    return json.loads(cmux_run("--json", *args))


def all_workspaces():
    """Each workspace in each window, minus the generated anchor workspace of each group.

    Each one is a dict: ref, id, window, title, group, last, agent (the Claude state that cmux
    shows), state (the agent state if it is a NEEDS_INPUT state, else ""), paused, remind, until.
    """
    remind, until, agents = reminders(), cmux_pauses(), agent_states()
    result = []
    for win in cmux_json("list-windows"):
        wid = win["id"]
        groups = cmux_json("workspace", "group", "list", "--window", wid).get("groups", [])
        anchors = {g.get("anchor_workspace_ref") for g in groups
                   if g.get("anchor_workspace_provenance") == "generated"}
        group_of = {ref: g["name"] for g in groups for ref in g.get("member_workspace_refs", [])}
        for w in cmux_json("workspace", "list", "--window", wid).get("workspaces", []):
            if w.get("ref") in anchors:
                continue
            ws_id = (w.get("id") or "").upper()
            title = w.get("custom_title") or w.get("title") or ""
            agent = agents.get(ws_id, "")
            result.append({"ref": w.get("ref"), "id": ws_id, "window": wid, "title": title,
                           "group": group_of.get(w.get("ref"), ""),
                           "last": parse_time(w.get("latest_submitted_at")), "agent": agent,
                           "state": agent if agent in NEEDS_INPUT else "",
                           "paused": bool(PAUSED_RE.search(title)),
                           "remind": remind.get(ws_id), "until": until.get(ws_id)})
    return result


def agent_states():
    """workspace id -> the Claude state of its session: Needs input, Waiting, Running, or Idle."""
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
                tags.setdefault(owner.split(":", 1)[-1].upper(), []).append(f[6])
    return {ws: next((s for s in (*ACTIVE, "Idle") if s in states), "") for ws, states in tags.items()}


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
    local_now = datetime.now().astimezone()
    t = datetime.strptime(f"{local_now.year} {text}", "%Y %b %d %I:%M%p").replace(tzinfo=local_now.tzinfo)
    if t < local_now - timedelta(days=180):  # a December run read in January
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
    cache, scanned, result = load_cache(), {}, {}
    for s in sessions:
        path, ws_id = s.get("transcript_path"), (s.get("workspace_id") or "").upper()
        if not (path and ws_id and s.get("stored_pid_exists")) or not os.path.exists(path):
            continue
        entry = scanned[path] = scan_transcript(path, cache.get(path))
        future = [t for job, when in entry["runs"].items() if job not in entry["deleted"]
                  for t in [next_run(when)] if t > NOW]
        if future:
            result[ws_id] = min([*future, result.get(ws_id, future[0])])
    write_json(REMINDER_CACHE, scanned)  # only the live transcripts
    return result


def scan_transcript(path, entry):
    """Add the jobs in the bytes written since the last scan. A transcript can be tens of MB.

    A file shorter than the last offset was rewritten, so the scan starts again from byte 0.
    A partial last line waits for the next scan, so a regex never sees half a line.
    """
    size = os.path.getsize(path)
    if not entry or size < entry["offset"]:
        entry = {"offset": 0, "runs": {}, "deleted": []}
    with open(path, "rb") as f:
        f.seek(entry["offset"])
        chunk = f.read(size - entry["offset"])
    chunk = chunk[:chunk.rfind(b"\n") + 1]
    entry["runs"].update({job.decode(): when.decode() for job, when in SCHEDULED_RE.findall(chunk)})
    entry["deleted"] = sorted({*entry["deleted"], *(j.decode() for j in CRON_DELETE_RE.findall(chunk))})
    entry["offset"] += len(chunk)
    return entry


def load_cache():
    try:
        return json.loads(REMINDER_CACHE.read_text())
    except (OSError, ValueError):
        return {}


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


def collect(config, all_ws):
    """The work log items and the incident workspaces, ranked by config.tiers."""
    idle = config["idle"]
    boards = [b.upper() for b in config["boards"]]
    ws = {w["title"]: w for w in all_ws}
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
        if any(i["key"] == ticket.upper() and i["tier"] == "incident" for i in items):
            continue
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


def board(config, all_ws, pauses):
    """The session table: active, then idle, then paused.

    In each section the rows go in config.groups order, then the sessions that need input,
    then the oldest last message. A workspace in no group is "incident" if its title starts
    with INC-<n>, else "other", and "other" goes after the groups.
    """
    order = {g: n for n, g in enumerate(config.get("groups", DEFAULT_GROUPS))}
    rows = []
    for w in all_ws:
        m = INCIDENT_RE.match(w["title"]) or KEY_RE.match(w["title"].upper())
        row = {**w, "key": m.group(1).upper() if m else None,
               "group": w["group"] or ("incident" if INCIDENT_RE.match(w["title"]) else "other")}
        row["section"] = ("paused" if is_paused(row, pauses)
                          else "active" if w["agent"] in ACTIVE else "idle")
        rows.append(row)
    rows.sort(key=lambda r: (SECTIONS.index(r["section"]), order.get(r["group"], len(order)),
                             0 if r["state"] else 1, r["last"] or NOW))
    return rows


def is_paused(item, pauses):
    return (item["paused"] or item["remind"] is not None or item["until"] is not None
            or item["key"] in pauses)


def pause_note(item, pauses):
    if item["paused"]:
        return "paused (workspace title)"
    if item["until"]:
        return f"paused until {local(item['until'])} (cmux-pause)"
    if item["remind"]:
        return f"paused: reminder at {local(item['remind'])}"
    if item["key"] in pauses:
        return f"paused until {local(parse_time(pauses[item['key']]))}"
    return ""


def active_pauses(state):
    pauses = state["pauses"]
    for key in [k for k, v in pauses.items() if parse_time(v) <= NOW]:
        del pauses[key]
    return pauses


def current_workspace():
    return cmux_json("current-workspace")["workspace"]["id"].upper()


def print_board(rows, pauses):
    if not rows:
        print("No open sessions.")
        return
    save_board(rows)
    current = current_workspace()
    print(f"{'#':>3}  {'group':<9} {'state':<12} {'last':>5}  workspace")
    section = None
    for n, r in enumerate(rows, 1):
        if r["section"] != section:
            section = r["section"]
            print(f"--- {section}")
        mark = "*" if r["id"] == current else " "
        note = pause_note(r, pauses)
        print(f"{mark}{n:>2}  {r['group']:<9} {(r['agent'] or 'no agent').lower():<12} "
              f"{age(r['last']):>5}  {r['title']}{'  · ' + note if note else ''}")


def save_board(rows):
    """Write a temporary file and move it, so focus.sh never reads half a table."""
    BOARD.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=BOARD.parent, prefix=".board.", suffix=".tsv")
    with os.fdopen(fd, "w") as f:
        for n, r in enumerate(rows, 1):
            needs_input = "1" if r["section"] == "active" and r["state"] else "0"
            title = re.sub(r"[\t\n]", " ", r["title"])
            f.write("\t".join([str(n), r["section"], needs_input, r["ref"], r["window"], r["id"], title]) + "\n")
    os.replace(tmp, BOARD)


def print_items(items, pauses):
    if not items:
        print("No open items.")
        return
    # Paused items go last, so the numbers at the top are the work to do.
    items = sorted(items, key=lambda i: is_paused(i, pauses))
    print(f"{'#':>2}  {'tier':<9} {'key':<10} {'status':<11} {'last':>5}  attention / title")
    for n, i in enumerate(items, 1):
        note = pause_note(i, pauses)
        if not note:
            note = i["attention"] or i["title"]
            if i["attention"]:
                note = f"!! {note} · focus pause {i['key']} <30m|4h|2d|1w>"
        print(f"{n:>2}  {i['tier']:<9} {i['key']:<10} {i['status']:<11} {age(i['last']):>5}  {note}")


def in_active_hours(daemon):
    start, end = daemon["activeHours"].split("-")
    first, last = (int(d) for d in daemon["days"].split("-"))
    t = datetime.now().astimezone()
    return first <= t.isoweekday() <= last and start <= t.strftime("%H:%M") < end


def ping(items, rows, data):
    """Ping the work log items with attention, then the other sessions that need input."""
    config, state = data["config"], data["state"]
    if not in_active_hours({**DEFAULT_DAEMON, **config.get("daemon", {})}):
        print("outside the active hours: nothing pinged")
        return
    pauses = active_pauses(state)
    repeat = timedelta(hours=config["repingHours"])
    wait = timedelta(minutes=config["idle"]["waitingMinutes"])
    keys = {i["key"] for i in items}
    for r in rows:
        key = r["key"] or r["title"]
        if (r["section"] == "active" and r["state"] and key not in keys
                and (r["last"] is None or NOW - r["last"] >= wait)):
            items.append({**r, "key": key, "tier": r["group"],
                          "attention": f"session {r['state'].lower()}"})
    sent = []

    def pinged_recently(item):
        last = parse_time(state["pinged"].get(item["key"]))
        return last is not None and NOW - last < repeat

    # Skip the recent pings before the pingMax cut, so lower items still get a ping.
    due = [i for i in items if i["attention"] and not is_paused(i, pauses) and not pinged_recently(i)]
    for i in due[:config["pingMax"]]:
        how = f"focus pause {i['key']} <30m|4h|2d|1w>" if i["key"] in keys else "cmux-pause <4h|until mon>"
        args = [CMUX, "notify", "--title", f"focus: {i['key']} ({i['tier']})",
                "--body", f"{i['attention']}. Pause it: {how}"]
        if i["ref"]:
            args += ["--workspace", i["ref"]]
        subprocess.run(args, capture_output=True, timeout=20, env={**os.environ, "CMUX_QUIET": "1"})
        state["pinged"][i["key"]] = NOW.isoformat(timespec="seconds")
        sent.append(f"pinged {i['key']} ({i['tier']}): {i['attention']}")
    live = {i["key"] for i in items if i["attention"]}
    state["pinged"] = {k: v for k, v in state["pinged"].items() if k in live}
    save_data(data)
    print("\n".join(sent) if sent else "nothing to ping")


def daemon(argv, config):
    sub = argv[0] if argv else ""
    domain = f"gui/{os.getuid()}"
    if sub == "install":
        minutes = int(argv[1]) if len(argv) > 1 else {**DEFAULT_DAEMON, **config.get("daemon", {})}["everyMinutes"]
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        PLIST.write_bytes(plistlib.dumps({
            "Label": LABEL, "ProgramArguments": [str(Path(__file__).resolve()), "--ping"],
            "StartInterval": minutes * 60, "StandardOutPath": str(LOG), "StandardErrorPath": str(LOG)}))
        subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
        out = subprocess.run(["launchctl", "bootstrap", domain, str(PLIST)], capture_output=True, text=True)
        if out.returncode != 0:
            die(f"launchctl bootstrap failed: {out.stderr.strip()}")
        print(f"daemon runs focus --ping every {minutes}m. Log: {LOG}")
    elif sub == "uninstall":
        subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
        PLIST.unlink(missing_ok=True)
        print("daemon removed")
    elif sub == "status":
        out = subprocess.run(["launchctl", "print", f"{domain}/{LABEL}"], capture_output=True, text=True)
        if out.returncode != 0:
            print("daemon not loaded")
            return
        every = re.search(r"run interval = (\d+)", out.stdout)
        print(f"daemon loaded, every {int(every.group(1)) // 60}m. Log: {LOG}" if every else "daemon loaded")
    else:
        die("usage: focus daemon <install [<minutes>]|uninstall|status>")


def main(argv):
    cmd = argv[0] if argv else ""
    data = load_data()
    state = data["state"]

    if cmd == "pause":
        if len(argv) != 3:
            die("usage: focus pause <key> <30m|4h|2d|1w>")
        key = argv[1].upper()
        until = NOW + parse_duration(argv[2])
        state["pauses"][key] = until.isoformat(timespec="seconds")
        state["pinged"].pop(key, None)
        save_data(data)
        print(f"paused {key} until {local(until)}")
        return
    if cmd == "resume":
        if len(argv) != 2:
            die("usage: focus resume <key>")
        key = argv[1].upper()
        print(f"resumed {key}" if state["pauses"].pop(key, None) else f"{key} was not paused")
        save_data(data)
        return
    if cmd == "pauses":
        pauses = active_pauses(state)
        save_data(data)
        for k, v in sorted(pauses.items(), key=lambda kv: kv[1]):
            print(f"{k:<10} until {local(parse_time(v))}")
        if not pauses:
            print("no active pauses")
        return
    if cmd == "daemon":
        daemon(argv[1:], data["config"])
        return
    if cmd not in ("", "items", "--ping"):
        die(f"unknown command '{cmd}'. Use: (none), items, --ping, daemon, pause, resume, pauses")

    all_ws = all_workspaces()
    pauses = active_pauses(state)
    if cmd == "":
        print_board(board(data["config"], all_ws, pauses), pauses)
    elif cmd == "--ping":
        ping(collect(data["config"], all_ws), board(data["config"], all_ws, pauses), data)
    else:
        items = collect(data["config"], all_ws)
        if argv[1:] == ["--attention"]:
            items = [i for i in items if i["attention"] and not is_paused(i, pauses)]
            if not items:
                print("Nothing needs attention.")
                return
        print_items(items, pauses)


if __name__ == "__main__":
    main(sys.argv[1:])
