# Implementation Plan: SQL Testcase Metadata Header Convention

> Source spec: `.omc/specs/deep-interview-sql-testcase-metadata-header.md`
> External authority: `~/cubrid-testtools/doc/sql_guide.md` (§5 categories, §6 testcase rules)
> Mode: ralplan consensus (short RALPLAN-DR), iter 2 — incorporates Architect + Critic feedback

## Requirements Summary

`cubrid-testcases` 저장소의 `.sql` 테스트케이스 파일 시작에 표준 키-값 메타데이터 헤더(`-- @<key>: <value>`) 컨벤션을 도입한다. CTP 러너의 기존 예약 prefix(`--+ ...` 라인-스캔, `--@<word>` 인라인 지시자)와 충돌하지 않으며, 신규 파일에 lint + CI gate 로 강제하고 기존 파일은 점진 마이그레이션한다.

**Mandatory keys**: `@issue`, `@description`, `@expected`
**Optional keys**: `@type`, `@category`, `@id`, `@author`, `@date`, `@answer_variants`
**Grammar separation (NOT a closed reserved-key list)**: 모든 `--@<word>` (공백 없이 `@`) 라인은 CTP 인라인 지시자로 간주, 메타데이터 검증 대상에서 제외 (pass-through). 예: `--@queryplan`, `--@joingraph` 그리고 향후 추가될 모든 인라인 지시자.

**Scope by directory** (실측 .sql 카운트 기준):
- `sql/` — 17,393 .sql 파일, 풀 적용
- `medium/` — 970 .sql 파일, 풀 적용
- `isolation/` — 0 .sql 파일 (다른 포맷의 시나리오 디렉토리), **본 컨벤션 적용 외**

## RALPLAN-DR Summary (Short, iter 2)

### Principles
1. **외부 권위 존중** — `~/cubrid-testtools/doc/sql_guide.md` 가 카테고리/작성 규칙의 single source of truth. 본 플랜은 그 위에 메타데이터 layer 만 얹음.
2. **기존 grammar 침해 금지** — `--+` 러너 지시자, `--@<word>` 인라인 지시자, 기존 첫 줄 설명 주석을 깨면 안 됨. 분리는 **whitespace-and-colon grammar** 로 (`-- @key: value` vs `--@directive`).
3. **점진 도입** — 17,393+970 ≈ 18,363 개 기존 .sql 의 일괄 변경은 위험. 신규/수정 파일에만 lint gate, 기존은 grandfathered.
4. **자동 검증 우선** — reviewer 수작업에 의존하지 않고 lint + CI 로 강제. lint 도구 자체는 단순/이식 가능 (Python stdlib only).
5. **Authoritative SHA pinning** — `sql/AGENTS.md` + lint script 가 sql_guide.md 의 commit SHA 를 명시 pin → upstream drift 감지 가능.

### Decision Drivers (top 3)
1. CTP 러너 호환성 — `--+` (per-line 스캔, SQLParser.java:83,162-165 검증), `--@<word>` (인라인) 와 grammatically 분리
2. 점진적 채택 — 18K+ 파일 일괄 변경 부담 회피
3. 자동화된 강제력 — PR 머지 차단 가능한 CI lint

### Viable Options

**Option A — Python stdlib lint + GitHub Actions (선택)**
- *Approach*: `tool/lint_sql_metadata.py` (단일 파일, stdlib only), `.github/workflows/sql-metadata-lint.yml` 가 PR 의 변경된 .sql 만 검사. SHA-pin via header comment.
- *Pros*: stdlib 만 → 환경 구성 부담 없음, regex/dataclass 로 검증 가독성 우수, file-system cross-check (`@answer_variants`) 단순.
- *Cons*: Python 인터프리터 필요 (CI 표준 환경 기본 포함).

**Option B — Shell (`bash + grep + awk`) lint + GitHub Actions**
- *Approach*: `tool/lint_sql_metadata.sh`.
- *Pros*: 저장소가 이미 `tool/tc_grep.sh` 사용 → 동질적.
- *Cons*: enum 검증/cross-file 검증이 길어지고 CRLF/BOM 처리 수동, Windows runner 호환성 약함.

**Invalidation Rationale**
- *Java + Ant 통합 (CTP 측 lint)*: 본 spec 적용 범위 외 (`~/cubrid-testtools` 무수정). 빌드 사이클 불일치로 PR-time 강제 불가. 후속 follow-up 가능.
- *pre-commit framework*: 추가 의존(.pre-commit-config.yaml + framework 설치). CI gate 보다 강제력 약함. 차후 add-on.

**선택: Option A**.

## ADR (Architecture Decision Record)

