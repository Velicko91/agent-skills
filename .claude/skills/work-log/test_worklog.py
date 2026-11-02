"""Tests for worklog.py. Run: python3 -m unittest discover -s .claude/skills/work-log"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worklog  # noqa: E402

T0 = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)
PR = "https://github.com/acme/api/pull/42"


class WorklogTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = Path(self.dir.name) / "worklog.db"
        self.clock = T0
        patches = [
            mock.patch.dict(os.environ, {"WORKLOG_DB": str(self.db)}),
            mock.patch.object(worklog, "now", side_effect=lambda: self.clock),
            mock.patch.object(worklog, "find_session_cwd", return_value="/work/acme"),
            mock.patch.object(worklog, "pr_state", return_value={"state": "OPEN"}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self.dir.cleanup)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = worklog.main(["--db", str(self.db), *argv])
        return code, out.getvalue(), err.getvalue()

    def ok(self, *argv):
        code, out, err = self.run_cli(*argv)
        self.assertEqual(code, 0, err)
        return out

    def refused(self, *argv):
        code, _, err = self.run_cli(*argv)
        self.assertEqual(code, 1)
        return err

    def show(self, key):
        return json.loads(self.ok("show", key))

    def add_branch(self, branch="feat/PROJ-1234-add-pagination", key="PROJ-1234"):
        self.ok("add", "--ticket", key, "--title", "Add pagination", "--branch", branch,
                "--session", f"{key}-add-pagination", "--session-id", "abc")

    def later(self, **delta):
        self.clock += timedelta(**delta)


class TicketTest(WorklogTest):
    def test_add_creates_an_open_ticket_with_one_branch(self):
        self.add_branch()
        item = self.show("PROJ-1234")
        self.assertEqual((item["type"], item["status"]), ("ticket", "open"))
        branch = item["branches"][0]
        self.assertEqual(branch["status"], "in-progress")
        self.assertEqual(branch["sessionCwd"], "/work/acme")
        self.assertEqual(branch["transitions"], [{"status": "in-progress", "enteredAt": "2026-01-10T09:00:00Z"}])

    def test_add_refuses_a_second_entry_for_the_same_branch(self):
        self.add_branch()
        self.assertIn("exists already", self.refused(
            "add", "--ticket", "PROJ-1234", "--title", "x", "--branch", "feat/PROJ-1234-add-pagination",
            "--session", "s", "--session-id", "abc"))

    def test_update_refuses_a_move_that_is_not_an_edge(self):
        self.add_branch()
        err = self.refused("update", "--branch", "feat/PROJ-1234-add-pagination", "--status", "dev-tested")
        self.assertIn("in-progress → dev-tested is not allowed. Next: in-review, merged, abandoned", err)
        self.assertEqual(self.show("PROJ-1234")["branches"][0]["status"], "in-progress")

    def test_update_with_force_allows_any_move(self):
        self.add_branch()
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--status", "dev-tested", "--force")
        self.assertEqual(self.show("PROJ-1234")["branches"][0]["status"], "dev-tested")

    def test_ticket_is_done_when_all_branches_finish_and_opens_again_for_a_new_branch(self):
        self.add_branch()
        self.add_branch("feat/PROJ-1234-second-pr")
        for status in ("merged", "prod-tested"):
            self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--status", status)
        self.assertEqual(self.show("PROJ-1234")["status"], "open")
        self.ok("update", "--branch", "feat/PROJ-1234-second-pr", "--status", "abandoned")
        self.assertEqual(self.show("PROJ-1234")["status"], "done")
        self.add_branch("feat/PROJ-1234-third-pr")
        item = self.show("PROJ-1234")
        self.assertEqual(item["status"], "open")
        self.assertEqual([t["status"] for t in item["transitions"]], ["open", "done", "open"])

    def test_keys_ignore_case(self):
        self.add_branch(key="proj-1234")
        self.add_branch("feat/PROJ-1234-second-pr", key="PROJ-1234")
        self.assertEqual(len(self.show("PROJ-1234")["branches"]), 2)

    def test_ticket_status_cannot_be_set_by_hand(self):
        self.add_branch()
        self.assertIn("automatic", self.refused("item", "update", "--key", "PROJ-1234", "--status", "done"))

    def test_update_stores_and_removes_fields_of_other_skills(self):
        self.add_branch()
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--pr", PR,
                "--set", "sweepCheckedAt=2026-01-10T10:00:00Z")
        branch = self.show("PROJ-1234")["branches"][0]
        self.assertEqual((branch["pr"], branch["sweepCheckedAt"]), (PR, "2026-01-10T10:00:00Z"))
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--set", "sweepCheckedAt=")
        self.assertNotIn("sweepCheckedAt", self.show("PROJ-1234")["branches"][0])

    def test_set_refuses_a_column_name(self):
        self.add_branch()
        self.assertIn("is a column", self.refused(
            "update", "--branch", "feat/PROJ-1234-add-pagination", "--set", "status=merged"))

    def test_durations_sum_the_time_in_each_state(self):
        self.add_branch()
        branch = "feat/PROJ-1234-add-pagination"
        self.later(hours=1)
        self.ok("update", "--branch", branch, "--status", "in-review")
        self.later(hours=2)
        self.ok("update", "--branch", branch, "--status", "in-progress")
        self.later(hours=1)
        self.ok("update", "--branch", branch, "--status", "in-review")
        self.later(hours=1)
        item = self.show("PROJ-1234")
        self.assertEqual(item["branches"][0]["durations"], {"in-progress": 7200, "in-review": 10800})
        self.assertEqual(item["durations"], {"open": 18000})

    def test_a_terminal_state_does_not_count_up(self):
        self.add_branch()
        self.later(hours=1)
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--status", "abandoned")
        self.later(days=3)
        item = self.show("PROJ-1234")
        self.assertEqual(item["branches"][0]["durations"], {"in-progress": 3600})
        self.assertEqual(item["durations"], {"open": 3600})


class IncidentTest(WorklogTest):
    def setUp(self):
        super().setUp()
        self.ok("item", "add", "--type", "incident", "--key", "INC-1", "--title", "Checkout errors")

    def move(self, *statuses):
        for status in statuses:
            self.ok("item", "update", "--key", "INC-1", "--status", status)

    def test_incident_starts_investigating(self):
        self.assertEqual(self.show("INC-1")["status"], "investigating")

    def test_incident_refuses_a_move_that_is_not_an_edge(self):
        err = self.refused("item", "update", "--key", "INC-1", "--status", "monitoring")
        self.assertIn("Next: cause-found, false-positive", err)

    def test_incident_refuses_an_unknown_status(self):
        self.assertIn("Unknown status", self.refused("item", "update", "--key", "INC-1", "--status", "done"))

    def test_resolved_needs_summary_and_resolution_also_with_force(self):
        self.move("cause-found", "fixing", "monitoring")
        self.assertIn("needs summary, resolution",
                      self.refused("item", "update", "--key", "INC-1", "--status", "resolved"))
        self.assertIn("needs resolution", self.refused(
            "item", "update", "--key", "INC-1", "--status", "resolved", "--force", "--set", "summary=Pool full"))
        self.ok("item", "update", "--key", "INC-1", "--status", "resolved",
                "--set", "summary=Pool full", "--set", "resolution=Raised the pool size")
        item = self.show("INC-1")
        self.assertEqual((item["status"], item["summary"]), ("resolved", "Pool full"))

    def test_a_fix_branch_attaches_to_the_incident(self):
        self.add_branch("fix/INC-1-pool-size", key="INC-1")
        item = self.show("INC-1")
        self.assertEqual((item["type"], item["branches"][0]["branch"]), ("incident", "fix/INC-1-pool-size"))
        self.ok("update", "--branch", "fix/INC-1-pool-size", "--status", "abandoned")
        self.assertEqual(self.show("INC-1")["status"], "investigating")

    def test_a_resolved_incident_with_an_open_branch_stays_in_list_open(self):
        self.add_branch("fix/INC-1-follow-up", key="INC-1")
        self.ok("item", "update", "--key", "INC-1", "--status", "false-positive")
        self.assertEqual([i["key"] for i in json.loads(self.ok("list", "--open"))], ["INC-1"])

    def test_status_lists_open_incidents(self):
        self.assertIn("🚨 Open incidents", self.ok("status"))
        self.move("false-positive")
        self.assertNotIn("Open incidents", self.ok("status"))


class ListTest(WorklogTest):
    def setUp(self):
        super().setUp()
        self.add_branch()
        self.ok("item", "add", "--type", "incident", "--key", "INC-1", "--title", "Checkout errors",
                "--set", "summary=The 100% pool")

    def keys(self, *argv):
        return [i["key"] for i in json.loads(self.ok("list", *argv))]

    def test_filters(self):
        self.assertEqual(self.keys(), ["PROJ-1234", "INC-1"])
        self.assertEqual(self.keys("--type", "incident"), ["INC-1"])
        self.assertEqual(self.keys("--key", "proj-1234"), ["PROJ-1234"])
        self.assertEqual(self.keys("--branch", "feat/PROJ-1234-add-pagination"), ["PROJ-1234"])
        self.assertEqual(self.keys("--session-id", "abc"), ["PROJ-1234"])
        self.assertEqual(self.keys("--status", "in-progress"), ["PROJ-1234"])

    def test_search_matches_titles_and_values_but_not_key_names(self):
        self.assertEqual(self.keys("--search", "pagination"), ["PROJ-1234"])
        self.assertEqual(self.keys("--search", "pool"), ["INC-1"])
        self.assertEqual(self.keys("--search", "summary"), [])
        self.assertEqual(self.keys("--search", "100%"), ["INC-1"])
        self.assertEqual(self.keys("--search", "1_0"), [])

    def test_open_hides_finished_items(self):
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--status", "abandoned")
        self.ok("item", "update", "--key", "INC-1", "--status", "false-positive")
        self.assertEqual(self.keys("--open"), [])

    def test_types_prints_the_machines(self):
        machines = json.loads(self.ok("types"))
        self.assertEqual(set(machines), {"branch", "ticket", "incident"})
        self.assertEqual(machines["incident"]["required"], {"resolved": ["summary", "resolution"]})


class GitHubTest(WorklogTest):
    def setUp(self):
        super().setUp()
        self.add_branch()
        self.ok("update", "--branch", "feat/PROJ-1234-add-pagination", "--pr", PR, "--status", "in-review")

    def test_status_reconciles_a_merged_pr(self):
        with mock.patch.object(worklog, "pr_state", return_value={"state": "MERGED"}):
            out = self.ok("status")
        self.assertIn("🧪 Waiting for a test", out)
        self.assertIn("since 2026-01-10   next: dev test", out)
        self.assertEqual(self.show("PROJ-1234")["branches"][0]["status"], "merged")

    def test_status_warns_when_gh_fails(self):
        with mock.patch.object(worklog, "pr_state", return_value=None):
            self.assertIn("Could not read", self.ok("status"))

    def test_merged_prints_no_yes_or_closed(self):
        self.assertEqual(self.ok("merged", "--branch", "feat/PROJ-1234-add-pagination").strip(), "no")
        with mock.patch.object(worklog, "pr_state", return_value={"state": "CLOSED"}):
            self.assertEqual(self.ok("merged", "--branch", "feat/PROJ-1234-add-pagination").strip(), "closed")
        self.assertEqual(self.show("PROJ-1234")["branches"][0]["status"], "abandoned")

    def test_merged_refuses_a_branch_without_a_pr(self):
        self.add_branch("feat/PROJ-1234-second-pr")
        self.assertIn("No entry with a PR", self.refused("merged", "--branch", "feat/PROJ-1234-second-pr"))


class LockTest(WorklogTest):
    def setUp(self):
        super().setUp()
        self.add_branch()
        self.branch = "feat/PROJ-1234-add-pagination"

    def test_a_second_lock_fails_until_unlock(self):
        self.assertEqual(self.ok("lock", "--branch", self.branch).strip(), "locked")
        self.assertIn("Another run owns it", self.refused("lock", "--branch", self.branch))
        self.ok("unlock", "--branch", self.branch)
        self.ok("lock", "--branch", self.branch)

    def test_a_stale_lock_is_taken_over(self):
        self.ok("lock", "--branch", self.branch)
        self.later(hours=2, seconds=1)
        self.ok("lock", "--branch", self.branch)
        self.assertEqual(self.show("PROJ-1234")["branches"][0]["sweepLockedAt"], "2026-01-10T11:00:01Z")


class StorageTest(WorklogTest):
    def legacy(self, log):
        path = Path(self.dir.name) / "data.json"
        path.write_text(json.dumps(log))
        return path

    def entry(self, **fields):
        return {"ticket": "PROJ-1", "title": "Old work", "branch": "feat/PROJ-1-old", "worktree": None,
                "session": "PROJ-1-old", "pr": PR, "status": "in-review", "createdAt": "2025-12-01",
                "mergedAt": None, **fields}

    def import_log(self, log):
        path = self.legacy(log)
        conn = worklog.connect(self.db)
        with redirect_stderr(io.StringIO()):
            worklog.import_once(conn, path)
        conn.close()
        return path

    def test_migrations_set_the_user_version(self):
        conn = worklog.connect(self.db)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], len(worklog.MIGRATIONS))
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_import_converts_entries_and_renames_the_file(self):
        path = self.import_log({
            "active": [
                self.entry(sweepLockedAt="2025-12-02T00:00:00Z", sweepCheckedAt="2025-12-02T01:00:00Z"),
                self.entry(branch="feat/PROJ-2-done", ticket="PROJ-2", status="prod-tested",
                           mergedAt="2025-12-03", prodTestedAt="2025-12-05"),
            ],
            "readyToDelete": [
                self.entry(branch="feat/PROJ-1-old", status="abandoned"),
                self.entry(branch="feat/PROJ-3-merged", ticket="PROJ-3", status="merged",
                           mergedAt="2025-11-01", movedAt="2025-12-10"),
            ],
        })
        self.assertFalse(path.exists())
        self.assertTrue(path.with_name("data.json.migrated").exists())
        old = self.show("PROJ-1")["branches"]
        self.assertEqual(len(old), 1)
        self.assertEqual(old[0]["status"], "in-review")
        self.assertEqual(old[0]["sweepCheckedAt"], "2025-12-02T01:00:00Z")
        self.assertNotIn("sweepLockedAt", old[0])
        self.assertEqual([t["status"] for t in old[0]["transitions"]], ["in-progress", "in-review"])
        done = self.show("PROJ-2")
        self.assertEqual(done["status"], "done")
        self.assertEqual([t["status"] for t in done["branches"][0]["transitions"]],
                         ["in-progress", "merged", "prod-tested"])
        self.assertEqual(done["transitions"][-1], {"status": "done", "enteredAt": "2025-12-05T00:00:00Z"})
        moved = self.show("PROJ-3")
        self.assertEqual((moved["status"], moved["branches"][0]["status"]), ("done", "prod-tested"))
        self.assertEqual(moved["branches"][0]["transitions"][-1]["enteredAt"], "2025-12-10T00:00:00Z")

    def test_import_runs_only_once(self):
        self.import_log({"active": [self.entry()], "readyToDelete": []})
        path = self.import_log({"active": [self.entry(ticket="PROJ-9", branch="feat/PROJ-9-x")],
                                "readyToDelete": []})
        self.assertTrue(path.exists())
        self.assertEqual(self.refused("show", "PROJ-9").strip(), "No item with key PROJ-9.")

    def test_only_the_home_database_imports(self):
        self.legacy({"active": [self.entry()], "readyToDelete": []})
        with mock.patch.object(worklog, "LEGACY_FILE", Path(self.dir.name) / "data.json"):
            self.ok("status")
        self.assertTrue((Path(self.dir.name) / "data.json").exists())

    def test_a_failed_import_leaves_the_file_and_no_items(self):
        path = self.legacy({"active": [{"ticket": "PROJ-1"}], "readyToDelete": []})
        conn = worklog.connect(self.db)
        with self.assertRaisesRegex(worklog.WorklogError, "Cannot import"):
            worklog.import_once(conn, path)
        self.assertTrue(path.exists())
        self.assertIsNone(conn.execute("SELECT 1 FROM items").fetchone())


if __name__ == "__main__":
    unittest.main()
