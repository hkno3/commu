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
GEMINI_API_KEYS = [
    k for k in [
        os.environ.get("GEMINI_API_KEY_1", ""),
        os.environ.get("GEMINI_API_KEY_2", ""),
        os.environ.get("GEMINI_API_KEY_3", ""),
    ] if k
]
NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"

CATEGORIES = [
    "정치", "경제", "사회", "생활/문화", "IT/과학",
    "부동산", "헬스/건강", "스포츠", "연예", "자동차",
    "가상화폐", "주식",
]

DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published.json")
MAX_PUBLISHED = 500

# 카테고리 → ASCII 파일명 (FTP 한글 파일명 문제 해결)
CAT_FILENAME = {
    "정치": "politics", "경제": "economy", "사회": "society",
    "생활/문화": "lifestyle", "IT/과학": "tech",
    "부동산": "realestate", "헬스/건강": "health", "스포츠": "sports",
    "연예": "entertainment", "자동차": "auto",
    "가상화폐": "crypto", "주식": "stock",
}

def cat_to_filename(category: str) -> str:
    return CAT_FILENAME.get(category, category.replace("/", "_"))

# 이미지 검색 실패 시 폴백용 영문 키워드 (카테고리별 보편적인 검색어)
CAT_IMAGE_FALLBACK = {
    "정치": "politics", "경제": "economy", "사회": "city street",
    "생활/문화": "lifestyle", "IT/과학": "technology",
    "부동산": "real estate", "헬스/건강": "health", "스포츠": "sports",
    "연예": "entertainment", "자동차": "car",
    "가상화폐": "cryptocurrency", "주식": "stock market",
}

_CAT_LIST = "정치, 경제, 사회, 생활/문화, IT/과학, 부동산, 헬스/건강, 스포츠, 연예, 자동차, 가상화폐, 주식"

