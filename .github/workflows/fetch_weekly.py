#!/usr/bin/env python3
"""
천천히 늙자 - 주간 AI 연구 기획서
지난 7일간 발행된 논문 포스트를 종합 분석해 실현 가능한 연구 아이디어를 제안한다.
매주 월요일 1회 실행
"""

import os
import json
import hashlib
import requests
import markdown
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_3", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
SAVE_SECRET = os.environ.get("SAVE_SECRET", "nc_save_s3cr3t_2026")
SAVE_API_URL = "https://newscommu.com/api/save_article.php"

DATA_DIR = "data"
ANIMAL_FILE  = os.path.join(DATA_DIR, "animal.json")
WEEKLY_FILE  = os.path.join(DATA_DIR, "weekly_research.json")
LATEST_FILE  = os.path.join(DATA_DIR, "latest.json")

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    if os.path.exists(path):
        try:
            return json.loads(open(path, encoding="utf-8").read()) or []
        except Exception:
            pass
    return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def search_unsplash_image(keyword: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        return ""
    for kw in [keyword, "animal research laboratory"]:
        try:
            r = requests.get(
                UNSPLASH_SEARCH_URL,
                params={"query": kw, "per_page": 5, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=10,
            )
            results = r.json().get("results", [])
            for item in results:
                url = item.get("urls", {}).get("regular", "")
                if url and "plus.unsplash.com" not in url:
                    return url
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# Collect last 7 days of animal posts
# ---------------------------------------------------------------------------

def collect_recent_posts() -> list:
    articles = load_json(ANIMAL_FILE)
    cutoff = datetime.now(KST) - timedelta(days=7)
    recent = []
    for a in articles:
        pub = a.get("pub_date") or a.get("pubDate", "")
        try:
            dt = datetime.fromisoformat(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            if dt >= cutoff:
                recent.append(a)
        except Exception:
            pass
    return recent


# ---------------------------------------------------------------------------
# Gemini: generate weekly research proposal
# ---------------------------------------------------------------------------

WEEKLY_PROMPT = """당신은 동물 노화 및 수명 연구 전문가입니다.

[현재 시점]
오늘 날짜: {today}  |  연도: {year}년

[지난 7일간 발행된 논문 포스트 목록]
{summaries}

---
위 {count}편의 논문 포스트를 **깊이 종합 분석**하여, 현재 과학계에서 실제로 실현 가능한 연구 기획서를 한 편 작성하세요.

요구사항:
- 단순 요약 나열 금지 — 논문들 사이의 **연결고리, 공백, 모순**을 찾아내세요
- {year}년 현재 기술 수준에서 실제로 진행할 수 있는 연구 주제여야 합니다
- 동물(특히 반려동물)의 수명·건강수명 연장에 실용적으로 기여할 수 있어야 합니다
- 독자(비전문가 애견·애묘인)가 "우와, 이런 연구가 정말 가능해?" 하고 흥분할 수 있는 내용

출력 형식 (마크다운):
## 🔬 이번 주 연구 기획서: [제목]

### 왜 지금 이 연구인가?
(이번 주 논문들에서 발견한 패턴과 공백 설명, 200자 이상)

### 연구 가설
(구체적이고 검증 가능한 가설 1~2개)

### 실험 설계
(실제로 어떻게 진행할지 단계별 설명)

### 예상 결과와 의의
(성공 시 반려동물·인간에게 어떤 변화가 올지)

### 🐾 집에서 지금 할 수 있는 것
(이 연구 방향과 연결된 실천 팁 2~3가지)

주의: 생각 과정(thinking)은 출력하지 마세요. 완성된 글만 출력하세요."""


def generate_weekly_proposal(posts: list) -> dict | None:
    now = datetime.now(KST)
    today = now.strftime("%Y년 %m월 %d일")
    year = now.year

    summaries_parts = []
    for i, p in enumerate(posts, 1):
        title = p.get("title", "")
        body = p.get("content", p.get("body", ""))[:500]
        summaries_parts.append(f"[{i}] {title}\n{body}")
    summaries = "\n\n".join(summaries_parts)

    prompt = WEEKLY_PROMPT.format(
        today=today,
        year=year,
        count=len(posts),
        summaries=summaries,
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 4096,
            "thinkingConfig": {"thinkingBudget": 8000},
        },
    }

    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        content = "".join(
            p["text"] for p in parts if not p.get("thought", False)
        ).strip()

        if not content:
            print("Gemini 응답 비어 있음")
            return None

        # Extract title from first H2
        title = "이번 주의 연구 기획서"
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("## "):
                title = line.lstrip("#").strip()
                if title.startswith("🔬"):
                    title = title[1:].strip()
                title = title.replace("이번 주 연구 기획서: ", "").strip()
                break

        content_html = markdown.markdown(content, extensions=['nl2br'])
        return {"title": title, "content": content_html}

    except Exception as e:
        print(f"Gemini 오류: {e}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY_3 없음")
        return

    now = datetime.now(KST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')} KST] 주간 연구 기획서 생성 시작")

    posts = collect_recent_posts()
    print(f"최근 7일 포스트: {len(posts)}편")

    if len(posts) < 3:
        print("포스트가 3편 미만 — 이번 주는 건너뜀")
        return

    result = generate_weekly_proposal(posts)
    if not result:
        return

    title   = result["title"]
    content = result["content"]
    print(f"기획서 제목: {title}")

    # Image
    image_url = search_unsplash_image("animal longevity research")

    # Article ID
    article_id = "weekly_" + hashlib.md5(
        (title + now.strftime("%Y-%W")).encode()
    ).hexdigest()[:12]

    pub_date = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    article = {
        "article_id":   article_id,
        "title":        f"🔬 {title}",
        "content":      content,
        "image_url":    image_url,
        "category":     "천천히_늙자",
        "article_type": "weekly_research",
        "pub_date":     pub_date,
        "pubDate":      pub_date,
        "original_url": "",
        "source":       "AI 연구 기획",
        "based_on_posts": len(posts),
    }

    # Save to weekly_research.json
    weekly = load_json(WEEKLY_FILE)
    weekly = [a for a in weekly if a.get("article_id") != article_id]
    weekly.insert(0, article)
    weekly = weekly[:52]  # keep 1 year
    save_json(WEEKLY_FILE, weekly)
    print(f"저장: {WEEKLY_FILE}")

    # Update latest.json
    latest = load_json(LATEST_FILE)
    latest = [a for a in latest if a.get("article_id") != article_id]
    latest.insert(0, article)
    latest = latest[:500]
    save_json(LATEST_FILE, latest)

    # Also append to animal.json so it shows in 천천히 늙자 feed
    animal = load_json(os.path.join(DATA_DIR, "animal.json"))
    animal = [a for a in animal if a.get("article_id") != article_id]
    animal.insert(0, article)
    animal = animal[:200]
    save_json(os.path.join(DATA_DIR, "animal.json"), animal)

    # DB 저장
    try:
        r = requests.post(
            SAVE_API_URL,
            json=article,
            headers={"X-Save-Secret": SAVE_SECRET, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            print(f"  [DB] 저장 완료: {article_id[:20]}")
        else:
            print(f"  [DB] 저장 실패: {r.status_code}")
    except Exception as e:
        print(f"  [DB] 저장 실패 (무시): {e}")

    print("완료!")


if __name__ == "__main__":
    main()
