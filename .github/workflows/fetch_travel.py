#!/usr/bin/env python3
"""
여행지 소개 — AI 여행 가이드 생성기
2시간마다 1개 여행지 가이드 기사를 생성한다.
이미지: 한국관광공사 공식 API 우선, 없으면 Wikimedia Commons 폴백
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

GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY_3", "")
KTO_API_KEY        = os.environ.get("KTO_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
PIXABAY_API_KEY    = os.environ.get("PIXABAY_API_KEY", "")
PEXELS_API_KEY     = os.environ.get("PEXELS_API_KEY", "")
SAVE_SECRET        = os.environ.get("SAVE_SECRET", "nc_save_s3cr3t_2026")
SAVE_API_URL       = "https://newscommu.com/api/save_article.php"

DATA_DIR    = "data"
TRAVEL_FILE = os.path.join(DATA_DIR, "travelguide.json")
LATEST_FILE = os.path.join(DATA_DIR, "latest.json")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)
KTO_BASE = "https://apis.data.go.kr/B551011/KorService2"

# 전체 여행지 목록 (순환)
DEST_SLUG = {
    "제주도 동부 해안": "jeju-east-coast",
    "제주 서귀포 올레길": "jeju-seogwipo-olle",
    "제주 한라산 트레킹": "jeju-hallasan",
    "부산 해운대·광안리": "busan-haeundae",
    "부산 감천문화마을·태종대": "busan-gamcheon",
    "경주 불국사·석굴암": "gyeongju-bulguksa",
    "경주 동궁과 월지·첨성대": "gyeongju-donggung",
    "전주 한옥마을": "jeonju-hanok",
    "전주 한식 투어": "jeonju-food-tour",
    "여수 오동도·돌산도": "yeosu-odongdo",
    "여수 낭만포차거리": "yeosu-pocha",
    "통영 한려수도·미륵도": "tongyeong-hallyeo",
    "통영 케이블카·달아공원": "tongyeong-cablecar",
    "강릉 경포대·안목해변": "gangneung-gyeongpo",
    "강릉 커피거리·오죽헌": "gangneung-coffee",
    "속초 설악산·청초호": "sokcho-seoraksan",
    "강원 인제 내린천·백담사": "inje-naerin",
    "춘천 소양강댐·남이섬": "chuncheon-nami",
    "가평 청평호·잣향기 푸른숲": "gapyeong-chungpyung",
    "서울 경복궁·인사동": "seoul-gyeongbokgung",
    "서울 북촌한옥마을·창덕궁": "seoul-bukchon",
    "서울 한강공원·노을공원": "seoul-hangang",
    "서울 남산타워·이태원": "seoul-namsan",
    "인천 소래포구·월미도": "incheon-wolmido",
    "인천 강화도·전등사": "incheon-ganghwa",
    "공주·부여 백제역사유적": "baekje-heritage",
    "안동 하회마을·도산서원": "andong-hahoe",
    "순천만 갈대밭·낙안읍성": "suncheon-bay",
    "담양 죽녹원·메타세쿼이아길": "damyang-bamboo",
    "거제도 해금강·바람의 언덕": "geoje-haegumgang",
    "남해 독일마을·상주은모래비치": "namhae-german",
    "설악산 대청봉·비선대": "seoraksan-summit",
    "지리산 노고단·천왕봉": "jirisan-nogodan",
    "내장산 단풍": "naejangsan-autumn",
    "덕유산 향적봉·무주 리조트": "deogyusan-muju",
    "울릉도·독도": "ulleungdo-dokdo",
    "신안 1004섬·압해도": "shinan-islands",
    "태안 해안국립공원": "taean-coast",
    "충남 서산 마애삼존불·해미읍성": "seosan-heritage",
    "경북 청송 주왕산": "cheongsong-juwang",
    "경남 하동 십리벚꽃길": "hadong-cherry",
    "전남 구례 산수유마을": "gurye-sansuyu",
    "진해 군항제 벚꽃": "jinhae-cherry",
    "일본 도쿄 아사쿠사·시부야": "tokyo-asakusa-shibuya",
    "일본 교토 기온·아라시야마": "kyoto-gion-arashiyama",
    "일본 오사카 도톤보리·유니버설스튜디오": "osaka-dotonbori",
    "일본 홋카이도 삿포로": "hokkaido-sapporo",
    "일본 후쿠오카·나가사키": "fukuoka-nagasaki",
    "태국 방콕 왓포·왓아룬": "bangkok-temples",
    "태국 치앙마이 님만해민": "chiangmai-nimman",
    "태국 푸켓 빠통해변": "phuket-patong",
    "태국 코사무이": "koh-samui",
    "베트남 하노이 호안끼엠호수": "hanoi-hoan-kiem",
    "베트남 다낭·호이안": "danang-hoian",
    "베트남 호치민 벤탄시장·메콩델타": "hochiminh-mekong",
    "필리핀 세부·보홀": "cebu-bohol",
    "필리핀 팔라완 엘니도": "palawan-elnido",
    "인도네시아 발리 우붓·딴아롯사원": "bali-ubud",
    "인도네시아 롬복·길리": "lombok-gili",
    "대만 타이베이 지우펀·야류": "taipei-jiufen",
    "대만 타이중·타이난": "taichung-tainan",
    "홍콩 야경·빅토리아피크": "hongkong-victoria",
    "마카오 세나도광장·베네시안": "macau-senado",
    "싱가포르 마리나베이샌즈·가든스바이더베이": "singapore-marinabay",
    "말레이시아 쿠알라룸프르·페낭": "malaysia-kl-penang",
    "터키 이스탄불 블루모스크·그랜드바자르": "istanbul-bluemosque",
    "터키 카파도키아 열기구": "cappadocia-balloon",
    "그리스 산토리니·아테네": "greece-santorini",
    "그리스 미코노스·크레타": "greece-mykonos",
    "이탈리아 로마 콜로세움·트레비분수": "rome-colosseum",
    "이탈리아 피렌체·토스카나": "florence-tuscany",
    "이탈리아 베네치아·밀라노": "venice-milan",
    "프랑스 파리 에펠탑·루브르": "paris-eiffel",
    "프랑스 니스·몽생미셸": "france-nice-montsaintmichel",
    "스페인 바르셀로나 사그라다파밀리아": "barcelona-sagrada",
    "스페인 세비야·그라나다": "spain-sevilla-granada",
    "포르투갈 리스본·포르투": "lisbon-porto",
    "체코 프라하 카를교·구시가지": "prague-karlsbridge",
    "오스트리아 빈 쇤브룬궁전": "vienna-schoenbrunn",
    "헝가리 부다페스트 어부의요새": "budapest-fishermans",
    "스위스 인터라켄·융프라우": "interlaken-jungfrau",
    "독일 뮌헨·노이슈반슈타인성": "munich-neuschwanstein",
    "노르웨이 피오르·베르겐": "norway-fjord-bergen",
    "아이슬란드 오로라·레이캬비크": "iceland-aurora",
    "영국 런던 빅벤·버킹엄궁전": "london-bigben",
    "스코틀랜드 에든버러성": "edinburgh-castle",
    "모로코 마라케시 제마엘프나광장": "marrakech-jemaa",
    "이집트 카이로 피라미드": "cairo-pyramids",
    "남아공 케이프타운 테이블마운틴": "capetown-tablemountain",
    "미국 뉴욕 타임스스퀘어·센트럴파크": "newyork-timessquare",
    "미국 로스앤젤레스 할리우드": "la-hollywood",
    "미국 라스베이거스·그랜드캐니언": "lasvegas-grandcanyon",
    "미국 샌프란시스코 금문교": "sf-goldengate",
    "캐나다 밴쿠버·휘슬러": "vancouver-whistler",
    "캐나다 밴프 국립공원": "banff-national-park",
    "멕시코 칸쿤·툴룸": "cancun-tulum",
    "페루 마추픽추·쿠스코": "peru-machupicchu",
    "아랍에미리트 두바이 버즈칼리파": "dubai-burjkhalifa",
    "요르단 페트라": "jordan-petra",
    "인도 타지마할·자이푸르": "india-tajmahal",
    "네팔 카트만두·안나푸르나": "nepal-annapurna",
    "호주 시드니 오페라하우스·본다이비치": "sydney-opera",
    "호주 멜버른·그레이트오션로드": "melbourne-greatocean",
    "뉴질랜드 퀸즈타운·밀퍼드사운드": "queenstown-milford",
}

ALL_DESTINATIONS = [
    # 국내
    "제주도 동부 해안", "제주 서귀포 올레길", "제주 한라산 트레킹",
    "부산 해운대·광안리", "부산 감천문화마을·태종대",
    "경주 불국사·석굴암", "경주 동궁과 월지·첨성대",
    "전주 한옥마을", "전주 한식 투어",
    "여수 오동도·돌산도", "여수 낭만포차거리",
    "통영 한려수도·미륵도", "통영 케이블카·달아공원",
    "강릉 경포대·안목해변", "강릉 커피거리·오죽헌",
    "속초 설악산·청초호", "강원 인제 내린천·백담사",
    "춘천 소양강댐·남이섬", "가평 청평호·잣향기 푸른숲",
    "서울 경복궁·인사동", "서울 북촌한옥마을·창덕궁",
    "서울 한강공원·노을공원", "서울 남산타워·이태원",
    "인천 소래포구·월미도", "인천 강화도·전등사",
    "공주·부여 백제역사유적", "안동 하회마을·도산서원",
    "순천만 갈대밭·낙안읍성", "담양 죽녹원·메타세쿼이아길",
    "거제도 해금강·바람의 언덕", "남해 독일마을·상주은모래비치",
    "설악산 대청봉·비선대", "지리산 노고단·천왕봉",
    "내장산 단풍", "덕유산 향적봉·무주 리조트",
    "울릉도·독도", "신안 1004섬·압해도",
    "태안 해안국립공원", "충남 서산 마애삼존불·해미읍성",
    "경북 청송 주왕산", "경남 하동 십리벚꽃길",
    "전남 구례 산수유마을", "진해 군항제 벚꽃",
    # 해외
    "일본 도쿄 아사쿠사·시부야", "일본 교토 기온·아라시야마",
    "일본 오사카 도톤보리·유니버설스튜디오", "일본 홋카이도 삿포로",
    "일본 후쿠오카·나가사키",
    "태국 방콕 왓포·왓아룬", "태국 치앙마이 님만해민",
    "태국 푸켓 빠통해변", "태국 코사무이",
    "베트남 하노이 호안끼엠호수", "베트남 다낭·호이안",
    "베트남 호치민 벤탄시장·메콩델타",
    "필리핀 세부·보홀", "필리핀 팔라완 엘니도",
    "인도네시아 발리 우붓·딴아롯사원", "인도네시아 롬복·길리",
    "대만 타이베이 지우펀·야류", "대만 타이중·타이난",
    "홍콩 야경·빅토리아피크", "마카오 세나도광장·베네시안",
    "싱가포르 마리나베이샌즈·가든스바이더베이",
    "말레이시아 쿠알라룸프르·페낭",
    "터키 이스탄불 블루모스크·그랜드바자르", "터키 카파도키아 열기구",
    "그리스 산토리니·아테네", "그리스 미코노스·크레타",
    "이탈리아 로마 콜로세움·트레비분수", "이탈리아 피렌체·토스카나",
    "이탈리아 베네치아·밀라노",
    "프랑스 파리 에펠탑·루브르", "프랑스 니스·몽생미셸",
    "스페인 바르셀로나 사그라다파밀리아", "스페인 세비야·그라나다",
    "포르투갈 리스본·포르투",
    "체코 프라하 카를교·구시가지", "오스트리아 빈 쇤브룬궁전",
    "헝가리 부다페스트 어부의요새",
    "스위스 인터라켄·융프라우", "독일 뮌헨·노이슈반슈타인성",
    "노르웨이 피오르·베르겐", "아이슬란드 오로라·레이캬비크",
    "영국 런던 빅벤·버킹엄궁전", "스코틀랜드 에든버러성",
    "모로코 마라케시 제마엘프나광장", "이집트 카이로 피라미드",
    "남아공 케이프타운 테이블마운틴",
    "미국 뉴욕 타임스스퀘어·센트럴파크", "미국 로스앤젤레스 할리우드",
    "미국 라스베이거스·그랜드캐니언", "미국 샌프란시스코 금문교",
    "캐나다 밴쿠버·휘슬러", "캐나다 밴프 국립공원",
    "멕시코 칸쿤·툴룸", "페루 마추픽추·쿠스코",
    "아랍에미리트 두바이 버즈칼리파", "요르단 페트라",
    "인도 타지마할·자이푸르", "네팔 카트만두·안나푸르나",
    "호주 시드니 오페라하우스·본다이비치", "호주 멜버른·그레이트오션로드",
    "뉴질랜드 퀸즈타운·밀퍼드사운드",
]


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


def pick_destination(travel_data: list) -> str:
    """실행 시각 기반으로 아직 안 쓴 여행지를 선택"""
    now = datetime.now(KST)
    # 이미 발행된 여행지 제목에서 destination 추출
    done = {a.get("destination", "") for a in travel_data}

    # 시간 기반 오프셋으로 순서 섞기
    hour_offset = (now.day * 24 + now.hour) % len(ALL_DESTINATIONS)
    rotated = ALL_DESTINATIONS[hour_offset:] + ALL_DESTINATIONS[:hour_offset]

    for dest in rotated:
        if dest not in done:
            return dest

    # 전부 다 했으면 처음부터 다시
    return rotated[0]


# ---------------------------------------------------------------------------
# 해외 여행지 이미지: Unsplash / Pixabay / Pexels 랜덤 순환
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


def search_travel_image(keyword: str) -> str:
    """Unsplash/Pixabay/Pexels 랜덤 순환으로 이미지 검색"""
    sources = [search_unsplash_image, search_pixabay_image, search_pexels_image]
    random.shuffle(sources)
    for fn in sources:
        url = fn(keyword)
        if url:
            return url
    return ""


# ---------------------------------------------------------------------------
# 한국관광공사 API (국내 관광지 공식 이미지)
# ---------------------------------------------------------------------------

def get_kto_image(keyword: str) -> dict:
    """한국관광공사 API로 관광지 공식 이미지 조회"""
    empty = {"url": "", "credit": ""}
    if not KTO_API_KEY:
        return empty

    # URL 인코딩된 키는 requests가 자동 처리하므로 디코딩해서 사용
    key = unquote(KTO_API_KEY)

    try:
        # 키워드로 관광지 검색
        r = requests.get(
            f"{KTO_BASE}/searchKeyword2",
            params={
                "serviceKey": key,
                "numOfRows": 5,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "newscommu",
                "_type": "json",
                "keyword": keyword,
                "contentTypeId": 12,  # 관광지
            },
            timeout=10,
        )
        body = r.json().get("response", {}).get("body", {})
        items = body.get("items", {})
        if not items:
            return empty
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        if not item_list:
            return empty

        # 이미지 있는 항목 우선 선택, 없으면 랜덤
        candidates = [i for i in item_list if i.get("firstimage") or i.get("firstimage2")]
        first = random.choice(candidates) if candidates else random.choice(item_list)
        img_url = first.get("firstimage", "") or first.get("firstimage2", "")
        if img_url:
            return {
                "url": img_url,
                "credit": "한국관광공사",
            }

        # 대표 이미지 없으면 서브 이미지 조회
        content_id = first.get("contentid", "")
        if content_id:
            r2 = requests.get(
                f"{KTO_BASE}/detailImage2",
                params={
                    "serviceKey": key,
                    "numOfRows": 3,
                    "pageNo": 1,
                    "MobileOS": "ETC",
                    "MobileApp": "newscommu",
                    "_type": "json",
                    "contentId": content_id,
                    "imageYN": "Y",
                    "subImageYN": "Y",
                },
                timeout=10,
            )
            body2 = r2.json().get("response", {}).get("body", {})
            items2 = body2.get("items", {})
            if items2:
                imgs = items2.get("item", [])
                if isinstance(imgs, dict):
                    imgs = [imgs]
                if imgs and imgs[0].get("originimgurl"):
                    return {
                        "url": imgs[0]["originimgurl"],
                        "credit": "한국관광공사",
                    }
    except Exception as e:
        print(f"  KTO API 오류: {e}")

    return empty


def get_wikimedia_image(keyword: str) -> dict:
    """Wikimedia Commons 이미지 — CC0/CC BY/CC BY-SA만 허용 (NC/ND 제외)"""
    empty = {"url": "", "credit": ""}
    for kw in [keyword, "travel landscape scenic"]:
        try:
            resp = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrnamespace": 6,
                    "gsrsearch": kw,
                    "gsrlimit": 20,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata",
                    "iiurlwidth": 800,
                    "format": "json",
                },
                headers={"User-Agent": "newscommu.com/1.0 (across1211@gmail.com)"},
                timeout=15,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            candidates = []
            for page in pages.values():
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                meta = info.get("extmetadata", {})
                license_name = meta.get("LicenseShortName", {}).get("value", "")
                if not license_name:
                    continue
                ln_upper = license_name.upper()
                if "NC" in ln_upper or "ND" in ln_upper:
                    continue
                image_url = info.get("thumburl") or info.get("url", "")
                if not image_url:
                    continue
                if not re.search(r"\.(jpe?g|png|webp)", image_url, re.IGNORECASE):
                    continue
                artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
                is_free = any(x in ln_upper for x in ["CC0", "PUBLIC DOMAIN", "PD"])
                credit_text = None if is_free else (
                    f"{artist} ({license_name})" if artist else license_name
                )
                candidates.append({"url": image_url, "credit_text": credit_text, "license": license_name})
            if candidates:
                chosen = random.choice(candidates)
                return {
                    "url": chosen["url"],
                    "credit_text": chosen["credit_text"],
                    "credit": "wikimedia",
                }
        except Exception as e:
            print(f"  [Wikimedia] 오류: {e}")
    return empty


def get_best_image(destination: str) -> dict:
    """국내: KTO 우선 → Unsplash/Pixabay/Pexels / 해외: Unsplash/Pixabay/Pexels → Wikimedia"""
    is_domestic = not any(w in destination for w in [
        "일본", "태국", "베트남", "필리핀", "인도네시아", "대만", "홍콩", "마카오",
        "싱가포르", "말레이시아", "터키", "그리스", "이탈리아", "프랑스", "스페인",
        "포르투갈", "체코", "오스트리아", "헝가리", "스위스", "독일", "노르웨이",
        "아이슬란드", "영국", "스코틀랜드", "모로코", "이집트", "남아공",
        "미국", "캐나다", "멕시코", "페루", "아랍", "요르단", "인도", "네팔",
        "호주", "뉴질랜드",
    ])

    specific_kw = destination.split("·")[0].strip()
    city_kw     = specific_kw.split(" ")[0]

    if is_domestic and KTO_API_KEY:
        img = get_kto_image(specific_kw)
        if img["url"]:
            print(f"  이미지: KTO 공식 ({specific_kw})")
            return img
        img = get_kto_image(city_kw)
        if img["url"]:
            print(f"  이미지: KTO 공식 ({city_kw})")
            return img

    # 국내 KTO 실패 or 해외 → Unsplash/Pixabay/Pexels
    url = search_travel_image(specific_kw)
    if url:
        print(f"  이미지: Unsplash/Pixabay/Pexels ({specific_kw})")
        return {"url": url, "credit": ""}

    # 최후 폴백: Wikimedia
    img = get_wikimedia_image(specific_kw)
    if img["url"]:
        print(f"  이미지: Wikimedia Commons ({img.get('credit_text', 'CC0')})")
        return img

    print("  이미지: 없음")
    return {"url": "", "credit": ""}


# ---------------------------------------------------------------------------
# Gemini: 여행지 가이드 생성
# ---------------------------------------------------------------------------

TRAVEL_PROMPT = """당신은 한국어 여행 전문 작가입니다. '{destination}'에 대한 완성도 높은 여행 가이드를 작성하세요.