REWRITE_PROMPT = (
    "다음 뉴스 기사를 커뮤니티 에디터의 시각으로 재작성해주세요.\n"
    "원문이 짧거나 내용이 부족하면 주제와 관련된 배경지식, 역사적 맥락, 관련 사례를 추가해서 풍부하게 작성하세요.\n\n"
    "반드시 아래 형식 그대로 출력하세요 (마크다운 ** 기호 절대 사용 금지):\n\n"
    "제목: (30자 이내. 아래 제목 규칙 적용)\n"
    "슬러그: (영어 URL 슬러그. 소문자+하이픈, 3~6단어. 예: korea-ai-startup-investment)\n"
    "요약: (2문장 구어체 요약. 카드 미리보기용)\n"
    "내용: (아래 본문 규칙 적용)\n"
    f"카테고리: (본문 전체를 쓴 뒤 내용에 맞는 카테고리 1개 선택. 목록: [{_CAT_LIST}])\n"
    "이미지키워드: (기사 대표 이미지를 검색할 영어 키워드 1~2단어. 예: bitcoin crash, election debate, ai robot)\n\n"
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
    "- h2 개수: 3~4개. 각 h2 섹션마다 최소 3문장 이상 작성\n"
    "- h2는 본문의 주요 섹션 제목. '자주 묻는 질문', '마치며' 등 독립 섹션도 반드시 h2 사용\n"
    "- h3는 h2 섹션 내부의 소제목에만 사용 (h2 없이 단독 h3 금지)\n"
    "- 원문 내용 외에 관련 배경, 원인, 영향, 전망 등을 추가로 서술해서 깊이 있게 작성\n"
    "- 아래 요소 중 2~3개 랜덤 포함:\n"
    "  1) 팁 박스: <p style=\"background:#fff8e1; border-left:4px solid #f39c12; padding:12px 16px; margin:16px 0;\">💡 <strong>팁:</strong> 내용</p>\n"
    "  2) 주의 박스: <p style=\"background:#fff3f3; border-left:4px solid #e74c3c; padding:12px 16px; margin:16px 0;\">⚠️ <strong>주의:</strong> 내용</p>\n"
    "  3) 안내 박스: <p style=\"background:#f0fff0; border-left:4px solid #27ae60; padding:12px 16px; margin:16px 0;\">✅ <strong>안내:</strong> 내용</p>\n"
    "  4) FAQ (details 태그) - 반드시 정확히 3개:\n"
    "     <h2>자주 묻는 질문</h2>\n"
    "     <details style=\"background:#e3f2fd; border:1px solid #90caf9; border-radius:6px; padding:12px 16px; margin:8px 0;\"><summary style=\"font-weight:bold; cursor:pointer;\">질문1</summary><p style=\"margin-top:10px;\">답변1</p></details>\n"
    "     <details style=\"background:#e3f2fd; border:1px solid #90caf9; border-radius:6px; padding:12px 16px; margin:8px 0;\"><summary style=\"font-weight:bold; cursor:pointer;\">질문2</summary><p style=\"margin-top:10px;\">답변2</p></details>\n"
    "     <details style=\"background:#e3f2fd; border:1px solid #90caf9; border-radius:6px; padding:12px 16px; margin:8px 0;\"><summary style=\"font-weight:bold; cursor:pointer;\">질문3</summary><p style=\"margin-top:10px;\">답변3</p></details>\n"
    "  5) 에디터 의견: '솔직히 말하면...' / '개인적으로는...' 식으로 1~2문장\n"
    "  6) 독자 질문: 마지막에 독자 의견 묻는 질문 1개\n\n"
    "- 비교/정리가 필요한 내용은 표로 작성 (예: 항목 비교, 연도별 변화, 장단점):\n"
    "  <table style=\"width:100%; border-collapse:collapse; margin:16px 0;\">\n"
    "  <thead><tr style=\"background:#f0f4ff;\"><th style=\"border:1px solid #ddd; padding:8px 12px;\">항목</th><th style=\"border:1px solid #ddd; padding:8px 12px;\">내용</th></tr></thead>\n"
    "  <tbody><tr><td style=\"border:1px solid #ddd; padding:8px 12px;\">값</td><td style=\"border:1px solid #ddd; padding:8px 12px;\">값</td></tr></tbody>\n"
    "  </table>\n"
    "  ※ 표 작성 규칙(필수): 모든 <tr>은 <thead>의 <th> 개수와 동일한 개수의 <td>를 가져야 하며,\n"
    "  빈 칸 없이 모든 셀을 채울 것. 행/열 개수를 중간에 빼먹거나 줄이지 말 것. <table>은 반드시 </table>로 닫을 것.\n\n"
    "[1인칭 에디터 말투 강화]\n"
    "- 단순 정보 나열 금지. 반드시 에디터 본인이 직접 겪거나 느낀 것처럼 작성\n"
    "- 예) '솔직히 처음 이 뉴스 봤을 때 좀 놀랐어요' / '주변에서도 이런 경우 많이 봤는데'\n"
    "- 예) '제가 직접 확인해봤더니~' / '이게 왜 중요하냐면~' / '실제로 해보면 느끼는 게'\n"
    "- 독자가 '아 이 에디터가 진짜 관심 있구나' 느낄 수 있게\n"
    "- 실용적인 팁, 독자가 바로 써먹을 수 있는 정보 반드시 포함\n\n"
    "사용 가능 태그: h2, h3, p, strong, details, summary, table, thead, tbody, tr, th, td (인라인 스타일 허용)\n"
    "※ 본문의 모든 단락(문장 덩어리)은 반드시 <p>...</p> 태그로 감쌀 것. 태그 없이 줄바꿈만 된 문장은 가독성을 해침.\n"
    "금지: 마크다운 **, ## 등 / 딱딱한 문체(~했습니다) → 구어체(~했대요, ~인 것 같아요)\n"
    "본문 전체 1200~1800자 (반드시 1200자 이상 작성)\n"
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


_gemini_key_index = 0  # 현재 사용 중인 Gemini 키 인덱스

def rewrite_with_gemini(text: str, original_title: str) -> dict | None:
    """Gemini로 재작성. 할당량 초과(429) 시 다음 키로 전환, 일시적 오류(503 등)는 같은 키로 재시도. 모두 소진 시 None 반환."""
    global _gemini_key_index
    if not GEMINI_API_KEYS:
        return None

    import time
    while _gemini_key_index < len(GEMINI_API_KEYS):
        api_key = GEMINI_API_KEYS[_gemini_key_index]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"{REWRITE_PROMPT}\n\n{text}"}]}],
            "generationConfig": {"maxOutputTokens": 40000, "temperature": 0.9},
        }
        retry_done = False
        for attempt in range(2):
            try:
                resp = requests.post(url, json=payload, timeout=120)
                if resp.status_code == 429:
                    print(f"[Gemini KEY_{_gemini_key_index+1}] 할당량 초과, 다음 키로 전환")
                    _gemini_key_index += 1
                    retry_done = True
                    break
                if resp.status_code in (401, 403):
                    print(f"[Gemini KEY_{_gemini_key_index+1}] 키 인증 오류({resp.status_code}), 다음 키로 전환")
                    _gemini_key_index += 1
                    retry_done = True
                    break
                if resp.status_code in (500, 502, 503, 504):
                    if attempt == 0:
                        print(f"[Gemini KEY_{_gemini_key_index+1}] 일시적 서버 오류({resp.status_code}), 같은 키로 재시도")
                        time.sleep(5)
                        continue
                    print(f"[Gemini KEY_{_gemini_key_index+1}] 일시적 서버 오류({resp.status_code}) 재시도 실패, 이번 기사 건너뜀")
                    return None
                resp.raise_for_status()
                data = resp.json()
                candidate = data["candidates"][0]
                finish_reason = candidate.get("finishReason", "?")
                usage = data.get("usageMetadata", {})
                result = candidate["content"]["parts"][0]["text"].strip()
                print(f"[Gemini KEY_{_gemini_key_index+1} 응답] finishReason={finish_reason} "
                      f"thoughtsTokens={usage.get('thoughtsTokenCount', '?')} "
                      f"outputTokens={usage.get('candidatesTokenCount', '?')}")
                if finish_reason == "MAX_TOKENS":
                    print(f"[경고] 토큰 한도 도달로 응답이 잘렸을 수 있음")
                print(f"[Gemini KEY_{_gemini_key_index+1} 응답 본문]\n{result[:300]}")
                return _parse_rewrite_result(result, original_title)
            except Exception as exc:
                if attempt == 0:
                    print(f"[Gemini KEY_{_gemini_key_index+1}] 오류: {exc} (재시도)")
                    time.sleep(5)
                    continue
                print(f"[Gemini KEY_{_gemini_key_index+1}] 오류: {exc}")
                return None
        if retry_done:
            continue

            _gemini_key_index += 1

    print("[Gemini] 모든 키 소진")
    return None


