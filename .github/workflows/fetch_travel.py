#!/usr/bin/env python3
"""
여행지 소개 — AI 여행 가이드 생성기
매주 3개의 여행지 가이드 기사를 생성한다.
GEMINI_API_KEY_3 사용
"""

import os
import json
import hashlib
import time
import requests
import markdown
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_3", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
SAVE_SECRET = os.environ.get("SAVE_SECRET", "nc_save_s3cr3t_2026")
SAVE_API_URL = "https://newscommu.com/api/save_article.php"

DATA_DIR = "data"
TRAVEL_FILE = os.path.join(DATA_DIR, "travelguide.json")
LATEST_FILE = os.path.join(DATA_DIR, "latest.json")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

# 주차별 여행지 테마 및 목적지 목록 (52주 × 3개)
DESTINATION_THEMES = [
    # (테마, [목적지1, 목적지2, 목적지3])
    ("겨울 온천 여행", ["일본 벳푸 온천", "강원도 평창", "충청도 아산 온양온천"]),
    ("동남아 해변 휴양", ["태국 푸켓", "베트남 다낭", "필리핀 세부"]),
    ("국내 역사 탐방", ["경주", "전주 한옥마을", "공주·부여"]),
    ("유럽 도시 여행", ["체코 프라하", "오스트리아 빈", "헝가리 부다페스트"]),
    ("제주도 테마 여행", ["제주 동부 해안", "제주 서귀포 올레길", "제주 한라산 트레킹"]),
    ("일본 주요 도시", ["오사카·교토", "도쿄 근교", "홋카이도 삿포로"]),
    ("국내 바다 여행", ["부산 해운대·광안리", "여수 오동도·돌산도", "통영 한려수도"]),
    ("중앙아시아·터키", ["터키 이스탄불", "터키 카파도키아", "조지아 트빌리시"]),
    ("봄 벚꽃 여행지", ["진해 군항제", "경주 보문호", "일본 교토 마루야마 공원"]),
    ("동유럽 감성 여행", ["폴란드 크라쿠프", "슬로바키아 브라티슬라바", "루마니아 부쿠레슈티"]),
    ("국내 산악 트레킹", ["설악산 대청봉", "지리산 천왕봉", "덕유산 향적봉"]),
    ("동남아 문화 탐방", ["베트남 하노이", "캄보디아 앙코르와트", "미얀마 바간"]),
    ("스페인·포르투갈", ["스페인 바르셀로나", "스페인 세비야", "포르투갈 리스본"]),
    ("국내 섬 여행", ["울릉도·독도", "거제도", "신안 1004섬"]),
    ("중국 주요 명소", ["장가계", "구채구·황룡", "계림 이강"]),
    ("북유럽 여행", ["아이슬란드 레이캬비크", "노르웨이 피오르", "핀란드 헬싱키"]),
    ("국내 강·계곡 여행", ["강원도 인제 내린천", "경북 청송 주왕산", "충북 단양"]),
    ("미국 주요 도시", ["뉴욕", "로스앤젤레스", "샌프란시스코"]),
    ("여름 해외 피서지", ["몰디브", "발리 우붓", "그리스 산토리니"]),
    ("국내 드라이브 코스", ["동해 해안도로", "남해 독일마을·미조항", "서해 태안 해안도로"]),
    ("이탈리아 여행", ["로마", "피렌체·토스카나", "베네치아"]),
    ("동북아 근거리 여행", ["대만 타이베이", "홍콩", "마카오"]),
    ("국내 캠핑 명소", ["강원 홍천 미약골", "경기 가평 잣향기 푸른숲", "충남 태안 백사장항"]),
    ("중남미 여행", ["페루 마추픽추", "아르헨티나 부에노스아이레스", "쿠바 아바나"]),
    ("국내 겨울 눈꽃 여행", ["태백 태백산 눈축제", "강원 횡성 삼배봉", "지리산 노고단"]),
    ("인도·네팔", ["인도 바라나시", "네팔 카트만두", "인도 라자스탄 조드푸르"]),
    ("국내 봄 꽃 명소", ["경남 하동 십리벚꽃길", "전남 구례 산수유", "강원 평창 야생화"]),
    ("아프리카 여행", ["남아공 케이프타운", "탄자니아 킬리만자로", "모로코 마라케시"]),
    ("국내 가을 단풍", ["내장산", "설악산 천불동계곡", "강원 오대산"]),
    ("중동 여행", ["아랍에미리트 두바이", "이스라엘 예루살렘", "요르단 페트라"]),
    ("국내 미식 여행", ["전주 한식 투어", "부산 해산물 투어", "강릉 커피와 막국수"]),
    ("캐나다·알래스카", ["캐나다 밴쿠버", "캐나다 밴프 국립공원", "알래스카 오로라 투어"]),
    ("국내 문화·예술 도시", ["광주 국립아시아문화전당", "인천 아트플랫폼", "춘천 마임축제"]),
    ("인도네시아 여행", ["발리 우붓 문화지구", "발리 꾸따·스미냑", "롬복·길리 아일랜드"]),
    ("국내 한적한 농촌 마을", ["전남 순천 낙안읍성", "경북 안동 하회마을", "충남 외암 민속마을"]),
    ("호주·뉴질랜드", ["호주 시드니", "호주 멜버른", "뉴질랜드 퀸즈타운"]),
    ("국내 사찰 템플스테이", ["경남 합천 해인사", "전남 순천 선암사", "강원 오대산 월정사"]),
    ("러시아·동유럽", ["러시아 모스크바", "러시아 상트페테르부르크", "체코 프라하 카를교"]),
    ("국내 해양 스포츠", ["부산 송정해수욕장 서핑", "제주 서귀포 스쿠버다이빙", "강원 양양 서핑"]),
    ("프랑스 여행", ["파리", "니스·코트다쥐르", "몽생미셸"]),
    ("국내 온천·스파", ["충청도 덕산 스파캐슬", "강원 속초 워터피아", "전북 무주 덕유산 리조트"]),
    ("중미·카리브해", ["멕시코 칸쿤", "코스타리카", "도미니카 공화국 푼타카나"]),
    ("국내 겨울 스키장", ["강원 하이원 리조트", "강원 휘닉스 파크", "경기 비발디파크"]),
    ("독일·스위스·오스트리아", ["독일 뮌헨·노이슈반슈타인성", "스위스 인터라켄", "오스트리아 잘츠부르크"]),
    ("국내 워케이션 명소", ["강릉 안목해변 카페거리", "제주 애월", "전남 여수 낭만포차거리"]),
    ("태국 전체 여행", ["방콕", "치앙마이", "태국 코사무이·코판냔"]),
    ("국내 야경 명소", ["서울 남산타워", "부산 감천문화마을", "인천 소래포구"]),
    ("그리스 섬 여행", ["산토리니", "미코노스", "크레타 섬"]),
    ("국내 자연 생태 여행", ["순천만 갈대밭", "충남 서천 금강하구", "강원 철원 두루미 탐조"]),
    ("영국 여행", ["런던", "스코틀랜드 에든버러", "잉글랜드 코츠월드"]),
    ("국내 도보 여행", ["제주 올레길 1코스", "부산 갈맷길", "서울 둘레길"]),
    ("베트남 전국 일주", ["하노이 하롱베이", "다낭·호이안", "호치민 메콩델타"]),
]


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


