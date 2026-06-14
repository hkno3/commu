# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 프로젝트 정보 (newscommu.com)

- PHP 뉴스 커뮤니티 사이트, FastComet 공유호스팅 FTP 배포
- GitHub Actions 자동화 (cron-job.org → workflow_dispatch)
- 데이터: `data/*.json` + MySQL DB (2중 백업)
- 개발 브랜치: `claude/wonderful-goldberg-GEsSG` → PR → main

### 카테고리
- 정치, 경제, 사회, 생활/문화, IT/과학 (뉴스)
- 천천히 늙자 (PubMed 논문, `data/animal.json`)
- 주간 연구 기획서 (`data/weekly_research.json`, 매주 월요일)

### 파이프라인
- `fetch_news.py`: 네이버 뉴스 → Gemini KEY_1 → JSON + DB
- `fetch_animal.py`: PubMed → Gemini KEY_2 → JSON + DB (매 6시간 30분)
- `fetch_weekly.py`: 7일 animal 포스트 → Gemini KEY_3 → 주간 기획서 (매주 월요일)
- `api/save_article.php`: FTP 배포 후 DB 저장용 API

### cron 시간 (cron-job.org, Asia/Seoul)
- 뉴스: `0 * * * *` (매시 정각)
- 동물: `30 */6 * * *` (6시간마다 30분) ← 뉴스와 동시 실행 방지
- 주간: 매주 월요일

### 주의사항
- FTP sync 모드는 로컬에 없는 파일을 서버에서 삭제함
- rss.xml, sitemap.xml은 FTP exclude 목록에 있음
- animal/weekly workflow는 실행 전 서버의 모든 data/*.json 다운로드
- FastComet은 외부 MySQL 접속 차단 → PHP API로만 DB 저장
- `save_article.php` 인증: `X-Save-Secret` + `Content-Type: application/json` 둘 다 필수
- `config.php`를 항상 secret check 전에 require_once
- 어드민 경로는 robots.txt에 노출 금지
