#!/usr/bin/env python3
"""
여행지 소개 — KTO 한국관광공사 데이터 기반 AI 여행 가이드 생성기
KTO API에서 최신 업데이트된 관광지 정보를 가져와 Gemini로 가이드 작성
"""

import os
import json
import re
import random
import hashlib
import time
import requests
import markdown
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
from link_utils import load_links_cache, insert_related_buttons

KST = timezone(timedelta(hours=9))

GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY_3", "")
KTO_API_KEY         = os.environ.get("KTO_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
PIXABAY_API_KEY     = os.environ.get("PIXABAY_API_KEY", "")
PEXELS_API_KEY      = os.environ.get("PEXELS_API_KEY", "")
SAVE_SECRET         = os.environ.get("SAVE_SECRET", "nc_save_s3cr3t_2026")
SAVE_API_URL        = "https://newscommu.com/api/save_article.php"

DATA_DIR    = "data"
TRAVEL_FILE = os.path.join(DATA_DIR, "travelguide.json")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)
KTO_BASE = "https://apis.data.go.kr/B551011/KorService2"

# KTO contentTypeId
CONTENT_TYPES = [12, 14, 25]  # 관광지, 문화시설, 여행코스


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


def kto_params(extra: dict) -> dict:
    key = unquote(KTO_API_KEY)
    base = {
        "serviceKey": key,
        "MobileOS": "ETC",
        "MobileApp": "newscommu",
        "_type": "json",
    }
    base.update(extra)
    return base


def kto_items(r) -> list:
    try:
        body = r.json().get("response", {}).get("body", {})
        items = body.get("items", {})
        if not items:
            return []
        lst = items.get("item", [])
        return [lst] if isinstance(lst, dict) else lst
    except Exception:
        return []


# ---------------------------------------------------------------------------
# KTO: 전체 관광지 목록 조회 (가나다순 순환)
# ---------------------------------------------------------------------------

def fetch_kto_page(page: int = 1, num: int = 30, ctype: int = 12) -> list:
    """가나다순(arrange=A) 전체 목록에서 특정 페이지 조회"""
    try:
        r = requests.get(
            f"{KTO_BASE}/areaBasedList2",
            params=kto_params({
                "numOfRows": num,
                "pageNo": page,
                "arrange": "A",          # 가나다순 (전체 순환용)
                "contentTypeId": ctype,
            }),
            timeout=10,
        )
        return kto_items(r)
    except Exception as e:
        print(f"  KTO areaBasedList2 오류 (type {ctype}, page {page}): {e}")
        return []


# ---------------------------------------------------------------------------
# KTO: 관광지 상세 정보 조회
# ---------------------------------------------------------------------------

def fetch_kto_detail(content_id: str, content_type: str) -> dict:
    """관광지 상세 공통정보 (overview, tel, homepage 등)"""
    try:
        r = requests.get(
            f"{KTO_BASE}/detailCommon2",
            params=kto_params({
                "contentId": content_id,
                "contentTypeId": content_type,
                "defaultYN": "Y",
                "firstImageYN": "Y",
                "areacodeYN": "Y",
                "addrinfoYN": "Y",
                "mapinfoYN": "Y",
                "overviewYN": "Y",
            }),
            timeout=10,
        )
        items = kto_items(r)
        return items[0] if items else {}
    except Exception as e:
        print(f"  detailCommon2 오류: {e}")
        return {}


def fetch_kto_intro(content_id: str, content_type: str) -> dict:
    """관광지 소개정보 (운영시간, 입장료 등)"""
    try:
        r = requests.get(
            f"{KTO_BASE}/detailIntro2",
            params=kto_params({
                "contentId": content_id,
                "contentTypeId": content_type,
            }),
            timeout=10,
        )
        items = kto_items(r)
        return items[0] if items else {}
    except Exception as e:
        print(f"  detailIntro2 오류: {e}")
        return {}


