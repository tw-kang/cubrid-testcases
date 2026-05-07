#!/usr/bin/env python3
# Synthesized from cubrid-testtools@1a3f2f877690fe1214430d8986abdfc3902c55a8 sql_guide.md §5,§6
"""SQL testcase metadata header lint.

Validates `-- @key: value` header conventions for cubrid-testcases .sql files.
Stdlib only, Python 3.10+.

CLI:
    python3 tool/lint_sql_metadata.py [--strict] [--migrated-since <ref>] \
        [--github-output] [--auto-strip-leading-blank] <file_or_dir> [...]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

LINT_VERSION = "0.1.0"
SQL_GUIDE_SHA = "1a3f2f877690fe1214430d8986abdfc3902c55a8"

REQUIRED_KEYS = ("issue", "description", "expected")
OPTIONAL_KEYS = ("type", "category", "id", "author", "date", "answer_variants")
KNOWN_KEYS = set(REQUIRED_KEYS) | set(OPTIONAL_KEYS)

ENUM_EXPECTED = {"normal", "error", "mixed"}
ENUM_TYPE = {"issue", "feature", "regression", "medium"}

META_LINE = re.compile(r"^-- @([a-z][a-z0-9_]*): (.+)$")
META_LINE_LOOSE = re.compile(r"^--\s*@([A-Za-z][A-Za-z0-9_]*)\s*:?\s*(.*)$")
INLINE_DIRECTIVE = re.compile(r"^--@\w+")
RUNNER_DIRECTIVE = re.compile(r"^--\+ ?")
ISSUE_FORMAT = re.compile(r"^(CBRD-\d+)(,CBRD-\d+)*$|^none$")
BOM = b"\xef\xbb\xbf"
MAX_FILE_BYTES = 1 << 20  # 1 MiB; SQL testcases are small (largest in corpus is ~50 KB)
VARIANT_TOKEN = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    col: int
    code: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def format_plain(self) -> str:
        return f"{self.path}:{self.line}:{self.col}: {self.code}: {self.message}"

    def format_github(self) -> str:
        kind = "error" if self.severity == "error" else "warning"
        msg = self.message.replace("\n", " ").replace("\r", " ")
        return f"::{kind} file={self.path},line={self.line},col={self.col}::{self.code}: {msg}"


@dataclass
class Header:
    path: str
    keys: dict[str, str] = field(default_factory=dict)
    key_lines: dict[str, int] = field(default_factory=dict)
    block_end_line: int = 0
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read(MAX_FILE_BYTES + 1)


def parse_header(path: Path, *, auto_strip_leading_blank: bool = False) -> Header:
    h = Header(path=str(path))
    if path.is_symlink():
        h.diagnostics.append(
            Diagnostic(str(path), 1, 1, "SQL-META009",
                       f"path is a symlink; refusing to follow: {path}")
        )
        return h
    if not path.is_file():
        h.diagnostics.append(
            Diagnostic(str(path), 1, 1, "SQL-META009",
                       f"path is not a regular file: {path}")
        )
        return h
    raw = _read_bytes(path)

    if len(raw) > MAX_FILE_BYTES:
        h.diagnostics.append(
            Diagnostic(str(path), 1, 1, "SQL-META009",
                       f"file exceeds {MAX_FILE_BYTES} bytes; refusing to lint")
        )
        return h

    if raw.startswith(BOM):
        h.diagnostics.append(
            Diagnostic(h.path, 1, 1, "SQL-META007",
                       "UTF-8 BOM at file start; remove BOM bytes")
        )
        raw = raw[len(BOM):]

    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    if not text.strip():
        h.diagnostics.append(
            Diagnostic(h.path, 1, 1, "SQL-META010",
                       "file empty; metadata header required")
        )
        return h

    idx = 0
    if auto_strip_leading_blank:
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
    elif lines and lines[0].strip() == "":
        h.diagnostics.append(
            Diagnostic(h.path, 1, 1, "SQL-META005",
                       "metadata block must start at line 1 (leading blank line); "
                       "use --auto-strip-leading-blank for migration")
        )
        return h

    if idx >= len(lines):
        h.diagnostics.append(
            Diagnostic(h.path, 1, 1, "SQL-META010",
                       "file empty; metadata header required")
        )
        return h

    first = lines[idx]
    if RUNNER_DIRECTIVE.match(first):
        h.diagnostics.append(
            Diagnostic(h.path, idx + 1, 1, "SQL-META005",
                       "metadata block must precede '--+' runner directives")
        )
        return h
    if INLINE_DIRECTIVE.match(first):
        h.diagnostics.append(
            Diagnostic(h.path, idx + 1, 1, "SQL-META001",
                       "missing required metadata header (file starts with inline directive)")
        )
        return h
    if not first.startswith("-- @"):
        h.diagnostics.append(
            Diagnostic(h.path, idx + 1, 1, "SQL-META001",
                       "missing required metadata header at file start "
                       "(expected '-- @key: value')")
        )
        return h

    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            break
        if RUNNER_DIRECTIVE.match(line):
            h.diagnostics.append(
                Diagnostic(h.path, idx + 1, 1, "SQL-META005",
                           "metadata block must precede '--+' runner directives; "
                           "separate the block with a blank line")
            )
            break
        if INLINE_DIRECTIVE.match(line):
            # Inline directives like --@queryplan terminate the metadata block (treated
            # like a blank line). They never trigger SQL-META004 grammar diagnostics.
            break
        m = META_LINE.match(line)
        if m:
            key, value = m.group(1), m.group(2).rstrip()
            if key in h.keys:
                h.diagnostics.append(
                    Diagnostic(h.path, idx + 1, 1, "SQL-META004",
                               f"duplicate metadata key '@{key}'")
                )
            h.keys[key] = value
            h.key_lines[key] = idx + 1
            idx += 1
            continue

        loose = META_LINE_LOOSE.match(line)
        if loose:
            h.diagnostics.append(
                Diagnostic(h.path, idx + 1, 1, "SQL-META004",
                           "metadata grammar violation: expected exactly "
                           "'-- @<key>: <value>' (lowercase key, non-empty value, "
                           "single space after '--', single space after ':')")
            )
            idx += 1
            continue

        h.diagnostics.append(
            Diagnostic(h.path, idx + 1, 1, "SQL-META008",
                       "metadata block continuation not allowed; "
                       "values must be single-line. End block with a blank line.")
        )
        idx += 1

    h.block_end_line = idx

    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "":
            idx += 1
            continue
        if line.startswith("-- @") and META_LINE.match(line):
            h.diagnostics.append(
                Diagnostic(h.path, idx + 1, 1, "SQL-META005",
                           "metadata key found after blank line; "
                           "header block must be contiguous from file start")
            )
        break

    return h


def validate(header: Header) -> list[Diagnostic]:
    diags: list[Diagnostic] = list(header.diagnostics)

    if any(d.code == "SQL-META005" and "leading blank" in d.message for d in diags):
        return diags
    if any(d.code in ("SQL-META009", "SQL-META010") for d in diags):
        return diags
    # A bare missing-header SQL-META001 from parse_header (e.g. "starts with
    # inline directive", "no @key found at line 1") also short-circuits — the
    # missing-key follow-ups would be redundant noise.
    if any(d.code == "SQL-META001" and d.line == 1 and "metadata header" in d.message
           for d in diags):
        return diags

    for k in REQUIRED_KEYS:
        if k not in header.keys:
            diags.append(
                Diagnostic(header.path, 1, 1, "SQL-META001",
                           f"missing required key '@{k}'")
            )

    if "expected" in header.keys:
        v = header.keys["expected"].strip()
        if v not in ENUM_EXPECTED:
            diags.append(
                Diagnostic(header.path, header.key_lines["expected"], 1,
                           "SQL-META002",
                           f"@expected: '{v}' not in {sorted(ENUM_EXPECTED)}")
            )
    if "type" in header.keys:
        v = header.keys["type"].strip()
        if v not in ENUM_TYPE:
            diags.append(
                Diagnostic(header.path, header.key_lines["type"], 1,
                           "SQL-META002",
                           f"@type: '{v}' not in {sorted(ENUM_TYPE)}")
            )

    if "issue" in header.keys:
        v = header.keys["issue"].strip()
        if not ISSUE_FORMAT.match(v):
            diags.append(
                Diagnostic(header.path, header.key_lines["issue"], 1,
                           "SQL-META003",
                           f"@issue: '{v}' does not match "
                           "'CBRD-<digits>(,CBRD-<digits>)*' or 'none'")
            )

    if "description" in header.keys:
        v = header.keys["description"].strip()
        if len(v) < 20:
            diags.append(
                Diagnostic(header.path, header.key_lines["description"], 1,
                           "SQL-META102",
                           f"@description shorter than 20 chars ({len(v)}); "
                           "describe what is verified",
                           severity="warning")
            )

    for k in header.keys:
        if k not in KNOWN_KEYS:
            diags.append(
                Diagnostic(header.path, header.key_lines[k], 1,
                           "SQL-META101",
                           f"unknown metadata key '@{k}'",
                           severity="warning")
            )

    if "answer_variants" in header.keys:
        variants_raw = header.keys["answer_variants"].strip()
        variants = [v.strip() for v in variants_raw.split(",") if v.strip()]
        sql_path = Path(header.path)
        cases_dir = sql_path.parent
        if cases_dir.name == "cases":
            answers_dir = cases_dir.parent / "answers"
            base = sql_path.stem
            for variant in variants:
                if not VARIANT_TOKEN.match(variant):
                    diags.append(
                        Diagnostic(header.path,
                                   header.key_lines["answer_variants"], 1,
                                   "SQL-META006",
                                   f"invalid variant token '{variant}' "
                                   "(must match [A-Za-z0-9_]+)")
                    )
                    continue
                expected = answers_dir / f"{base}.answer_{variant}"
                if not expected.exists():
                    diags.append(
                        Diagnostic(header.path,
                                   header.key_lines["answer_variants"], 1,
                                   "SQL-META006",
                                   f"@answer_variants references missing file: {expected}")
                    )

    return diags


def _iter_sql_files(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.sql")))
        elif p.is_file():
            if p.suffix == ".sql":
                out.append(p)
        else:
            print(f"warning: path not found: {t}", file=sys.stderr)
    return out


def _diff_sql_files(ref: str) -> list[Path]:
    if ref.startswith("-"):
        print(f"error: ref must not start with '-': {ref!r}", file=sys.stderr)
        sys.exit(2)
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM",
             f"{ref}...HEAD", "--", "*.sql"],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("error: git not found in PATH", file=sys.stderr)
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print(f"error: git diff failed against ref '{ref}': {e.stderr.strip()}",
              file=sys.stderr)
        print(f"hint: ensure '{ref}' is fetched (e.g., "
              f"'git fetch origin {ref}:refs/remotes/{ref}')",
              file=sys.stderr)
        sys.exit(2)
    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    return [f for f in files if f.exists() and f.suffix == ".sql"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_sql_metadata",
        description="Lint SQL testcase metadata headers per cubrid-testcases convention.",
    )
    parser.add_argument("paths", nargs="*", help="files or directories to lint")
    parser.add_argument("--strict", action="store_true",
                        help="promote warnings (SQL-META101, SQL-META102) to errors")
    parser.add_argument("--migrated-since", metavar="REF",
                        help="lint only .sql changed since git REF (paths arg ignored)")
    parser.add_argument("--github-output", action="store_true",
                        help="emit GitHub Actions annotation format")
    parser.add_argument("--auto-strip-leading-blank", action="store_true",
                        help="tolerate leading blank line(s) before header (migration aid)")
    parser.add_argument("--version", action="store_true",
                        help="print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(f"lint_sql_metadata {LINT_VERSION} "
              f"(sql_guide.md@{SQL_GUIDE_SHA})")
        return 0

    if args.migrated_since and args.paths:
        parser.error("--migrated-since is mutually exclusive with positional <paths>")

    if args.migrated_since:
        files = _diff_sql_files(args.migrated_since)
    elif args.paths:
        files = _iter_sql_files(args.paths)
    else:
        parser.error("no paths provided (or use --migrated-since REF)")

    if not files:
        if args.migrated_since:
            print(f"info: no .sql changes since '{args.migrated_since}'",
                  file=sys.stderr)
        return 0

    error_count = 0
    warning_count = 0

    for f in files:
        header = parse_header(f, auto_strip_leading_blank=args.auto_strip_leading_blank)
        diags = validate(header)
        for d in diags:
            severity = d.severity
            if args.strict and severity == "warning":
                severity = "error"
            effective = Diagnostic(d.path, d.line, d.col, d.code, d.message, severity)
            if args.github_output:
                print(effective.format_github())
            else:
                print(effective.format_plain())
            if severity == "error":
                error_count += 1
            else:
                warning_count += 1

    if error_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
