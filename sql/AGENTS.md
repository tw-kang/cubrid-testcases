# sql/ — Testcase Authoring Guide

This directory holds the SQL testcase corpus consumed by the **CTP** runner
in [`cubrid-testtools`](https://github.com/CUBRID/cubrid-testtools).

> External authority: `~/cubrid-testtools/doc/sql_guide.md`
> Pinned commit: `1a3f2f877690fe1214430d8986abdfc3902c55a8`
> §5 categories · §6 testcase rules
>
> Repository back-link: [root `AGENTS.md`](../AGENTS.md)

The metadata-header convention below is a **layer on top of** sql_guide.md.
It does not modify or replace the runner rules.

## 1. Metadata header

Every newly added `.sql` file starts with a contiguous block of `-- @key: value`
lines, terminated by a blank line, before any SQL statement or `--+` runner
directive:

```sql
-- @issue: CBRD-25054
-- @description: verifies INSERT with rownum into a numeric column overflows
-- @expected: error
-- @type: issue
-- @category: _13_issues/_24_1h

set names utf8;
select 1;
```

### 1.1 Grammar (whitespace-and-colon)

| Form                              | Meaning                                       | Linted?      |
|-----------------------------------|-----------------------------------------------|--------------|
| `^-- @[a-z][a-z0-9_]*: .+$`       | Metadata line (one space after `--`, one after `:`) | **Yes**      |
| `^--@\w+`                         | Inline CTP runner directive (e.g. `--@queryplan`, `--@joingraph`) | No (pass-through) |
| `^--\+ ?...`                      | CTP control directive (e.g. `--+ holdcas on;`) | No (must follow header block) |
| Other `--` comments               | Ordinary SQL comments                          | No (must follow header block) |

The grammar separator is a **single space and a colon** after `--`. There is no
closed list of "reserved keys": any `--@<word>` (no whitespace) is treated as
an inline runner directive and never validated, which lets the runner's
directive set evolve without changing this lint.

### 1.2 Required keys

| Key            | Purpose                                                    |
|----------------|------------------------------------------------------------|
| `@issue`       | `CBRD-<digits>(,CBRD-<digits>)*` or literal `none`         |
| `@description` | Free-text, single line. **What is verified** (see §3).     |
| `@expected`    | Enum: `normal`, `error`, `mixed`                           |

### 1.3 Optional keys

| Key                | Purpose                                                  |
|--------------------|----------------------------------------------------------|
| `@type`            | Enum: `issue`, `feature`, `regression`, `medium`         |
| `@category`        | Sub-path label, e.g. `_13_issues/_24_1h`                 |
| `@id`              | Stable identifier, typically `cbrd_<digits>`             |
| `@author`          | Author handle                                            |
| `@date`            | `YYYY-MM-DD`                                             |
| `@answer_variants` | Comma list of suffixes, e.g. `WIN,cci`. Lint cross-checks `../answers/<basename>.answer_<variant>` exists. |

### 1.4 Category enum (sql_guide.md §5)

The `@type` enum mirrors the runner-side category buckets:

| `@type`      | Typical home                                  |
|--------------|-----------------------------------------------|
| `issue`      | `sql/_13_issues/...` — bug-fix regressions    |
| `feature`    | `sql/_<NN>_<feature>/...` — new feature suites |
| `regression` | Generic regression coverage                   |
| `medium`     | `medium/...` — data-fixture-dependent scenarios |

## 2. Header position & formatting rules

| Code         | Rule                                                                  |
|--------------|-----------------------------------------------------------------------|
| SQL-META001  | Required keys must all be present.                                    |
| SQL-META002  | `@expected` / `@type` values must be in the declared enum.            |
| SQL-META003  | `@issue` must match the format above.                                 |
| SQL-META004  | Lines in the block must match the exact `-- @key: value` grammar (no extra whitespace, no duplicate keys). |
| SQL-META005  | Block starts at file line 1 (or right after BOM-stripped start) and ends at the first blank line. It must precede `--+` directives. |
| SQL-META006  | `@answer_variants` files must exist on disk.                          |
| SQL-META007  | UTF-8 BOM at file start is rejected.                                  |
| SQL-META008  | Values are single-line — no continuation lines inside the block.      |
| SQL-META101  | Unknown `@key` warns (error under `--strict`).                        |
| SQL-META102  | `@description` shorter than 20 chars warns (error under `--strict`).  |

CRLF line endings are tolerated (normalised to `\n` before validation). One or
more leading blank lines can be tolerated for migration with
`--auto-strip-leading-blank`.

## 3. Description style guide

`@description` is free text (one line) but must convey **what is being
verified**. The linter only enforces a soft length floor (`SQL-META102`,
< 20 chars warns); semantic quality is a reviewer concern.

### 3.1 Field semantics

- `@description` = **what is tested** (target / scenario)
- `@expected`    = **outcome** (`normal` / `error` / `mixed`)

Read together they should form a natural sentence:
> *"@description"* should produce *"@expected"*.

### 3.2 Recommended verbs (lead with one when possible)

`verifies` · `asserts` · `checks` · `expects` · `reproduces` · `exercises`

### 3.3 Good

| Example                                                                           | Why |
|-----------------------------------------------------------------------------------|-----|
| `verifies CBRD-25054 — rownum INSERT into numeric column overflows must error`    | ticket + scenario + expected outcome  |
| `asserts varchar(0) and nchar varying(0) report syntax error at create time`      | input + expected behaviour            |
| `checks query plan stability for /*+ recompile */ hint after CBRD-25098 fix`      | target + trigger + ticket context     |
| `reproduces CBRD-22696 — varchar select returns different bytes on Windows vs CCI`| environment-comparison intent         |
| `exercises PL/CSQL block-scope rule: default expr must not reference later-decl`  | rule + violation condition            |

### 3.4 Avoid

| Example                              | Why weak                                |
|--------------------------------------|-----------------------------------------|
| ~~`create table with varchar data type`~~ | "what is verified" is empty        |
| ~~`select test`~~                          | < 20 chars → SQL-META102 warning   |
| ~~`test for varchar`~~                     | vague & generic                    |
| ~~`bug fix`~~                              | zero scenario detail               |

### 3.5 Migration heuristics

When absorbing the existing first-line comment(s) into `@description`:

1. Strip a leading `[er]` token → encode as `@expected: error` instead.
2. "Verified for CBRD-NNNNN" → fold into `@issue`, drop from description.
3. Multi-line descriptive comments → pick the most informative line, or
   concat-and-trim.
4. If < 20 chars or no recommended verb, insert a `[REVIEW]` marker and have
   a human revisit.
5. Optional: `~/skills/jira` to cross-check description against the JIRA
   ticket body (`CBRD-NNNNN`).

## 4. Query- and block-level labels (informational, not enforced)

Inside the SQL body — i.e. **after** the metadata block's terminating blank
line — two labelling idioms are common in the corpus and remain free-form:

1. `evaluate '<label>';` — a CUBRID SQL statement whose result is captured
   into the `.answer` file, easing diff-time identification. ~136 files,
   typically PL/CSQL areas.
2. `-- N. <label>` numbered comment — plain `--` comment. Common in issue
   testcases.

Neither is normalised by this convention. The linter never inspects the SQL
body, so both forms remain valid. Pick whichever fits the area's existing
style; new files have no obligation to use either.

## 5. Reference examples

### 5.1 Regression

```sql
-- @issue: CBRD-25054
-- @description: reproduces rownum INSERT overflow into a numeric column
-- @expected: error
-- @type: regression

create table t (n numeric(3));
insert into t select rownum from db_class limit 5000;
```

### 5.2 Issue (with answer variants)

```sql
-- @issue: CBRD-22696
-- @description: verifies varchar select returns identical bytes on WIN and cci
-- @expected: normal
-- @type: issue
-- @answer_variants: WIN,cci

select cast('abc' as varchar(3));
```

### 5.3 Feature

```sql
-- @issue: CBRD-25447
-- @description: verifies parallel heap scan returns correct rows under load
-- @expected: normal
-- @type: feature

set parallel_heap_scan = on;
select count(*) from large_tbl;
```

### 5.4 Multiple tickets

```sql
-- @issue: CBRD-26104,CBRD-26200,CBRD-26206
-- @description: asserts uncorrelated subqueries execute in parallel by default
-- @expected: normal
-- @type: feature
```

## 6. Linting locally

```bash
# Single file
python3 tool/lint_sql_metadata.py sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql

# Whole subtree
python3 tool/lint_sql_metadata.py sql/_36_guava

# Strict (warnings → errors)
python3 tool/lint_sql_metadata.py --strict sql/_36_guava

# Mirror the CI behaviour
python3 tool/lint_sql_metadata.py --migrated-since origin/develop
```

See [`tool/README.md`](../tool/README.md) for the full diagnostic table.

## 7. Adoption policy

- **New `.sql` files** are gated by [the CI workflow](../.github/workflows/sql-metadata-lint.yml).
- **Modified `.sql` files** are also gated; if you touch a file without a
  header, add one as part of your change.
- **Untouched `.sql` files** are grandfathered. A bulk migration to a directory
  may be done as its own PR using `--auto-strip-leading-blank` plus a manual
  review pass.

When the metadata-header coverage of `sql/_13_issues/` reaches ~80%, the
`SQL-META101` (unknown key) and `SQL-META102` (short description) warnings
will be evaluated for promotion to errors. That decision is tracked in the
plan's "Follow-ups" list.