def fetch_kto_images(content_id: str) -> list:
    """관광지 이미지 목록"""
    try:
        r = requests.get(
            f"{KTO_BASE}/detailImage2",
            params=kto_params({
                "contentId": content_id,
                "numOfRows": 10,
                "pageNo": 1,
                "imageYN": "Y",
                "subImageYN": "Y",
            }),
            timeout=10,
        )
        return kto_items(r)
    except Exception as e:
        print(f"  detailImage2 오류: {e}")
        return []


# ---------------------------------------------------------------------------
# 해외/국내 KTO 실패 시 이미지 폴백: Unsplash / Pixabay / Pexels
# ---------------------------------------------------------------------------

def search_unsplash_image(keyword: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        return ""
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={"query": keyword, "per_page": 10, "orientation": "landscape"},
            timeout=8,
        )
        results = r.json().get("results", [])
        if results:
            return random.choice(results)["urls"]["regular"]
    except Exception:
        pass
    return ""


def search_pixabay_image(keyword: str) -> str:
    if not PIXABAY_API_KEY:
        return ""
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_API_KEY, "q": keyword, "image_type": "photo",
                    "orientation": "horizontal", "per_page": 10, "safesearch": "true"},
            timeout=8,
        )
        hits = r.json().get("hits", [])
        if hits:
            return random.choice(hits)["webformatURL"]
    except Exception:
        pass
    return ""


def search_pexels_image(keyword: str) -> str:
    if not PEXELS_API_KEY:
        return ""
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": keyword, "per_page": 10, "orientation": "landscape"},
            timeout=8,
        )
        photos = r.json().get("photos", [])
        if photos:
            return random.choice(photos)["src"]["large"]
    except Exception:
        pass
    return ""


def search_fallback_image(keyword: str) -> str:
    sources = [search_unsplash_image, search_pixabay_image, search_pexels_image]
    random.shuffle(sources)
    for fn in sources:
        url = fn(keyword)
        if url:
            return url
    return ""


def insert_content_images(content_html: str, image_urls: list) -> str:
    """h2 섹션 시작 직전에 KTO 이미지를 순서대로 삽입 (최대 4장)"""
    if not image_urls:
        return content_html

    def make_img_tag(url: str) -> str:
        safe = url.replace('"', "&quot;")
        return (
            f'\n<figure style="margin:24px 0; text-align:center;">'
            f'<img src="{safe}" alt="한국관광공사 제공 이미지" '
            f'style="max-width:100%; border-radius:8px;" '
            f'onerror="this.parentElement.style.display=\'none\'">'
            f'<figcaption style="font-size:12px; color:#888; margin-top:6px;">'
            f'사진 제공: <a href="https://www.visitkorea.or.kr" target="_blank" rel="noopener">한국관광공사</a>'
            f'</figcaption></figure>\n'
        )

    # h2 기준으로 분할
    parts = re.split(r'(?=<h2[\s>])', content_html, flags=re.IGNORECASE)
    if len(parts) < 2:
        # h2가 없으면 끝에 추가
        result = content_html
        for url in image_urls[:4]:
            result += make_img_tag(url)
        return result

    result = parts[0]
    img_idx = 0
    for i, part in enumerate(parts[1:], 1):
        result += part
        # 2번째 h2부터 삽입 (1번째는 소개 섹션이라 썸네일과 겹침)
        if i >= 2 and img_idx < len(image_urls) and img_idx < 4:
            result += make_img_tag(image_urls[img_idx])
            img_idx += 1

    return result


# ---------------------------------------------------------------------------
# KTO에서 발행할 콘텐츠 선택
# ---------------------------------------------------------------------------

