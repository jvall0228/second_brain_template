"""Tests for the task module (spec §17, issue #28): checkbox extraction,
emoji metadata, malformed-date posture, restricted reduction, the `brain
tasks` query command, and the `tasks` config key.

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import io
import json
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "vault"
CONVENTIONS = (FIXTURE / "00_Meta/conventions.md").read_text(encoding="utf-8") + (
    "| `restricted/*` | Privacy marking | `private` |\n"
)


def make_vault(tmp: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def note(body: str, title: str = "Note", extra_tags: str = "") -> str:
    return (
        f"---\ntitle: {title}\ntags:\n  - type/note\n{extra_tags}"
        f"updated: 2026-08-11\n---\n\n{body}"
    )


def build(root: Path) -> dict:
    notes, assets = brain.walk_corpus(root)
    return brain.build_index(root, notes, assets)


class TaskExtractionTests(unittest.TestCase):
    """§17.1–17.2: recognition, metadata forms, exclusion zones."""

    def tasks_of(self, body: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), {"n.md": note(body)})
            return build(root)["notes"]["n.md"]["tasks"]

    def test_record_shape_every_field_present(self):
        (t,) = self.tasks_of("- [ ] call dentist 📅 2026-08-15 ⏫\n")
        self.assertEqual(
            t,
            {
                "due": "2026-08-15",
                "line": 8,
                "malformed": [],
                "priority": "high",
                "status": "open",
                "text": "call dentist",
            },
        )

    def test_status_mapping(self):
        tasks = self.tasks_of("- [ ] open\n- [x] done\n- [X] Done\n- [/] custom\n")
        self.assertEqual(
            [t["status"] for t in tasks], ["open", "done", "done", "done"]
        )

    def test_bullets_and_nesting(self):
        tasks = self.tasks_of(
            "- [ ] parent\n  - [ ] nested child\n* [x] star\n+ [ ] plus\n"
        )
        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[1]["text"], "nested child")
        self.assertEqual(tasks[1]["line"], 9)

    def test_non_tasks_are_not_indexed(self):
        tasks = self.tasks_of(
            "- [ ]\n"  # no text
            "-[ ] no space after bullet\n"
            "1. [ ] ordered list\n"
            "> - [ ] blockquoted\n"
            "- [xx] two status chars\n"
            "just - [ ] mid-line\n"
        )
        self.assertEqual(tasks, [])

    def test_code_fence_and_inline_code_excluded(self):
        tasks = self.tasks_of(
            "```\n- [ ] inside fence\n```\n"
            "`- [ ] inside span`\n"
            "- [ ] real task with `inline code` kept\n"
        )
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["text"], "real task with `inline code` kept")

    def test_all_metadata_forms_stripped(self):
        (t,) = self.tasks_of(
            "- [x] ship it ⏳ 2026-08-12 🛫 2026-08-10 ✅ 2026-08-14 "
            "➕ 2026-08-01 🔁 every week 📅 2026-08-15 🔽\n"
        )
        self.assertEqual(t["text"], "ship it")
        self.assertEqual(t["due"], "2026-08-15")
        self.assertEqual(t["priority"], "low")
        self.assertEqual(t["malformed"], [])
        self.assertEqual(t["status"], "done")

    def test_priority_and_due_last_occurrence_wins(self):
        (t,) = self.tasks_of("- [ ] x 📅 2026-01-01 📅 2026-02-02 ⏫ 🔼\n")
        self.assertEqual(t["due"], "2026-02-02")
        self.assertEqual(t["priority"], "medium")

    def test_malformed_dates_flag_and_still_index(self):
        tasks = self.tasks_of(
            "- [ ] bad calendar 📅 2026-13-40\n"
            "- [ ] not a date 📅 soon\n"
            "- [ ] missing value 📅\n"
            "- [ ] scheduled bad ⏳ nope 📅 2026-08-15\n"
        )
        self.assertEqual([t["malformed"] for t in tasks[:3]], [["due"]] * 3)
        self.assertIsNone(tasks[0]["due"])
        # Date-shaped-but-invalid token is consumed; prose value stays.
        self.assertEqual(tasks[0]["text"], "bad calendar")
        self.assertEqual(tasks[1]["text"], "not a date soon")
        # A bad field does not poison the others.
        self.assertEqual(tasks[3]["malformed"], ["scheduled"])
        self.assertEqual(tasks[3]["due"], "2026-08-15")

    def test_variation_selector_tolerated(self):
        (t,) = self.tasks_of("- [ ] vs 📅️ 2026-08-15\n")
        self.assertEqual(t["due"], "2026-08-15")
        self.assertEqual(t["text"], "vs")

    def test_extraction_is_deterministic(self):
        body = "- [ ] a 📅 2026-08-15\n\n- [x] b 🔼\n"
        self.assertEqual(self.tasks_of(body), self.tasks_of(body))


class TaskValidateTests(unittest.TestCase):
    """§10.2 task-invalid-date: warning severity, template exemption."""

    def test_malformed_date_warns_never_errors(self):
        files = {
            "00_Meta/conventions.md": CONVENTIONS,
            "n.md": note("- [ ] bad 📅 2026-13-40\n"),
        }
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            errors, warnings = brain.run_validate(root, check_index=False)
        self.assertFalse(any(f["rule"] == "task-invalid-date" for f in errors))
        hits = [f for f in warnings if f["rule"] == "task-invalid-date"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["path"], "n.md")
        self.assertEqual(hits[0]["line"], 8)
        self.assertIn("due", hits[0]["message"])

    def test_template_placeholder_task_is_exempt(self):
        files = {
            "00_Meta/conventions.md": CONVENTIONS,
            "09_Templates/template-x.md": (
                "---\ntitle: \"{{title}}\"\ntags:\n  - type/note\n"
                "updated: {{date}}\n---\n\n- [ ] follow up 📅 {{date}}\n"
            ),
        }
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            _, warnings = brain.run_validate(root, check_index=False)
        self.assertFalse(
            any(f["rule"] == "task-invalid-date" for f in warnings), warnings
        )


class TaskRestrictedReductionTests(unittest.TestCase):
    """§8.3: the committed index empties tasks for restricted notes."""

    FILES = {
        "00_Meta/conventions.md": CONVENTIONS,
        "secret.md": note(
            "- [ ] secret errand 📅 2026-08-15\n",
            title="Secret",
            extra_tags="  - restricted/private\n",
        ),
        "plain.md": note("- [ ] public errand\n", title="Plain"),
    }

    def test_reduce_restricted_empties_tasks(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(self.FILES))
            index = build(root)
            self.assertEqual(len(index["notes"]["secret.md"]["tasks"]), 1)
            reduced = brain.reduce_restricted(index)
            rec = reduced["notes"]["secret.md"]
            self.assertEqual(rec["tasks"], [])
            self.assertIn("tasks", rec)  # emptied, never omitted
            self.assertEqual(len(reduced["notes"]["plain.md"]["tasks"]), 1)

    def test_cmd_index_writes_reduced_tasks(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(self.FILES))
            self.assertEqual(brain.main(["index", "--vault", str(root)]), 0)
            data = json.loads(
                (root / brain.INDEX_RELPATH).read_text(encoding="utf-8")
            )
            self.assertEqual(data["notes"]["secret.md"]["tasks"], [])
            self.assertEqual(
                data["notes"]["plain.md"]["tasks"][0]["text"], "public errand"
            )


class TasksCommandTests(unittest.TestCase):
    """§17.3: filters, --due today boundary, deterministic ordering."""

    TODAY = date(2026, 8, 11)

    FILES = {
        "00_Meta/conventions.md": CONVENTIONS,
        "04_Projects/alpha/README.md": note(
            "- [ ] overdue task 📅 2026-08-10\n"
            "- [ ] due today 📅 2026-08-11\n"
            "- [x] done overdue 📅 2026-08-01\n",
            title="Alpha",
        ),
        "05_Areas/beta.md": note(
            "- [ ] due later 📅 2026-09-01\n- [ ] undated task\n", title="Beta"
        ),
    }

    def run_tasks(self, *argv: str):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), dict(self.FILES))
            buf = io.StringIO()
            with mock.patch.object(brain, "today", lambda: self.TODAY):
                with redirect_stdout(buf):
                    rc = brain.main(["tasks", "--vault", str(root), *argv])
        return rc, buf.getvalue()

    def json_rows(self, *argv: str):
        rc, out = self.run_tasks("--json", *argv)
        self.assertEqual(rc, 0)
        return json.loads(out)

    def test_default_lists_all_in_order(self):
        rows = self.json_rows()
        # Due ascending, nulls last, then path, then line.
        self.assertEqual(
            [(r["due"], r["path"], r["line"]) for r in rows],
            [
                ("2026-08-01", "04_Projects/alpha/README.md", 10),
                ("2026-08-10", "04_Projects/alpha/README.md", 8),
                ("2026-08-11", "04_Projects/alpha/README.md", 9),
                ("2026-09-01", "05_Areas/beta.md", 8),
                (None, "05_Areas/beta.md", 9),
            ],
        )
        for r in rows:
            self.assertEqual(
                sorted(r), ["due", "line", "malformed", "path", "priority", "status", "text"]
            )

    def test_open_filter(self):
        rows = self.json_rows("--open")
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["status"] == "open" for r in rows))

    def test_due_today_boundary(self):
        rows = self.json_rows("--due", "today")
        # On or before today; the undated and later-due tasks never match.
        self.assertEqual(
            [r["due"] for r in rows], ["2026-08-01", "2026-08-10", "2026-08-11"]
        )

    def test_due_explicit_date(self):
        rows = self.json_rows("--due", "2026-08-10")
        self.assertEqual([r["due"] for r in rows], ["2026-08-01", "2026-08-10"])

    def test_due_invalid_is_operational_error(self):
        rc, _ = self.run_tasks("--due", "2026-13-01")
        self.assertEqual(rc, 1)

    def test_overdue_is_open_and_strictly_past(self):
        rows = self.json_rows("--overdue")
        # Due today is not overdue; the done task never is.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "overdue task")

    def test_project_prefix_filter(self):
        rows = self.json_rows("--project", "04_Projects/")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["path"].startswith("04_Projects/") for r in rows))

    def test_filters_combine(self):
        rows = self.json_rows("--open", "--due", "today", "--project", "04_Projects/")
        self.assertEqual([r["text"] for r in rows], ["overdue task", "due today"])

    def test_human_output_shape(self):
        rc, out = self.run_tasks("--overdue")
        self.assertEqual(rc, 0)
        self.assertEqual(
            out,
            "04_Projects/alpha/README.md:8  [ ] overdue task  (due 2026-08-10)\n",
        )

    def test_json_output_is_deterministic(self):
        self.assertEqual(self.json_rows("--open"), self.json_rows("--open"))


class TasksConfigTests(unittest.TestCase):
    """§15.3/§15.4/§17.4: the `tasks` config key and carry-over reader."""

    def check(self, text: str):
        config, findings = brain.parse_config(text)
        with tempfile.TemporaryDirectory() as td:
            errors, warnings = brain.check_config(Path(td), config, findings)
        return config, errors, warnings

    def test_default_is_on(self):
        self.assertTrue(brain.tasks_carry_over({}))
        self.assertTrue(brain.tasks_carry_over({"tasks": None}))
        self.assertTrue(brain.tasks_carry_over({"tasks": {"carry_over": None}}))

    def test_off_and_on(self):
        config, errors, warnings = self.check("tasks:\n  carry_over: off\n")
        self.assertFalse(brain.tasks_carry_over(config))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        config, _, _ = self.check("tasks:\n  carry_over: on\n")
        self.assertTrue(brain.tasks_carry_over(config))

    def test_malformed_value_warns_and_falls_back(self):
        config, errors, warnings = self.check("tasks:\n  carry_over: maybe\n")
        self.assertTrue(brain.tasks_carry_over(config))
        self.assertEqual(errors, [])
        self.assertEqual(
            [w["rule"] for w in warnings], ["config-unknown-value"]
        )

    def test_non_mapping_is_invalid_value(self):
        _, errors, _ = self.check("tasks: yes\n")
        self.assertEqual([e["rule"] for e in errors], ["config-invalid-value"])

    def test_unknown_subkey_warns_dotted(self):
        _, errors, warnings = self.check("tasks:\n  digest: daily\n")
        self.assertEqual(errors, [])
        self.assertTrue(
            any(
                w["rule"] == "config-unknown-key" and "tasks.digest" in w["message"]
                for w in warnings
            ),
            warnings,
        )

    def test_tasks_is_implemented_not_unknown(self):
        _, _, warnings = self.check("tasks:\n  carry_over: on\n")
        self.assertFalse(any(w["rule"] == "config-unknown-key" for w in warnings))

    def test_cmd_config_reports_effective_toggle(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(
                Path(td),
                {"00_Meta/config.yaml": "tasks:\n  carry_over: off\n"},
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = brain.main(["config", "--vault", str(root), "--json"])
            self.assertEqual(rc, 0)
            self.assertFalse(json.loads(buf.getvalue())["tasksCarryOver"])


if __name__ == "__main__":
    unittest.main()
