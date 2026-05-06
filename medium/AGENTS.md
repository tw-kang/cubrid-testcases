# medium/ — Data-fixture-dependent Testcases

This directory holds ~970 `.sql` testcases that depend on backed-up CUBRID
data fixtures (the "MEDIUM" scenarios in CTP terminology). The metadata-header
convention defined in [`../sql/AGENTS.md`](../sql/AGENTS.md) applies here
unchanged.

> External authority: `~/cubrid-testtools/doc/sql_guide.md`
> Pinned commit: `1a3f2f877690fe1214430d8986abdfc3902c55a8`
>
> Repository back-link: [root `AGENTS.md`](../AGENTS.md)

## Header convention

New `.sql` files start with the same `-- @key: value` block as `sql/`. Use
`@type: medium` so consumers can filter the corpus by category:

```sql
-- @issue: CBRD-XXXXX
-- @description: verifies <scenario> against the medium-data backup fixture
-- @expected: normal
-- @type: medium
-- @category: <subdir>

select count(*) from huge_tbl;
```

For full grammar, enums, the Description Style Guide, and reference examples,
see [`../sql/AGENTS.md`](../sql/AGENTS.md). For lint usage, see
[`../tool/README.md`](../tool/README.md).

## Notes specific to `medium/`

- Tests here usually assume a pre-loaded backup; the runner restores the
  fixture before each run. Do not include schema/data setup at the top of
  the case unless the scenario explicitly needs to override the backup.
- Because the data volume is large, `@expected: mixed` is more common than
  in `sql/` — partial-error scenarios often coexist with success paths in
  the same case.

## Adoption policy

Same as [`../sql/AGENTS.md` §7](../sql/AGENTS.md): new and modified `.sql`
files are linted by the CI workflow; untouched files are grandfathered.
