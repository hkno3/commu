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
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEYS = [
    k for k in [
        os.environ.get("GEMINI_API_KEY_1", ""),
        os.environ.get("GEMINI_API_KEY_2", ""),
    ] if k
]
NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

CATEGORIES = [
    "정치", "경제", "사회", "생활/문화", "세계", "IT/과학",
    "부동산", "헬스/건강", "스포츠", "연예", "자동차", "날씨",
    "가상화폐", "주식", "육아", "여행", "게임", "패션/뷰티",
    "음식/맛집", "교육", "환경", "법률", "취업/직장", "반려동물", "영화",
]

DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published.json")
MAX_PUBLISHED = 500

# 카테고리 → ASCII 파일명 (FTP 한글 파일명 문제 해결)
CAT_FILENAME = {
    "정치": "politics", "경제": "economy", "사회": "society",
    "생활/문화": "lifestyle", "세계": "world", "IT/과학": "tech",
    "부동산": "realestate", "헬스/건강": "health", "스포츠": "sports",
    "연예": "entertainment", "자동차": "auto", "날씨": "weather",
    "가상화폐": "crypto", "주식": "stock", "육아": "parenting",
    "여행": "travel", "게임": "game", "패션/뷰티": "fashion",
    "음식/맛집": "food", "교육": "education", "환경": "environment",
    "법률": "law", "취업/직장": "jobs", "반려동물": "pets", "영화": "movies",
}

def cat_to_filename(category: str) -> str:
    return CAT_FILENAME.get(category, category.replace("/", "_"))

_CAT_LIST = "정치, 경제, 사회, 생활/문화, 세계, IT/과학, 부동산, 헬스/건강, 스포츠, 연예, 자동차, 날씨, 가상화폐, 주식, 육아, 여행, 게임, 패션/뷰티, 음식/맛집, 교육, 환경, 법률, 취업/직장, 반려동물, 영화"

REWRITE_PROMPT = (
    "다음 뉴스 기사를 커뮤니티 에디터의 시각으로 재작성해주세요.\n\n"
    "반드시 아래 형식 그대로 출력하세요 (마크다운 ** 기호 절대 사용 금지):\n\n"
    "제목: (30자 이내. 아래 제목 규칙 적용)\n"
    "슬러그: (영어 URL 슬러그. 소문자+하이픈, 3~6단어. 예: korea-ai-startup-investment)\n"
    "요약: (2문장 구어체 요약. 카드 미리보기용)\n"
    "내용: (아래 본문 규칙 적용)\n"
    f"카테고리: (본문 전체를 쓴 뒤 내용에 맞는 카테고리 1개 선택. 목록: [{_CAT_LIST}])\n\n"
    "=== 제목 규칙 ===\n"
    "- 핵심 키워드를 앞 15자 이내에 배치\n"
    "- 숫자를 반드시 1개 이상 포함 (개수/연도/금액/기간)\n"
    "- 후킹 패턴 중 하나 선택 (매번 다르게):\n"
    "  예) '~하면 안 되는 이유 N가지' / '아무도 몰랐던 ~' / '~ 전에 꼭 확인할 것'\n"
    "  예) '~ 했더니 생긴 일' / '공식 발표로 본 ~ 총정리' / '~ N가지 핵심 정리'\n"
    "- 특수문자/광고성 단어(최고, 무료, 강추) 금지\n\n"
    "=== 본문 규칙 ===\n"
    "글마다 구조와 톤이 달라야 함. 아래에서 선택:\n\n"
    "[첫 문장 톤 - 매번 랜덤 선택]\n"
    "A. 직설형: '결론부터 말하면 ~'\n"
    "B. 공감형: '막상 ~하려면 막막한 게 사실이다'\n"
    "C. 의문형: '정말 ~일까?'\n"
    "D. 결론선제형: '이 뉴스의 핵심은 단 하나다'\n\n"
    "[본문 구조 - 매번 다르게]\n"
    "- h2 개수: 2~4개 사이에서 변형\n"
    "- 아래 요소 중 2~3개 랜덤 포함:\n"
    "  1) 팁 박스: <p style=\"background:#fff8e1; border-left:4px solid #f39c12; padding:12px 16px; margin:16px 0;\">💡 <strong>팁:</strong> 내용</p>\n"
    "  2) 주의 박스: <p style=\"background:#fff3f3; border-left:4px solid #e74c3c; padding:12px 16px; margin:16px 0;\">⚠️ <strong>주의:</strong> 내용</p>\n"
    "  3) 안내 박스: <p style=\"background:#f0fff0; border-left:4px solid #27ae60; padding:12px 16px; margin:16px 0;\">✅ <strong>안내:</strong> 내용</p>\n"
    "  4) FAQ (details 태그):\n"
    "     <h3>자주 묻는 질문</h3>\n"
    "     <details style=\"background:#e3f2fd; border:1px solid #90caf9; border-radius:6px; padding:12px 16px; margin:8px 0;\"><summary style=\"font-weight:bold; cursor:pointer;\">질문</summary><p style=\"margin-top:10px;\">답변</p></details>\n"
    "  5) 에디터 의견: '솔직히 말하면...' / '개인적으로는...' 식으로 1~2문장\n"
    "  6) 독자 질문: 마지막에 독자 의견 묻는 질문 1개\n\n"
    "사용 가능 태그: h2, h3, p, strong, details, summary (인라인 스타일 허용)\n"
    "금지: 마크다운 **, ## 등 / 딱딱한 문체(~했습니다) → 구어체(~했대요, ~인 것 같아요)\n"
    "본문 전체 800~1200자\n"
    "'제목:', '카테고리:', '슬러그:', '요약:', '내용:' 앞에 ** 붙이지 말 것"
)

