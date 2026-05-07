"""Unit tests for tool/lint_sql_metadata.py.

Run from repo root:
    python3 -m unittest tool.tests.test_lint_sql_metadata -v
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tool"))

# Sentinel: if this test file is moved, the parents[2] math breaks. Fail
# loudly here instead of producing misleading "missing CI workflow" or
# "fixture not found" errors downstream.
assert (REPO_ROOT / "tool" / "lint_sql_metadata.py").is_file(), (
    f"REPO_ROOT resolution broken (got {REPO_ROOT}); "
    f"adjust Path(__file__).resolve().parents[N] or move tests back to tool/tests/"
)

import lint_sql_metadata as lint  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CASES = FIXTURES / "cases"


def has_code(diags, code, severity=None):
    for d in diags:
        if d.code == code and (severity is None or d.severity == severity):
            return True
    return False


def make_sql_fixture(td, content, *, name="t.sql", mode="text"):
    """Write a temp .sql fixture and return its Path. mode=text|bytes."""
    p = Path(td) / name
    if mode == "bytes":
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
    else:
        p.write_text(content)
    return p


def diag_for(content, *, mode="text", parse_kwargs=None):
    """One-shot: write content to temp file, parse + validate, return diagnostics."""
    parse_kwargs = parse_kwargs or {}
    with tempfile.TemporaryDirectory() as td:
        p = make_sql_fixture(td, content, mode=mode)
        h = lint.parse_header(p, **parse_kwargs)
        return lint.validate(h)


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
        self.assertEqual(
            set(h.keys),
            {"issue", "description", "expected", "type", "category",
             "id", "author", "date"},
            f"expected all 8 keys to parse, got {set(h.keys)}"
        )

    def test_valid_answer_variants_resolves(self):
        # Preconditions for the cross-check resolver: the cases dir must be
        # named exactly "cases" AND the sibling answers files must exist on
        # disk. Without these, the resolver silently skips and the test would
        # false-pass.
        self.assertEqual(CASES.name, "cases",
                         f"fixture parent must be named 'cases', got {CASES.name!r}")
        self.assertTrue((FIXTURES / "answers" / "valid_answer_variants.answer_WIN").is_file(),
                        "fixture answer_WIN missing — cross-check would silently skip")
        self.assertTrue((FIXTURES / "answers" / "valid_answer_variants.answer_cci").is_file(),
                        "fixture answer_cci missing — cross-check would silently skip")
        h, diags = self._run("valid_answer_variants.sql")
        errors = [d for d in diags if d.severity == "error"]
        self.assertEqual(errors, [], f"unexpected errors: {errors}")
        # Pin that the cross-check fired (i.e. answers/ resolution is working,
        # not silently skipped). Both variants resolve, so zero SQL-META006.
        meta006 = [d for d in diags if d.code == "SQL-META006"]
        self.assertEqual(meta006, [],
                         f"variants WIN+cci both exist on disk; META006 must not fire: {meta006}")
        # And confirm both keys parsed
        self.assertIn("answer_variants", h.keys)
        self.assertEqual(h.keys["answer_variants"], "WIN,cci")

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

    def test_missing_required_and_enum_coexist(self):
        """Both SQL-META001 (missing key) and SQL-META002 (bad enum) must surface."""
        diags = diag_for(
            "-- @issue: none\n"
            "-- @description: missing @expected, plus invalid @type enum value\n"
            "-- @type: notatype\n\nselect 1;\n"
        )
        codes = {d.code for d in diags}
        self.assertIn("SQL-META001", codes,
                      f"expected SQL-META001 (missing @expected), got {codes}")
        self.assertIn("SQL-META002", codes,
                      f"expected SQL-META002 (invalid @type), got {codes}")

    def test_no_meta001_when_all_required_keys_present(self):
        """Explicit pin: SQL-META001 must not fire on a valid minimal header."""
        _, diags = self._run("valid_minimal.sql")
        self.assertFalse(any(d.code == "SQL-META001" for d in diags),
                         f"SQL-META001 must not fire on valid file: "
                         f"{[d.code for d in diags]}")

    def test_inline_directive_inside_header_block(self):
        """An inline `--@directive` between metadata lines must terminate the block, not trigger SQL-META004."""
        diags = diag_for(
            "-- @issue: none\n"
            "-- @description: inline directive splits the header without a META004\n"
            "--@queryplan\n"
            "-- @expected: normal\n\nselect 1;\n"
        )
        codes = {d.code for d in diags}
        self.assertNotIn("SQL-META004", codes,
                         f"inline directive must not be reported as grammar violation: {codes}")
        # The header block ended at --@queryplan; @expected was never parsed.
        self.assertIn("SQL-META001", codes,
                      f"@expected appears after the inline directive so it's missing: {codes}")

    def test_issue_format_rejects_embedded_substring(self):
        """If the ^...$ anchors on ISSUE_FORMAT are dropped, 'prefix CBRD-123 suffix' would match.
        Pin that the anchors are honored."""
        diags = diag_for(
            "-- @issue: prefix CBRD-123 suffix\n"
            "-- @description: anchored regex must reject embedded ticket substrings\n"
            "-- @expected: normal\n\nselect 1;\n"
        )
        self.assertTrue(any(d.code == "SQL-META003" for d in diags),
                        f"embedded CBRD substring must be rejected, got {[d.code for d in diags]}")


class FileTypeGuardTests(unittest.TestCase):
    def test_directory_path_reports_meta009(self):
        with tempfile.TemporaryDirectory() as td:
            h = lint.parse_header(Path(td))
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META009" for d in diags))

    def test_broken_symlink_reports_meta009(self):
        with tempfile.TemporaryDirectory() as td:
            link = Path(td) / "broken.sql"
            link.symlink_to(Path(td) / "nonexistent.sql")
            h = lint.parse_header(link)
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META009" for d in diags))

    def test_symlink_to_regular_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "real.sql"
            target.write_text("-- @issue: none\n"
                              "-- @description: target file used by symlink test\n"
                              "-- @expected: normal\n\nselect 1;\n")
            link = Path(td) / "link.sql"
            link.symlink_to(target)
            h = lint.parse_header(link)
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META009" and "symlink" in d.message
                                for d in diags),
                            f"expected symlink rejection, got {diags}")

    def test_oversized_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "big.sql"
            # write 2 MiB (over the 1 MiB cap)
            p.write_bytes(b"-- @issue: none\n" + b"x" * (2 << 20))
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META009" and "exceeds" in d.message
                                for d in diags),
                            f"expected size-cap rejection, got {diags}")


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

    def test_multiple_leading_blanks_tolerated_with_flag(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lead.sql"
            p.write_bytes(b"\n\n\n-- @issue: none\n"
                          b"-- @description: multiple leading blank lines also tolerated\n"
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

    def test_well_formed_header_does_not_trigger_meta008(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.sql"
            p.write_text(
                "-- @issue: CBRD-12345\n"
                "-- @description: well-formed multi-key header must not trigger META008\n"
                "-- @expected: normal\n"
                "-- @type: feature\n"
                "-- @category: test\n\nselect 1;\n"
            )
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertFalse(any(d.code == "SQL-META008" for d in diags),
                             f"well-formed header must not emit SQL-META008: "
                             f"{[d.code for d in diags]}")


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

    def test_answer_variants_outside_cases_dir_silently_skipped(self):
        """If the .sql is not inside a `cases/` dir, the cross-check is skipped (no META006)."""
        with tempfile.TemporaryDirectory() as td:
            sql_path = Path(td) / "loose.sql"  # NOT inside a `cases/` directory
            sql_path.write_text(
                "-- @issue: none\n"
                "-- @description: file outside cases directory bypasses cross-check\n"
                "-- @expected: normal\n"
                "-- @answer_variants: WIN\n\nselect 1;\n"
            )
            h = lint.parse_header(sql_path)
            diags = lint.validate(h)
            self.assertFalse(any(d.code == "SQL-META006" for d in diags),
                             "out-of-cases file must skip the cross-check")


class EmptyFileTests(unittest.TestCase):
    def test_empty_or_whitespace_only_reports_meta010(self):
        """Empty file or whitespace-only file → SQL-META010 (not SQL-META005)."""
        for content in [b"", b"\n\n\n"]:
            with self.subTest(content=content):
                diags = diag_for(content, mode="bytes")
                codes = {d.code for d in diags}
                self.assertIn("SQL-META010", codes,
                              f"content={content!r}: codes={codes}")
                self.assertNotIn("SQL-META005", codes,
                                 f"content={content!r}: codes={codes}")

    def test_bom_only_file_reports_both_codes(self):
        """A file consisting only of BOM bytes reports SQL-META007 (BOM) AND SQL-META010 (empty)."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bom_only.sql"
            p.write_bytes(b"\xef\xbb\xbf")
            h = lint.parse_header(p)
            diags = lint.validate(h)
            codes = {d.code for d in diags}
            self.assertIn("SQL-META007", codes,
                          f"expected SQL-META007 for BOM, got {codes}")
            self.assertIn("SQL-META010", codes,
                          f"expected SQL-META010 for empty post-BOM content, got {codes}")


