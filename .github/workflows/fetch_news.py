#!/usr/bin/env python3
"""
15분마다 실행: 현재 시간 기반으로 카테고리 순서 계산 → 1개 기사 발행
중복 기사는 published.json으로 추적하여 건너뜀
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

CATEGORIES = [
    "정치", "경제", "사회", "생활/문화", "세계", "IT/과학",
    "부동산", "헬스/건강", "스포츠", "연예", "자동차", "날씨",
    "가상화폐", "주식", "육아", "여행", "게임", "패션/뷰티",
    "음식/맛집", "교육", "환경", "법률", "취업/직장", "반려동물", "영화",
]

DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published.json")
MAX_PUBLISHED = 500  # 최근 500개만 유지

REWRITE_PROMPT = (
    "다음 뉴스 기사를 200자 내외로 핵심만 간결하게 요약해주세요. "
    "원문과 다른 표현을 사용하되 사실은 정확하게 유지하세요:"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()

def get_current_category() -> str:
    """현재 시간 기반으로 어떤 카테고리 차례인지 계산 (15분 단위)"""
    now = datetime.now(timezone.utc)
    # 00:00부터 몇 번째 15분 구간인지
    minutes_since_midnight = now.hour * 60 + now.minute
    slot = (minutes_since_midnight // 15) % len(CATEGORIES)
    category = CATEGORIES[slot]
    print(f"[*] 현재 시각 {now.strftime('%H:%M')} UTC → 카테고리 [{slot}] {category}")
    return category

def load_published() -> set:
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_published(published: set) -> None:
    # 최근 MAX_PUBLISHED개만 유지 (오래된 것 자동 삭제)
    ids = list(published)[-MAX_PUBLISHED:]
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False)

def load_category_articles(category: str) -> list:
    filename = category.replace("/", "_")
    path = os.path.join(DATA_DIR, f"{filename}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_category_articles(category: str, articles: list) -> None:
    filename = category.replace("/", "_")
    path = os.path.join(DATA_DIR, f"{filename}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Naver News fetch
# ---------------------------------------------------------------------------

def fetch_naver_news(query: str, display: int = 20) -> list:
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": 1, "sort": "date"}
    try:
        resp = requests.get(NAVER_API_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as exc:
        print(f"[Naver] 오류: {exc}")
        return []

# ---------------------------------------------------------------------------
# Groq rewrite
# ---------------------------------------------------------------------------

def rewrite_with_groq(text: str) -> str:
    if not GROQ_API_KEY:
        return text
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": f"{REWRITE_PROMPT}\n\n{text}"}],
        "max_tokens": 400,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"[Groq] 오류: {exc}")
        return text

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[ERROR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정")
        return

    # 1. 현재 카테고리 결정
    category = get_current_category()

    # 2. 발행된 기사 ID 로드
    published = load_published()
    print(f"[*] 발행된 기사 수: {len(published)}개")

    # 3. 네이버에서 기사 가져오기 (20개 — 중복 제거 후 1개 남겨야 하므로 여유있게)
    raw_items = fetch_naver_news(category, display=20)
    if not raw_items:
        print("[!] 기사를 가져오지 못했습니다.")
        return

    # 4. 중복 제거 후 새 기사 1개 선택
    new_article = None
    for item in raw_items:
        original_url = item.get("originallink") or item.get("link", "")
        article_id = make_article_id(original_url)
        if article_id in published:
            print(f"    건너뜀 (중복): {strip_html(item.get('title',''))[:40]}")
            continue

        # 새 기사 발견!
        title = strip_html(item.get("title", ""))
        description = strip_html(item.get("description", ""))
        source = item.get("link", "").split("/")[2] if item.get("link") else ""
        pub_date = item.get("pubDate", "")
        try:
            dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            pub_date = dt.isoformat()
        except Exception:
            pass

        print(f"[+] 새 기사 선택: {title[:50]}")
        summary = rewrite_with_groq(f"{title}\n{description}")

        new_article = {
            "article_id": article_id,
            "title": title,
            "summary": summary,
            "original_url": original_url,
            "url": original_url,
            "source": source,
            "pubDate": pub_date,
            "pub_date": pub_date,
            "category": category.replace("/", "_"),
            "category_label": category,
        }
        break

    if not new_article:
        print("[!] 새 기사 없음 (모두 중복)")
        return

    # 5. 카테고리 파일에 앞에 추가 (최신순 유지, 최대 50개)
    existing = load_category_articles(category)
    existing.insert(0, new_article)
    existing = existing[:50]
    save_category_articles(category, existing)

    # 6. latest.json 업데이트 (전체 카테고리 합산 최신 50개)
    all_articles = []
    for cat in CATEGORIES:
        all_articles.extend(load_category_articles(cat))
    all_articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(all_articles[:50], f, ensure_ascii=False, indent=2)

    # 7. 발행 목록에 추가
    published.add(new_article["article_id"])
    save_published(published)

    print(f"\n[완료] '{category}' 카테고리에 기사 1개 발행됨: {new_article['title'][:50]}")


if __name__ == "__main__":
    main()