### Decision
Python stdlib-only lint script (`tool/lint_sql_metadata.py`) + GitHub Actions workflow (`.github/workflows/sql-metadata-lint.yml`) 로 메타데이터 헤더 강제. 컨벤션 문서: 루트 `AGENTS.md` 신규 + `sql/AGENTS.md` 신규 + `medium/AGENTS.md` 신규. Lint 와 docs 모두 `sql_guide.md` 의 commit SHA 를 pin.

### Drivers
- 신규 PR 즉시 머지 차단 가능한 자동 게이트
- 18K+ 기존 파일 영향 최소화
- CTP 러너 grammar 침해 금지

### Alternatives Considered
- Shell-only lint: enum/cross-file/CRLF 처리 가독성 부족 → 거절
- Java/Ant 통합: 적용 범위 외 + 사이클 불일치 → 거절 (follow-up 가능)
- pre-commit framework: 약한 강제력 + 추가 의존 → 후속 add-on

### Why Chosen
Python stdlib lint 는 (1) 외부 의존 없음, (2) regex+dataclass 가독성, (3) `@answer_variants` cross-check 단순, (4) CI gate 강제력 최고, (5) sql_guide.md SHA pin via header comment 으로 drift 감지 가능.

### Consequences
- Python 3.10+ 가 CI runner + 개발 환경에 필요 (GitHub Actions ubuntu-latest 기본 지원).
- 기존 파일 lint warning 은 changed-only 모드로 grandfathered.
- Lint 가 CTP 외부에 살아 sql_guide.md 와 두 source-of-truth 위험 → SHA pin + quarterly drift check 으로 완화.

### Follow-ups
- 자동 마이그레이션 스크립트(`tool/migrate_sql_metadata.py`) 별도 PR. `~/skills/jira` 연동(선택)으로 CBRD-XXXXX 설명 검증.
- `.answer` / `.queryPlan` 메타데이터 도입은 v2 spec.
- Warning → error 승격 트리거: `sql/_13_issues/` 의 헤더 보유율 ≥ 80% 도달 시 다음 quarterly cleanup PR.
- CTP 측 통합(Option D) 재평가는 Phase 4 완료 + 6개월 후.

## Acceptance Criteria

### Lint Script (`tool/lint_sql_metadata.py`)
- [ ] 단일 Python 파일, stdlib only, Python 3.10+ 호환
- [ ] CLI: `python3 tool/lint_sql_metadata.py [--strict] [--migrated-since <git-ref>] [--github-output] <file_or_dir> [...]`
- [ ] Header comment 에 `# Synthesized from cubrid-testtools@<SHA> sql_guide.md §5,§6` 명시
- [ ] `--version` 출력에 lint script semver + sql_guide.md SHA 포함
- [ ] Exit code: `0` = pass 또는 warning만, `1` = error, `2` = invocation error
- [ ] `--strict` 모드: warning → error 승격
- [ ] **Required key 검증**: `@issue`, `@description`, `@expected` 모두 존재 → 미존재 시 `SQL-META001`
- [ ] **Enum 검증**: `@expected ∈ {normal, error, mixed}`, `@type ∈ {issue, feature, regression, medium}` (있는 경우만) → `SQL-META002` (`isolation` enum 제거 — 0 .sql 파일)
- [ ] **Format 검증**: `@issue` 가 `(CBRD-\d+)(,CBRD-\d+)*` 또는 `none` → `SQL-META003`
- [ ] **Grammar 분리 (whitespace-and-colon)**: 메타데이터 라인은 정확히 `^-- @[a-z][a-z0-9_]*: .+$` (CRLF normalize 후), 모든 `^--@\w+` (공백 없이 `@`) 라인은 CTP 인라인 지시자로 간주 → pass-through, 검증/경고 대상 외 → `SQL-META004` (오직 `-- @key:` 형태에서 공백/콜론 grammar 위반 시)
- [ ] **Header position 검증**: 메타데이터 블록은 파일 첫 줄부터 시작(또는 BOM 직후), 첫 빈 줄에서 종료, `--+` 지시자보다 앞 → `SQL-META005`
- [ ] **Cross-file 검증**: `@answer_variants: WIN,cci` → `../answers/{basename}.answer_WIN`, `.answer_cci` 실존 검증 → `SQL-META006`
- [ ] **BOM rejection**: UTF-8 BOM (`\xef\xbb\xbf`) 파일 시작 → `SQL-META007`
- [ ] **Continuation rejection**: 메타데이터 블록 내 `@key:` 가 아닌 라인(빈 줄 전까지) → `SQL-META008` (값은 단일 라인)
- [ ] **CRLF tolerance**: `\r\n` 라인 엔딩을 `\n` 으로 정규화 후 검증, 값에서 trailing whitespace `.rstrip()` 후 비교
- [ ] **Leading-blank-line tolerance**: `--auto-strip-leading-blank` 플래그 (default: off) — 마이그레이션 시 첫 빈 줄 제거 가능. 켜지지 않으면 `SQL-META005`. (예: `sql/_11_codecoverage/cases/coverage6_01.sql`)
- [ ] **Unknown key 처리**: 정의되지 않은 `@<key>` 는 warning (`SQL-META101`), `--strict` 면 error
- [ ] **Description quality (soft)**: `@description` 길이 < 20자 → warning (`SQL-META102`). 의미 검증은 강제하지 않음 (자연어 의미는 reviewer/AGENTS.md 가이드 영역). `--strict` 면 error.
- [ ] **Helpful error**: `path:line:col: code: message` 형식, GitHub annotation 모드(`--github-output`)에선 `::error file=...,line=...,col=...::message`
- [ ] **Migration mode**: `--migrated-since <ref>` 옵션 — 해당 ref 이후 변경된 .sql 만 검사. base ref 미페치면 actionable error 출력하며 fail loudly.
- [ ] **Tests**: `tool/tests/test_lint_sql_metadata.py` 단위 테스트 (`unittest`) — 모든 SQL-META00X / 101 코드 양/음성 케이스 + fixture 시나리오 (CRLF, BOM, leading-blank, `--@queryplan`, `--@joingraph`, `--@futuredirective` 가상 케이스)
- [ ] **Performance**: 18K-file 풀 스캔 < 30초 on CI runner (대규모 마이그레이션 PR 대비)