class RunnerDirectiveInsideHeaderTests(unittest.TestCase):
    def test_runner_directive_no_blank_separator(self):
        """Header followed immediately by --+ (no blank line) → SQL-META005, not 008."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "no_sep.sql"
            p.write_bytes(
                b"-- @issue: none\n"
                b"-- @description: header runs into runner directive without blank line\n"
                b"-- @expected: normal\n"
                b"--+ holdcas on;\n"
                b"select 1;\n"
            )
            h = lint.parse_header(p)
            diags = lint.validate(h)
            codes = [d.code for d in diags]
            self.assertIn("SQL-META005", codes,
                          f"expected SQL-META005 for runner-after-header, got {codes}")
            self.assertNotIn("SQL-META008", codes,
                             f"runner directive must not be reported as continuation: {codes}")


class PartialAnswerVariantsTests(unittest.TestCase):
    def test_partial_variant_hit_reports_only_missing(self):
        with tempfile.TemporaryDirectory() as td:
            cases = Path(td) / "x" / "cases"
            answers = Path(td) / "x" / "answers"
            cases.mkdir(parents=True)
            answers.mkdir()
            (answers / "t.answer_cci").write_text("ok\n")
            sql_path = cases / "t.sql"
            sql_path.write_text(
                "-- @issue: none\n"
                "-- @description: variant cci exists, WIN does not — expect one report\n"
                "-- @expected: normal\n"
                "-- @answer_variants: WIN,cci\n\nselect 1;\n"
            )
            h = lint.parse_header(sql_path)
            diags = lint.validate(h)
            meta006 = [d for d in diags if d.code == "SQL-META006"]
            self.assertEqual(len(meta006), 1,
                             f"expected exactly one SQL-META006, got {meta006}")
            self.assertIn("WIN", meta006[0].message)


class VariantTokenValidationTests(unittest.TestCase):
    def test_path_traversal_variant_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cases = Path(td) / "x" / "cases"
            answers = Path(td) / "x" / "answers"
            cases.mkdir(parents=True)
            answers.mkdir()
            sql_path = cases / "t.sql"
            sql_path.write_text(
                "-- @issue: none\n"
                "-- @description: variant token with path traversal must be rejected\n"
                "-- @expected: normal\n"
                "-- @answer_variants: ../../etc/passwd_x\n\nselect 1;\n"
            )
            h = lint.parse_header(sql_path)
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META006" and "invalid variant token" in d.message
                                for d in diags),
                            f"expected invalid-variant-token rejection, got {diags}")
            # also confirm we did NOT probe the traversal path
            self.assertFalse(any("etc/passwd" in d.message and "missing file" in d.message
                                 for d in diags),
                             "must not probe path-traversal target")


class RefValidationTests(unittest.TestCase):
    def test_ref_starting_with_dash_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            lint._diff_sql_files("-rf")
        self.assertEqual(cm.exception.code, 2)


class GrammarViolationTests(unittest.TestCase):
    """SQL-META004: malformed grammar lines and duplicate keys."""

    def test_meta004_grammar_violations(self):
        """SQL-META004 fires for: uppercase key, missing space after colon, duplicate key."""
        cases = [
            (
                "uppercase_key",
                "-- @issue: none\n"
                "-- @Description: capitalised key must trigger grammar violation\n"
                "-- @expected: normal\n\nselect 1;\n",
                None,  # no extra substring assertion
            ),
            (
                "missing_space_after_colon",
                "-- @issue:none\n"
                "-- @description: missing space after colon should be reported\n"
                "-- @expected: normal\n\nselect 1;\n",
                None,
            ),
            (
                "duplicate_key",
                "-- @issue: none\n"
                "-- @issue: none\n"
                "-- @description: duplicate key must surface as a META004 diagnostic\n"
                "-- @expected: normal\n\nselect 1;\n",
                "duplicate",  # message must contain this substring
            ),
        ]
        for label, content, msg_substr in cases:
            with self.subTest(case=label):
                diags = diag_for(content)
                meta004 = [d for d in diags if d.code == "SQL-META004"]
                self.assertGreaterEqual(len(meta004), 1,
                                        f"{label}: expected SQL-META004, got "
                                        f"{[d.code for d in diags]}")
                if msg_substr:
                    self.assertTrue(
                        any(msg_substr in d.message for d in meta004),
                        f"{label}: '{msg_substr}' not in any META004 message")


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

    def test_migrated_since_with_paths_errors(self):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                lint.main(["--migrated-since", "HEAD~1",
                           str(CASES / "valid_minimal.sql")])
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("mutually exclusive", err.getvalue())

    def test_github_output_warning_shape(self):
        rc, out, _ = self._run_main("--github-output",
                                    str(CASES / "unknown_key_warns.sql"))
        self.assertEqual(rc, 0, f"warnings only must exit 0; got rc={rc}, out={out}")
        self.assertIn("::warning file=", out)
        self.assertIn("SQL-META101", out)

    def test_strict_github_output_promotes_to_error(self):
        rc, out, _ = self._run_main("--strict", "--github-output",
                                    str(CASES / "unknown_key_warns.sql"))
        self.assertEqual(rc, 1)
        self.assertIn("::error file=", out)
        self.assertIn("SQL-META101", out)

    def test_no_paths_exits_two(self):
        with self.assertRaises(SystemExit) as cm:
            lint.main([])
        self.assertEqual(cm.exception.code, 2)

    def test_invalid_file_exits_one_without_strict(self):
        """An error fixture must produce rc=1 even without --strict.
        Catches the inverse mutation 'severity="warning" elsewhere'."""
        rc, _, _ = self._run_main(str(CASES / "invalid_missing_required.sql"))
        self.assertEqual(rc, 1, "error fixture must exit 1 without --strict")
        rc_strict, _, _ = self._run_main("--strict",
                                         str(CASES / "invalid_missing_required.sql"))
        self.assertEqual(rc_strict, 1,
                         "error fixture must remain exit 1 under --strict (cannot regress to 0)")


class ModuleHeaderPinTests(unittest.TestCase):
    """Pin the cubrid-testtools commit SHA in the lint module's header comment."""
    EXPECTED_SHA = "1a3f2f877690fe1214430d8986abdfc3902c55a8"

    def test_sql_guide_sha_constant_exact(self):
        self.assertEqual(lint.SQL_GUIDE_SHA, self.EXPECTED_SHA)

    def test_sha_appears_in_header_comment(self):
        module_path = Path(lint.__file__)
        first_block = "\n".join(module_path.read_text().splitlines()[:5])
        self.assertIn(self.EXPECTED_SHA, first_block,
                      "SHA pin must appear in the file header comment")

    def test_lint_version_is_semver(self):
        self.assertIsNotNone(re.fullmatch(r"\d+\.\d+\.\d+", lint.LINT_VERSION),
                             f"LINT_VERSION must be semver, got {lint.LINT_VERSION!r}")


