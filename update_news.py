# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml 을 읽어 hub-news.json 을 갱신하는 스크립트.
GitHub Actions 에서 30분마다 실행됨. 표준 라이브러리만 사용 (설치 불필요).

[2026-08 구조 변경]
AI 활용팁 자료도 노션 CONTENTS 데이터베이스에 등록되어 daoukiwoom.ai 안에서
열리도록 바뀌었다. 따라서 리포의 HTML 을 스캔하지 않고 sitemap 하나만 본다.
활용팁 판별은 노션 원본 제목의 "[활용팁] " 접두어로 한다.

[2026-08 날짜/정렬 수정] ★ 이번 수정의 핵심
구버전은 활용팁 자료의 날짜를 'git 최초 커밋일'로 잡아 항상 최신으로 올려줬다.
sitemap 기반으로 바꾸면서 그 기준이 사라지고, 대신 두 가지가 어긋났다.

  (1) 표시 날짜 : 시드로 넣은 2026-01-01 이 그대로 노출됨
                 → 기존 글이 전부 "2026-01-01" 로 보임
  (2) 정렬     : sitemap 의 lastmod 는 노션 '마지막 수정 시각'이라
                 오래된 글을 손대면 최신글로 올라오고, Super 가 모든 글에
                 같은 값을 주면 정렬 자체가 무의미해짐

그래서 '유효 날짜(effective date)' 개념을 도입했다.

  · 최초 발견일이 기록돼 있고 시드값이 아니면  → 그 날짜 사용 (진짜 발행일)
  · 시드값(2026-01-01)이거나 기록이 없으면     → lastmod 로 폴백 (구버전과 동일)

이렇게 하면 기존 글은 구버전과 똑같이 보이고, 앞으로 올라오는 글은
발행일 기준으로 정확히 정렬된다. news-first-seen.json 의 시드 날짜를
실제 발행일로 손수 채워 넣으면 기존 글도 즉시 정확해진다.

진단:  python update_news.py --diag     (파일을 쓰지 않고 상태만 출력)
"""

import html as html_lib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import (unquote, urlparse, urlsplit, urlunsplit,
                          parse_qsl, urlencode, quote)

SITEMAP_URL = os.environ.get("SITEMAP_URL", "https://daoukiwoom.ai/sitemap.xml")
OUTPUT_FILE = "hub-news.json"
FIRST_SEEN_FILE = "news-first-seen.json"

MAX_ITEMS = 8          # JSON 에 담을 최대 글 수 (위젯은 이 중 5개 표시)
SCAN_MULTIPLIER = 4    # 제목을 가져올 후보 수 = MAX_ITEMS * 이 값
FETCH_TITLES = True    # 활용팁 판별이 제목 접두어에 의존하므로 True 유지 필수

TIP_CATEGORY = "활용팁"
TIP_PREFIX_RE = re.compile(r"^\s*\[\s*활용팁\s*\]\s*")

RESERVE_TIP_SLOTS = 0  # 활용팁 자리를 최소 몇 개 보장할지. 0 이면 순수 최신순

# 위젯에서 뺄 키워드 (카테고리·URL·제목 어디든 걸리면 제외)
# '템플릿' — CONTENTS DB 의 "콘텐츠 템플릿" 같은 작성용 껍데기 페이지 제거
EXCLUDE_KEYWORDS = ["아카데미", "academy", "템플릿", "template"]

SEED_DATE = "2026-01-01"   # 기록 파일이 없을 때 기존 글에 붙였던 '과거 글' 표식

# 글 페이지 HTML 에서 발행일을 직접 긁어올지 여부 (가장 정확한 소스)
# 노션 CONTENTS DB 의 날짜 속성이 페이지에 렌더링되면 그 값을 쓴다.
# 못 찾으면 기록 → lastmod 순으로 자동 폴백하므로 켜 둬도 안전하다.
SCRAPE_PAGE_DATE = True

ADD_UTM = True
UTM_PARAMS = {
    "utm_source": "portal",
    "utm_medium": "widget",
    "utm_campaign": "ai_hub_news",
}

HEADERS = {"User-Agent": "DaouKiwoom-AXTeam-HubWidget/1.0 (internal)"}
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ------------------------------------------------------------------ 공통

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def today_kst():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9)))


def add_utm(url):
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@!$&'()*+,;=~-._")
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if ADD_UTM:
        for k, v in UTM_PARAMS.items():
            q.setdefault(k, v)
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(q), parts.fragment))


def canonical_url(url):
    """UTM 등 쿼리를 뗀 순수 URL (기록의 키)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


# ------------------------------------------------------------------ sitemap

