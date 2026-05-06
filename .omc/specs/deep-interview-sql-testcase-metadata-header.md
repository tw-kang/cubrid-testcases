# Deep Interview Spec: SQL Testcase Metadata Header Convention

## Metadata
- Interview ID: di-sql-meta-header-2026-05-06
- Rounds: 2 (auto-mode compressed)
- Final Ambiguity Score: ~9% (post cubrid-testtools cross-reference)
- Type: brownfield
- Generated: 2026-05-06
- Threshold: 20%
- Initial Context Summarized: no
- Status: PASSED
- External References:
  - `~/cubrid-testtools/doc/sql_guide.md` § 5 ("How to make a SQL test case") and § 6 ("Test Case Specification")
  - `~/cubrid-testtools/CTP/conf/sql.conf` (`scenario=${HOME}/cubrid-testcases/sql`)
  - `~/cubrid-testtools/CTP/conf/isolation.conf` (`scenario=${HOME}/cubrid-testcases/isolation`)
  - `~/cubrid-testtools/CTP/sql/AGENTS.md`, `~/cubrid-testtools/CTP/AGENTS.md`

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.93 | 0.35 | 0.326 |
| Constraint Clarity | 0.90 | 0.25 | 0.225 |
| Success Criteria | 0.91 | 0.25 | 0.228 |
| Context Clarity (brownfield) | 0.90 | 0.15 | 0.135 |
| **Total Clarity** | | | **0.914** |
| **Ambiguity** | | | **0.086 (≈9%)** |

## Goal
`cubrid-testcases` 저장소 (`sql/`, `isolation/`, `medium/`) 의 모든 SQL 테스트케이스 파일에 대해, 파일 시작부 주석으로 표준화된 키-값 메타데이터 헤더 컨벤션을 도입한다. CTP 테스트 러너(`~/cubrid-testtools`)가 이미 사용 중인 `--+` 러너 지시자와 `--@<directive>` 인라인 지시자(예: `--@queryplan`)를 침해하지 않으면서, 테스트의 의도·분류·관련 이슈·기대 동작·답변 변형을 기계 파싱 가능한 형식으로 명시한다.

## Authoritative Category Taxonomy (from cubrid-testtools/doc/sql_guide.md)

`sql_guide.md` § 5 가 정의하는 두 개의 공식 카테고리 + 저장소 디렉토리 구조에서 도출되는 세 번째 카테고리:

| `@type` | 디렉토리 패턴 | 파일명 규칙 | 예시 |
|---------|-------------|-----------|------|
| `issue` | `sql/_13_issues/_{yy}_{1\|2}h/cases/` | `cbrd_xxxxx.sql`, `cbrd_xxxxx_1.sql`, `cbrd_xxxxx_2.sql`, `cbrd_xxxxx_xasl.sql` | `sql/_13_issues/_24_1h/cases/cbrd_25054.sql` |
| `feature` | `sql/_{no}_{release_code}/cbrd_xxxxx_{feature}/cases/` | `{any_structured_name}.sql` | `sql/_05_plcsql/_01_testspec/.../cases/02_02_02-02_error_same_block.sql` |
| `regression` | `sql/_NN_<topic>/_NNN_<sub>/cases/` | `NNNN.sql` (4자리 시퀀셜) | `sql/_01_object/_01_type/_001_nchar_nvarchar/cases/1001.sql` |
| `isolation` | `isolation/_NN_<level>/<scenario>/` | `_NNN_<name>.sql` | `isolation/_01_ReadCommitted/dml_ddl/_001_concurrent_ddl_dml.sql` |
| `medium` | `medium/...` | (별도 시나리오 루트, `data_file=...mdb.tar.gz`) | (CTP `medium.conf` 기준) |

**규칙:** `@type` 값은 해당 5개 enum 중 하나만 허용. `@category` 는 디렉토리 상대 경로(scenario root 기준) 를 표기 — 예: `_01_object/_01_type/_001_nchar_nvarchar`.

## Format Decision
구조화된 라인 주석 키-값 블록. 모든 메타데이터 라인은 다음 정확한 형태:

