#!/usr/bin/env python3
"""Runs one read-only SQL statement against a database from data.json.

Usage:
  query.py list                          Show the configured databases (no secrets).
  query.py check <alias>                 Check the password, the port forward, and the connection.
  query.py run <alias> [--limit N] < sql Run one read-only statement. Prints CSV.
  query.py stop <alias>                  Stop the port forward that this script started.

Read-only mode has two layers, because the database user may be able to write:
  1. The guard refuses every statement that is not one SELECT, WITH, EXPLAIN, SHOW, TABLE or VALUES,
     and every statement that holds a write keyword or a function with side effects.
  2. The session starts with default_transaction_read_only=on, so the server refuses a write
     that the guard did not catch.

The password comes from the macOS Keychain, never from data.json:
  security add-generic-password -U -s <keychainService> -a <alias> -w
"""
import csv
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
CONFIG = SKILL_DIR / "data.json"
STATE = Path("/tmp/query-db")

ALLOWED_FIRST = {"select", "with", "explain", "show", "table", "values"}
# Statements such as SET, BEGIN or VACUUM can only come first, so the first-word check blocks them.
# These words can also hide inside an allowed statement: a CTE, EXPLAIN, or SELECT INTO.
WRITE_WORDS = {
    "insert", "update", "delete", "merge", "truncate", "drop", "create", "alter", "grant",
    "revoke", "copy", "call", "into", "execute", "prepare", "declare", "lock", "refresh",
}
SIDE_EFFECT_FUNCS = re.compile(
    r"\b(pg_terminate_backend|pg_cancel_backend|pg_reload_conf|pg_rotate_logfile|set_config"
    r"|lo_\w+|dblink\w*|pg_read_\w+|pg_ls_\w+|pg_stat_reset\w*|pg_advisory\w*|pg_sleep\w*"
    r"|nextval|setval|pg_create_\w+|pg_drop_\w+|pg_replication_\w+|pg_switch_wal|pg_promote"
    r"|pg_file_\w+|pg_logical_\w+)\s*\(",
    re.IGNORECASE,
)


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_config():
    if not CONFIG.exists():
        die(f"{CONFIG} not found. Copy data.example.json to data.json and fill it in.", 2)
    return json.loads(CONFIG.read_text())


def entry_for(cfg, alias):
    dbs = cfg.get("databases", {})
    if alias in dbs:
        return dbs[alias]
    matches = [a for a in dbs if a.startswith(alias)]
    if len(matches) == 1:
        return dbs[matches[0]]
    die(f"unknown database '{alias}'. Configured: {', '.join(sorted(dbs)) or 'none'}", 2)


def strip_sql(sql):
    """Removes comments, string literals and quoted identifiers, so keywords inside them do not count."""
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                die("unterminated /* comment", 3)
            i = j + 2
        elif c == "'":
            j = i + 1
            while True:
                j = sql.find("'", j)
                if j < 0:
                    die("unterminated string literal", 3)
                if sql.startswith("''", j):
                    j += 2
                    continue
                break
            out.append(" '' ")
            i = j + 1
        elif c == '"':
            j = sql.find('"', i + 1)
            if j < 0:
                die("unterminated quoted identifier", 3)
            out.append(' "x" ')
            i = j + 1
        elif c == "$" and (m := re.match(r"\$([A-Za-z_]\w*)?\$", sql[i:])):
            tag = m.group(0)
            j = sql.find(tag, i + len(tag))
            if j < 0:
                die("unterminated dollar-quoted string", 3)
            out.append(" '' ")
            i = j + len(tag)
        else:
            out.append(c)
            i += 1
    return "".join(out)


def guard(sql):
    body = strip_sql(sql).strip().rstrip(";").strip()
    if not body:
        die("empty statement", 3)
    if ";" in body:
        die("only one statement is allowed", 3)
    if "\\" in body:
        die("psql backslash commands are not allowed", 3)
    words = re.findall(r"[A-Za-z_]+", body.lower())
    if words[0] not in ALLOWED_FIRST:
        die(f"'{words[0].upper()}' is not allowed. Only {', '.join(sorted(w.upper() for w in ALLOWED_FIRST))}", 3)
    bad = sorted(set(words) & WRITE_WORDS)
    if bad:
        die(f"write keyword(s) not allowed: {', '.join(w.upper() for w in bad)}", 3)
    if m := SIDE_EFFECT_FUNCS.search(body):
        die(f"function with side effects not allowed: {m.group(1)}", 3)