### CI Workflow (`.github/workflows/sql-metadata-lint.yml`)
- [ ] Trigger: `pull_request` (paths: `**.sql`, `tool/lint_sql_metadata.py`, `tool/tests/**`, `.github/workflows/sql-metadata-lint.yml`)
- [ ] Steps (순서):
  1. `actions/checkout@v4` with `fetch-depth: 0`
  2. `git fetch origin ${{ github.base_ref }}:refs/remotes/origin/${{ github.base_ref }}` (fork-PR 안전)
  3. `actions/setup-python@v5` with `python-version: '3.11'`
  4. Run `python3 -m unittest tool.tests.test_lint_sql_metadata -v` (lint 자체 단위 테스트)
  5. Diff-based 파일 추출: `git diff --name-only --diff-filter=AM origin/${{ github.base_ref }}...HEAD -- '**.sql'`
  6. 추출된 .sql 파일에 대해 `python3 tool/lint_sql_metadata.py --github-output <files>` 실행
  7. Sanity check: PR 제목/body 에 `.sql` 단어 포함 + 추출 파일 0개 → CI warning (silent pass 방지)
- [ ] Fail PR check on lint error (exit 1)
- [ ] GitHub annotation 으로 line-level error 표시
- [ ] Workflow 50-file PR 기준 < 60s p95 (Actions timing log 측정)
- [ ] CI 자체 자가 검증: 의도적 lint-fail fixture 가 포함된 PR 이 reliably fail 하는지 self-test

### Documentation
- [ ] 루트 `AGENTS.md` 생성 (신규):
  - 저장소 overview + 디렉토리 맵 (sql/, medium/, isolation/, tool/, .github/)
  - 외부: `~/cubrid-testtools` 가 테스트 러너이며 `doc/sql_guide.md` 가 작성 가이드 권위 출처임을 명시
  - sql_guide.md commit SHA pin
  - sub-AGENTS.md cross-link (sql/AGENTS.md, medium/AGENTS.md, tool/README.md)
  - **isolation/ 는 .sql 가 아닌 다른 포맷이므로 본 메타데이터 컨벤션 적용 외임을 명시**
- [ ] `sql/AGENTS.md` 생성 (신규):
  - 메타데이터 헤더 grammar 전체 명세 (`-- @key: value` ↔ `--@directive` 분리 규칙)
  - 카테고리 enum 표 (issue/feature/regression/medium, sql_guide.md §5 출처)
  - Required/Optional 필드 표
  - Grammar 분리 정책 (`--@<word>` 패스스루)
  - **`@description` 작성 가이드라인 섹션** (필수 포함):
    - 의미 분리 명시: `@description` = **what is tested**, `@expected` = **outcome**
    - 권장 동사: `verifies`, `asserts`, `checks`, `expects`, `reproduces`, `exercises`
    - "무엇을 검증하는지" 가 자연어로 드러나야 함 (강제 아님, reviewer 영역)
    - Good / Avoid 예시 각 3개 이상 (아래 §"Description Style Guide" 섹션 참고)
    - Soft lint 경고: 길이 < 20자 → `SQL-META102` warning (강제 아님, `--strict` 시만 error)
  - Reference 예시 4종 (regression / issue / feature / answer_variants)
  - **Query/Block-level Labels 섹션** (인지용, 강제 X):
    - 파일-level `@description` 과 별개로, SQL body 안에서 쿼리/섹션 단위 라벨이 두 형태로 관용 사용됨:
      1. `evaluate '<label>';` — SQL statement (answer 파일에 결과로 찍혀 diff 시 식별 보조). PL/CSQL 영역에 ~136 파일.
      2. `-- N. <label>` numbered comment — 평이한 `--` 주석. issues 영역에 빈번.
    - 둘 다 자유 형태 유지 권장. 메타데이터 헤더 블록 (첫 빈 줄까지) **이후** 에만 등장해야 함.
    - 새 컨벤션 강제 안 함 — 기존 corpus 와의 호환성 우선.
  - Lint 실행 + CI 동작
  - sql_guide.md §5, §6 cross-link with commit SHA pin
  - 루트 AGENTS.md back-link