```
-- @<key>: <value>
```

- 반드시 `--`(line comment) 이후 단일 공백, 이어서 `@`, 키, 콜론, 단일 공백, 값.
- `@queryplan` 등 CTP 인라인 지시자(`--@queryplan`, 공백 없음) 와 명확히 구분됨.
- `--+ <directive>` (CTP 러너 지시자) 와도 grammatically 분리.

### 표준 배치 순서 (file top → SQL body)
```sql
-- @issue: CBRD-25054
-- @type: issue
-- @category: _13_issues/_24_1h
-- @description: rownum INSERT into numeric column should raise out-of-range error
-- @expected: error
-- @answer_variants: WIN,cci         (optional, 콤마로 구분)
-- @author: tw-kang                  (optional)
-- @date: 2026-05-06                 (optional)
--+ server-message on
--+ holdcas on

drop table if exists ...;
```

규칙:
1. 메타데이터 헤더 블록은 **파일의 가장 처음** 에 위치 (BOM/공백 줄도 그 앞에 둘 수 없음).
2. 메타데이터 블록의 끝은 **첫 빈 줄** 또는 **첫 비-`-- @`-line** 으로 정의.
3. 메타데이터 블록 다음에는 `--+` 러너 지시자, 그 다음 빈 줄, 그 다음 SQL.
4. 메타데이터 라인 사이에는 빈 줄 금지.
5. 키 이름은 lowercase, `_` 허용, `@` prefix 강제.
6. 값은 단일 라인. 다중 라인 설명은 메타데이터 블록 종료 후 일반 주석(`-- ...`) 으로 추가.
7. **공백 유무가 결정적**: `-- @<key>` (공백 있음) = 메타데이터, `--@<directive>` (공백 없음) = CTP 지시자. lint 가 양자를 엄격히 구분.

### 예약 / 금지 키
| 키 | 사유 |
|---|---|
| `@queryplan` | CTP 인라인 지시자(`--@queryplan`)와 의미 충돌. 메타데이터 필드로 사용 금지. |
| `@cci`, `@WIN` | answer 변형 의미 — `@answer_variants` 사용. |
| 공백을 포함한 키 | grammar 단순화. lint error. |

## Constraints
- 기존 `--+` 지시자(server-message, holdcas, ...) 는 그대로 유지하며 메타데이터 블록 **아래** 에 배치.
- 기존 `--@<directive>` 인라인 지시자(`--@queryplan`) 는 SQL 본문 직전에 그대로 유지. 메타데이터 헤더 블록과 분리.
- 기존 첫 줄 설명 주석(`--설명`, `--[er]설명`) 은 마이그레이션 시 `@description` 으로 흡수, `[er]` prefix 는 `@expected: error` 로 정규화.
- `tool/tc_grep.sh` 등 기존 러너 스크립트와의 호환성: `--+` / `--@queryplan` 파싱은 영향 없음.
- CTP `conf/sql.conf`, `conf/isolation.conf`, `conf/medium.conf` 의 scenario 루트 경로 변경 없음.
- SQL 파서가 `--` 라인 주석을 정상 처리하는 것을 전제 (CUBRID CSQL 기본 동작, sql_guide.md 검증).
- `.answer`, `.answer_WIN`, `.answer_cci`, `.queryPlan`, `.result` 등 비-`.sql` 자산은 본 spec 적용 대상 외.

## Non-Goals
- YAML 프론트매터, JSON 블록 헤더, XML 도입 — 모두 SQL 라인 주석 컨벤션과 이질적.
- 수천 개의 기존 .sql 파일 일괄 자동 마이그레이션 — 점진 마이그레이션 정책.
- 한 줄 설명을 넘어선 풍부한 메타데이터(테스트 데이터셋, 의존 스키마 등) — 본 spec 범위 외.
- `.answer` / `.result` / `.queryPlan` 파일 헤더 — 본 spec 은 `.sql` 만.
- sql_guide.md § 6 "Test Case Specification" 의 의미적 규칙 (DROP TABLE if exists, ORDER BY 등) 강제 — 별도 lint 영역.
- `~/cubrid-testtools` 자체에 대한 변경 — 본 spec 은 `~/cubrid-testcases` 만 수정.