def pick_kto_content(travel_data: list) -> dict | None:
    """
    KTO 전체 35,000건을 가나다순으로 순환하며 미발행 관광지 선택.
    마지막 스캔 위치(ctype_idx, page)를 travel_data 메타에 저장해 이어서 진행.
    """
    published = {
        a["kto_content_id"]
        for a in travel_data
        if a.get("kto_content_id")
    }

    # 마지막 스캔 위치 복원
    meta = next((a for a in travel_data if a.get("_meta")), {})
    ctype_idx = meta.get("kto_ctype_idx", 0)   # CONTENT_TYPES 인덱스
    last_page = meta.get("kto_last_page", 0)    # 0 = 아직 시작 안 함

    num_per_page = 30
    max_pages = 1200  # 35,000 / 30 ≈ 1,167

    # 현재 ctype부터 최대 2 ctype × 5페이지씩 탐색 (API 과부하 방지)
    for ci in range(len(CONTENT_TYPES)):
        actual_ci = (ctype_idx + ci) % len(CONTENT_TYPES)
        ctype = CONTENT_TYPES[actual_ci]
        start_page = (last_page + 1) if ci == 0 else 1

        for page in range(start_page, start_page + 5):
            real_page = ((page - 1) % max_pages) + 1  # 끝까지 가면 1로 리셋
            items = fetch_kto_page(page=real_page, num=num_per_page, ctype=ctype)
            print(f"  스캔: contentType={ctype}, page={real_page}, {len(items)}건")

            if not items:
                # 이 ctype 끝 → 다음 ctype으로
                ctype_idx = (actual_ci + 1) % len(CONTENT_TYPES)
                last_page = 0
                _save_scan_meta(travel_data, ctype_idx, 0)
                break

            for item in items:
                cid = str(item.get("contentid", ""))
                if not cid or cid in published:
                    continue
                img = item.get("firstimage", "") or item.get("firstimage2", "")
                if not img:
                    print(f"  스킵 (대표이미지 없음): {item.get('title','')}")
                    continue
                title = item.get("title", "").strip()
                addr  = item.get("addr1", "").strip()
                # 스캔 위치 저장
                _save_scan_meta(travel_data, actual_ci, real_page)
                print(f"  선택: {title} (contentId={cid}, type={ctype}, page={real_page})")
                return {
                    "contentid":   cid,
                    "contenttype": str(item.get("contenttypeid", ctype)),
                    "title":       title,
                    "addr":        addr,
                    "firstimage":  img,
                    "modifiedtime": str(item.get("modifiedtime", "")),
                }
            # 페이지 소진 → 위치 갱신
            last_page = real_page

    # 모두 발행 완료 → ctype 0, page 0으로 리셋 후 가장 오래된 글 재발행
    print("  전체 순환 완료 → 처음부터 다시 시작")
    _save_scan_meta(travel_data, 0, 0)
    if travel_data:
        articles = [a for a in travel_data if not a.get("_meta")]
        if articles:
            oldest = sorted(articles, key=lambda a: a.get("pub_date", ""))
            item_old = oldest[0]
            return {
                "contentid":   item_old.get("kto_content_id", ""),
                "contenttype": "12",
                "title":       item_old.get("destination", item_old.get("title", "")),
                "addr":        "",
                "firstimage":  "",
                "modifiedtime": "",
            }
    return None


def _save_scan_meta(travel_data: list, ctype_idx: int, page: int):
    """travel_data 내 _meta 항목에 스캔 위치 저장"""
    for a in travel_data:
        if a.get("_meta"):
            a["kto_ctype_idx"] = ctype_idx
            a["kto_last_page"] = page
            return
    travel_data.append({"_meta": True, "kto_ctype_idx": ctype_idx, "kto_last_page": page})


# ---------------------------------------------------------------------------
# Gemini: KTO 데이터 기반 여행 가이드 작성
# ---------------------------------------------------------------------------