def _parse_rewrite_result(result: str, original_title: str) -> dict:
    """Claude/Gemini 공통 응답 파싱"""
    result = result.replace("**", "").replace("*", "")
    result = re.sub(r'^###\s*(.+)$', r'<h3>\1</h3>', result, flags=re.MULTILINE)
    result = re.sub(r'^##\s*(.+)$', r'<h2>\1</h2>', result, flags=re.MULTILINE)

    new_title = None
    new_category = None
    new_slug = None
    new_image_keyword = None
    summary_text = None
    content_lines = []
    section = None

    for line in result.split("\n"):
        stripped = line.strip()
        # 본문 섹션에 진입한 후에는 어떤 필드 마커가 나와도 본문 수집을 멈추지 않음
        # (카테고리 등 마커성 텍스트가 본문 중간에 우연히 등장해도 잘림 방지)
        if section == 'content':
            if re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
                new_category = re.sub(r"^카\s*테\s*고\s*리\s*[:：]\s*", "", stripped).strip()
            elif re.match(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]", stripped):
                new_image_keyword = re.sub(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]\s*", "", stripped).strip()
            else:
                content_lines.append(line)
            continue

        if re.match(r"^제\s*목\s*[:：]", stripped):
            new_title = re.sub(r"^제\s*목\s*[:：]\s*", "", stripped).strip()
            section = None
        elif re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
            new_category = re.sub(r"^카\s*테\s*고\s*리\s*[:：]\s*", "", stripped).strip()
        elif re.match(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]", stripped):
            new_image_keyword = re.sub(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]\s*", "", stripped).strip()
        elif re.match(r"^슬\s*러\s*그\s*[:：]", stripped):
            raw_slug = re.sub(r"^슬\s*러\s*그\s*[:：]\s*", "", stripped).strip()
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

    if not new_title:
        new_title = original_title

    allowed = re.compile(r'<(?!/?(h2|h3|p|br|strong|details|summary|table|thead|tbody|tr|th|td)(\s|>))[^>]+>', re.IGNORECASE)

    # 줄바꿈만 되고 <p> 등 블록 태그로 감싸지지 않은 일반 텍스트 줄은
    # 브라우저가 한 덩어리로 이어붙여 가독성이 떨어짐 -> 자동으로 <p>로 감싸 보강
    block_tag_re = re.compile(r"^<(h2|h3|p|details|summary|table|thead|tbody|tr|th|td)\b", re.IGNORECASE)
    wrapped_lines = []
    for line in content_lines:
        stripped = line.strip()
        if stripped and not block_tag_re.match(stripped):
            wrapped_lines.append(f"<p>{stripped}</p>")
        else:
            wrapped_lines.append(line)

    raw_content = "\n".join(wrapped_lines).strip()
    content_html = allowed.sub("", raw_content) if raw_content else f"<p>{summary_text or ''}</p>"

    if not summary_text:
        m = re.search(r"<p>(.*?)</p>", content_html, re.DOTALL)
        summary_text = m.group(1).strip() if m else ""

    if new_category:
        print(f"[파싱] 카테고리: {new_category}")

    return {"title": new_title, "slug": new_slug, "summary": summary_text, "content": content_html, "category": new_category, "image_keyword": new_image_keyword}