def _parse_urlset(raw):
    root = ET.fromstring(raw)
    if root.tag.split("}")[-1] == "sitemapindex":     # 인덱스면 하위를 따라간다
        out = []
        for sm in root.findall("sm:sitemap", NS):
            loc = sm.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue
            print(f"sitemap index -> {loc.text.strip()}")
            try:
                out.extend(_parse_urlset(fetch(loc.text.strip())))
            except Exception as e:
                print(f"WARNING: 하위 sitemap 실패 {loc.text} ({e})", file=sys.stderr)
        return out

    entries = []
    for url_el in root.findall("sm:url", NS):
        loc_el = url_el.find("sm:loc", NS)
        mod_el = url_el.find("sm:lastmod", NS)
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        if not urlparse(loc).path.startswith("/contents/"):
            continue
        lastmod = mod_el.text.strip() if (mod_el is not None and mod_el.text) else ""
        entries.append((loc, lastmod))
    return entries


def get_sitemap_entries():
    return _parse_urlset(fetch(SITEMAP_URL))


# ------------------------------------------------------------------ 발행일 기록

def load_registry():
    """(registry, seeding). seeding=True 면 기록 파일이 없던 최초 실행."""
    if not os.path.isfile(FIRST_SEEN_FILE):
        return {}, True
    try:
        with open(FIRST_SEEN_FILE, encoding="utf-8") as f:
            return json.load(f), False
    except Exception as e:
        print(f"WARNING: {FIRST_SEEN_FILE} 파싱 실패({e}) -> 새로 생성", file=sys.stderr)
        return {}, True


def update_registry(registry, seeding, all_urls):
    """sitemap 전체 글을 기록에 등재."""
    today = today_kst().strftime("%Y-%m-%d")
    for url in all_urls:
        key = canonical_url(url)
        if key in registry:
            continue
        registry[key] = SEED_DATE if seeding else today
        if not seeding:
            print(f"new: 처음 발견한 글 ({today}) -> {unquote(urlparse(key).path)}")
    if seeding:
        print(f"{FIRST_SEEN_FILE} 최초 생성: 기존 {len(registry)}건을 과거 글로 시드")


def save_registry(registry):
    with open(FIRST_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2, sort_keys=True)


def effective_date(url, lastmod, registry):
    """★ 표시·정렬에 쓰는 날짜.

    우선순위
      ① 글 페이지에 렌더링된 발행일   ← 가장 정확 (SCRAPE_PAGE_DATE)
      ② news-first-seen.json 의 최초 발견일 (시드값 2026-01-01 제외)
      ③ sitemap 의 lastmod            ← 구버전과 동일한 폴백

    ①을 못 찾아도 ②③으로 자동으로 내려가므로 안전하다.
    ②를 실제 발행일로 손수 채워 넣으면 그 글부터 즉시 정확해진다.
    """
    page = fetch_page_date(url)                    # ① 페이지에 박힌 발행일
    if page:
        return page
    fs = registry.get(canonical_url(url), "")      # ② 최초 발견일 (시드 제외)
    if fs and fs != SEED_DATE:
        return fs
    return lastmod[:10] if lastmod else ""         # ③ sitemap 수정일


def order_key(url, lastmod, registry):
    """1순위 유효 날짜, 2순위 lastmod (동점자 처리). 둘 다 내림차순."""
    return (effective_date(url, lastmod, registry), lastmod or "")


# ------------------------------------------------------------------ 제목/항목

def slug_info(url):
    slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    slug = re.sub(r"-\d+$", "", slug)
    parts = slug.split("-", 1)
    category = parts[0] if parts else ""
    title = parts[1].replace("-", " ").strip() if len(parts) > 1 else slug.replace("-", " ")
    return category, title


def extract_title_from_html(html):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html)
    if not m:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html)
    if not m:
        return None
    title = html_lib.unescape(m.group(1)).strip()
    title = re.split(r"\s*[|–—-]\s*DAOUKIWOOM", title, flags=re.I)[0].strip()
    return title or None


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def extract_date_from_html(html):
    """글 페이지에서 발행일(YYYY-MM-DD)을 찾는다. 못 찾으면 None.

    오탐을 줄이려고 '날짜를 담을 만한 자리'만 순서대로 본다.
    본문 아무 데나 있는 숫자는 보지 않는다.
    """
    # (1) 표준 메타 태그
    m = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+'
                  r'content=["\'](\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)

    # (2) <time datetime="...">
    m = re.search(r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)

    # (3) 노션 날짜 속성이 렌더링된 영역 안에서만 탐색
    blocks = re.findall(
        r'class=["\'][^"\']*notion-(?:property__date|page__date|'
        r'collection-card__property--date)[^"\']*["\'][^>]*>(.{0,300})',
        html, re.S)
    for b in blocks:
        b = re.sub(r"<[^>]+>", " ", b)          # 내부 태그 제거 후 텍스트만 본다
        m = re.search(r'(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})\s*일?', b)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
        m = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', b)
        if m and m.group(1)[:3].lower() in _MONTHS:
            mo = _MONTHS[m.group(1)[:3].lower()]
            return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(2)):02d}"
    return None


_page_cache = {}


def fetch_page(url):
    """글 페이지 HTML 을 한 번만 받아 재사용 (제목 + 날짜 공용)."""
    if url not in _page_cache:
        try:
            _page_cache[url] = fetch(url).decode("utf-8", errors="ignore")
        except Exception:
            _page_cache[url] = ""
    return _page_cache[url]


