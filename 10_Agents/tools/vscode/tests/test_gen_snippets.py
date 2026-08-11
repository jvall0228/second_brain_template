"""Tests for gen_snippets.py (VS Code snippet generation, PRD §6.5).

Run via the tools runner:
    python3 10_Agents/tools/run_tests.py
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_snippets  # noqa: E402


class EscapingTests(unittest.TestCase):
    def test_backslash_and_dollar_escaped(self):
        self.assertEqual(gen_snippets.escape_snippet_text(r"a\b$c"), r"a\\b\$c")

    def test_backslash_escaped_before_dollar(self):
        # Wrong order would turn "$" into "\\$" (escaped backslash + bare $).
        self.assertEqual(gen_snippets.escape_snippet_text("$"), "\\$")
        self.assertEqual(gen_snippets.escape_snippet_text("\\$"), "\\\\\\$")

    def test_plain_text_untouched(self):
        self.assertEqual(gen_snippets.escape_snippet_text("plain text"), "plain text")


class TemplateBodyTests(unittest.TestCase):
    def test_date_token_becomes_date_variable(self):
        body = gen_snippets.template_to_body("updated: {{date}}\n")
        self.assertEqual(body, ["updated: " + gen_snippets.DATE_VAR])

    def test_tabstops_numbered_by_first_appearance(self):
        body = gen_snippets.template_to_body("{{title}} {{topic}} {{title}}\n")
        self.assertEqual(body, ["${1:title} ${2:topic} ${1:title}"])

    def test_literal_dollar_escaped_but_tokens_survive(self):
        body = gen_snippets.template_to_body("cost $5 for {{thing}}\n")
        self.assertEqual(body, ["cost \\$5 for ${1:thing}"])

    def test_trailing_newlines_stripped(self):
        self.assertEqual(gen_snippets.template_to_body("line\n\n\n"), ["line"])


class RenderTests(unittest.TestCase):
    def _fixture_dir(self, tmp: str) -> Path:
        d = Path(tmp)
        (d / "template-alpha.md").write_text("# {{title}}\n", encoding="utf-8")
        (d / "template-beta.md").write_text("beta {{date}}\n", encoding="utf-8")
        return d

    def test_render_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(gen_snippets, "TEMPLATES_DIR", self._fixture_dir(tmp)):
                self.assertEqual(gen_snippets.render(), gen_snippets.render())

    def test_render_covers_every_template_plus_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(gen_snippets, "TEMPLATES_DIR", self._fixture_dir(tmp)):
                snippets = gen_snippets.build_snippets()
        self.assertEqual(
            sorted(s["prefix"] for s in snippets.values()),
            ["sb-alpha", "sb-beta", "sb-frontmatter"],
        )

    def test_check_mode_detects_stale_and_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.code-snippets"
            patches = (
                mock.patch.object(gen_snippets, "TEMPLATES_DIR", self._fixture_dir(tmp)),
                mock.patch.object(gen_snippets, "OUT_PATH", out),
                mock.patch.object(gen_snippets, "ROOT", Path(tmp)),
            )
            with patches[0], patches[1], patches[2]:
                with mock.patch.object(sys, "argv", ["gen_snippets.py", "--check"]):
                    self.assertEqual(gen_snippets.main(), 1)  # missing = stale
                with mock.patch.object(sys, "argv", ["gen_snippets.py"]):
                    self.assertEqual(gen_snippets.main(), 0)  # write
                with mock.patch.object(sys, "argv", ["gen_snippets.py", "--check"]):
                    self.assertEqual(gen_snippets.main(), 0)  # now fresh
                # Template change makes it stale again.
                (Path(tmp) / "template-alpha.md").write_text("changed\n", encoding="utf-8")
                with mock.patch.object(sys, "argv", ["gen_snippets.py", "--check"]):
                    self.assertEqual(gen_snippets.main(), 1)

    def test_committed_snippets_are_fresh(self):
        # Parity guard for this repo itself: the committed file matches the
        # current templates (same assertion the pre-commit hook enforces).
        self.assertEqual(
            gen_snippets.OUT_PATH.read_text(encoding="utf-8"), gen_snippets.render()
        )


if __name__ == "__main__":
    unittest.main()