오늘 날짜: {today}

**요구사항:**
- 독자: 한국인 여행자 (20~50대)
- 실용적이고 구체적인 정보 중심
- 현재 시점({year}년)에 유효한 정보
- 총 1200자 이상의 풍부한 내용
- 마크다운 형식으로 작성

**출력 형식 (반드시 이 순서대로, h2/h3 구조 필수):**

제목: ({destination} 여행의 핵심을 담은 30자 이내 제목. 이모지 없이. 예: "서울 경복궁·인사동 완벽 가이드 — 역사와 맛을 한번에")

## ✈️ {destination} 소개
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

### 명소 4: (명소명)
(구체적인 설명, 관람 팁, 소요 시간)

### 명소 5: (명소명)
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
| 항공권/교통 | |
| 숙박 (1박) | |
| 식비 (1일) | |
| 관광·입장료 | |
| 총 예상 비용 (3박 4일) | |

### 🚌 교통 & 이동
(현지에서 이동하는 방법, 출발지에서 도착까지)

## 💡 알아두면 좋은 팁

<details>
<summary>현지 유용한 정보</summary>

- **언어**: (현지 언어 간단 소개, 영어 통용 여부)
- **환전**: (환전 방법, 추천 환율, 카드 사용 가능 여부)
- **유심/데이터**: (현지 유심 구매 방법, 추천 통신사)
- **필수 앱**: (지도, 교통, 번역 등 꼭 필요한 앱)
- **짐싸기 팁**: (날씨·문화에 맞는 필수 준비물)