def fetch_page_title(url):
    return extract_title_from_html(fetch_page(url))


def fetch_page_date(url):
    if not SCRAPE_PAGE_DATE:
        return None
    return extract_date_from_html(fetch_page(url))


def is_excluded(text):
    t = (text or "").lower()
    return any(k.lower() in t for k in EXCLUDE_KEYWORDS)


def build_item(url, lastmod, registry):
    if is_excluded(unquote(url)):                 # 제목 조회 전에 URL 로 1차 제외
        print(f"skip (excluded/url): {unquote(urlparse(url).path)}")
        return None

    slug_cat, rough_title = slug_info(url)
    title = (fetch_page_title(url) if FETCH_TITLES else None) or rough_title
    category = TIP_CATEGORY if TIP_PREFIX_RE.match(title) else slug_cat

    if is_excluded(category) or is_excluded(title):
        print(f"skip (excluded): {title}")
        return None

    return {
        "category": category,
        "title": title,
        "url": add_utm(url),
        "date": effective_date(url, lastmod, registry),
        "_sort": order_key(url, lastmod, registry),
    }


def pick(items, limit, reserve_tips):
    items = sorted(items, key=lambda it: it["_sort"], reverse=True)
    if reserve_tips <= 0:
        return items[:limit]
    top = items[:limit]
    need = reserve_tips - sum(1 for it in top if it["category"] == TIP_CATEGORY)
    if need <= 0:
        return top
    spare = [it for it in items[limit:] if it["category"] == TIP_CATEGORY][:need]
    if not spare:
        return top
    keep = [it for it in top if it["category"] == TIP_CATEGORY]
    others = [it for it in top if it["category"] != TIP_CATEGORY]
    others = others[:max(0, limit - len(keep) - len(spare))]
    print(f"reserve: 활용팁 {len(spare)}건을 끌어올림")
    return sorted(keep + spare + others, key=lambda it: it["_sort"], reverse=True)


# ------------------------------------------------------------------ 진단

def diagnose(entries, registry):
    mods = [m for _, m in entries]
    distinct = len(set(mods))
    print("\n===== sitemap 진단 =====")
    print(f"/contents/ 글 수      : {len(entries)}")
    print(f"lastmod 서로 다른 값  : {distinct}")
    print(f"lastmod 비어 있는 항목: {sum(1 for m in mods if not m)}")
    if len(entries) > 1 and distinct <= 1:
        print("WARNING: 모든 글의 lastmod 가 동일합니다 → lastmod 만으로는 최신순 불가.\n"
              "         news-first-seen.json 의 시드 날짜를 실제 발행일로 채우세요.",
              file=sys.stderr)

    seeded = [u for u, _ in entries
              if registry.get(canonical_url(u)) == SEED_DATE]
    print(f"시드({SEED_DATE}) 상태 : {len(seeded)}건  ← 이 글들은 lastmod 로 폴백합니다")

    ranked = sorted(entries, key=lambda e: order_key(e[0], e[1], registry), reverse=True)
    print("\n--- 유효 날짜 기준 상위 10 ---")
    for u, m in ranked[:10]:
        fs = registry.get(canonical_url(u), "(미등재)")
        print(f"  유효 {effective_date(u, m, registry) or '(없음)'} "
              f"| 기록 {fs} | lastmod {m or '(없음)':<26} "
              f"| {unquote(urlparse(u).path)}")
    print("========================\n")


# ------------------------------------------------------------------ main

def main():
    diag_only = "--diag" in sys.argv

    entries = get_sitemap_entries()
    if not entries:
        print("ERROR: sitemap 에서 /contents/ 콘텐츠를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    # 후보를 자르기 '전에' 전체를 등재해야 새 글이 탈락하지 않는다
    registry, seeding = load_registry()
    update_registry(registry, seeding, [u for u, _ in entries])

    diagnose(entries, registry)
    if diag_only:
        print("(--diag: 파일을 쓰지 않고 종료합니다)")
        return

    save_registry(registry)

    ranked = sorted(entries, key=lambda e: order_key(e[0], e[1], registry), reverse=True)

    items = []
    for url, lastmod in ranked[:MAX_ITEMS * SCAN_MULTIPLIER]:
        it = build_item(url, lastmod, registry)
        if it:
            items.append(it)
            src_tag = ("page" if fetch_page_date(url)
                       else "기록" if registry.get(canonical_url(url), "") not in ("", SEED_DATE)
                       else "lastmod")
            print(f"item: [{it['category']}] {it['title']} ({it['date']} · {src_tag})")

    tips = sum(1 for it in items if it["category"] == TIP_CATEGORY)
    print(f"활용팁 {tips}건 확인" if tips else
          "WARNING: '[활용팁] ' 로 시작하는 글을 찾지 못했습니다.")

    items = pick(items, MAX_ITEMS, RESERVE_TIP_SLOTS)
    for it in items:
        it.pop("_sort", None)

    payload = {"updated": today_kst().isoformat(timespec="seconds"), "items": items}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(items)}건 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
