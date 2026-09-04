"""Tests for §28: the compiled bootstrap file (`brain bootstrap`) and
skill-scoped context (`brain context --for`).

Run from the vault root:
    python3 -m unittest discover -s 10_Agents/tools/brain/tests
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brain  # noqa: E402
from test_brain import FIXTURE, make_vault  # noqa: E402

CONVENTIONS = (FIXTURE / "00_Meta/CONVENTIONS.md").read_text(encoding="utf-8")


def doc(title, body, updated="2026-08-11", tags=("type/meta",)):
    return (
        "---\n"
        f'title: "{title}"\n'
        "tags:\n" + "".join(f"  - {t}\n" for t in tags) + f"updated: {updated}\n---\n\n{body}\n"
    )


def bootstrap_files():
    return {
        "00_Meta/CONVENTIONS.md": CONVENTIONS,
        "AGENTS.md": doc(
            "Agents",
            "# Agents\n\nRead [NOW](01_Profile/NOW.md) and [conv](00_Meta/CONVENTIONS.md#tag-namespaces).\n"
            "Keep `[literal](01_Profile/NOW.md)` and ![img](08_Assets/pic.png).\n\n"
            "## Rules\n\n```\n# not a heading\n[x](01_Profile/NOW.md)\n```\n\n"
            "See <https://example.com> and [site](https://example.com/a) and [frag](#rules).\n",
            updated="2026-08-20",
        ),
        "01_Profile/NOW.md": doc("Now", "# Now\n\nBack to [AGENTS](../AGENTS.md) and [prefs](PREFERENCES.md).\n", updated="2026-08-25"),
        "01_Profile/PREFERENCES.md": doc("Preferences", "No heading first.\n\n## Style\n\nTerse.\n"),
        "00_Meta/INDEX.md": doc("Index", "# Index\n\n- [conv](CONVENTIONS.md)\n- [now](../01_Profile/NOW.md)\n"),
        "01_Profile/DEFAULTS.md": doc("Defaults", "# Defaults\n\nUTC.\n"),
        "08_Assets/pic.png": "not really a png",
    }


class CompileTests(unittest.TestCase):
    def build(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            payload = brain.build_bootstrap(root)
            return payload, payload["rendered"].decode("utf-8")

    def test_order_headings_links_and_code_are_handled(self):
        payload, text = self.build(bootstrap_files())
        body = text.split("# Bootstrap\n", 1)[1]
        # Sources in must-read order, each with a source line.
        heads = [line for line in body.split("\n") if line.startswith("## ")]
        self.assertEqual(len(heads), 6)
        self.assertEqual([heads[i] for i in (0, 1, 2, 4, 5)], ["## Agents", "## Now", "## Preferences", "## Index", "## Defaults"])
        self.assertTrue(heads[3].startswith("## "), heads[3])
        self.assertEqual(
            [line for line in body.split("\n") if line.startswith("*Source:")],
            [
                "*Source: [AGENTS.md](../AGENTS.md)*",
                "*Source: [01_Profile/NOW.md](../01_Profile/NOW.md)*",
                "*Source: [01_Profile/PREFERENCES.md](../01_Profile/PREFERENCES.md)*",
                "*Source: [00_Meta/CONVENTIONS.md](CONVENTIONS.md)*",
                "*Source: [00_Meta/INDEX.md](INDEX.md)*",
                "*Source: [01_Profile/DEFAULTS.md](../01_Profile/DEFAULTS.md)*",
            ],
        )
        # Headings demoted; a doc without a leading H1 gets a synthesized one.
        self.assertIn("\n### Rules\n", body)
        self.assertIn("## Preferences\n\n*Source:", body)
        self.assertIn("\n### Style\n", body)
        # Links re-relativized to 00_Meta/, fragments kept, code untouched.
        self.assertIn("[NOW](../01_Profile/NOW.md)", body)
        self.assertIn("[conv](CONVENTIONS.md#tag-namespaces)", body)
        self.assertIn("![img](../08_Assets/pic.png)", body)
        self.assertIn("[AGENTS](../AGENTS.md) and [prefs](../01_Profile/PREFERENCES.md)", body)
        self.assertIn("[now](../01_Profile/NOW.md)", body)
        self.assertIn("`[literal](01_Profile/NOW.md)`", body)
        self.assertIn("# not a heading\n[x](01_Profile/NOW.md)\n", body)
        self.assertIn("[site](https://example.com/a) and [frag](#rules)", body)
        # Frontmatter: newest source date, marker, digest.
        self.assertIn("updated: 2026-08-25\n", text)
        self.assertIn(f"generated: {brain.BOOTSTRAP_MARKER}\n", text)
        self.assertRegex(text, r'content-digest: "[0-9a-f]{64}"')
        self.assertEqual([s["path"] for s in payload["sources"]], list(brain.BOOTSTRAP_ORDER))
        self.assertEqual(payload["budget"], brain.BOOTSTRAP_TOTAL_BUDGET)

    def test_deterministic_and_missing_source_is_an_error(self):
        _, a = self.build(bootstrap_files())
        _, b = self.build(bootstrap_files())
        self.assertEqual(a, b)
        files = bootstrap_files()
        del files["01_Profile/DEFAULTS.md"]
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            with self.assertRaises(brain.BootstrapError):
                brain.build_bootstrap(root)


class CliTests(unittest.TestCase):
    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue()

    def test_check_write_cycle_and_corpus_pruning(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), bootstrap_files())
            code, out = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 1)
            self.assertIn("missing", out)
            code, out = self.run_cli(root, "bootstrap", "--write")
            self.assertEqual(code, 0)
            self.assertIn("written", out)
            code, out = self.run_cli(root, "bootstrap", "--write")
            self.assertIn("unchanged", out)
            code, out = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 0)
            self.assertIn("fresh", out)
            # Pruned: not a note, not an asset, not validated.
            notes, assets = brain.walk_corpus(root, selected_environment=None)
            self.assertNotIn(brain.BOOTSTRAP_RELPATH, notes)
            self.assertNotIn(brain.BOOTSTRAP_RELPATH, assets)
            errors, _ = brain.run_validate(root, check_index=False)
            self.assertFalse([e for e in errors if e["path"] == brain.BOOTSTRAP_RELPATH])
            # Editing a source makes it stale; context reports the state.
            (root / "01_Profile/DEFAULTS.md").write_text(doc("Defaults", "# Defaults\n\nEST.\n"), encoding="utf-8")
            code, out = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 1)
            self.assertIn("stale", out)
            code, out = self.run_cli(root, "context", "--json")
            self.assertEqual(json.loads(out)["bootstrap"]["state"], "stale")
            code, out = self.run_cli(root, "bootstrap", "--json")
            data = json.loads(out)
            self.assertEqual((data["state"], data["fresh"], data["overBudget"]), ("stale", False, False))

    def test_over_budget_render_is_refused_by_write_and_check(self):
        files = bootstrap_files()
        files["01_Profile/DEFAULTS.md"] = doc("Defaults", "# Defaults\n\n" + "x" * (brain.BOOTSTRAP_TOTAL_BUDGET + 10))
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out = self.run_cli(root, "bootstrap", "--write", "--json")
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["write"], "refused")
            self.assertFalse((root / brain.BOOTSTRAP_RELPATH).exists())
            code, out = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 1)
            self.assertIn("missing", out)
            self.assertIn("OVER BUDGET", out)

    def test_sources_within_budget_but_render_over_budget_is_refused(self):
        # F8: compilation does not always shrink content — every relative
        # link in 01_Profile/ grows by "../01_Profile/" — so the rendered
        # size is enforced independently of the per-source budgets.
        files = bootstrap_files()
        link = "[a](x.md) "
        now_links = (brain.BOOTSTRAP_BUDGETS["01_Profile/NOW.md"] - 200) // len(link)
        pref_links = (brain.BOOTSTRAP_BUDGETS["01_Profile/PREFERENCES.md"] - 200) // len(link)
        files["01_Profile/NOW.md"] = doc("Now", "# Now\n\n" + link * now_links)
        files["01_Profile/PREFERENCES.md"] = doc("Preferences", "# Preferences\n\n" + link * pref_links)
        files["01_Profile/x.md"] = doc("X", "# X\n")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            # Fill the remaining source allowance across three docs, each
            # kept inside its own per-source budget.
            report = brain.context_report(root)
            remaining = brain.BOOTSTRAP_TOTAL_BUDGET - report["totalBytes"] - 100
            self.assertGreater(remaining, 0)
            for rel, title in (("AGENTS.md", "Agents"), ("00_Meta/CONVENTIONS.md", "Conventions"), ("00_Meta/INDEX.md", "Index")):
                current = next(row for row in report["docs"] if row["path"] == rel)
                room = min(remaining, current["budget"] - current["sizeBytes"] - 50)
                files[rel] = doc(title, f"# {title}\n\n" + "y" * (current["sizeBytes"] + room - 60))
                remaining -= room
            root = make_vault(Path(td), files)
            report = brain.context_report(root)
            self.assertLessEqual(report["totalBytes"], report["totalBudget"])
            self.assertTrue(all(row["sizeBytes"] <= row["budget"] for row in report["docs"]), report["docs"])
            payload = brain.build_bootstrap(root)
            self.assertGreater(payload["sizeBytes"], payload["budget"])
            code, out = self.run_cli(root, "bootstrap", "--write")
            self.assertEqual(code, 1)
            self.assertFalse((root / brain.BOOTSTRAP_RELPATH).exists())
            code, _ = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 1)


class WriteSafetyTests(unittest.TestCase):
    """R4: `bootstrap --write` never writes through a symlinked target or
    parent; the external file keeps its bytes and the run exits 1."""

    def run_cli(self, root, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue(), err.getvalue()

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_target_is_refused_and_external_bytes_survive(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", bootstrap_files())
            outside = Path(td) / "outside.md"
            outside.write_bytes(b"external content\n")
            target = root / brain.BOOTSTRAP_RELPATH
            os.symlink(outside, target)
            code, out, err = self.run_cli(root, "bootstrap", "--write")
            self.assertEqual(code, 1)
            self.assertIn("UNSAFE PATH", err)
            self.assertEqual(outside.read_bytes(), b"external content\n")
            self.assertTrue(target.is_symlink())
            code, out, _ = self.run_cli(root, "bootstrap", "--check")
            self.assertEqual(code, 1)
            self.assertIn("unsafe", out)
            code, out, _ = self.run_cli(root, "bootstrap", "--write", "--json")
            self.assertEqual((code, json.loads(out)["write"], json.loads(out)["state"]), (1, "refused", "unsafe"))
            code, out, _ = self.run_cli(root, "context", "--json")
            self.assertEqual(json.loads(out)["bootstrap"]["state"], "unsafe")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_parent_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td) / "vault", bootstrap_files())
            elsewhere = Path(td) / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "BOOTSTRAP.md").write_bytes(b"external\n")
            meta = root / "00_Meta"
            for child in list(meta.iterdir()):
                child.rename(elsewhere / child.name)
            meta.rmdir()
            os.symlink(elsewhere, meta)
            code, _, err = self.run_cli(root, "bootstrap", "--write")
            self.assertEqual(code, 1)
            self.assertIn("UNSAFE PATH", err)
            self.assertEqual((elsewhere / "BOOTSTRAP.md").read_bytes(), b"external\n")

    def test_regular_target_still_written(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), bootstrap_files())
            code, out, _ = self.run_cli(root, "bootstrap", "--write")
            self.assertEqual(code, 0)
            self.assertIn("written", out)
            self.assertTrue((root / brain.BOOTSTRAP_RELPATH).is_file())


class ParserTests(unittest.TestCase):
    """F7: the compiler runs on the §5 link parser, exact-length code-span
    masking, the §5.2 fence scanner, and the §7 heading grammar."""

    def build(self, files):
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            return brain.build_bootstrap(root)["rendered"].decode("utf-8")

    def test_output_is_independent_of_working_directory(self):
        files = bootstrap_files()
        files["AGENTS.md"] = doc(
            "Agents",
            "# Agents\n\nRoot [r](/etc/passwd) proto [p](//host/x.md) up [u](../outside.md) "
            "deep [d](01_Profile/../01_Profile/NOW.md).\n",
        )
        renders = []
        for cwd in (tempfile.gettempdir(), "/"):
            before = os.getcwd()
            os.chdir(cwd)
            try:
                renders.append(self.build(files))
            finally:
                os.chdir(before)
        self.assertEqual(renders[0], renders[1])
        body = renders[0]
        self.assertIn("[r](/etc/passwd)", body)
        self.assertIn("[p](//host/x.md)", body)
        self.assertIn("[u](../outside.md)", body)
        self.assertIn("[d](../01_Profile/NOW.md)", body)

    def test_titles_angle_destinations_and_encoded_paths(self):
        files = bootstrap_files()
        files["AGENTS.md"] = doc(
            "Agents",
            "# Agents\n\n[t](01_Profile/NOW.md \"Now page\") [a](<01_Profile/NOW.md>) "
            "[b](<01_Profile/NOW.md#top> 'x') [e](01_Profile/NOW.md#tag-namespaces) "
            "[esc\\]ape](01_Profile/NOW.md) [i](01_Profile/N%4FW.md).\n",
        )
        body = self.build(files)
        self.assertIn('[t](../01_Profile/NOW.md "Now page")', body)
        self.assertIn("[a](<../01_Profile/NOW.md>)", body)
        self.assertIn("[b](<../01_Profile/NOW.md#top> 'x')", body)
        self.assertIn("[e](../01_Profile/NOW.md#tag-namespaces)", body)
        self.assertIn("[esc\\]ape](../01_Profile/NOW.md)", body)
        self.assertIn("[i](../01_Profile/NOW.md)", body)

    def test_code_spans_of_every_length_are_protected(self):
        files = bootstrap_files()
        files["AGENTS.md"] = doc(
            "Agents",
            "# Agents\n\n``[x](01_Profile/NOW.md)`` and ` `` ` [y](01_Profile/NOW.md) "
            "`[z](01_Profile/NOW.md)` ```[w](01_Profile/NOW.md)```.\n",
        )
        body = self.build(files)
        self.assertIn("``[x](01_Profile/NOW.md)``", body)
        self.assertIn("[y](../01_Profile/NOW.md)", body)
        self.assertIn("`[z](01_Profile/NOW.md)`", body)
        self.assertIn("```[w](01_Profile/NOW.md)```", body)

    def test_fences_three_four_and_mixed(self):
        files = bootstrap_files()
        files["AGENTS.md"] = doc(
            "Agents",
            "# Agents\n\n````md\n```\n# inner\n[a](01_Profile/NOW.md)\n```\n````\n"
            "[b](01_Profile/NOW.md)\n~~~\n# tilde\n```\n[c](01_Profile/NOW.md)\n~~~\n"
            "[d](01_Profile/NOW.md)\n   ```\n# indented fence\n   ```\n[e](01_Profile/NOW.md)\n",
        )
        body = self.build(files)
        self.assertIn("```\n# inner\n[a](01_Profile/NOW.md)\n```\n````\n", body)
        self.assertIn("[b](../01_Profile/NOW.md)", body)
        self.assertIn("# tilde\n```\n[c](01_Profile/NOW.md)\n~~~\n", body)
        self.assertIn("[d](../01_Profile/NOW.md)", body)
        self.assertIn("# indented fence\n", body)
        self.assertIn("[e](../01_Profile/NOW.md)", body)

    def test_headings_indented_up_to_three_spaces_demote_and_no_h1_survives(self):
        files = bootstrap_files()
        files["AGENTS.md"] = doc(
            "Agents",
            "  # Indented title\n\n   ## Three\n\n    # code block, not a heading\n\n###### Six\n\n#NotAHeading\n\n# Second H1\n",
        )
        files["01_Profile/PREFERENCES.md"] = doc("Preferences", "Prose first.\n\n# Late H1\n")
        body = self.build(files).split("# Bootstrap\n", 1)[1]
        self.assertIn("  ## Indented title\n", body)
        self.assertIn("   ### Three\n", body)
        self.assertIn("    # code block, not a heading\n", body)
        self.assertIn("###### Six\n", body)
        self.assertIn("#NotAHeading\n", body)
        self.assertIn("## Second H1\n", body)
        self.assertIn("## Preferences\n\n*Source:", body)
        self.assertIn("## Late H1\n", body)
        self.assertFalse([line for line in body.split("\n") if line.startswith("# ")], body)
        # An indented H1 is a heading, so it takes the source line rather
        # than a synthesized section heading.
        self.assertIn("  ## Indented title\n\n*Source: [AGENTS.md](../AGENTS.md)*", body)



SKILL = (
    "---\nname: demo\ndescription: demo skill\ntitle: \"Skill: Demo\"\ntags:\n  - type/reference\n"
    "updated: 2026-08-11\n---\n\n# Demo\n\n## Steps\n\n1. Read [conv](../../../00_Meta/CONVENTIONS.md).\n\n"
    "## References\n\n- `01_Profile/NOW.md` — now\n- [conv](../../../00_Meta/CONVENTIONS.md#tag-namespaces) — twice\n"
    "- `00_Meta/CONVENTIONS.md` — again\n- [self](SKILL.md)\n- `04_Projects/` — a directory\n- [gone](../../../nope.md)\n"
    "- [web](https://example.com)\n"
    "- [titled](../../../01_Profile/DEFAULTS.md \"defaults\") — a titled link\n"
    "- [angle](<../../../00_Meta/INDEX.md>) — an angle destination\n"
    "- ``[ex](../../../01_Profile/PREFERENCES.md)`` and ``01_Profile/PREFERENCES.md`` — examples, not references\n"
    "- `[ex2](../../../01_Profile/PREFERENCES.md)` — a code span holding a link\n"
    "\n```\n- [fenced](../../../01_Profile/PREFERENCES.md)\n- `01_Profile/PREFERENCES.md`\n## References\n```\n"
    "\n## Not References\n\n- [after](../../../08_Assets/pic.png)\n"
)


class SkillContextTests(unittest.TestCase):
    def run_cli(self, root, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = brain.main([*argv, "--vault", str(root)])
        return code, out.getvalue()

    def test_references_resolved_deduped_and_totaled(self):
        files = bootstrap_files()
        files["10_Agents/skills/demo/SKILL.md"] = SKILL
        files["10_Agents/skills/setup/nested/SKILL.md"] = SKILL.replace("name: demo", "name: nested")
        with tempfile.TemporaryDirectory() as td:
            root = make_vault(Path(td), files)
            code, out = self.run_cli(root, "context", "--for", "demo", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["skill"]["path"], "10_Agents/skills/demo/SKILL.md")
            # F9: titled and angle destinations count; anything inside fenced
            # code or a multi-backtick span is an example, and a later
            # section ends the scan.
            self.assertEqual(
                [r["path"] for r in data["references"]],
                ["01_Profile/NOW.md", "00_Meta/CONVENTIONS.md", "01_Profile/DEFAULTS.md", "00_Meta/INDEX.md"],
            )
            self.assertEqual([r["path"] for r in data["bootstrap"]], list(brain.BOOTSTRAP_ORDER))
            expected = (
                sum(r["sizeBytes"] for r in data["bootstrap"])
                + data["skill"]["sizeBytes"]
                + sum(r["sizeBytes"] for r in data["references"])
            )
            self.assertEqual(data["totalBytes"], expected)
            # Nested skill directories resolve by name; unknown skills fail.
            code, out = self.run_cli(root, "context", "--for", "nested", "--json")
            self.assertEqual(json.loads(out)["skill"]["path"], "10_Agents/skills/setup/nested/SKILL.md")
            code, out = self.run_cli(root, "context", "--for", "missing")
            self.assertEqual(code, 1)
            code, out = self.run_cli(root, "context", "--for", "demo")
            self.assertIn("skill  10_Agents/skills/demo/SKILL.md", out)
            self.assertIn("  01_Profile/NOW.md  ", out)
            self.assertTrue(out.strip().endswith(f"total  {expected} bytes"))


if __name__ == "__main__":
    unittest.main()