# 중복 판단: 핵심 명사가 이 비율 이상 겹치면 중복
SIMILARITY_THRESHOLD = 0.5

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
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&apos;", "'").replace("&#39;", "'")
    return text.strip()


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
    filename = cat_to_filename(category)
    path = os.path.join(DATA_DIR, f"{filename}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_category_articles(category: str, articles: list) -> None:
    filename = cat_to_filename(category)
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


def rewrite_with_claude(text: str, original_title: str) -> dict:
    """제목·요약·HTML본문을 재작성. {'title': ..., 'summary': ..., 'content': ...} 반환"""
    if not ANTHROPIC_API_KEY:
        return {"title": original_title, "summary": text, "content": f"<p>{text}</p>"}
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": f"{REWRITE_PROMPT}\n\n{text}"}],
    }
    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()["content"][0]["text"].strip()
        print(f"[Claude 응답]\n{result[:300]}")

        # ** 마크다운 제거
        result = result.replace("**", "").replace("*", "")

        new_title = None
        new_category = None
        new_slug = None
        summary_text = None
        content_lines = []
        section = None  # 'summary' | 'content'

        for line in result.split("\n"):
            stripped = line.strip()
            if re.match(r"^제\s*목\s*[:：]", stripped):
                new_title = re.sub(r"^제\s*목\s*[:：]\s*", "", stripped).strip()
                section = None
            elif re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
                new_category = re.sub(r"^카\s*테\s*고\s*리\s*[:：]\s*", "", stripped).strip()
                section = None  # 카테고리는 항상 최우선 파싱 (내용: 이후에 나와도)
            elif re.match(r"^슬\s*러\s*그\s*[:：]", stripped):
                raw_slug = re.sub(r"^슬\s*러\s*그\s*[:：]\s*", "", stripped).strip()
                # 소문자, 영문/숫자/하이픈만 허용
                new_slug = re.sub(r"[^a-z0-9-]", "", raw_slug.lower().replace(" ", "-"))
                section = None
            elif re.match(r"^요\s*약\s*[:：]", stripped):
                summary_text = re.sub(r"^요\s*약\s*[:：]\s*", "", stripped).strip()
                section = 'summary'
            elif re.match(r"^내\s*용\s*[:：]", stripped):
                section = 'content'
            else:
                if section == 'summary' and stripped and not summary_text:
                    summary_text = stripped
                elif section == 'content':
                    if not re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
                        content_lines.append(line)

        if not new_title:
            print("[Claude] 제목 파싱 실패, 원본 사용")
            new_title = original_title

        # HTML 본문 조합 (허용 태그만 유지)
        # strong, details, summary, style 속성 포함 허용
        allowed = re.compile(r'<(?!/?(h2|h3|p|br|strong|details|summary)(\s|>))[^>]+>', re.IGNORECASE)
        raw_content = "\n".join(content_lines).strip()
        content_html = allowed.sub("", raw_content) if raw_content else f"<p>{summary_text or text}</p>"

        # 요약이 없으면 본문에서 첫 p 태그 내용 추출
        if not summary_text:
            m = re.search(r"<p>(.*?)</p>", content_html, re.DOTALL)
            summary_text = m.group(1).strip() if m else text

        if new_category:
            print(f"[Claude] 카테고리: {new_category}")

        return {"title": new_title, "slug": new_slug, "summary": summary_text, "content": content_html, "category": new_category}
    except Exception as exc:
        print(f"[Claude] 오류: {exc}")
        return {"title": original_title, "slug": None, "summary": text, "content": f"<p>{text}</p>"}


