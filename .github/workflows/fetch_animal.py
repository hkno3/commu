#!/usr/bin/env python3
"""
천천히 늙자 - PubMed 동물 수명 논문 수집 → Gemini 한국어 재작성 → 발행
6시간마다 1편 발행
"""

import os
import json
import re
import hashlib
import requests

from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_2", "")
PUBMED_API_KEY = os.environ.get("PUBMED_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"

DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_animal.json")
CATEGORY_FILE  = os.path.join(DATA_DIR, "animal.json")
CATEGORY_KEY   = "천천히 늙자"
CATEGORY_SLUG  = "animal"

# PubMed 검색 키워드 (동물 수명/노화 관련)
SEARCH_QUERIES = [
    "animal longevity mechanism",
    "dog aging lifespan",
    "cat longevity genetics",
    "mammal lifespan extension",
    "animal aging biomarker",
    "naked mole rat aging",
    "dog lifespan genetics",
    "feline aging biology",
    "animal healthspan research",
    "species longevity comparison",
]

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

REWRITE_PROMPT = """[현재 시점 안내]
오늘은 {today}입니다. 본문에서 연도를 언급할 때는 이 시점을 기준으로 작성하세요.

당신은 반려동물을 사랑하는 따뜻한 과학 에디터입니다.
아래 동물 수명/노화 관련 논문(영어)을 한국어로 재작성해주세요.

반드시 아래 형식 그대로 출력하세요:

제목: (30자 이내. 흥미롭고 따뜻한 제목. 동물 이름이나 핵심 발견을 포함)
슬러그: (영어 URL 슬러그. 소문자+하이픈, 3~6단어. 예: dog-aging-gene-discovery)
요약: (2문장. 따뜻하고 쉬운 말로. 반려인이 공감할 수 있게)
내용:
<h2>📌 이 논문이 밝혀낸 것</h2>
<p>어떤 동물을 연구했는지, 핵심 발견이 무엇인지, 기존 연구와 무엇이 다른지 설명. 에디터가 직접 읽은 것처럼 생동감 있게.</p>

<h2>💡 쉽게 풀면</h2>
<p>전문 용어 없이 일반인 언어로 설명. "쉽게 말하면 ~" 식으로. 비유 활용.</p>

<h2>🐾 반려동물에 적용하면?</h2>
<p>이 연구가 개/고양이 등 반려동물에 어떤 의미가 있는지. 아직 연구 중인 부분도 솔직하게.</p>

<h2>❓ 함께 생각해봐요</h2>
<p>독자에게 질문 1개. 댓글 유도. 예) "여러분의 반려동물은 몇 살인가요? 댓글로 알려주세요!"</p>

카테고리: 천천히 늙자
이미지키워드: (논문 주제에 맞는 영어 키워드 1~2단어. 예: old dog, laboratory animal, aging research)

=== 규칙 ===
- 마크다운 ** 기호 절대 사용 금지
- 구어체 사용 (~했대요, ~인 것 같아요)
- 에디터가 직접 읽고 감동받은 것처럼 따뜻하게
- 반려인의 마음을 공감하는 톤 유지
"""

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

SAVE_SECRET = os.environ.get("SAVE_SECRET", "nc_save_s3cr3t_2026")
SAVE_API_URL = "https://newscommu.com/api/save_article.php"

def save_article_to_db(article: dict) -> None:
    try:
        r = requests.post(
            SAVE_API_URL,
            json=article,
            headers={"X-Save-Secret": SAVE_SECRET, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            print(f"  [DB] 저장 완료: {article.get('article_id','')[:20]}")
        else:
            print(f"  [DB] 저장 실패: {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"  [DB] 저장 실패 (무시): {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_article_id(pmid: str) -> str:
    return hashlib.md5(f"pubmed_{pmid}".encode()).hexdigest()

def load_published() -> set:
    if os.path.exists(PUBLISHED_FILE):
        try:
            data = json.load(open(PUBLISHED_FILE, encoding="utf-8"))
            return set(data.get("ids", []))
        except Exception:
            pass
    return set()

def save_published(ids: set):
    with open(PUBLISHED_FILE, "w", encoding="utf-8") as f:
        json.dump({"ids": list(ids)}, f, ensure_ascii=False, indent=2)

def load_category_articles() -> list:
    if os.path.exists(CATEGORY_FILE):
        try:
            return json.load(open(CATEGORY_FILE, encoding="utf-8")) or []
        except Exception:
            pass
    return []

def save_category_articles(articles: list):
    with open(CATEGORY_FILE, "w", encoding="utf-8") as f:
        json.dump(articles[:10000], f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# PubMed API
# ---------------------------------------------------------------------------

def search_pubmed(query: str, max_results: int = 20) -> list:
    """PubMed에서 논문 PMID 목록 검색"""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date",
        "datetype": "pdat",
        "reldate": 365,  # 최근 1년 논문
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    try:
        resp = requests.get(PUBMED_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        print(f"[PubMed] '{query}' 검색 결과: {len(ids)}건")
        return ids
    except Exception as e:
        print(f"[PubMed 검색 실패] {e}")
        return []

def fetch_pubmed_abstract(pmid: str) -> dict | None:
    """PMID로 논문 상세정보(제목+초록) 가져오기"""
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
        "rettype": "abstract",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    try:
        resp = requests.get(PUBMED_FETCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        xml = resp.text

        # 제목 추출
        title_m = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", xml, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

        # 초록 추출
        abstract_m = re.search(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.DOTALL)
        abstract = re.sub(r"<[^>]+>", "", abstract_m.group(1)).strip() if abstract_m else ""

        # 저널명
        journal_m = re.search(r"<Title>(.*?)</Title>", xml, re.DOTALL)
        journal = re.sub(r"<[^>]+>", "", journal_m.group(1)).strip() if journal_m else ""

        # 발행년도
        year_m = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", xml, re.DOTALL)
        year = year_m.group(1) if year_m else ""

        if not title or not abstract:
            return None

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
    except Exception as e:
        print(f"[PubMed fetch 실패] PMID={pmid}: {e}")
        return None

# ---------------------------------------------------------------------------
# Gemini 재작성
# ---------------------------------------------------------------------------

def rewrite_with_gemini(paper: dict) -> dict | None:
    if not GEMINI_API_KEY:
        print("[Gemini] GEMINI_API_KEY_2 미설정")
        return None

    now_kst = datetime.now(KST)
    prompt = REWRITE_PROMPT.format(today=now_kst.strftime("%Y년 %m월 %d일"))

    text = f"""논문 제목: {paper['title']}
저널: {paper['journal']} ({paper['year']})
PubMed ID: {paper['pmid']}

초록(Abstract):
{paper['abstract']}"""

    payload = {
        "contents": [{"parts": [{"text": f"{prompt}\n\n{text}"}]}],
        "generationConfig": {"maxOutputTokens": 40000, "temperature": 0.9},
    }

    import time
    for attempt in range(2):
        try:
            resp = requests.post(GEMINI_URL, json=payload, timeout=120)
            if resp.status_code == 429:
                print("[Gemini] 할당량 초과")
                return None
            resp.raise_for_status()
            data = resp.json()
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            result = "".join(p["text"] for p in parts if not p.get("thought", False)).strip()
            print(f"[Gemini] 재작성 완료 ({len(result)}자)")
            return parse_result(result, paper['title'])
        except Exception as e:
            if attempt == 0:
                print(f"[Gemini] 오류: {e} (재시도)")
                time.sleep(5)
            else:
                print(f"[Gemini] 오류: {e}")
                return None

def parse_result(result: str, original_title: str) -> dict:
    result = result.replace("**", "").replace("*", "")
    result = re.sub(r'^###\s*(.+)$', r'<h3>\1</h3>', result, flags=re.MULTILINE)
    result = re.sub(r'^##\s*(.+)$', r'<h2>\1</h2>', result, flags=re.MULTILINE)

    new_title = new_slug = summary_text = new_image_keyword = None
    content_lines = []
    section = None

    for line in result.split("\n"):
        stripped = line.strip()
        if section == 'content':
            if re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
                pass
            elif re.match(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]", stripped):
                new_image_keyword = re.sub(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]\s*", "", stripped).strip()
            else:
                content_lines.append(line)
            continue

        if re.match(r"^제\s*목\s*[:：]", stripped):
            new_title = re.sub(r"^제\s*목\s*[:：]\s*", "", stripped).strip()
        elif re.match(r"^슬\s*러\s*그\s*[:：]", stripped):
            raw = re.sub(r"^슬\s*러\s*그\s*[:：]\s*", "", stripped).strip()
            new_slug = re.sub(r"[^a-z0-9-]", "", raw.lower().replace(" ", "-"))
        elif re.match(r"^요\s*약\s*[:：]", stripped):
            summary_text = re.sub(r"^요\s*약\s*[:：]\s*", "", stripped).strip()
            section = 'summary'
        elif re.match(r"^내\s*용\s*[:：]", stripped):
            section = 'content'
        elif re.match(r"^카\s*테\s*고\s*리\s*[:：]", stripped):
            pass
        elif re.match(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]", stripped):
            new_image_keyword = re.sub(r"^이\s*미\s*지\s*키\s*워\s*드\s*[:：]\s*", "", stripped).strip()
        else:
            if section == 'summary' and stripped and not summary_text:
                summary_text = stripped

    if not new_title:
        new_title = original_title

    block_tag_re = re.compile(r"^<(h2|h3|p|details|summary|table|thead|tbody|tr|th|td)\b", re.IGNORECASE)
    allowed = re.compile(r'<(?!/?(h2|h3|p|br|strong|details|summary|table|thead|tbody|tr|th|td)(\s|>))[^>]+>', re.IGNORECASE)
    wrapped = []
    for line in content_lines:
        s = line.strip()
        if s and not block_tag_re.match(s):
            wrapped.append(f"<p>{s}</p>")
        else:
            wrapped.append(line)

    raw_content = "\n".join(wrapped).strip()
    content_html = allowed.sub("", raw_content) if raw_content else f"<p>{summary_text or ''}</p>"

    if not summary_text:
        m = re.search(r"<p>(.*?)</p>", content_html, re.DOTALL)
        summary_text = m.group(1).strip() if m else ""

    return {
        "title": new_title,
        "slug": new_slug,
        "summary": summary_text,
        "content": content_html,
        "image_keyword": new_image_keyword,
    }

# ---------------------------------------------------------------------------
# Unsplash 이미지
# ---------------------------------------------------------------------------

def search_unsplash_image(keyword: str) -> str | None:
    if not UNSPLASH_ACCESS_KEY or not keyword:
        return None
    try:
        resp = requests.get(
            UNSPLASH_SEARCH_URL,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={"query": keyword, "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        print(f"[Unsplash] '{keyword}' 결과 {len(results)}건")
        if results:
            return results[0].get("urls", {}).get("regular")
        # 폴백: animal 키워드
        resp2 = requests.get(
            UNSPLASH_SEARCH_URL,
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={"query": "animal nature", "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        results2 = resp2.json().get("results", [])
        return results2[0].get("urls", {}).get("regular") if results2 else None
    except Exception as e:
        print(f"[Unsplash 실패] {e}")
        return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY_2 미설정")
        return

    published = load_published()
    print(f"[*] 발행 이력: {len(published)}개")

    # 쿼리를 시간 기반으로 순환 선택
    now_kst = datetime.now(KST)
    query_idx = (now_kst.hour // 6) % len(SEARCH_QUERIES)
    query = SEARCH_QUERIES[query_idx]
    print(f"[*] 검색 쿼리: '{query}'")

    pmids = search_pubmed(query, max_results=30)
    if not pmids:
        print("[!] 논문 없음")
        return

    new_article = None
    for pmid in pmids:
        article_id = make_article_id(pmid)
        if article_id in published:
            print(f"    건너뜀 (중복): PMID={pmid}")
            continue

        paper = fetch_pubmed_abstract(pmid)
        if not paper:
            continue
        if len(paper['abstract']) < 100:
            print(f"    건너뜀 (초록 너무 짧음): {paper['title'][:40]}")
            continue

        print(f"[+] 새 논문: {paper['title'][:60]}")
        rewritten = rewrite_with_gemini(paper)
        if not rewritten:
            print("[!] Gemini 실패, 건너뜀")
            continue

        image_keyword = rewritten.get("image_keyword") or "animal research"
        image_url = search_unsplash_image(image_keyword)

        now_kst = datetime.now(KST)
        publish_time = now_kst.isoformat()

        new_article = {
            "article_id": article_id,
            "title": rewritten["title"],
            "slug": rewritten.get("slug") or article_id,
            "original_title": paper["title"],
            "summary": rewritten["summary"],
            "content": rewritten.get("content", ""),
            "image_url": image_url,
            "original_url": paper["url"],
            "url": paper["url"],
            "source": paper.get("journal", "PubMed"),
            "pubDate": publish_time,
            "pub_date": publish_time,
            "category": "천천히_늙자",
            "category_label": CATEGORY_KEY,
            "pmid": pmid,
            "article_type": "paper",
        }

        published.add(article_id)
        break

    if not new_article:
        print("[!] 발행할 새 논문 없음")
        save_published(published)
        return

    # DB 저장
    save_article_to_db(new_article)

    # 카테고리 파일 업데이트
    existing = load_category_articles()
    existing.insert(0, new_article)
    save_category_articles(existing)
    save_published(published)

    # latest.json에도 추가
    latest_path = os.path.join(DATA_DIR, "latest.json")
    try:
        latest = json.load(open(latest_path, encoding="utf-8")) if os.path.exists(latest_path) else []
    except Exception:
        latest = []
    latest.insert(0, new_article)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(latest[:500], f, ensure_ascii=False, indent=2)

    print(f"[✓] 발행 완료: {new_article['title']}")

if __name__ == "__main__":
    main()