## Required vs Optional Fields
| Key | Required | Type | Allowed values / Format | Notes |
|-----|----------|------|--------------------------|-------|
| `@issue` | ✅ | string | `CBRD-XXXXX` (다중: 콤마 구분) 또는 `none` | 관련 티켓 없으면 명시적으로 `none`. |
| `@description` | ✅ | string (단일 라인) | 자유 텍스트 | 기존 첫 줄 설명 주석을 흡수. `[er]` prefix 금지(→ `@expected: error`). |
| `@expected` | ✅ | enum | `normal` \| `error` \| `mixed` | sql_guide.md `--[er]` 표식의 정규화 형태. |
| `@type` | ⬜ | enum | `issue` \| `feature` \| `regression` \| `isolation` \| `medium` | sql_guide.md § 5 분류. 디렉토리에서 자동 도출 가능 → 선택. |
| `@category` | ⬜ | string | scenario root 기준 상대 디렉토리 경로 | 예: `_13_issues/_24_1h`. 디렉토리에서 자동 도출 가능 → 선택. |
| `@id` | ⬜ | string | basename without extension | 권장하지 않음(파일명과 중복). lint 가 동일성만 검증. |
| `@author` | ⬜ | string | git user.name / GitHub handle | |
| `@date` | ⬜ | string | `YYYY-MM-DD` | 최초 작성일. |
| `@answer_variants` | ⬜ | string | `WIN`, `cci`, `WIN,cci` | sql_guide.md `.answer_WIN` / `.answer_cci` 변형 명시. lint 가 실제 파일 존재성과 교차 검증 가능. |

미정의 키(예: `@requires`, `@locale`)는 lint 가 unknown key 경고만 띄우고 실패시키지 않음(확장성 보존). 단 예약 키(`@queryplan`, `@cci`, `@WIN`)는 error.

## Migration Policy
- **신규 파일 (추가/수정 시)**: 헤더 필수. lint 실패 시 CI block.
- **기존 파일 (touched in PR)**: lint 가 헤더 부재를 **warning** 으로 표시 (다음 단계에서 error 로 승격 가능).
- **기존 파일 (untouched)**: grandfathered, lint 통과.
- **일괄 마이그레이션 PR**: 디렉토리 단위로 별도 PR 분할.
  - 자동 추정 가능한 필드: `@type`(디렉토리 패턴), `@category`(상대경로), `@expected`(`[er]` 토큰), `@description`(첫 줄 주석)
  - 수동 검증 필요: `@issue`(CBRD 티켓 매핑은 git log/커밋 메시지에서 best-effort 추출, 자신 없으면 `none`)
- **CBRD 티켓 추출 휴리스틱**:
  - 파일명 `cbrd_NNNNN.sql` → `@issue: CBRD-NNNNN`
  - 디렉토리 `cbrd_NNNNN_<feature>/` → `@issue: CBRD-NNNNN`
  - 본문 주석 `-- Verified for CBRD-NNNNN` → 동일
  - 그 외 → `@issue: none`

## Acceptance Criteria
- [ ] `tool/lint_sql_metadata.py` (또는 `.sh`) 가 작성되어 다음을 검증:
  - [ ] 신규/변경된 `.sql` 파일은 `@issue`, `@description`, `@expected` 가 모두 존재
  - [ ] `@expected` 값은 `normal`/`error`/`mixed` 중 하나
  - [ ] `@issue` 값은 `CBRD-\d+` 패턴(다중 시 콤마 구분) 또는 `none`
  - [ ] `@type` 값(존재 시)은 enum 5개 중 하나, 디렉토리 패턴과 일치하는지 cross-check
  - [ ] 메타데이터 블록은 파일 최상단에 위치하고 `--+` 지시자보다 앞에 있음
  - [ ] `--@<directive>` (공백 없음) 라인은 메타데이터로 인식되지 않음 (false positive 회피)
  - [ ] 예약 키(`@queryplan`, `@cci`, `@WIN`) 는 error
  - [ ] 알려지지 않은 `@key` 는 warning, 미정의 필수 키는 error
  - [ ] `@answer_variants` 값에 명시된 변형(`WIN`, `cci`)에 대응하는 `answers/{basename}.answer_WIN` / `.answer_cci` 가 실제 존재 (cross-check)