def keychain_password(cfg, alias, e):
    service = e.get("keychainService", cfg.get("defaults", {}).get("keychainService", "query-db"))
    account = e.get("keychainAccount", alias)
    r = subprocess.run(["security", "find-generic-password", "-s", service, "-a", account, "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die(f"no Keychain password for service '{service}', account '{account}'. "
            f"Store it with: security add-generic-password -U -s {service} -a {account} -w", 4)
    return r.stdout.rstrip("\n")


def port_open(host, port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def listener(port):
    r = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True)
    pid = r.stdout.split()[0] if r.stdout.split() else None
    if not pid:
        return None, ""
    cmd = subprocess.run(["ps", "-p", pid, "-o", "command="], capture_output=True, text=True).stdout.strip()
    return pid, cmd


def ensure_forward(alias, e):
    """Reuses a running forward. Starts one only when the entry has portForward and nothing listens."""
    host, port = e.get("host", "127.0.0.1"), int(e["port"])
    pf = e.get("portForward")
    if not pf:
        return
    if port_open(host, port):
        pid, cmd = listener(port)
        print(f"FORWARD: port {port} already open (pid {pid or '?'}: {cmd or 'unknown'})", file=sys.stderr)
        return
    if "command" in pf:
        # Any other forwarder, for example cloud-sql-proxy. It must listen on `port`.
        cmd = pf["command"]
    else:
        contexts = subprocess.run(["kubectl", "config", "get-contexts", "-o", "name"],
                                  capture_output=True, text=True).stdout.split()
        if pf["context"] not in contexts:
            die(f"kubectl context '{pf['context']}' not found. Log in to the cluster first.", 5)
        cmd = ["kubectl", "--context", pf["context"], "-n", pf["namespace"], "port-forward",
               pf["target"], f"{port}:{pf.get('remotePort', 5432)}"]
    STATE.mkdir(exist_ok=True)
    log = open(STATE / f"{alias}.log", "w")
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (STATE / f"{alias}.pid").write_text(f"{p.pid}\n{cmd[0]}")
    for _ in range(60):
        if port_open(host, port):
            print(f"FORWARD: started (pid {p.pid}): {' '.join(cmd)}", file=sys.stderr)
            return
        if p.poll() is not None:
            break
        time.sleep(0.25)
    die(f"port forward did not start. See {STATE / f'{alias}.log'}", 5)


def psql(cfg, alias, e, sql, extra=()):
    if e.get("engine", "postgres") != "postgres":
        die(f"engine '{e.get('engine')}' is not supported yet. Only postgres.", 2)
    timeout = e.get("statementTimeout", cfg.get("defaults", {}).get("statementTimeout", "30s"))
    env = dict(os.environ)
    env.pop("PGPASSWORD", None)
    if not e.get("passwordless"):
        env["PGPASSWORD"] = keychain_password(cfg, alias, e)
    env.update(PGOPTIONS=f"-c default_transaction_read_only=on -c statement_timeout={timeout}",
               PGAPPNAME="query-db",
               PGSSLMODE=e.get("sslmode", "prefer"),
               PGCONNECT_TIMEOUT="10")
    cmd = ["psql", "-X", "--no-password", "-v", "ON_ERROR_STOP=1",
           "-h", e.get("host", "127.0.0.1"), "-p", str(e["port"]),
           "-U", e["user"], "-d", e["database"], *extra, "-c", sql]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def cmd_list(cfg):
    for alias, e in sorted(cfg.get("databases", {}).items()):
        print(f"{alias}: engine={e.get('engine', 'postgres')} db={e.get('database')} user={e.get('user')} "
              f"forward={'yes' if e.get('portForward') else 'no'}")
        if e.get("keywords"):
            print(f"  keywords: {', '.join(e['keywords'])}")
        for t, desc in e.get("tables", {}).items():
            print(f"  table {t}: {desc}")
        if e.get("notes"):
            print(f"  notes: {e['notes']}")


def cmd_check(cfg, alias):
    e = entry_for(cfg, alias)
    ensure_forward(alias, e)
    r = psql(cfg, alias, e, "SHOW transaction_read_only", ["-At"])
    if r.returncode != 0:
        die(r.stderr.strip(), 6)
    if r.stdout.strip() != "on":
        die("the session is not read-only - refusing to continue", 6)
    print(f"OK: {alias} connected, session read-only")


def cmd_run(cfg, alias, limit):
    e = entry_for(cfg, alias)
    sql = sys.stdin.read()
    guard(sql)
    ensure_forward(alias, e)
    r = psql(cfg, alias, e, sql, ["--csv"])
    if r.returncode != 0:
        die(r.stderr.strip(), 6)
    rows = list(csv.reader(io.StringIO(r.stdout)))
    w = csv.writer(sys.stdout)
    w.writerows(rows[: limit + 1])
    if len(rows) - 1 > limit:
        print(f"NOTE: {len(rows) - 1} rows, showing {limit}", file=sys.stderr)


def cmd_stop(alias):
    pidfile = STATE / f"{alias}.pid"
    if not pidfile.exists():
        print(f"no port forward started by query-db for {alias}")
        return
    pid, exe = (pidfile.read_text().split("\n") + [""])[:2]
    cmd = subprocess.run(["ps", "-p", pid, "-o", "command="], capture_output=True, text=True).stdout
    if exe and exe in cmd:
        os.kill(int(pid), 15)
        print(f"stopped port forward (pid {pid})")
    pidfile.unlink()


def main(argv):
    if not argv or argv[0] not in {"list", "check", "run", "stop"}:
        die(__doc__.strip(), 2)
    if argv[0] == "stop":
        return cmd_stop(argv[1])
    cfg = load_config()
    if argv[0] == "list":
        return cmd_list(cfg)
    if len(argv) < 2:
        die("missing <alias>", 2)
    if argv[0] == "check":
        return cmd_check(cfg, argv[1])
    limit = cfg.get("defaults", {}).get("limit", 100)
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    cmd_run(cfg, argv[1], limit)


if __name__ == "__main__":
    main(sys.argv[1:])