- [ ] `medium/AGENTS.md` 생성 (신규):
  - sql/AGENTS.md 컨벤션 그대로 적용 (`@type: medium`)
  - MEDIUM 시나리오 특이점(데이터 백업 파일 의존) 간단 노트
  - sql/AGENTS.md cross-link
- [ ] **isolation/AGENTS.md 작성하지 않음** (.sql 파일 0개, 본 컨벤션 비적용)
- [ ] 모든 cross-link 가 동일 PR 내 실제 파일을 가리키는지 검증

### Reference Migration
- [ ] 신규 sample 파일 1개 작성: `sql/_13_issues/_26_1h/cases/cbrd_26999_metadata_sample.sql` + `answers/cbrd_26999_metadata_sample.answer`
- [ ] 기존 파일 마이그레이션 reference: `sql/_13_issues/_24_1h/cases/cbrd_25054.sql`
  - 첫 두 줄 주석 (`-- This test case verifies CBRD-25054 issue.` + `-- When inserting data using rownum, does not show any error...`) → `@description` 으로 단일 라인 collapse (긴 라인 우선 휴리스틱: "Verified for" 가 아닌 가장 긴 라인 채택, 또는 두 라인 연결 후 trim)
  - `@issue: CBRD-25054`, `@type: issue`, `@category: _13_issues/_24_1h`, `@expected: error`
  - 마이그레이션 후 lint 통과 + (가능 시) CTP 인터랙티브 모드에서 답변 일치 확인

### Migration Helper (Optional, follow-up PR)
- [ ] `tool/migrate_sql_metadata.py` 작성:
  - `--dry-run` 기본
  - 디렉토리 패턴 → `@type`/`@category`
  - 파일명 `cbrd_NNNNN[_suffix].sql` → `@issue: CBRD-NNNNN`
  - 첫 N개 연속 `--` 라인(빈 줄 전까지) → `@description` 으로 collapse (휴리스틱: 가장 긴 non-`Verified for` 라인 또는 모든 라인 연결 후 trim)
  - `[er]` prefix → `@expected: error` + description 정제
  - **선택적 jira 통합**: `--jira-verify` 옵션 — `~/skills/jira/scripts/jira_search.py CBRD-NNNNN` 호출하여 description 의 ticket 요약과 cross-check, 불일치 시 `[REVIEW]` 마커 삽입
  - 단위 테스트 포함

## Implementation Steps

### PR1 — Lint script + CI workflow (atomic)
1. **`tool/lint_sql_metadata.py` 작성** (file: `/home/dev/cubrid-testcases/tool/lint_sql_metadata.py`)
   - Module: `Header` dataclass, `parse_header(path) -> Header`, `validate(header, repo_root) -> List[Diagnostic]`, `main(argv) -> int`
   - Regex (CRLF-normalized input):
     - `META_LINE = re.compile(r"^-- @([a-z][a-z0-9_]*): (.+)$")`
     - `INLINE_DIRECTIVE = re.compile(r"^--@\w+")` (no whitespace before `@`, pass-through)
     - `RUNNER_DIRECTIVE = re.compile(r"^--\+ ?")`
     - `BOM = b"\xef\xbb\xbf"`
   - Diagnostic codes 010~006 (errors), 007~008 (errors, BOM/continuation), 101 (warn unknown key)
   - Header comment: `# Synthesized from cubrid-testtools@<SHA> sql_guide.md §5,§6` (SHA 는 cubrid-testtools `git rev-parse HEAD` 시점 값)
2. **`tool/tests/test_lint_sql_metadata.py` 작성** (file: `/home/dev/cubrid-testcases/tool/tests/test_lint_sql_metadata.py`)
   - `unittest.TestCase` 기반, 각 SQL-META 코드별 양/음성 케이스
   - Fixtures: `tool/tests/fixtures/`:
     - `valid_minimal.sql`, `valid_full.sql`, `valid_answer_variants.sql`
     - `invalid_missing_required.sql`, `invalid_enum.sql`, `invalid_format.sql`
     - `invalid_position_metadata_after_runner.sql`, `bom_at_start.sql`, `crlf_endings.sql`, `leading_blank_line.sql`
     - `inline_directive_collision.sql` (`--@queryplan`, `--@joingraph`, `--@futuredirective` 모두 보존)
     - `unknown_key_warns.sql`
     - `query_level_labels.sql` (헤더 블록 종료 후 `evaluate 'N. ...';` 와 `-- N. ...` numbered comment 가 SQL body 안에 자유롭게 등장 — lint false-positive 없이 통과해야 함, 136 파일 corpus 패턴 참조)