- [ ] GitHub Actions 워크플로우(`.github/workflows/sql-metadata-lint.yml`)가 PR 의 변경된 `.sql` 파일을 대상으로 lint 실행. 실패 시 머지 차단.
- [ ] 루트 `AGENTS.md` 또는 `sql/AGENTS.md` 에 컨벤션 섹션 추가하고 `~/cubrid-testtools/doc/sql_guide.md` 를 권위 출처로 cross-link.
- [ ] 신규 reference 샘플 1개 작성 + 기존 파일 1개 마이그레이션 reference (`sql/_13_issues/_24_1h/cases/cbrd_25054.sql`) 의 example 커밋.
- [ ] (선택) `tool/migrate_sql_metadata.py` 가 자동 추정 + dry-run 옵션 제공. 휴리스틱: 디렉토리→`@type`/`@category`, 파일명→`@issue`, `[er]` 토큰→`@expected`, 첫 줄 주석→`@description`.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| 카테고리 단순 분류 | sql_guide.md 가 issue/feature 두 카테고리 명시 + 디렉토리에서 regression/isolation/medium 추가 도출 | 5-value enum (`issue/feature/regression/isolation/medium`) |
| `-- @key:` prefix 안전 | `--@queryplan` 인라인 지시자 존재 (공백 없음) | 공백 유무로 grammatically 분리 + lint 강제 |
| YAML 프론트매터가 표준 | 기존 `--` 라인 주석 컨벤션 | `-- @key: value` 라인 주석 채택 |
| 모든 파일에 일괄 적용 | 수천 개 파일에 자동 헤더 삽입은 위험 | 신규 필수 + touched-in-PR warning + 점진 마이그레이션 |
| CBRD 티켓이 모든 테스트에 존재 | 일반 회귀 테스트 다수는 티켓 없음 | `@issue: none` 허용 |
| answer 변형 정보 불필요 | sql_guide.md 에 `.answer_WIN`, `.answer_cci` 명시 | `@answer_variants` 옵션 추가, 파일 존재성 cross-check |
| 검증을 reviewer 수작업 | 수천 PR 누적 시 누락 불가피 | 독립 lint 스크립트 + CI gating |
| 첫 줄 설명 주석 폐기 | 이미 ~90% 파일이 보유한 자산 | `@description` 으로 흡수, migrate 스크립트가 도와줌 |

## Technical Context (Brownfield)

### Repository (`~/cubrid-testcases`)
- 디렉토리 구조: `sql/_NN_<topic>/_NNN_<sub>/cases/{NNNN.sql, cbrd_NNNNN.sql}` + `answers/*.answer`. `isolation/_01_ReadCommitted/<scenario>/_NNN_<name>.sql`. `medium/...` (별도 시나리오 루트).
- 기존 헤더 패턴 3종:
  1. 평문 첫 줄 설명: `--create table with varchar...`
  2. 에러 표식: `--[er]description...`
  3. CBRD 참조 + 빈 줄 + 설명: `-- Verified for CBRD-XXXXX` / `-- description...`
- `--+ server-message on`, `--+ holdcas on;` = CTP 러너가 파싱하는 예약 prefix.
- `--@queryplan` = CTP 인라인 지시자, query 직전에 위치.
- 명명 규칙: `cbrd_NNNNN[_suffix].sql` (issue/feature) vs `NNNN.sql` (regression).
- AGENTS.md: 본 저장소엔 부재. 컨벤션 신규 추가 시 root 또는 sql/ 하위 작성.
- 러너: `tool/tc_grep.sh` (answer 파일 처리). 메타데이터 lint 는 별도 도구로 격리.