def get_unsplash_image(keyword: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        return ""
    for kw in [keyword, "travel landscape scenic"]:
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
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


TRAVEL_PROMPT = """당신은 한국어 여행 전문 작가입니다. '{destination}'에 대한 완성도 높은 여행 가이드를 작성하세요.

오늘 날짜: {today}

**요구사항:**
- 독자: 한국인 여행자 (20~50대)
- 실용적이고 구체적인 정보 중심
- 현재 시점({year}년)에 유효한 정보
- 총 1200자 이상의 풍부한 내용
- 마크다운 형식으로 작성

**출력 형식 (반드시 이 순서대로):**

## {destination} 완벽 여행 가이드

### ✈️ 여행지 소개
(이 여행지의 매력과 특징, 어떤 여행자에게 추천하는지 200자 이상)

### 🗓️ 최적 여행 시기
(월별 날씨와 추천 시기, 성수기·비수기 정보)

### 🏛️ 꼭 가봐야 할 명소 TOP 5
(각 명소마다 간략한 설명 포함)
1. **명소명**: 설명
2. **명소명**: 설명
3. **명소명**: 설명
4. **명소명**: 설명
5. **명소명**: 설명

### 🍜 현지 음식 & 맛집
(꼭 먹어봐야 할 음식 3~5가지와 추천 식당 또는 먹는 방법)

### 💰 예산 가이드
(항공, 숙박, 식비, 관광 예산을 표로 정리)

| 항목 | 예산 (1인 기준) |
|------|----------------|
| 항공권 | |
| 숙박 (1박) | |
| 식비 (1일) | |
| 관광·입장료 | |
| 총 예상 비용 (3박 4일) | |

### 🚌 교통 & 이동
(현지에서 이동하는 방법, 공항에서 시내까지 방법)

### 💡 알아두면 좋은 팁

<details>
<summary>현지 언어 기본 표현</summary>
간단한 현지어 인사말과 유용한 표현 3~5개
</details>

<details>
<summary>여행 전 준비사항 체크리스트</summary>
비자, 환전, 필수 앱, 짐싸기 팁
</details>

<details>
<summary>주의사항 & 안전 팁</summary>
현지에서 주의해야 할 점, 바가지 예방, 안전 수칙
</details>

### ⭐ 추천 일정 (3박 4일 기준)
(간략한 날짜별 일정)

**1일차**: ...
**2일차**: ...
**3일차**: ...
**4일차**: ...

---
주의: 생각 과정(thinking)은 출력하지 마세요. 완성된 글만 출력하세요."""


def generate_travel_article(destination: str) -> dict | None:
    now = datetime.now(KST)
    today = now.strftime("%Y년 %m월 %d일")
    year = now.year

    prompt = TRAVEL_PROMPT.format(
        destination=destination,
        today=today,
        year=year,
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
        data = r.json()
        parts = data["candidates"][0]["content"]["parts"]
        content = "".join(
            p["text"] for p in parts if not p.get("thought", False)
        ).strip()

        if not content:
            print("  Gemini 응답 비어 있음")
            return None

        # Extract first H2 as title
        title = f"{destination} 완벽 여행 가이드"
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("## "):
                title = line.lstrip("#").strip()
                break

        # Extract summary from introduction paragraph
        summary = f"{destination}의 매력을 소개하는 완벽 여행 가이드입니다. 최적 시기, 명소, 맛집, 예산까지 한 번에 확인하세요."
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "여행지 소개" in line and i + 1 < len(lines):
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        summary = lines[j].strip()[:150]
                        break
                break

        content_html = markdown.markdown(
            content,
            extensions=["nl2br", "tables"]
        )
        return {"title": title, "summary": summary, "content": content_html}

    except Exception as e:
        print(f"  응답 파싱 오류: {e}")
        return None


def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY_3 없음")
        return

    now = datetime.now(KST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')} KST] 여행지 가이드 생성 시작")

    # 주차 기반으로 테마 선택
    week_num = now.isocalendar()[1]
    theme_idx = week_num % len(DESTINATION_THEMES)
    theme_name, destinations = DESTINATION_THEMES[theme_idx]
    print(f"이번 주 테마: {theme_name} | 목적지: {', '.join(destinations)}")

    travel_data = load_json(TRAVEL_FILE)
    latest_data = load_json(LATEST_FILE)

    for destination in destinations:
        print(f"\n[생성 중] {destination}")

        result = generate_travel_article(destination)
        if not result:
            print(f"  건너뜀: {destination}")
            continue

        # Unsplash 이미지
        image_url = get_unsplash_image(destination.split(" ")[-1])
        if not image_url:
            image_url = get_unsplash_image("travel destination scenery")
        print(f"  이미지: {'있음' if image_url else '없음'}")

        article_id = "travel_" + hashlib.md5(
            (destination + now.strftime("%Y-%W")).encode()
        ).hexdigest()[:12]

        pub_date = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")

        article = {
            "article_id":   article_id,
            "title":        result["title"],
            "summary":      result["summary"],
            "content":      result["content"],
            "image_url":    image_url,
            "category":     "여행지",
            "category_label": "여행지",
            "article_type": "travel_guide",
            "pub_date":     pub_date,
            "pubDate":      pub_date,
            "original_url": "",
            "source":       "AI 여행 가이드",
            "destination":  destination,
        }

        # Save to travelguide.json
        travel_data = [a for a in travel_data if a.get("article_id") != article_id]
        travel_data.insert(0, article)
        travel_data = travel_data[:200]
        save_json(TRAVEL_FILE, travel_data)

        # Append to latest.json
        latest_data = [a for a in latest_data if a.get("article_id") != article_id]
        latest_data.insert(0, article)
        latest_data = latest_data[:500]
        save_json(LATEST_FILE, latest_data)

        # DB 저장
        try:
            r = requests.post(
                SAVE_API_URL,
                json=article,
                headers={"X-Save-Secret": SAVE_SECRET, "Content-Type": "application/json"},
                timeout=15,
            )
            if r.status_code == 200:
                print(f"  [DB] 저장 완료")
            else:
                print(f"  [DB] 저장 실패: {r.status_code}")
        except Exception as e:
            print(f"  [DB] 오류 (무시): {e}")

        print(f"  완료: {result['title'][:50]}")
        time.sleep(5)  # API 호출 간격

    print("\n모든 여행지 가이드 생성 완료!")


if __name__ == "__main__":
    main()
