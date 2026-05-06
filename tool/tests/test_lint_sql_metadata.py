"""Unit tests for tool/lint_sql_metadata.py.

Run from repo root:
    python3 -m unittest tool.tests.test_lint_sql_metadata -v
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

import lint_sql_metadata as lint  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CASES = FIXTURES / "cases"


def codes_of(diags):
    return sorted(d.code for d in diags)


def has_code(diags, code, severity=None):
    for d in diags:
        if d.code == code and (severity is None or d.severity == severity):
            return True
    return False


class ParseAndValidateTests(unittest.TestCase):
    def _run(self, name, **kwargs):
        h = lint.parse_header(CASES / name, **kwargs)
        return h, lint.validate(h)

    def test_valid_minimal(self):
        h, diags = self._run("valid_minimal.sql")
        self.assertEqual([d for d in diags if d.severity == "error"], [],
                         f"unexpected errors: {diags}")

    def test_valid_full(self):
        h, diags = self._run("valid_full.sql")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [], f"unexpected errors: {errors}")

    def test_valid_answer_variants_resolves(self):
        h, diags = self._run("valid_answer_variants.sql")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [], f"unexpected errors: {errors}")

    def test_invalid_missing_required(self):
        _, diags = self._run("invalid_missing_required.sql")
        self.assertTrue(has_code(diags, "SQL-META001"))

    def test_invalid_enum(self):
        _, diags = self._run("invalid_enum.sql")
        meta002 = [d for d in diags if d.code == "SQL-META002"]
        self.assertGreaterEqual(len(meta002), 2,
                                f"expected 2 enum errors (expected, type), got {meta002}")

    def test_invalid_format(self):
        _, diags = self._run("invalid_format.sql")
        self.assertTrue(has_code(diags, "SQL-META003"))

    def test_metadata_after_runner_directive(self):
        _, diags = self._run("invalid_position_metadata_after_runner.sql")
        self.assertTrue(has_code(diags, "SQL-META005"))

    def test_inline_directives_pass_through(self):
        _, diags = self._run("inline_directive_collision.sql")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [],
                         f"inline directives must not raise errors: {errors}")

    def test_unknown_key_warns(self):
        _, diags = self._run("unknown_key_warns.sql")
        warns = [d for d in diags if d.code == "SQL-META101"]
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].severity, "warning")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [])

    def test_short_description_warns(self):
        _, diags = self._run("short_description.sql")
        warns = [d for d in diags if d.code == "SQL-META102"]
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].severity, "warning")

    def test_query_level_labels_pass(self):
        _, diags = self._run("query_level_labels.sql")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [],
                         f"query-level labels must not raise errors: {errors}")


class BomCrlfLeadingBlankTests(unittest.TestCase):
    def test_bom_at_start_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bom.sql"
            p.write_bytes(b"\xef\xbb\xbf-- @issue: none\n"
                          b"-- @description: bom test fixture for utf-8 byte order mark\n"
                          b"-- @expected: normal\n\nselect 1;\n")
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertTrue(has_code(diags, "SQL-META007"))

    def test_crlf_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "crlf.sql"
            content = (
                b"-- @issue: none\r\n"
                b"-- @description: crlf line endings normalize to lf for validation\r\n"
                b"-- @expected: normal\r\n\r\nselect 1;\r\n"
            )
            p.write_bytes(content)
            h = lint.parse_header(p)
            diags = lint.validate(h)
            errors = [d for d in diags if d.severity == "error"]
            self.assertEqual(errors, [], f"unexpected errors: {errors}")

    def test_leading_blank_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lead.sql"
            p.write_bytes(b"\n-- @issue: none\n"
                          b"-- @description: leading blank line should fail by default\n"
                          b"-- @expected: normal\n\nselect 1;\n")
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertTrue(has_code(diags, "SQL-META005"))

    def test_leading_blank_tolerated_with_flag(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lead.sql"
            p.write_bytes(b"\n-- @issue: none\n"
                          b"-- @description: leading blank line tolerated with auto-strip flag\n"
                          b"-- @expected: normal\n\nselect 1;\n")
            h = lint.parse_header(p, auto_strip_leading_blank=True)
            diags = lint.validate(h)
            errors = [d for d in diags if d.severity == "error"]
            self.assertEqual(errors, [], f"unexpected errors: {errors}")


class ContinuationTests(unittest.TestCase):
    def test_continuation_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cont.sql"
            p.write_bytes(
                b"-- @issue: none\n"
                b"-- @description: this description spans\n"
                b"   continuation line that is not allowed\n"
                b"-- @expected: normal\n\nselect 1;\n"
            )
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertTrue(has_code(diags, "SQL-META008"))


class AnswerVariantsCrossCheckTests(unittest.TestCase):
    def test_missing_variant_reports(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "x" / "cases"
            base.mkdir(parents=True)
            (Path(td) / "x" / "answers").mkdir()
            sql_path = base / "t.sql"
            sql_path.write_text(
                "-- @issue: none\n"
                "-- @description: answer_variants missing file should report SQL-META006\n"
                "-- @expected: normal\n"
                "-- @answer_variants: WIN\n\nselect 1;\n"
            )
            h = lint.parse_header(sql_path)
            diags = lint.validate(h)
            self.assertTrue(has_code(diags, "SQL-META006"))


class CliTests(unittest.TestCase):
    def _run_main(self, *argv) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = lint.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_version(self):
        rc, out, _ = self._run_main("--version")
        self.assertEqual(rc, 0)
        self.assertIn("lint_sql_metadata", out)
        self.assertIn(lint.SQL_GUIDE_SHA, out)

    def test_valid_minimal_exits_zero(self):
        rc, out, _ = self._run_main(str(CASES / "valid_minimal.sql"))
        self.assertEqual(rc, 0, f"stdout={out}")

    def test_invalid_exits_one(self):
        rc, _, _ = self._run_main(str(CASES / "invalid_missing_required.sql"))
        self.assertEqual(rc, 1)

    def test_strict_promotes_warning(self):
        rc_warn, _, _ = self._run_main(str(CASES / "unknown_key_warns.sql"))
        self.assertEqual(rc_warn, 0)
        rc_strict, _, _ = self._run_main("--strict", str(CASES / "unknown_key_warns.sql"))
        self.assertEqual(rc_strict, 1)

    def test_github_output_format(self):
        rc, out, _ = self._run_main("--github-output",
                                    str(CASES / "invalid_missing_required.sql"))
        self.assertEqual(rc, 1)
        self.assertIn("::error file=", out)
        self.assertIn("SQL-META001", out)


if __name__ == "__main__":
    unittest.main()
