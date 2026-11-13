#!/usr/bin/python3
"""Sets up the weekly project-tracker job in the loops daemon. Safe to run again.

Usage: setup.py

Steps:
  1. Make data.json from data.example.json, if it is missing, and stop: set loops.dir first.
  2. Write <loops.settingsDir>/project-tracker-settings.json: the permissions of the session.
  3. Add or update the "project-tracker" job in <loops.dir>/loops.json, from data.json.
  4. Run loops.py --check.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data.json"
JOB = "project-tracker"
ALLOW = [
    "Skill(project-tracker)",
    "mcp__linear__whoami",
    "mcp__linear__list_projects",
    "mcp__linear__get_project",
    "mcp__linear__list_issues",
    "mcp__linear__list_milestones",
    "mcp__linear__get_status_updates",
    "mcp__linear__save_status_update",
    "Bash(~/.claude/skills/work-log/worklog.py *)",
    "Bash(cmux notify *)",
]


def die(msg):
    print(f"error: {msg}")
    sys.exit(1)


def write_json(path, value):
    """Write a temporary file and move it, so a crash keeps the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def main():
    if not DATA.exists():
        shutil.copy(HERE / "data.example.json", DATA)
        DATA.chmod(0o600)
        die(f"made {DATA}. Set loops.dir to the folder of loops.json, then run setup.py again.")
    data = json.loads(DATA.read_text())
    loops = data.get("loops", {})
    if not loops.get("dir"):
        die(f"loops.dir is empty in {DATA}. Set it to the folder of loops.json.")
    loops_dir = Path(os.path.expanduser(loops["dir"]))
    config = loops_dir / "loops.json"
    if not config.exists():
        die(f"{config} is missing. Install the loops daemon first.")

    settings = Path(os.path.expanduser(loops.get("settingsDir", "~/.config/cmux/loops"))) / f"{JOB}-settings.json"
    write_json(settings, {"permissions": {"allow": ALLOW, "deny": ["WebFetch", "WebSearch"]}})
    print(f"wrote {settings}")

    schedule = data.get("schedule", {})
    job = {"name": JOB, "cron": schedule.get("cron", "0 10 * * 3"), "prompt": "/project-tracker",
           "session": "new", "model": loops.get("model", "sonnet"), "restart_after_hours": 0,
           "settings": str(settings).replace(str(Path.home()), "~", 1)}
    if schedule.get("tz"):
        job["tz"] = schedule["tz"]
    cfg = json.loads(config.read_text())
    jobs = cfg.setdefault("jobs", [])
    old = next((j for j in jobs if j.get("name") == JOB), None)
    if old:
        old.update(job)  # keeps "enabled" and other keys that the user set
    else:
        jobs.append(job)
    write_json(config, cfg)
    print(f"{'updated' if old else 'added'} the {JOB} job in {config}: {job['cron']}")

    check = subprocess.run([sys.executable, str(loops_dir / "loops.py"), "--check"],
                           capture_output=True, text=True)
    print(check.stdout.strip() or check.stderr.strip())
    if check.returncode != 0:
        die("loops.py --check failed")


if __name__ == "__main__":
    main()