3. **`tool/README.md` 신규 또는 업데이트** (file: `/home/dev/cubrid-testcases/tool/README.md`)
   - Lint 사용법, exit code, diagnostic codes 표, jira skill 연동 안내
4. **`.github/workflows/sql-metadata-lint.yml` 작성** (file: `/home/dev/cubrid-testcases/.github/workflows/sql-metadata-lint.yml`)
   - 위 AC 의 7-step 구성
5. **CI self-test**: 의도적 lint-fail 케이스를 PR 에 포함 → 워크플로 fail 확인 → 수정 후 pass 확인 (PR 머지 전 evidence)

### PR2 — Documentation
6. **루트 `AGENTS.md` 생성** (file: `/home/dev/cubrid-testcases/AGENTS.md`)
7. **`sql/AGENTS.md` 생성** (file: `/home/dev/cubrid-testcases/sql/AGENTS.md`)
8. **`medium/AGENTS.md` 생성** (file: `/home/dev/cubrid-testcases/medium/AGENTS.md`)
9. **Cross-link 검증**: `grep -E "AGENTS\.md|README\.md" AGENTS.md sql/AGENTS.md medium/AGENTS.md tool/README.md` 의 모든 path 가 실재하는지 자동 체크

### PR3 — Reference migration
10. **Sample 신규 파일** (files: `sql/_13_issues/_26_1h/cases/cbrd_26999_metadata_sample.sql`, `answers/cbrd_26999_metadata_sample.answer`)
    - `_26_1h` 디렉토리 부재 시 `mkdir -p` 후 생성. 또는 lint 통과만이 목적이면 기존 디렉토리 재사용
    - Answer 파일은 sql_guide.md §5 step 3-5 절차로 CTP 인터랙티브 모드에서 생성. CTP 환경 부재 시 minimal stub
11. **기존 파일 마이그레이션 reference** (file: `sql/_13_issues/_24_1h/cases/cbrd_25054.sql`)
    - 다중 첫줄 주석 collapse 휴리스틱 적용
    - lint 양/음성 검증
    - (선택) `~/skills/jira` 로 CBRD-25054 ticket 본문과 description 일치 확인

### PR4 — (Optional) Migration helper
12. **`tool/migrate_sql_metadata.py`** (file: `/home/dev/cubrid-testcases/tool/migrate_sql_metadata.py`)
    - 휴리스틱 + `--dry-run`/`--apply` + `--jira-verify`
    - 단위 테스트 포함
    - **자체 적용 가능 디렉토리부터 점진**: `sql/_13_issues/_26_1h/` (가장 신규) 부터 시범 적용 PR

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `--@<word>` 인라인 지시자(예: `--@queryplan`, `--@joingraph`)가 lint 에서 false-positive | Medium | High | 정규식 `INLINE_DIRECTIVE` 가 `^--@\w+` 만 매칭 (공백 없음)·전체 라인 패스스루. fixture `inline_directive_collision.sql` 가 corpus 내 모든 알려진 인라인 지시자 + 가상 미래 지시자 케이스. AC 명시. |
| 메타데이터 헤더가 SQL 실행/answer 비교에 영향 | Very Low | High | 검증된 사실: SQLParser.java:74-89 (line iteration), :83 (`getControlCommand` per-line), :162-165 (`--+` line.startsWith 체크) — `--+` 는 line-1 강제 아님, `--` 라인은 모두 skip. 추가로 sample 마이그레이션 파일을 CTP 인터랙티브에서 실제 실행하여 verification 단계로 확정. |
| 기존 파일 lint warning 의 PR noise | High | Medium | `--migrated-since` + diff-based CI lint 으로 changed-only. untouched 파일 grandfathered. |
| CRLF 라인 엔딩 / leading blank / BOM 으로 lint false-positive | Medium | Medium | 명시 AC: CRLF normalize, `--auto-strip-leading-blank` 플래그, BOM 탐지/명시 reject. fixture 로 양/음성 cover. |
| Diff-based CI lint 이 fork/rebase/merge 에서 잘못된 파일 셋 산출 | Medium | Medium | 명시 step: `git fetch origin <base_ref>` + sanity check ("PR 본문에 .sql 언급되는데 추출 파일 0개" → CI warning). 대안: `gh pr diff --name-only` fallback. |
| CBRD 자동 추출 오류 (마이그레이션) | Medium | Low | `--dry-run` 기본, `--apply` 명시. `--jira-verify` 로 cross-check. 추출 실패 시 `@issue: none` fallback. |
| `sql_guide.md` 변경 시 lint drift | Medium | Medium | sql_guide.md SHA pin in lint header + `sql/AGENTS.md`. quarterly drift check (CI cron 또는 manual). |
| isolation/ 또는 다른 비-.sql 시나리오에 lint 가 잘못 적용 | Low | Medium | lint 가 `*.sql` glob 만, isolation/ 은 0 .sql 파일이라 영향 없음. AGENTS.md 가 적용 범위 명시. |
| 쿼리-level 라벨 (`evaluate '...';`, `-- N. ...`) 이 lint false-positive | Low | Medium | `evaluate` 는 `--` 로 시작 안 하므로 메타데이터 lint 와 grammar 충돌 0. numbered comment 는 헤더 블록(첫 빈 줄까지) **이후** 위치하면 검증 대상 외. fixture `query_level_labels.sql` 가 corpus 패턴 (136 파일) 회귀 방지. |
| Reserved-key 목록이 CTP 인라인 지시자의 open set 을 표현 못함 | Was Medium | Was Medium | **해소**: 명시적 reserved-key 리스트 폐기, whitespace-and-colon grammar 가 유일한 분리 규칙. AC, 문서, 테스트 모두 반영. |
| Multi-line `@description` 미정의로 구현자 자의적 해석 | Was Medium | Was Low | **해소**: AC 가 `SQL-META008` 으로 continuation 명시 reject. 다중 라인 설명은 메타데이터 블록 종료 후 일반 `--` 주석 사용. |