SITE_URL = "https://newscommu.com"

def update_sitemap(all_articles: list) -> None:
    """all_articles 기반으로 sitemap.xml 생성"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # 메인 페이지
    lines.append(f"""  <url>
    <loc>{SITE_URL}/</loc>
    <changefreq>hourly</changefreq>
    <priority>1.0</priority>
    <lastmod>{now}</lastmod>
  </url>""")

    # 기사 상세 페이지
    seen = set()
    for a in all_articles:
        aid = a.get("article_id", "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        pub = (a.get("pub_date") or a.get("pubDate") or "")[:10] or now
        lines.append(f"""  <url>
    <loc>{SITE_URL}/article.php?id={aid}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <lastmod>{pub}</lastmod>
  </url>""")

    lines.append("</urlset>")
    sitemap_path = os.path.join(os.path.dirname(DATA_DIR) if DATA_DIR != "data" else ".", "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[sitemap] {len(seen)}개 기사 URL 업데이트")


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

    # latest.json에 있는 article_id도 published에 추가 (published.json 삭제돼도 중복 방지)
    latest_path = os.path.join(DATA_DIR, "latest.json")
    if os.path.exists(latest_path):
        try:
            latest = json.load(open(latest_path, encoding="utf-8"))
            for a in latest:
                published["ids"].add(a.get("article_id", ""))
                # 원본 제목도 중복 이력에 추가
                orig_title = a.get("original_title") or a.get("title", "")
                if orig_title:
                    published["titles"].append({
                        "date": (a.get("pubDate") or a.get("pub_date") or "")[:10],
                        "keywords": list(extract_keywords(orig_title)),
                    })
        except Exception:
            pass
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
        rewritten = rewrite_with_claude(f"{title}\n{description}", title)

        # Claude가 분류한 카테고리가 유효하면 사용, 아니면 검색 카테고리 유지
        claude_cat = rewritten.get("category", "")
        if claude_cat and claude_cat in CATEGORIES:
            final_category = claude_cat
        else:
            final_category = category

        image_url = None

        # 발행 시각 = 현재 시각 (한국 시간 KST = UTC+9)
        from datetime import timedelta
        KST = timezone(timedelta(hours=9))
        now_kst = datetime.now(KST)
        publish_time = now_kst.isoformat()

        new_article = {
            "article_id": article_id,
            "title": rewritten["title"],
            "slug": rewritten.get("slug") or article_id,
            "original_title": title,
            "summary": rewritten["summary"],
            "content": rewritten.get("content", ""),
            "image_url": image_url,
            "original_url": original_url,
            "url": original_url,
            "source": source,
            "pubDate": publish_time,
            "pub_date": publish_time,
            "category": final_category.replace("/", "_"),
            "category_label": final_category,
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

    # 5. 카테고리 파일 업데이트 (Claude 분류 카테고리 기준, 최신순, 최대 50개)
    existing = load_category_articles(final_category)
    existing.insert(0, new_article)
    save_category_articles(final_category, existing[:50])

    # 6. latest.json 업데이트
    all_articles = []
    for cat in CATEGORIES:
        all_articles.extend(load_category_articles(cat))
    all_articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(all_articles[:50], f, ensure_ascii=False, indent=2)

    # 7. 발행 이력 저장
    save_published(published)

    # 8. sitemap.xml 갱신
    update_sitemap(all_articles)

    print(f"\n[완료] '{category}' → {new_article['title'][:50]}")


if __name__ == "__main__":
    main()
