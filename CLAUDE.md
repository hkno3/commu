# newscommu.com 프로젝트 지침

## 핵심 규칙: 코딩 전 반드시 계획 먼저

**코드 수정 전에 항상:**
1. 무엇을 왜 바꿀지 설명
2. 어떤 파일을 어떻게 바꿀지 계획 제시
3. 사용자 확인 받은 후 코딩 시작

단순 오타 수정이라도 먼저 말하고 확인받기.

---

## 프로젝트 구조

- PHP 뉴스 커뮤니티 사이트 (newscommu.com)
- FastComet 공유호스팅 FTP 배포
- GitHub Actions로 자동화 (cron-job.org → workflow_dispatch)
- 데이터: `data/*.json` (JSON 파일) + MySQL DB (2중 백업)

## 브랜치

- 개발: `claude/wonderful-goldberg-GEsSG`
- 항상 이 브랜치에서 작업 후 PR → main 머지

## 카테고리

- 정치, 경제, 사회, 생활/문화, IT/과학 (뉴스)
- 천천히 늙자 (PubMed 논문 기반, `data/animal.json`)
- 주간 연구 기획서 (`data/weekly_research.json`, 매주 월요일)

## 주요 파이프라인

- `fetch_news.py`: 네이버 뉴스 → Gemini KEY_1 → JSON + DB
- `fetch_animal.py`: PubMed → Gemini KEY_2 → JSON + DB (매 6시간 30분에 실행)
- `fetch_weekly.py`: 7일 animal 포스트 → Gemini KEY_3 → 주간 기획서 (매주 월요일)
- `api/save_article.php`: Python이 FTP 배포 후 DB 저장용 API

## cron 시간 (cron-job.org, Asia/Seoul)

- 뉴스: `0 * * * *` (매시 정각)
- 동물: `30 */6 * * *` (6시간마다 30분) ← 뉴스와 동시 실행 방지
- 주간: 매주 월요일 설정

## 주의사항

- FTP sync 모드는 로컬에 없는 파일을 서버에서 삭제함
- rss.xml, sitemap.xml은 FTP exclude 목록에 있음 (삭제 방지)
- animal/weekly workflow는 실행 전 서버의 모든 data/*.json 다운로드 (뉴스 파일 삭제 방지)
- FastComet은 외부 MySQL 접속 차단 → PHP API로만 DB 저장
- `save_article.php` 인증: `X-Save-Secret` 헤더 + `Content-Type: application/json` 둘 다 필수
- `config.php`를 항상 secret check 전에 require_once

## 어드민

- 경로 비공개 유지 (robots.txt에 노출 금지)
- 비밀번호 보호