TRAVEL_PROMPT = """당신은 한국어 여행 전문 작가입니다. 아래 한국관광공사 공식 데이터를 바탕으로 '{title}'에 대한 완성도 높은 여행 가이드를 작성하세요.

오늘 날짜: {today}

**한국관광공사 공식 데이터:**
- 관광지명: {title}
- 주소: {addr}
- 소개: {overview}
- 운영시간: {usetime}
- 입장료: {usefee}
- 주차: {parking}
- 전화: {tel}
- 홈페이지: {homepage}

**요구사항:**
- 위 공식 데이터를 최우선으로 활용하고, 부족한 부분은 여행 전문 지식으로 보완
- 독자: 한국인 여행자 (20~50대)
- 실용적이고 구체적인 정보 중심
- 총 1200자 이상의 풍부한 내용
- 마크다운 형식으로 작성

**출력 순서: 반드시 본문 먼저 쓰고, 본문을 다 쓴 뒤 마지막 줄에 제목을 출력할 것**

## ✈️ {title} 소개
(이 여행지의 매력과 특징, 어떤 여행자에게 추천하는지 200자 이상)

### 🗓️ 최적 여행 시기
(월별 날씨와 추천 시기, 성수기·비수기 정보)

## 🏛️ 꼭 가봐야 할 명소

### 명소 1: (명소명)
(구체적인 설명, 관람 팁, 소요 시간)

### 명소 2: (명소명)
(구체적인 설명, 관람 팁, 소요 시간)

### 명소 3: (명소명)
(구체적인 설명, 관람 팁, 소요 시간)

## 🍜 음식 & 맛집

### 꼭 먹어봐야 할 음식
(대표 음식 3~5가지와 추천 먹는 방법)

### 추천 식당 & 먹거리 거리
(구체적인 장소나 지역 추천)

## 💰 예산 & 교통

### 예산 가이드

| 항목 | 예산 (1인 기준) |
|------|----------------|
| 교통 | |
| 숙박 (1박) | |
| 식비 (1일) | |
| 관광·입장료 | |
| 총 예상 비용 (2박 3일) | |

### 🚌 교통 & 이동
(출발지에서 도착까지, 현지 이동 방법)

## 💡 알아두면 좋은 팁

<details>
<summary>현지 유용한 정보</summary>

- **운영시간**: (공식 데이터 기반)
- **입장료**: (공식 데이터 기반)
- **주차**: (공식 데이터 기반)
- **문의**: (전화번호/홈페이지)
- **짐싸기 팁**: (날씨·계절에 맞는 준비물)

</details>

<details>
<summary>주의사항 & 안전 팁</summary>

- **혼잡 시간대**: (피해야 할 시간)
- **예절**: (방문 시 지켜야 할 사항)
- **주변 편의시설**: (화장실, 매점, 휴게 공간 등)

</details>

## ⭐ 추천 일정

### 1일차
(오전·오후·저녁 일정 구체적으로)

### 2일차
(오전·오후·저녁 일정 구체적으로)

### 3일차
(오전·오후·저녁, 귀가)

---

**[마지막 줄] 위 본문을 다 쓴 뒤, 본문 내용을 참고해서 제목을 지어 아래 형식으로 출력:**
제목: (여기에 제목)

제목 규칙 (하나라도 어기면 실패):
1. {title} 이름 반드시 포함
2. 본문에서 다룬 구체적 특징(볼거리·음식·지형·체험·계절 중 1~2가지) 키워드 포함 — "여행", "명소", "추천"만 있으면 탈락
3. 마지막 단어는 명사로 끝낼 것 (~코스, ~산책, ~야경, ~해변, ~계곡, ~체험, ~축제 등)
4. 이모지 없이 30자 이내
5. "완벽 여행 가이드", "여행 정보", "총정리" 같은 뻔한 표현 절대 금지
✅ 예시: "내소사 전나무 숲길과 천년 고찰 산책", "해운대 일출과 마린시티 야경 코스"
❌ 금지: "경복궁 완벽 여행 가이드", "부산 여행 명소 추천"

주의: 생각 과정(thinking)은 출력하지 마세요. 완성된 글만 출력하세요."""