def search_unsplash_image(keyword: str, title: str) -> str | None:
    """Unsplash에서 키워드로 이미지 후보를 검색하고, 기사 제목과 가장 관련성 높은 것을 선택.
    이미지를 다운로드하지 않고 Unsplash가 제공하는 URL을 그대로 반환 (서버 용량 사용 안 함)"""
    if not UNSPLASH_ACCESS_KEY:
        print("[Unsplash] UNSPLASH_ACCESS_KEY가 설정되지 않음")
        return None
    if not keyword:
        print("[Unsplash] 검색 키워드가 없음")
        return None
    try:
        resp = requests.get(
            UNSPLASH_SEARCH_URL,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={"query": keyword, "per_page": 10, "orientation": "landscape"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        print(f"[Unsplash] '{keyword}' 검색 결과 {len(results)}건 (남은 호출: {resp.headers.get('X-Ratelimit-Remaining', '?')})")
        if not results:
            return None

        title_keywords = extract_keywords(title)
        keyword_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", keyword)}

        best_url = None
        best_score = -1
        for photo in results:
            tags = {t.get("title", "").lower() for t in photo.get("tags", []) if t.get("title")}
            description = (photo.get("description") or photo.get("alt_description") or "").lower()
            desc_words = set(re.findall(r"[a-zA-Z]+", description))
            candidate_words = tags | desc_words

            score = len(candidate_words & keyword_words)
            for kw in title_keywords:
                if any(kw.lower() in cw or cw in kw.lower() for cw in candidate_words):
                    score += 1

            if score > best_score:
                best_score = score
                best_url = photo.get("urls", {}).get("regular")

        return best_url
    except Exception as exc:
        print(f"[Unsplash 검색 실패] {exc}")
        return None



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
        slug = a.get("slug") or ""
        is_hex = bool(re.match(r'^[0-9a-f]{8,}$', slug))
        loc = f"{SITE_URL}/article.php?slug={slug}" if slug and not is_hex else f"{SITE_URL}/article.php?id={aid}"
        lines.append(f"""  <url>
    <loc>{loc}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <lastmod>{pub}</lastmod>
  </url>""")

    lines.append("</urlset>")
    sitemap_path = os.path.join(os.path.dirname(DATA_DIR) if DATA_DIR != "data" else ".", "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[sitemap] {len(seen)}개 기사 URL 업데이트")


def update_rss(all_articles: list) -> None:
    """최신 기사 50개로 rss.xml 생성"""
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '  <channel>',
        f'    <title>{esc("newscommu.com - 실시간 뉴스 커뮤니티")}</title>',
        f'    <link>{SITE_URL}</link>',
        f'    <description>{esc("한국 주요 뉴스를 한눈에 — 실시간 뉴스 커뮤니티")}</description>',
        '    <language>ko</language>',
        f'    <atom:link href="{SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>',
    ]

    seen = set()
    for a in all_articles[:50]:
        aid = a.get("article_id", "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        title = esc(a.get("title", ""))
        slug = a.get("slug") or ""
        is_hex = bool(re.match(r'^[0-9a-f]{8,}$', slug))
        link = f"{SITE_URL}/article.php?slug={slug}" if slug and not is_hex else f"{SITE_URL}/article.php?id={aid}"
        desc = esc(a.get("summary", ""))
        pub_date = a.get("pubDate") or a.get("pub_date") or ""
        cat_label = esc(a.get("category_label") or a.get("category", ""))
        lines.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{desc}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{aid}</guid>
      <category>{cat_label}</category>
    </item>""")

    lines.append('  </channel>')
    lines.append('</rss>')

    rss_path = os.path.join(os.path.dirname(DATA_DIR) if DATA_DIR != "data" else ".", "rss.xml")
    with open(rss_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[rss] {len(seen)}개 기사 RSS 업데이트")


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

        # 원문 품질 필터
        combined = f"{title} {description}".strip()
        BAD_PATTERNS = ["It is assumed", "errors in the English", "translation", "[인물 탐구]", "[기고]", "[광고]"]
        if len(combined) < 80:
            print(f"    건너뜀 (원문 너무 짧음 {len(combined)}자): {title[:40]}")
            continue
        if any(p in combined for p in BAD_PATTERNS):
            print(f"    건너뜀 (원문 이상 패턴): {title[:40]}")
            continue

        print(f"[+] 새 기사: {title[:50]}")
        rewritten = rewrite_with_gemini(f"{title}\n{description}", title)
        if rewritten is None:
            if _gemini_key_index >= len(GEMINI_API_KEYS):
                print("[*] Gemini 키 모두 소진, 이번 실행 종료")
                break
            print("[*] Gemini 응답 실패, 이번 기사 건너뜀")
            continue

        # Gemini가 분류한 카테고리가 유효하면 사용, 아니면 검색 카테고리 유지
        claude_cat = rewritten.get("category", "")
        if claude_cat and claude_cat in CATEGORIES:
            final_category = claude_cat
        else:
            final_category = category

        image_search_keyword = rewritten.get("image_keyword") or final_category
        print(f"[이미지 검색] 키워드: '{image_search_keyword}' (Gemini 추출: '{rewritten.get('image_keyword')}')")
        image_url = search_unsplash_image(image_search_keyword, rewritten["title"])

        # 1차 검색 실패 시 폴백: 콤마/공백으로 쪼갠 첫 구절 → 카테고리 영문 키워드 순으로 재시도
        if not image_url:
            fallback_keywords = []
            first_chunk = re.split(r"[,/]", image_search_keyword)[0].strip()
            if first_chunk and first_chunk.lower() != image_search_keyword.lower():
                fallback_keywords.append(first_chunk)
            cat_fallback = CAT_IMAGE_FALLBACK.get(final_category)
            if cat_fallback:
                fallback_keywords.append(cat_fallback)

            for fb_keyword in fallback_keywords:
                print(f"[이미지 검색] 1차 검색 실패, 폴백 키워드로 재시도: '{fb_keyword}'")
                image_url = search_unsplash_image(fb_keyword, rewritten["title"])
                if image_url:
                    break

        print(f"[이미지 검색 결과] {'찾음 → ' + image_url if image_url else '못 찾음 (image_url=None)'}")

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

    # 9. rss.xml 갱신
    update_rss(all_articles)

    print(f"\n[완료] '{category}' → {new_article['title'][:50]}")


if __name__ == "__main__":
    main()