class MigratedSinceMockTests(unittest.TestCase):
    """Mock subprocess.run to exercise --migrated-since paths without a live git fixture."""

    def test_lint_module_imports_subprocess_at_module_level(self):
        """Sanity check for patch.object targets: lint_sql_metadata must do
        `import subprocess` at module level so `lint.subprocess` is the patchable
        attribute. If a future refactor switches to `from subprocess import run`,
        the patches in this class silently no-op — guard against that here."""
        self.assertTrue(hasattr(lint, "subprocess"),
                        "lint_sql_metadata must `import subprocess` so the "
                        "MigratedSinceMockTests `patch.object(lint.subprocess, "
                        "'run', ...)` targets resolve correctly")

    def test_migrated_since_clean_diff_exits_zero(self):
        completed = subprocess.CompletedProcess(
            args=["git", "diff"], returncode=0, stdout="", stderr="")
        with patch.object(lint.subprocess, "run", return_value=completed):
            rc, _, err = self._run_main("--migrated-since", "HEAD~1")
        self.assertEqual(rc, 0)
        self.assertIn("no .sql changes", err)

    def test_migrated_since_git_failure_exits_two_with_hint(self):
        err_obj = lint.subprocess.CalledProcessError(
            128, ["git", "diff"], stderr="fatal: bad ref")
        with patch.object(lint.subprocess, "run", side_effect=err_obj):
            rc, _, err = self._run_main("--migrated-since", "nonexistent/ref")
        self.assertEqual(rc, 2)
        self.assertIn("git diff failed", err)
        self.assertIn("fetched", err)  # actionable hint mentions fetching

    def test_migrated_since_uses_sql_pathspec(self):
        """The git diff invocation must restrict to *.sql via pathspec."""
        completed = subprocess.CompletedProcess(
            args=["git", "diff"], returncode=0, stdout="", stderr="")
        with patch.object(lint.subprocess, "run", return_value=completed) as mock_run:
            self._run_main("--migrated-since", "HEAD~1")
        # Inspect the argv list passed to subprocess.run
        called_args = mock_run.call_args[0][0]
        self.assertIn("*.sql", called_args,
                      f"git diff must use *.sql pathspec; got argv {called_args}")
        self.assertIn("--", called_args,
                      f"-- separator required before pathspec; got argv {called_args}")

    def _run_main(self, *argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = lint.main(list(argv))
            except SystemExit as e:
                rc = e.code if e.code is not None else 0
        return rc, out.getvalue(), err.getvalue()


class WorkflowFileTests(unittest.TestCase):
    """Pin a few CI-workflow contract strings without depending on PyYAML."""
    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "sql-metadata-lint.yml"

    def test_workflow_file_exists(self):
        self.assertTrue(self.WORKFLOW.is_file(),
                        f"missing CI workflow at {self.WORKFLOW}")

    def test_workflow_uses_fetch_depth_zero(self):
        text = self.WORKFLOW.read_text()
        self.assertIn("fetch-depth: 0", text,
                      "checkout must request full history for diff base")

    def test_workflow_uses_strict_bash(self):
        # The threshold "2" pins the current shape: both the diff-collect step
        # and the lint step run under strict bash. If steps are split or merged
        # legitimately, update this number — that's the desired forcing function.
        text = self.WORKFLOW.read_text()
        self.assertGreaterEqual(text.count("set -euo pipefail"), 2,
                                "at least the diff and lint steps should run "
                                "with bash strict mode")

    def test_workflow_passes_base_ref_via_env(self):
        text = self.WORKFLOW.read_text()
        # security hardening from round 1: BASE_REF is exported as env var,
        # never interpolated raw into shell.
        self.assertIn("BASE_REF: ${{ github.base_ref }}", text)
        self.assertIn("${BASE_REF}", text)


class PerformanceTests(unittest.TestCase):
    """Performance AC: 18K-file corpus must lint in under 30s. Slow test, opt-in."""

    @unittest.skipUnless(
        os.environ.get("RUN_SLOW_TESTS"),
        "set RUN_SLOW_TESTS=1 to run the 18K-file performance pin")
    def test_full_corpus_under_thirty_seconds(self):
        import subprocess
        import time
        sql = REPO_ROOT / "sql"
        medium = REPO_ROOT / "medium"
        if not sql.is_dir() or not medium.is_dir():
            self.skipTest("sql/ or medium/ missing")
        cmd = ["python3", str(REPO_ROOT / "tool" / "lint_sql_metadata.py"),
               str(sql), str(medium)]
        t0 = time.time()
        # exit code is 1 on this corpus because most files lack headers; we only
        # care about the wall-clock time, not the exit code.
        subprocess.run(cmd, capture_output=True, check=False)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 30.0,
                        f"full-corpus lint must finish in under 30s; took {elapsed:.2f}s")