## Verification Steps

1. **Lint script 단위 테스트**:
   ```bash
   cd /home/dev/cubrid-testcases
   python3 -m unittest tool.tests.test_lint_sql_metadata -v
   ```
   Expected: all PASS.

2. **Lint script 양성 케이스**:
   ```bash
   python3 tool/lint_sql_metadata.py sql/_13_issues/_26_1h/cases/cbrd_26999_metadata_sample.sql
   echo "exit=$?"
   ```
   Expected: stdout empty, `exit=0`.

3. **Lint script 음성 케이스 (헤더 부재)**:
   ```bash
   echo "select 1;" > /tmp/no_header.sql
   python3 tool/lint_sql_metadata.py /tmp/no_header.sql
   echo "exit=$?"
   ```
   Expected: stdout/stderr 에 `SQL-META001`, `exit=1`.

4a. **Query/block-level label false-positive 회피**:
   ```bash
   cat > /tmp/query_labels.sql <<'EOF'
   -- @issue: none
   -- @description: verifies query labels coexist with metadata header
   -- @expected: normal

   --1. first scenario - basic select
   select 1;

   --2. second scenario - arithmetic
   evaluate '2. select list contains arithmetic operation (should work) -> mergeable list';
   select 1+2;

   evaluate 'Error (stack overflow): recursive call';
   select 3;
   EOF
   python3 tool/lint_sql_metadata.py /tmp/query_labels.sql; echo "exit=$?"
   ```
   Expected: `exit=0`. `evaluate '...'` 와 `--N.` numbered comment 모두 메타데이터 검증 대상이 아님.

4. **Inline directive false-positive 회피**:
   ```bash
   cat > /tmp/inline_test.sql <<'EOF'
   -- @issue: none
   -- @description: queryplan + joingraph inline directives must be passed through
   -- @expected: normal

   select 1;
   --@queryplan
   select 2;
   --@joingraph
   select 3;
   --@futuredirective
   select 4;
   EOF
   python3 tool/lint_sql_metadata.py /tmp/inline_test.sql; echo "exit=$?"
   ```
   Expected: `exit=0`, none of `--@queryplan`/`--@joingraph`/`--@futuredirective` triggers SQL-META00X.

5. **CRLF / BOM / leading-blank 케이스**:
   ```bash
   printf '\xef\xbb\xbf-- @issue: none\r\n-- @description: bom test\r\n-- @expected: normal\r\n\r\nselect 1;\r\n' > /tmp/bom_crlf.sql
   python3 tool/lint_sql_metadata.py /tmp/bom_crlf.sql; echo "exit=$?"
   ```
   Expected: `SQL-META007` (BOM), `exit=1`.
   ```bash
   printf '\n-- @issue: none\n-- @description: leading blank\n-- @expected: normal\n\nselect 1;\n' > /tmp/leadblank.sql
   python3 tool/lint_sql_metadata.py /tmp/leadblank.sql; echo "exit=$?"
   python3 tool/lint_sql_metadata.py --auto-strip-leading-blank /tmp/leadblank.sql; echo "exit=$?"
   ```
   Expected: 첫 호출 `SQL-META005` `exit=1`, 두 번째 호출 `exit=0`.

