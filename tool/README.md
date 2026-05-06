# tool/

Repository utilities for `cubrid-testcases`.

## `lint_sql_metadata.py`

Validates the `-- @key: value` metadata header convention on `.sql` testcase files.

> Synthesized from `cubrid-testtools@1a3f2f877690fe1214430d8986abdfc3902c55a8`
> `doc/sql_guide.md` §5 (categories) and §6 (testcase rules).

### Usage

```bash
# Lint a single file
python3 tool/lint_sql_metadata.py sql/_36_guava/cbrd_25447/cases/cbrd_25447.sql

# Lint a directory tree
python3 tool/lint_sql_metadata.py sql/_36_guava

# Diff-mode: lint only .sql added or modified since a git ref
python3 tool/lint_sql_metadata.py --migrated-since origin/develop

# Strict mode: warnings (SQL-META101, SQL-META102) become errors
python3 tool/lint_sql_metadata.py --strict sql/_36_guava

# GitHub Actions annotation output
python3 tool/lint_sql_metadata.py --github-output <files>

# Migration aid: tolerate one or more leading blank lines before the header
python3 tool/lint_sql_metadata.py --auto-strip-leading-blank <files>

# Print version and pinned sql_guide.md SHA
python3 tool/lint_sql_metadata.py --version
```

### Exit codes

| Code | Meaning                                     |
|------|---------------------------------------------|
| `0`  | pass (no errors; warnings are allowed)      |
| `1`  | one or more errors                          |
| `2`  | invocation error (bad args, git failure)    |

### Diagnostic codes

| Code           | Severity | Meaning                                                    |
|----------------|----------|------------------------------------------------------------|
| `SQL-META001`  | error    | missing required key (`@issue`, `@description`, `@expected`) |
| `SQL-META002`  | error    | enum violation (`@expected`, `@type`)                       |
| `SQL-META003`  | error    | `@issue` does not match `CBRD-<digits>(,CBRD-<digits>)*` or `none` |
| `SQL-META004`  | error    | grammar violation in `-- @key: value` line, or duplicate key |
| `SQL-META005`  | error    | header must start at file line 1, before any `--+` runner directive |
| `SQL-META006`  | error    | `@answer_variants` references a non-existent answer file    |
| `SQL-META007`  | error    | UTF-8 BOM at file start                                     |
| `SQL-META008`  | error    | metadata block continuation line (values must be single-line) |
| `SQL-META101`  | warning  | unknown metadata key (promoted to error under `--strict`)   |
| `SQL-META102`  | warning  | `@description` shorter than 20 chars (promoted under `--strict`) |

### Grammar

- **Metadata line**: `^-- @[a-z][a-z0-9_]*: .+$` (one space after `--`, one space after `:`).
- **Inline CTP directive**: `^--@\w+` (no space before `@`) is treated as pass-through and never validated. Examples: `--@queryplan`, `--@joingraph`.
- **Runner directive**: `--+ ...` (CTP control commands) must follow the metadata block.

### Tests

```bash
python3 -m unittest tool.tests.test_lint_sql_metadata -v
```

### JIRA cross-check (optional)

The `~/skills/jira` skill can be used to cross-check `@description` against the
CUBRID JIRA ticket body. See the (planned) `tool/migrate_sql_metadata.py
--jira-verify` flag.

## `tc_grep.sh`

Existing shell utility for grepping across the testcase corpus.
