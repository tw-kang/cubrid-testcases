# cubrid-testcases — Repository Guide

This repository holds CUBRID SQL/feature testcases driven by the **CTP** test
runner that lives in a sibling repository, [`cubrid-testtools`](https://github.com/CUBRID/cubrid-testtools).
The runner reads `.sql` cases from this tree, executes them, and diffs the
output against checked-in `.answer*` golden files.

## External authority

The single source of truth for **how to write a testcase** is:

> `~/cubrid-testtools/doc/sql_guide.md`
> Pinned commit: `1a3f2f877690fe1214430d8986abdfc3902c55a8`
> §5 covers categories, §6 covers the testcase rules.

This repository must **not** redefine those rules. The metadata-header
convention introduced here is a *layer on top* of the sql_guide rules — it does
not replace them.

## Directory map

| Path          | What lives here                                                   | Metadata header? |
|---------------|-------------------------------------------------------------------|------------------|
| `sql/`        | ~17.4k `.sql` testcases organised by feature/issue category       | Yes — see [`sql/AGENTS.md`](sql/AGENTS.md) |
| `medium/`     | ~970 `.sql` cases that depend on backed-up data fixtures          | Yes — see [`medium/AGENTS.md`](medium/AGENTS.md) |
| `isolation/`  | Transaction-isolation scenarios in a non-`.sql` runner format     | **No** — out of scope for this convention |
| `tool/`       | Repo utilities (lint, grep). See [`tool/README.md`](tool/README.md) |  — |
| `.github/`    | CI workflows (`sql-metadata-lint.yml` gates `.sql` PRs)           |  — |

## Metadata header convention (summary)

New `.sql` testcases under `sql/` and `medium/` start with a contiguous block
of `-- @key: value` lines, terminated by a blank line:

```sql
-- @issue: CBRD-12345
-- @description: verifies that <something specific> behaves as expected
-- @expected: normal

select 1;
```

Required keys: `@issue`, `@description`, `@expected`. Optional keys:
`@type`, `@category`, `@id`, `@author`, `@date`, `@answer_variants`.
**Inline CTP runner directives** like `--@queryplan` (no space before `@`) are
left untouched and pass through the linter unchanged.

Full grammar, enums, and the Description Style Guide live in
[`sql/AGENTS.md`](sql/AGENTS.md). Migration is gradual: existing files are
grandfathered, only added/modified `.sql` are gated by the
[`sql-metadata-lint`](.github/workflows/sql-metadata-lint.yml) CI workflow.

## Linter

```bash
python3 tool/lint_sql_metadata.py sql/_36_guava
python3 -m unittest tool.tests.test_lint_sql_metadata -v
```

See [`tool/README.md`](tool/README.md) for full usage, exit codes, and
diagnostic codes.

## Out of scope

- **`sql/_13_issues/_24_1h/cases/cbrd_25054.sql` migration + `_26_1h/cases/cbrd_26999_metadata_sample.sql` sample** were deferred from this branch. The `_36_guava` migration (12 files) substitutes equivalent reference evidence per the priority redirect. The `_13_issues` PR3 work is tracked as a follow-up PR.
- **`isolation/`** has zero `.sql` files; its scenario files use a different
  format and the metadata-header convention does not apply.
- **`~/cubrid-testtools`** is the upstream runner repo and is not modified
  from this side. Drift in `sql_guide.md` is detected via the SHA pin in
  `tool/lint_sql_metadata.py` and `sql/AGENTS.md`.