</details>

<details>
<summary>주의사항 & 안전 팁</summary>

- **치안**: (안전한 지역과 주의할 지역)
- **문화 예절**: (현지에서 지켜야 할 예절과 금기사항)
- **건강**: (식수, 음식 주의사항, 예방접종 여부)
- **긴급 연락처**: (대사관, 경찰, 병원 번호)

</details>

## ⭐ 추천 일정

### 1일차
(오전·오후·저녁 일정 구체적으로)

### 2일차
(오전·오후·저녁 일정 구체적으로)

### 3일차
(오전·오후·저녁 일정 구체적으로)

### 4일차
(오전·오후·저녁 일정, 귀국 준비)

---
주의: 생각 과정(thinking)은 출력하지 마세요. 완성된 글만 출력하세요."""


def generate_travel_article(destination: str) -> dict | None:
    now = datetime.now(KST)
    prompt = TRAVEL_PROMPT.format(
        destination=destination,
        today=now.strftime("%Y년 %m월 %d일"),
        year=now.year,
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

        title = f"{destination} 완벽 여행 가이드"
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("제목:"):
                title = stripped[3:].strip()
                break
            if stripped.startswith("제목 :"):
                title = stripped[4:].strip()
                break
        # 이모지 제거 (유니코드 이모지 블록)
        title = re.sub(r'[\U0001F300-\U0001FFFF\U00002702-\U000027B0\U0000FE0F]+', '', title).strip()

        summary = f"{destination}의 매력을 소개하는 완벽 여행 가이드입니다."
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "여행지 소개" in line:
                for j in range(i + 1, min(i + 6, len(lines))):
                    t = lines[j].strip()
                    if t and not t.startswith("#"):
                        summary = t[:150]
                        break
                break

        # 제목: 줄은 본문에서 제거
        content_clean = "\n".join(
            l for l in content.splitlines()
            if not l.strip().startswith("제목:")
        )
        content_html = markdown.markdown(content_clean, extensions=["tables", "sane_lists"])
        return {"title": title, "summary": summary, "content": content_html}
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

    links_cache = load_links_cache()

    now = datetime.now(KST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M')} KST] 여행지 가이드 생성 시작")

    travel_data = load_json(TRAVEL_FILE)
    latest_data = load_json(LATEST_FILE)

    destination = pick_destination(travel_data)
    print(f"선택된 여행지: {destination}")

    result = generate_travel_article(destination)
    if not result:
        print("생성 실패")
        return

    img = get_best_image(destination)

    article_id = "travel_" + hashlib.md5(
        (destination + now.strftime("%Y-%m-%d-%H")).encode()
    ).hexdigest()[:12]
    pub_date = now.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    # 이미지 출처 필드 구성
    img_credit_type = img.get("credit", "")
    is_kto = img_credit_type == "한국관광공사"
    is_wikimedia = img_credit_type == "wikimedia"
    slug = DEST_SLUG.get(destination, "")
    if not slug:
        slug = "travel-" + article_id.replace("travel_", "")

    article = {
        "article_id":          article_id,
        "slug":                slug,
        "title":               result["title"],
        "summary":             result["summary"],
        "content":             insert_related_buttons(
                                   result["content"], links_cache,
                                   result["title"], result.get("summary", "")
                               ),
        "image_url":           img.get("url", ""),
        "image_credit":        img.get("credit_text", "") if is_wikimedia else "",
        "image_credit_name":   "한국관광공사" if is_kto else "",
        "image_credit_url":    "https://www.visitkorea.or.kr" if is_kto else "",
        "image_source":        "kto" if is_kto else ("wikimedia" if is_wikimedia else ""),
        "category":            "여행지",
        "category_label":      "여행지",
        "article_type":        "travel_guide",
        "pub_date":            pub_date,
        "pubDate":             pub_date,
        "original_url":        "",
        "source":              "AI 여행 가이드",
        "destination":         destination,
    }

    travel_data = [a for a in travel_data if a.get("article_id") != article_id]
    travel_data.insert(0, article)
    travel_data = travel_data[:300]
    save_json(TRAVEL_FILE, travel_data)

    latest_data = [a for a in latest_data if a.get("article_id") != article_id]
    latest_data.insert(0, article)
    latest_data = latest_data[:500]
    save_json(LATEST_FILE, latest_data)

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
