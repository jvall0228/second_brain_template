#!/usr/bin/env python3
"""Run every tool test suite in one command (TDD convention, issue #5).

Discovers stdlib-unittest suites in each `10_Agents/tools/*/tests/` directory
and runs them as a single combined suite; exits non-zero on any failure or
error. This is the one entrypoint used locally and by CI — adding a new tool
with a `tests/` directory picks it up automatically, no wiring needed.

Usage (from anywhere):

    python3 10_Agents/tools/run_tests.py         # run everything
    python3 10_Agents/tools/run_tests.py -v      # verbose

Test modules must have unique filenames across tools (unittest imports them
by module name); each suite handles its own imports (tests insert their
tool's directory on sys.path), so discovery here stays mechanical.
"""

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent


def build_suite() -> tuple[unittest.TestSuite, list[str]]:
    suite = unittest.TestSuite()
    found: list[str] = []
    for tests_dir in sorted(TOOLS_DIR.glob("*/tests")):
        if not tests_dir.is_dir():
            continue
        found.append(str(tests_dir.relative_to(TOOLS_DIR)))
        # Fresh loader per directory: TestLoader caches top_level_dir from its
        # first discover() call, which breaks discovery of later directories.
        suite.addTests(unittest.TestLoader().discover(start_dir=str(tests_dir)))
    return suite, found


def main() -> int:
    suite, found = build_suite()
    if not found:
        print("run_tests: no */tests/ directories found — refusing to pass vacuously", file=sys.stderr)
        return 1
    print(f"run_tests: discovered suites in {', '.join(found)}")
    verbosity = 2 if "-v" in sys.argv[1:] else 1
    result = unittest.TextTestRunner(verbosity=verbosity, buffer=True).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