class ConstantsPinTests(unittest.TestCase):
    """Pin module-level public constants. These are the spec's executable contract;
    changes must be deliberate (require updating these tests) rather than silent."""

    def test_required_keys_membership(self):
        self.assertEqual(lint.REQUIRED_KEYS, ("issue", "description", "expected"))

    def test_optional_keys_membership(self):
        # Tuple equality also pins order. Order is not load-bearing in the lint
        # module (only set membership matters at runtime), but pinning it here
        # forces deliberate review of any reshuffle.
        self.assertEqual(
            lint.OPTIONAL_KEYS,
            ("type", "category", "id", "author", "date", "answer_variants"))

    def test_known_keys_is_union(self):
        self.assertEqual(
            lint.KNOWN_KEYS,
            set(lint.REQUIRED_KEYS) | set(lint.OPTIONAL_KEYS))

    def test_enum_expected_membership(self):
        self.assertEqual(lint.ENUM_EXPECTED, {"normal", "error", "mixed"})

    def test_enum_type_membership(self):
        self.assertEqual(lint.ENUM_TYPE, {"issue", "feature", "regression", "medium"})

    def test_max_file_bytes_value(self):
        self.assertEqual(lint.MAX_FILE_BYTES, 1 << 20)

    def test_diagnostic_severity_default_is_error(self):
        d = lint.Diagnostic(path="x", line=1, col=1, code="X", message="m")
        self.assertEqual(d.severity, "error")


