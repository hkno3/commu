#!/usr/bin/env python3
"""
Fetch Korean news from Naver API and rewrite summaries using Groq API.
Saves results to data/{category}.json files.
"""

import os
import json
import time
import hashlib
import requests
from datetime import datetime

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
    "정치",
    "경제",
    "사회",
    "생활/문화",
    "세계",
    "IT/과학",
    "부동산",
    "헬스/건강",
    "스포츠",
    "연예",
]

ARTICLES_PER_CATEGORY = 10
DATA_DIR = "data"

REWRITE_PROMPT = (
    "다음 뉴스 기사를 200자 내외로 핵심만 간결하게 요약해주세요. "
    "원문과 다른 표현을 사용하되 사실은 정확하게 유지하세요:"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_article_id(url: str) -> str:
    """Create a stable short ID from a URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def strip_html(text: str) -> str:
    """Remove basic HTML tags from Naver API responses."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


# ---------------------------------------------------------------------------
# Naver News fetch
# ---------------------------------------------------------------------------


def fetch_naver_news(query: str, display: int = 10) -> list:
    """Fetch news articles from Naver News API for a given query."""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": 1,
        "sort": "date",
    }
    try:
        resp = requests.get(NAVER_API_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", [])
    except Exception as exc:
        print(f"[Naver] Error fetching '{query}': {exc}")
        return []


# ---------------------------------------------------------------------------
# Groq rewrite
# ---------------------------------------------------------------------------


def rewrite_with_groq(text: str) -> str:
    """Rewrite/summarise a news snippet using Groq API."""
    if not GROQ_API_KEY:
        return text

    prompt = f"{REWRITE_PROMPT}\n\n{text}"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"[Groq] Rewrite error: {exc}")
        return text  # fall back to original text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def process_category(category: str) -> list:
    """Fetch, rewrite, and return articles for a single category."""
    print(f"[*] Processing category: {category}")
    raw_items = fetch_naver_news(category, display=ARTICLES_PER_CATEGORY)

    articles = []
    for item in raw_items:
        title = strip_html(item.get("title", ""))
        description = strip_html(item.get("description", ""))
        original_url = item.get("originallink") or item.get("link", "")
        source = item.get("link", "").split("/")[2] if item.get("link") else ""
        pub_date = item.get("pubDate", "")

        # Parse pubDate to ISO format if possible
        try:
            dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            pub_date = dt.isoformat()
        except Exception:
            pass

        full_text = f"{title}\n{description}"
        summary = rewrite_with_groq(full_text)

        article = {
            "article_id": make_article_id(original_url),
            "title": title,
            "summary": summary,
            "original_url": original_url,
            "source": source,
            "pubDate": pub_date,
            "category": category,
        }
        articles.append(article)
        print(f"    + {title[:40]}...")

        # Respect Groq rate limits
        time.sleep(0.5)

    return articles


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[ERROR] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET not set.")
        return

    all_articles = []

    for category in CATEGORIES:
        articles = process_category(category)

        # Safe filename: replace / with _
        filename = category.replace("/", "_")
        filepath = os.path.join(DATA_DIR, f"{filename}.json")

        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(articles, fh, ensure_ascii=False, indent=2)

        print(f"    Saved {len(articles)} articles to {filepath}")
        all_articles.extend(articles)

        # Be polite to Naver API
        time.sleep(1)

    # Also write a combined latest.json (all categories, sorted by pubDate)
    all_articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as fh:
        json.dump(all_articles[:50], fh, ensure_ascii=False, indent=2)

    print(f"\n[Done] Wrote {len(all_articles)} total articles. latest.json = top 50.")


if __name__ == "__main__":
    main()