### Test Runner (`~/cubrid-testtools`)
- Java 6 + Ant 기반 CTP. `bin/ctp.sh sql -c conf/sql.conf` 진입점.
- `CTP/conf/sql.conf` `scenario=${HOME}/cubrid-testcases/sql` (이 spec 의 적용 범위 정의).
- `CTP/conf/isolation.conf` `scenario=${HOME}/cubrid-testcases/isolation`.
- `CTP/conf/medium.conf` 는 sql.conf 사본 + `scenario=${HOME}/cubrid-testcases/medium` + `data_file=...mdb.tar.gz`.
- SQL_BY_CCI: 동일 .sql 파일을 CCI 인터페이스로 실행. `.answer_cci` 변형 제공 시 사용.
- Windows: `.answer_WIN` 변형 제공 시 사용.
- 테스트 작성 가이드: `~/cubrid-testtools/doc/sql_guide.md` § 5 ("How to make a SQL test case"), § 6 ("Test Case Specification").

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| TestCaseFile | core domain | path, basename, extension, headerBlock, runnerDirectives, inlineDirectives, sqlBody | belongs to Category, belongs to Type, references Issue, has AnswerVariants |
| MetadataHeader | core domain | issue, description, expected, type, category, id, author, date, answer_variants | embedded in TestCaseFile (top of file), separated by blank line from RunnerDirective block |
| RunnerDirective | supporting | name (`--+ <name>`), value | follows MetadataHeader, processed by CTP `tc_grep.sh` / runner |
| InlineDirective | supporting | name (`--@<name>`), position | inline in SQL body (e.g. `--@queryplan`), MUST NOT collide with MetadataHeader grammar |
| TestType | supporting | name (issue/feature/regression/isolation/medium) | derived from TestCaseFile.path, source: sql_guide.md § 5 |
| Category | supporting | dirPath relative to scenario root | derived from TestCaseFile.path |
| Issue | external | id (CBRD-XXXXX), tracker | referenced by MetadataHeader.issue |
| AnswerVariant | supporting | suffix (WIN, cci), file | sibling of TestCaseFile under `answers/` |
| LintScript | supporting | path (`tool/lint_sql_metadata.*`), exitCode, warnings, errors | validates MetadataHeader against rules + cross-checks AnswerVariant existence |
| MigrationScript | supporting | dryRun, transformRules | rewrites legacy first-line comments into MetadataHeader |
| CTP_Scenario | external | scenarioRoot (sql, medium, isolation), conf | sql.conf / medium.conf / isolation.conf in `~/cubrid-testtools/CTP/conf/` |
| AGENTS_doc | supporting | path (`sql/AGENTS.md` or root), conventionSection, sqlGuideXref | documents MetadataHeader rules; cross-links sql_guide.md |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 (exploration) | 5 | 5 | - | - | N/A |
| 2 (post-decisions) | 8 (+ LintScript, MigrationScript, AGENTS_doc) | 3 | 0 | 5 | 63% |
| 3 (post cubrid-testtools xref) | 12 (+ InlineDirective, TestType, AnswerVariant, CTP_Scenario) | 4 | 0 | 8 | 67% |

엔티티 명명은 모든 라운드에서 안정. cubrid-testtools 참조 후 CTP 측 외부 의존(InlineDirective, TestType, AnswerVariant, CTP_Scenario) 이 명시적으로 분리됨.

## Reference Migration Examples

### Before (regression, 기존 첫 줄 설명)
```sql
--create table with varchar data type and tests a create syntax with varchar data type and another constraint like unique,not null, shared and set default value
autocommit on;

CREATE CLASS ddl_0001(...);
```

### After
```sql
-- @issue: none
-- @type: regression
-- @description: create table with varchar data type — varchar+unique/not null/shared/default constraint syntax
-- @expected: normal

autocommit on;

CREATE CLASS ddl_0001(...);
```

### Before (regression, 에러 케이스 `[er]`)
```sql
--[er]create two tables with varchar and nchar varying data types and tests a create syntax with conditions like 'varchar(0)' or 'nchar varying(0)' and then report syntax error
create class c_v (v varchar(0));
```

