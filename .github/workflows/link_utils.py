"""
관련 링크 버튼 삽입 유틸리티
links_cache.json에서 기사와 유사도 30% 이상인 링크를 찾아 h2 섹션 뒤에 버튼으로 삽입
"""

import os
import re
import json
import random
from urllib.parse import unquote

# repo 루트 기준 절대 경로 (스크립트 위치에 무관하게 동작)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # .github/workflows/
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))  # .github/workflows/../../ = repo root
LINKS_CACHE_PATH = os.path.join(_REPO_ROOT, "links_cache.json")

STOPWORDS = {
    "이", "가", "은", "는", "을", "를", "의", "에", "서", "로", "으로",
    "와", "과", "도", "만", "에서", "에게", "부터", "까지", "하고", "이고",
    "그리고", "하지만", "그러나", "또한", "따라서", "그래서", "때문에",
    "위해", "통해", "대해", "관해", "따른", "위한", "대한", "관한",
    "있다", "없다", "했다", "한다", "된다", "됐다", "이다", "아니다",
    "했습니다", "합니다", "입니다", "습니다", "니다",
    "오늘", "내일", "어제", "현재", "최근", "지난", "이번", "올해",
    "기자", "뉴스", "단독", "속보", "종합", "방법", "정리", "가이드",
    "완벽", "추천", "핵심", "총정리", "방법", "이유", "가지", "위한",
}


def extract_keywords(text: str) -> set:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&[a-z]+;", "", text)
    words = re.findall(r"[가-힣a-zA-Z0-9]+", text)
    return {w for w in words if len(w) >= 2 and w not in STOPWORDS}


def load_links_cache() -> list:
    """links_cache.json → [{title, url}, ...] 플랫 리스트"""
    if not os.path.exists(LINKS_CACHE_PATH):
        print(f"[links_cache] 파일 없음: {LINKS_CACHE_PATH}")
        return []
    try:
        with open(LINKS_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        links = []
        for site_links in data.values():
            if not isinstance(site_links, list):
                continue
            for item in site_links:
                if not isinstance(item, dict):
                    continue
                title = unquote(item.get("t", "")).strip()
                url = item.get("u", "").strip()
                if title and url:
                    links.append({"title": title, "url": url})
        print(f"[links_cache] {len(links)}개 링크 로드")
        return links
    except Exception as e:
        print(f"[links_cache] 로드 실패: {e}")
        return []


def find_top_related_links(text: str, links: list, n: int = 2) -> list:
    """text와 유사도 30% 이상인 링크를 최대 n개 반환 (서로 다른 링크)"""
    article_kw = extract_keywords(text)
    if not article_kw or not links:
        return []

    scored = []
    for link in links:
        link_kw = extract_keywords(link["title"])
        if not link_kw:
            continue
        intersection = article_kw & link_kw
        union = article_kw | link_kw
        score = len(intersection) / len(union) if union else 0
        if score >= 0.3:
            scored.append((score, link))

    scored.sort(key=lambda x: -x[0])

    # 상위 n개 선택 (URL 중복 제거)
    seen_urls = set()
    result = []
    for score, link in scored:
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            result.append(link)
            print(f"[관련 링크] {link['title'][:40]} (유사도 {score:.0%})")
            if len(result) >= n:
                break

    return result


def make_button(title: str, url: str) -> str:
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    safe_url = url.replace('"', "&quot;")
    return (
        '\n<br>\n'
        '<p style="text-align:center; margin:24px auto;">\n'
        f'  <a href="{safe_url}" target="_blank"\n'
        '     style="display:inline-flex; align-items:center; justify-content:center;'
        'background:#e74c3c; color:white;'
        'width:auto; max-width:98%; box-sizing:border-box;'
        'padding:18px clamp(18px, 5vw, 80px);'
        'border-radius:10px; font-weight:bold;'
        'font-size:clamp(16px, 4.2vw, 22px);'
        'line-height:1.3; text-decoration:none;'
        'white-space:nowrap;'
        'animation:blink 1s infinite;">\n'
        f'    {safe_title}\n'
        '  </a>\n'
        '</p>\n'
        '<style>@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.5} }</style>\n'
        '<br>\n'
    )


def insert_related_buttons(content: str, links: list, title: str, summary: str) -> str:
    """h2 섹션 1, 2 끝 직전에 관련 링크 버튼 2개 삽입"""
    related = find_top_related_links(title + " " + summary, links, n=2)
    if not related:
        print("[관련 링크] 유사도 30% 이상 링크 없음 → 랜덤 선택")
        if links:
            picked = random.sample(links, min(2, len(links)))
            related = picked
        else:
            return content

    # <h2 태그 기준으로 분할 (태그 앞에서 분리)
    parts = re.split(r'(?=<h2[\s>])', content, flags=re.IGNORECASE)
    # parts[0] = h2 이전 내용 (보통 비어있거나 인트로)
    # parts[1] = 첫 번째 h2 섹션 ~ 두 번째 h2 전까지
    # parts[2] = 두 번째 h2 섹션 ~ ...

    if len(parts) < 3:
        # h2가 2개 미만이면 내용 끝에 버튼 추가
        result = content
        for link in related:
            result += make_button(link["title"], link["url"])
        return result

    result = parts[0]
    for i, part in enumerate(parts[1:], 1):
        result += part
        if i == 1 and len(related) >= 1:
            result += make_button(related[0]["title"], related[0]["url"])
        elif i == 2 and len(related) >= 2:
            result += make_button(related[1]["title"], related[1]["url"])

    return result