6. **`@answer_variants` cross-check**:
   - `@answer_variants: WIN` 명시 + `.answer_WIN` 부재 → `SQL-META006` `exit=1`
   - `.answer_WIN` 함께 존재 → `exit=0`

7. **CI workflow self-test**:
   - 의도적 lint-fail 케이스 포함 PR 생성 → workflow fail 확인 (Actions UI annotation 캡처)
   - 수정 후 push → workflow pass 확인
   - 변경 없는 .sql 은 lint 대상에서 제외 확인 (`Sanity check` warning 없음)

8. **Reference migration 양성 검증**:
   ```bash
   python3 tool/lint_sql_metadata.py sql/_13_issues/_24_1h/cases/cbrd_25054.sql
   echo "exit=$?"
   ```
   Expected: `exit=0`.

9. **CTP 러너 호환성 verification (필수, 환경 가용 시)**:
   - **권위 evidence**: `~/cubrid-testtools/CTP/sql/src/com/navercorp/cubridqa/cqt/common/SQLParser.java:74-89` (comment-line skip), `:83` (per-line `getControlCommand`), `:162-165` (`line.startsWith("--+")` — line-1 강제 아님)
   - **실측 검증** (CTP 가능 환경에서):
     ```bash
     # 환경 따라 ~/CTP/bin/ctp.sh 또는 ~/cubrid-testtools/CTP/bin/ctp.sh
     ~/cubrid-testtools/CTP/bin/ctp.sh sql -c ~/cubrid-testtools/CTP/conf/sql.conf --interactive
     sql> run sql/_13_issues/_24_1h/cases/cbrd_25054.sql
     ```
     Expected: 메타데이터 헤더가 SQL 실행/answer 비교에 영향 없음, 기존 answer 와 일치
   - sql_guide.md §2.1 의 표준 install 경로(`~/CTP/bin/ctp.sh`)는 별도 deploy 단계 후 활성화. 본 환경에선 `~/cubrid-testtools/CTP/bin/ctp.sh` 사용.

10. **Cross-link integrity**:
    ```bash
    cd /home/dev/cubrid-testcases
    grep -hoE '\b[A-Za-z0-9_/-]+\.(md|py|yml)\b' AGENTS.md sql/AGENTS.md medium/AGENTS.md tool/README.md \
      | sort -u | while read p; do test -e "$p" || echo "MISSING: $p"; done
    ```
    Expected: 출력 없음 (모든 cross-link 실재).

11. **18K-file 풀 스캔 성능**:
    ```bash
    time python3 tool/lint_sql_metadata.py sql medium
    ```
    Expected: < 30s wall clock.

12. **Pre-autopilot user confirmation**: 본 플랜이 Critic approval 받은 후 사용자에게 `AskUserQuestion` 으로 autopilot 진입 명시 컨펌. 사용자 거절 시 plan 만 보존.

## Files Touched

| Path | Action | PR |
|------|--------|-----|
| `tool/lint_sql_metadata.py` | create | PR1 |
| `tool/tests/test_lint_sql_metadata.py` | create | PR1 |
| `tool/tests/fixtures/*.sql` | create (10+ fixtures) | PR1 |
| `tool/README.md` | create or update | PR1 |
| `.github/workflows/sql-metadata-lint.yml` | create | PR1 |
| `AGENTS.md` (root) | create | PR2 |
| `sql/AGENTS.md` | create | PR2 |
| `medium/AGENTS.md` | create | PR2 |
| `sql/_13_issues/_26_1h/cases/cbrd_26999_metadata_sample.sql` | create | PR3 |
| `sql/_13_issues/_26_1h/answers/cbrd_26999_metadata_sample.answer` | create | PR3 |
| `sql/_13_issues/_24_1h/cases/cbrd_25054.sql` | modify (add header) | PR3 |
| `tool/migrate_sql_metadata.py` | create (optional) | PR4 |

**NOT touched** (out of scope or absent):
- `isolation/` — 0 .sql 파일, 비-.sql 포맷 시나리오. 적용 안 함.
- `~/cubrid-testtools/**` — 외부 권위 저장소, 무수정.

## Description Style Guide (sql/AGENTS.md 에 그대로 이식)

`@description` 은 자유 텍스트 한 줄이지만, **무엇을 검증하는지** 가 자연어로 드러나야 한다. 강제(lint)는 길이 < 20자 warning 까지만, 의미는 reviewer 영역.

### 의미 분리
- `@description` = **what is tested** (대상/시나리오)
- `@expected` = **outcome** (`normal`/`error`/`mixed`, enum)

두 필드를 합치면 한 문장이 자연스럽게 완성된다:
> *@description* 을 했을 때 *@expected* 결과가 나와야 한다.

### 권장 동사 (선두 권장, 강제 아님)
`verifies` · `asserts` · `checks` · `expects` · `reproduces` · `exercises`