### After
```sql
-- @issue: none
-- @type: regression
-- @description: create class with varchar(0) and nchar varying(0) — must report syntax error
-- @expected: error

create class c_v (v varchar(0));
```

### Before (issue, CBRD 참조 + `--+` 지시자)
```sql
--+ server-message on

-- Verified for CBRD-25017
-- a default value expression of a variable or constant cannot contain a variable/constant declared later in the same declaration block.

create or replace procedure poo as
    ...
```

### After
```sql
-- @issue: CBRD-25017
-- @type: feature
-- @category: _05_plcsql/_01_testspec/_02_declaration/_02_variable/_02_uninitialized
-- @description: PL/CSQL default value expression must not reference a variable declared later in the same block
-- @expected: error
--+ server-message on

create or replace procedure poo as
    ...
```

### Before (issue, queryplan 인라인 지시자 보존)
```sql
-- This test case verifies CBRD-25098 query plan regression.

drop table if exists t1;
create table t1 (a int);

--@queryplan
select /*+ recompile */ * from t1 where a = 1;
```

### After (인라인 지시자는 그대로, 메타데이터만 추가)
```sql
-- @issue: CBRD-25098
-- @type: issue
-- @category: _13_issues/_24_1h
-- @description: query plan regression for table scan with /*+ recompile */ hint
-- @expected: normal

drop table if exists t1;
create table t1 (a int);

--@queryplan
select /*+ recompile */ * from t1 where a = 1;
```

### Before (issue with answer variants)
```sql
-- This test case verifies CBRD-22696 — different result on Windows and CCI.

drop table if exists t1;
create table t1 (a varchar(10));
insert into t1 values ('test');
select * from t1;
```
- `answers/cbrd_22696.answer` (Linux JDBC)
- `answers/cbrd_22696.answer_WIN` (Windows variant)
- `answers/cbrd_22696.answer_cci` (CCI variant)

### After
```sql
-- @issue: CBRD-22696
-- @type: issue
-- @category: _13_issues/_22_1h
-- @description: result must differ on Windows and CCI for varchar select
-- @expected: normal
-- @answer_variants: WIN,cci

drop table if exists t1;
create table t1 (a varchar(10));
insert into t1 values ('test');
select * from t1;
```

## Interview Transcript

### Round 1 — 메타데이터 헤더 형식
**Q:** 어떤 형식으로 메타데이터를 표현할 것인가?
**A:** 구조화 키-값 헤더 (`-- @key: value`).

### Round 2 — 필수 필드 / 마이그레이션 / 검증
**Q1:** 필수 필드는?
**A1:** `@issue`, `@description`, `@expected`. `@id` 는 선택.
**Q2:** 기존 파일 마이그레이션 정책?
**A2:** 신규 파일만 필수 + 점진 마이그레이션.
**Q3:** 검증 방식?
**A3:** 독립 lint 스크립트 + CI.

### Round 3 — 외부 권위 출처 cross-reference
**Trigger:** 사용자가 `~/cubrid-testtools/` 를 카테고리 정보 참조처로 지목.
**Findings:**
- `doc/sql_guide.md` § 5 가 `issue` / `feature` 두 카테고리를 명시 → enum 도출 시 `regression` / `isolation` / `medium` 추가.
- `--@queryplan` 인라인 지시자 존재 → metadata grammar 와의 분리 규칙 명시 (공백 유무).
- `.answer_WIN`, `.answer_cci` 변형 → `@answer_variants` 옵션 필드 추가.
- `CTP/conf/{sql,isolation,medium}.conf` scenario 루트 = 본 spec 의 적용 범위 정의.
**Resolution:** `@type` 5-value enum 추가, 예약 키 목록 강화, 마이그레이션 휴리스틱 명시, AGENTS.md 가 sql_guide.md 를 cross-link.

**Final Ambiguity:** ~9% (Goal 0.93, Constraint 0.90, Criteria 0.91, Context 0.90)