class BoundaryTests(unittest.TestCase):
    """Pin exact threshold values. A one-off mutation of any boundary
    (1 MiB cap, 20-char description) should fail at least one test here."""

    def test_file_at_max_size_accepted(self):
        """Exactly MAX_FILE_BYTES is the largest size accepted; +1 byte is rejected."""
        with tempfile.TemporaryDirectory() as td:
            valid_header = (
                b"-- @issue: none\n"
                b"-- @description: padded to exactly the maximum allowed size\n"
                b"-- @expected: normal\n\n"
            )
            target = lint.MAX_FILE_BYTES
            tail = b"\nselect 1;\n"
            # The pad line is `-- ` + N x's + `\n` = N + 4 bytes. Solve for N.
            pad_overhead = len(b"-- \n")
            n_x = target - len(valid_header) - len(tail) - pad_overhead
            self.assertGreater(n_x, 0,
                               f"valid_header+tail too long for MAX_FILE_BYTES={target}")
            content = valid_header + b"-- " + b"x" * n_x + b"\n" + tail
            self.assertEqual(len(content), target,
                             "test construction error: content length must equal MAX_FILE_BYTES")
            p = Path(td) / "atmax.sql"
            p.write_bytes(content)
            self.assertEqual(p.stat().st_size, target)
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertFalse(any(d.code == "SQL-META009" for d in diags),
                             f"file at exactly MAX_FILE_BYTES must be accepted, got {diags}")

    def test_file_one_byte_over_max_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "over.sql"
            p.write_bytes(b"x" * (lint.MAX_FILE_BYTES + 1))
            h = lint.parse_header(p)
            diags = lint.validate(h)
            self.assertTrue(any(d.code == "SQL-META009" for d in diags),
                            f"file 1 byte over MAX_FILE_BYTES must be rejected, got {diags}")

    def test_size_threshold_one_byte_below_and_above(self):
        """Smaller boundary check: 1 byte below MAX_FILE_BYTES accepted; +1 byte rejected.
        Complements the at-exact-max and obviously-oversized tests."""
        with tempfile.TemporaryDirectory() as td:
            for delta, expect_meta009 in [(-1, False), (+1, True)]:
                with self.subTest(delta=delta):
                    p = Path(td) / f"sz{delta:+d}.sql"
                    p.write_bytes(b"x" * (lint.MAX_FILE_BYTES + delta))
                    h = lint.parse_header(p)
                    diags = lint.validate(h)
                    has = any(d.code == "SQL-META009" for d in diags)
                    self.assertEqual(has, expect_meta009,
                                     f"delta={delta:+d}: codes={[d.code for d in diags]}")

    def test_description_length_threshold(self):
        """SQL-META102 fires iff len(@description) < 20."""
        for length, expect_warn in [(19, True), (20, False)]:
            with self.subTest(length=length):
                desc = "x" * length
                content = (
                    f"-- @issue: none\n"
                    f"-- @description: {desc}\n"
                    f"-- @expected: normal\n\nselect 1;\n"
                )
                diags = diag_for(content)
                has_warn = any(d.code == "SQL-META102" for d in diags)
                self.assertEqual(has_warn, expect_warn,
                                 f"length={length}: expected warn={expect_warn}, "
                                 f"got codes {[d.code for d in diags]}")


if __name__ == "__main__":
    unittest.main()