def generate_travel_article(kto_data: dict) -> dict | None:
    title    = kto_data.get("title", "")
    addr     = kto_data.get("addr", "")
    overview = kto_data.get("overview", "정보 없음")
    usetime  = kto_data.get("usetime", "정보 없음")
    usefee   = kto_data.get("usefee", "정보 없음")
    parking  = kto_data.get("parking", "정보 없음")
    tel      = kto_data.get("tel", "정보 없음")
    homepage = kto_data.get("homepage", "정보 없음")

    now = datetime.now(KST)
    prompt = TRAVEL_PROMPT.format(
        title=title, addr=addr, overview=overview,
        usetime=usetime, usefee=usefee, parking=parking,
        tel=tel, homepage=homepage,
        today=now.strftime("%Y년 %m월 %d일"),
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 8000,
            "thinkingConfig": {"thinkingBudget": 2000},
        },
    }
    for attempt in range(1, 4):
        try:
            r = requests.post(GEMINI_URL, json=payload, timeout=180)
            r.raise_for_status()
            break
        except Exception as e:
            print(f"  Gemini 오류 (시도 {attempt}/3): {e}")
            if attempt < 3:
                time.sleep(20)
            else:
                return None

    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        content = "".join(p["text"] for p in parts if not p.get("thought", False)).strip()
        if not content:
            return None

        # 제목 추출 (본문 마지막에 위치)
        raw_title = ""
        for line in reversed(content.splitlines()):
            s = line.strip()
            if s.startswith("제목:"):
                raw_title = s[3:].strip()
                break
            if s.startswith("제목 :"):
                raw_title = s[4:].strip()
                break
        raw_title = re.sub(r'[\U0001F300-\U0001FFFF\U00002702-\U000027B0\U0000FE0F]+', '', raw_title).strip()

        # 금지 패턴 강제 제거
        BAN_PATTERNS = ["완벽 여행 가이드", "여행 가이드", "여행 정보", "여행지 소개", "총정리", "알아보기"]
        cleaned = raw_title
        for b in BAN_PATTERNS:
            cleaned = cleaned.replace(b, "").strip(" -–·,")
        # 지명만 남은 경우 기본 접미사 추가
        if not cleaned or cleaned == title:
            cleaned = f"{title} 여행 코스"
        article_title = cleaned
        if cleaned != raw_title:
            print(f"  제목 정제: '{raw_title}' → '{article_title}'")

        # 요약 추출
        summary = f"{title}의 매력을 소개하는 완벽 여행 가이드입니다."
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "소개" in line and line.startswith("##"):
                for j in range(i + 1, min(i + 6, len(lines))):
                    t = lines[j].strip()
                    if t and not t.startswith("#"):
                        summary = t[:150]
                        break
                break

        # 제목: 줄 및 마크다운 h1(# ...) 제거 후 HTML 변환
        content_clean = "\n".join(
            l for l in content.splitlines()
            if not l.strip().startswith("제목:")
            and not l.strip().startswith("제목 :")
            and not l.strip().startswith("# ")
            and l.strip() != "#"
        )
        content_html = markdown.markdown(content_clean, extensions=["tables", "sane_lists"])
        return {"title": article_title, "summary": summary, "content": content_html}
    except Exception as e:
        print(f"  파싱 오류: {e}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY_3 없음")
        return
    if not KTO_API_KEY:
        print("KTO_API_KEY 없음")
        return

    links_cache = load_links_cache()
    now = datetime.now(KST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')} KST] 여행지 가이드 생성 시작")

    travel_data = load_json(TRAVEL_FILE)

    # 1. KTO에서 발행할 관광지 선택
    spot = pick_kto_content(travel_data)
    if not spot:
        print("발행할 관광지 없음")
        return

    content_id   = spot["contentid"]
    content_type = spot["contenttype"]
    title        = spot["title"]
    print(f"관광지: {title} (contentId={content_id})")

    # 2. 상세 정보 조회
    detail = fetch_kto_detail(content_id, content_type)
    intro  = fetch_kto_intro(content_id, content_type)
    images = fetch_kto_images(content_id)

    # HTML 태그 제거 유틸
    def strip_html(s):
        return re.sub(r"<[^>]+>", "", s or "").strip()

    kto_data = {
        "title":    title,
        "addr":     detail.get("addr1", spot.get("addr", "")),
        "overview": strip_html(detail.get("overview", "")),
        "usetime":  strip_html(intro.get("usetime", "")),
        "usefee":   strip_html(intro.get("usefee", "") or intro.get("useseason", "")),
        "parking":  strip_html(intro.get("parking", "") or intro.get("chkparkingbeach", "")),
        "tel":      detail.get("tel", ""),
        "homepage": strip_html(detail.get("homepage", "")),
    }

    # 3. 이미지 선택 (KTO 공식 이미지만 사용, 없으면 건너뜀)
    img_candidates = [i.get("originimgurl", "") for i in images if i.get("originimgurl")]
    if not img_candidates:
        # detailImage2 없으면 firstimage로 보완
        fi_list = []
        if spot.get("firstimage"):
            fi_list.append(spot["firstimage"])
        fi = detail.get("firstimage", "") or detail.get("firstimage2", "")
        if fi and fi not in fi_list:
            fi_list.append(fi)
        img_candidates = fi_list

    img_candidates = [u for u in img_candidates if u]
    if not img_candidates:
        print(f"  스킵: KTO 공식 이미지 없음 → 다음 관광지로")
        return

    random.shuffle(img_candidates)
    image_url    = img_candidates[0]
    extra_images = img_candidates[1:]
    image_source = "kto"
    print(f"  이미지: KTO 공식 총 {len(img_candidates)}장 (썸네일 1 + 본문 {len(extra_images)})")

    # 4. Gemini로 글 생성
    result = generate_travel_article(kto_data)
    if not result:
        print("글 생성 실패")
        return

    # 5. article_id: contentId 기반 (업데이트 시 같은 ID로 덮어씀)
    article_id = f"travel_{content_id}"
    pub_date   = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    # slug: 기존 slug 유지 또는 새로 생성
    existing = next((a for a in travel_data if a.get("kto_content_id") == content_id), None)
    slug = existing.get("slug", "") if existing else ""
    if not slug:
        slug = f"travel-{content_id}"

    article = {
        "article_id":       article_id,
        "slug":             slug,
        "title":            result["title"],
        "summary":          result["summary"],
        "content":          insert_related_buttons(
                                insert_content_images(result["content"], extra_images),
                                links_cache,
                                result["title"], result.get("summary", "")
                            ),
        "image_url":        image_url,
        "image_credit":     "",
        "image_credit_name": "한국관광공사" if image_source == "kto" else "",
        "image_credit_url": "https://www.visitkorea.or.kr" if image_source == "kto" else "",
        "image_source":     image_source,
        "category":         "여행지",
        "category_label":   "여행지",
        "article_type":     "travel_guide",
        "pub_date":         pub_date,
        "pubDate":          pub_date,
        "original_url":     detail.get("homepage", ""),
        "source":           "한국관광공사 × AI 여행 가이드",
        "destination":      title,
        "kto_content_id":   content_id,
        "kto_modified":     spot.get("modifiedtime", ""),
    }

    # 기존 동일 article_id 교체 (_meta 항목은 보존)
    travel_data = [a for a in travel_data if a.get("article_id") != article_id]
    # _meta를 맨 뒤로 분리했다가 다시 붙임
    meta_items = [a for a in travel_data if a.get("_meta")]
    travel_data = [a for a in travel_data if not a.get("_meta")]
    travel_data.insert(0, article)
    travel_data.extend(meta_items)
    save_json(TRAVEL_FILE, travel_data)

    try:
        r = requests.post(
            SAVE_API_URL,
            json=article,
            headers={"X-Save-Secret": SAVE_SECRET, "Content-Type": "application/json"},
            timeout=15,
        )
        print(f"  DB: {'완료' if r.status_code == 200 else '실패 ' + str(r.status_code)}")
    except Exception as e:
        print(f"  DB 오류 (무시): {e}")

    print(f"완료: {result['title'][:60]}")


if __name__ == "__main__":
    main()