### Good (검증 대상이 명확)
| 예시 | 왜 좋은가 |
|---|---|
| `verifies CBRD-25054 — rownum INSERT into numeric column overflows must error` | 티켓 + 검증 시나리오 + 기대결과 단서 모두 포함 |
| `asserts varchar(0) and nchar varying(0) report syntax error at create time` | 입력 조건 + 기대 동작 명확 |
| `checks query plan stability for /*+ recompile */ hint after CBRD-25098 fix` | 검증 대상(query plan) + 트리거(hint) + 컨텍스트(티켓) |
| `reproduces CBRD-22696 — varchar select returns different bytes on Windows vs CCI` | 환경 차이 검증 의도 명확 |
| `exercises PL/CSQL block-scope rule: default expr must not reference later-declared variable` | 규칙 + 위반 조건 |

### Avoid (동작만 있고 검증 의도 모호)
| 예시 | 왜 약한가 |
|---|---|
| ~~`create table with varchar data type`~~ | "무엇을 검증?" 이 비어있음 |
| ~~`select test`~~ | 길이 < 20자 → SQL-META102 warning |
| ~~`test for varchar`~~ | 모호하고 일반적 |
| ~~`bug fix`~~ | 검증 시나리오 0 |

### Migration 시 휴리스틱
기존 첫 줄 주석을 흡수할 때 다음 순서로 정제 권장 (`tool/migrate_sql_metadata.py`):
1. `[er]` prefix 제거 → `@expected: error` 로 분리
2. "Verified for CBRD-NNNNN" 라인은 `@issue` 로 흡수 후 description 에서 제거
3. 여러 줄 주석은 가장 의미 충실한 라인 선택 또는 concat-and-trim
4. 길이 < 20자 또는 권장 동사 부재 시 `[REVIEW]` 마커 삽입 (수동 검토 유도)
5. (선택) `--jira-verify` 로 `~/skills/jira` 호출하여 CBRD 본문과 description 일치 확인

### Query-level 라벨 (자유 형태, 표준화 안 함)
`@description` 은 파일 전체 의도, 그 아래 SQL body 안의 쿼리/섹션 라벨은 별 layer 다.
- `evaluate '<label>';` — CUBRID SQL statement, answer 파일에 결과로 찍혀 diff 시 식별. PL/CSQL 영역 ~136 파일.
- `-- N. <label>` — 평이한 numbered comment. issues 영역에 빈번.

두 형태 모두 메타데이터 헤더 블록 종료(첫 빈 줄) **이후** SQL body 안에서 자유롭게 사용. lint 가 검증/경고 안 함. 신규 파일에서 어느 쪽을 사용할지는 작성자 재량 (PL/CSQL 은 `evaluate` 관용, 일반 SQL 은 numbered comment 관용).

## Open Questions (carried into autopilot Phase 2)

- `medium/_NN_<scenario>/_NNN_<sub>/cases/` 의 정확한 카테고리 enum (`@type: medium` 단일 유지 vs. 세분화)
- GitHub Actions check 의 branch protection 강제 여부 (settings 레벨, plan 외)
- Phase 4 자동 마이그레이션 PR 분할 단위 (디렉토리당 1 PR vs. 시즌당 1 PR)
- Description style guide 의 권장 동사 enum 이 향후 lint hard rule 로 승격 가능한지 (현재는 reviewer 영역)

## Changelog
- v1 (initial draft) — Planner produced from deep-interview spec.
- v2 — incorporates Architect (`isolation/`, `medium/`, `--@joingraph`, CRLF/BOM, diff-CI fragility, SHA pin, phase merge) + Critic (whitespace-grammar over reserved-list, SQLParser.java evidence, CTP path correction, BOM/continuation AC additions, multi-line description heuristic, jira skill integration) feedback. Phase 1+2 merged into PR1. isolation/AGENTS.md dropped (0 .sql files). medium/AGENTS.md added (970 .sql files). User-required pre-autopilot confirmation gate added.
- v3 — `@description` 가이드라인 보강 (Option B). Soft lint warning `SQL-META102` (길이 < 20자) 추가, sql/AGENTS.md 에 Description Style Guide 섹션 (의미 분리 / 권장 동사 / Good·Avoid 예시 / 마이그레이션 휴리스틱) 명시. 강제는 길이만, 의미 평가는 reviewer 영역.
- v4 (this) — Query/block-level 라벨 인지 추가. Corpus 의 두 관용 표현 (`evaluate '<label>';` 136 파일 / `-- N. <label>` issues 영역) 이 파일-level `@description` 과 다른 layer 임을 명시. lint false-positive 회피 fixture (`query_level_labels.sql`) + verification step 4a + risk row 추가. sql/AGENTS.md 에 인지 섹션 (강제 X, 자유 형태 유지). 표준화하지 않음 — corpus 호환성 우선.
