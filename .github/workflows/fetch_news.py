#!/usr/bin/env python3
"""
15분마다 실행: 현재 시간 기반으로 카테고리 순서 계산 → 1개 기사 발행
중복 기사는 published.json으로 추적 (URL 해시 + 핵심 명사 유사도)
"""

import os
import json
import re
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
MAX_PUBLISHED = 500

REWRITE_PROMPT = (
    "다음 뉴스 기사를 아래 형식으로 작성해주세요.\n"
    "제목: (원문과 다른 표현으로 핵심을 담은 제목, 30자 이내)\n"
    "내용: (300자 내외로 핵심만 간결하게 요약, 사실은 정확하게 유지)\n\n"
    "반드시 '제목:'과 '내용:' 형식을 지켜주세요."
)

# 중복 판단: 핵심 명사가 이 비율 이상 겹치면 중복
SIMILARITY_THRESHOLD = 0.7

# ---------------------------------------------------------------------------
# 중복 판단: 핵심 명사 추출 + 유사도 계산
# ---------------------------------------------------------------------------

# 제거할 불용어 (조사, 접속사, 일반 동사 등)
STOPWORDS = {
    "이", "가", "은", "는", "을", "를", "의", "에", "서", "로", "으로",
    "와", "과", "도", "만", "에서", "에게", "부터", "까지", "하고", "이고",
    "그리고", "하지만", "그러나", "또한", "따라서", "그래서", "때문에",
    "위해", "통해", "대해", "관해", "따른", "위한", "대한", "관한",
    "있다", "없다", "했다", "한다", "된다", "됐다", "이다", "아니다",
    "했습니다", "합니다", "입니다", "습니다", "니다",
    "오늘", "내일", "어제", "현재", "최근", "지난", "이번", "올해",
    "기자", "뉴스", "단독", "속보", "종합", "update", "포토",
}


def extract_keywords(title: str) -> set:
    """제목에서 핵심 명사 키워드 추출"""
    # HTML 특수문자 제거
    title = re.sub(r"&[a-z]+;", "", title)
    # 특수문자 제거 (한글, 영문, 숫자만 유지)
    words = re.findall(r"[가-힣a-zA-Z0-9]+", title)
    # 2글자 미만 제거 + 불용어 제거
    keywords = {w for w in words if len(w) >= 2 and w not in STOPWORDS}
    return keywords


def is_duplicate(title: str, pub_date: str, published_titles: list) -> bool:
    """
    핵심 명사 기반 유사도로 중복 판단
    같은 날짜 기사 중 키워드 70% 이상 겹치면 중복
    """
    keywords_new = extract_keywords(title)
    if not keywords_new:
        return False

    # 날짜 추출 (YYYY-MM-DD)
    date_new = pub_date[:10] if pub_date else ""

    for prev in published_titles:
        # 날짜가 다르면 중복 아님 (후속 기사 허용)
        if date_new and prev.get("date", "") and date_new != prev["date"]:
            continue

        keywords_prev = set(prev.get("keywords", []))
        if not keywords_prev:
            continue

        # Jaccard 유사도: 교집합 / 합집합
        intersection = keywords_new & keywords_prev
        union = keywords_new | keywords_prev
        similarity = len(intersection) / len(union) if union else 0

        if similarity >= SIMILARITY_THRESHOLD:
            print(f"    중복 감지 (유사도 {similarity:.0%}): {title[:40]}")
            return True

    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def get_current_category() -> str:
    now = datetime.now(timezone.utc)
    minutes_since_midnight = now.hour * 60 + now.minute
    slot = (minutes_since_midnight // 15) % len(CATEGORIES)
    category = CATEGORIES[slot]
    print(f"[*] 현재 시각 {now.strftime('%H:%M')} UTC → [{slot}] {category}")
    return category


def load_published() -> dict:
    """{'ids': set(), 'titles': [{'date':..., 'keywords':[...]}]}"""
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "ids": set(data.get("ids", [])),
                    "titles": data.get("titles", []),
                }
        except Exception:
            pass
    return {"ids": set(), "titles": []}


def save_published(published: dict) -> None:
    ids = list(published["ids"])[-MAX_PUBLISHED:]
    titles = published["titles"][-MAX_PUBLISHED:]
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": ids, "titles": titles}, f, ensure_ascii=False)


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
# Naver & Groq
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


def rewrite_with_groq(text: str, original_title: str) -> dict:
    """제목과 내용을 함께 재작성. {'title': ..., 'summary': ...} 반환"""
    if not GROQ_API_KEY:
        return {"title": original_title, "summary": text}
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
        result = resp.json()["choices"][0]["message"]["content"].strip()

        # 제목: / 내용: 파싱
        new_title = original_title
        summary = result
        for line in result.split("\n"):
            if line.startswith("제목:"):
                new_title = line.replace("제목:", "").strip()
            elif line.startswith("내용:"):
                summary = line.replace("내용:", "").strip()

        return {"title": new_title, "summary": summary}
    except Exception as exc:
        print(f"[Groq] 오류: {exc}")
        return {"title": original_title, "summary": text}


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

    # 2. 발행 이력 로드
    published = load_published()
    print(f"[*] 발행 이력: {len(published['ids'])}개")

    # 3. 네이버 기사 가져오기
    raw_items = fetch_naver_news(category, display=20)
    if not raw_items:
        print("[!] 기사를 가져오지 못했습니다.")
        return

    # 4. 중복 제거 후 새 기사 1개 선택
    new_article = None
    for item in raw_items:
        original_url = item.get("originallink") or item.get("link", "")
        article_id = make_article_id(original_url)
        title = strip_html(item.get("title", ""))
        pub_date = item.get("pubDate", "")

        try:
            dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            pub_date = dt.isoformat()
        except Exception:
            pass

        # URL 해시 중복 체크
        if article_id in published["ids"]:
            print(f"    건너뜀 (URL 중복): {title[:40]}")
            continue

        # 제목 유사도 중복 체크
        if is_duplicate(title, pub_date, published["titles"]):
            published["ids"].add(article_id)  # 중복이어도 ID 등록해서 재등장 방지
            continue

        # 새 기사 발견!
        description = strip_html(item.get("description", ""))
        source = item.get("link", "").split("/")[2] if item.get("link") else ""

        print(f"[+] 새 기사: {title[:50]}")
        rewritten = rewrite_with_groq(f"{title}\n{description}", title)

        new_article = {
            "article_id": article_id,
            "title": rewritten["title"],
            "original_title": title,
            "summary": rewritten["summary"],
            "original_url": original_url,
            "url": original_url,
            "source": source,
            "pubDate": pub_date,
            "pub_date": pub_date,
            "category": category.replace("/", "_"),
            "category_label": category,
        }

        # 발행 이력에 추가
        published["ids"].add(article_id)
        published["titles"].append({
            "date": pub_date[:10],
            "keywords": list(extract_keywords(title)),
        })
        break

    if not new_article:
        print("[!] 새 기사 없음 (모두 중복)")
        save_published(published)
        return

    # 5. 카테고리 파일 업데이트 (최신순, 최대 50개)
    existing = load_category_articles(category)
    existing.insert(0, new_article)
    save_category_articles(category, existing[:50])

    # 6. latest.json 업데이트
    all_articles = []
    for cat in CATEGORIES:
        all_articles.extend(load_category_articles(cat))
    all_articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(all_articles[:50], f, ensure_ascii=False, indent=2)

    # 7. 발행 이력 저장
    save_published(published)

    print(f"\n[완료] '{category}' → {new_article['title'][:50]}")


if __name__ == "__main__":
    main()
