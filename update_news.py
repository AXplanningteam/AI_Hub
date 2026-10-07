# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml 을 읽어 hub-news.json 을 갱신하는 스크립트.
GitHub Actions 에서 30분마다 실행됨. 표준 라이브러리만 사용 (설치 불필요).

[2026-08 구조 변경]
AI 활용팁 자료도 노션 CONTENTS 데이터베이스에 등록되어 daoukiwoom.ai 안에서
열리도록 바뀌었다. 따라서 리포의 HTML 을 스캔하지 않고 sitemap 하나만 본다.

[2026-08 날짜/정렬]
'유효 날짜(effective date)' 를 쓴다.
  ① 글 페이지에 렌더링된 발행일   ← 가장 정확
  ② news-first-seen.json 의 최초 발견일 (시드값 2026-01-01 제외)
  ③ sitemap 의 lastmod            ← 폴백

[2026-10-07 수정] ★ 이번 변경
(1) 제외 판단을 '주소'가 아니라 '제목'으로 바꿨다.
    노션에서 「콘텐츠 템플릿」 페이지를 복제해 글을 쓰면 제목만 바뀌고
    슬러그는 '콘텐츠-템플릿-N' 으로 굳는다. Super 는 제목을 바꿔도 URL 을
    따라 바꾸지 않는다. 그래서 주소에 '템플릿'이 들어간다는 이유로
    멀쩡한 글이 조용히 사라졌다.
      실제 사고: 2026-10-01 「[AX 피플] 일주일은 걸리던 시장 조사…」
                 주소가 /contents/콘텐츠-템플릿-3 이라 위젯에서 누락
    또한 '포함'이 아니라 '시작'으로 바꿨다. 포함으로 두면
    「[활용팁] 프롬프트 템플릿 만들기」 같은 정상 글도 걸린다.

(2) 카테고리를 제목의 대괄호에서 뽑는다.
    슬러그에서 뽑으면 위와 같은 글이 'ax' 나 '콘텐츠' 로 잡힌다.
    제목이 「[AX 피플] …」 이므로 거기서 꺼내는 편이 정확하다.
    이 변경만 되돌리려면 category_of() 를 slug_cat 반환으로 바꾸면 된다.

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
FETCH_TITLES = True    # 제외·카테고리 판단이 제목에 의존하므로 True 유지 필수

TIP_CATEGORY = "활용팁"
TIP_PREFIX_RE = re.compile(r"^\s*\[\s*활용팁\s*\]\s*")

# 제목 맨 앞 대괄호에서 카테고리를 꺼낸다.  "[AX 피플] 제목" -> "AX 피플"
TITLE_CAT_RE = re.compile(r"^\s*\[\s*([^\]]+?)\s*\]")

RESERVE_TIP_SLOTS = 0  # 활용팁 자리를 최소 몇 개 보장할지. 0 이면 순수 최신순

# ── 위젯에서 뺄 것 ────────────────────────────────────────────────
# ① 카테고리로 제외 (제목 대괄호 또는 슬러그 첫 조각)
EXCLUDE_CATEGORIES = ["아카데미", "academy", "AI 아카데미"]

# ② 작성용 껍데기 페이지 — '제목'으로 판단한다. 주소로 판단하면 안 된다.
#    '포함'이 아니라 '시작'이어야 정상 글이 걸리지 않는다.
EXCLUDE_TITLE_PREFIXES = ["콘텐츠 템플릿", "콘텐츠-템플릿", "템플릿"]

SEED_DATE = "2026-01-01"   # 기록 파일이 없을 때 기존 글에 붙였던 '과거 글' 표식

# 글 페이지 HTML 에서 발행일을 직접 긁어올지 여부 (가장 정확한 소스)
SCRAPE_PAGE_DATE = True

ADD_UTM = True
UTM_PARAMS = {
    "utm_source": "portal",
    "utm_medium": "widget",
    "utm_campaign": "ai_hub",
    "utm_content": "news_list",
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
    """표시·정렬에 쓰는 날짜.  ① 페이지 발행일 → ② 최초 발견일 → ③ lastmod"""
    page = fetch_page_date(url)
    if page:
        return page
    fs = registry.get(canonical_url(url), "")
    if fs and fs != SEED_DATE:
        return fs
    return lastmod[:10] if lastmod else ""


def order_key(url, lastmod, registry):
    """1순위 유효 날짜, 2순위 lastmod (동점자 처리). 둘 다 내림차순."""
    return (effective_date(url, lastmod, registry), lastmod or "")


# ------------------------------------------------------------------ 제목/항목

def slug_info(url):
    """슬러그에서 (카테고리, 대략적 제목). 제목을 못 가져올 때의 폴백."""
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
    오탐을 줄이려고 '날짜를 담을 만한 자리'만 순서대로 본다."""
    m = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+'
                  r'content=["\'](\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)

    m = re.search(r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)

    blocks = re.findall(
        r'class=["\'][^"\']*notion-(?:property__date|page__date|'
        r'collection-card__property--date)[^"\']*["\'][^>]*>(.{0,300})',
        html, re.S)
    for b in blocks:
        b = re.sub(r"<[^>]+>", " ", b)
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


def category_of(title, slug_cat):
    """카테고리는 제목의 대괄호에서. 없으면 슬러그 첫 조각으로 폴백.
    (슬러그는 템플릿 복제 등으로 제목과 어긋날 수 있어 신뢰도가 낮다)"""
    m = TITLE_CAT_RE.match(title or "")
    return m.group(1).strip() if m else slug_cat


def is_excluded(url, title, category):
    """제외 판단. 주소가 아니라 제목·카테고리로 한다."""
    cat = (category or "").strip().lower()
    if cat in [c.lower() for c in EXCLUDE_CATEGORIES]:
        return True

    slug_first = unquote(urlparse(url).path.rsplit("/", 1)[-1]).split("-")[0].lower()
    if slug_first in [c.lower() for c in EXCLUDE_CATEGORIES]:
        return True

    t = (title or "").strip()
    return any(t.startswith(p) for p in EXCLUDE_TITLE_PREFIXES)


def build_item(url, lastmod, registry):
    slug_cat, rough_title = slug_info(url)
    title = (fetch_page_title(url) if FETCH_TITLES else None) or rough_title
    category = category_of(title, slug_cat)

    if is_excluded(url, title, category):
        print(f"skip (excluded): {title}  <- {unquote(urlparse(url).path)}")
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
        print("WARNING: 모든 글의 lastmod 가 동일합니다 → lastmod 만으로는 최신순 불가.",
              file=sys.stderr)

    seeded = [u for u, _ in entries if registry.get(canonical_url(u)) == SEED_DATE]
    print(f"시드({SEED_DATE}) 상태 : {len(seeded)}건  ← 이 글들은 lastmod 로 폴백합니다")

    # sitemap 에 없는데 기록에만 남은 키 (슬러그 변경·삭제의 흔적)
    live = {canonical_url(u) for u, _ in entries}
    orphan = [k for k in registry if k not in live]
    if orphan:
        print(f"\n기록에만 남은 글    : {len(orphan)}건 (슬러그 변경·삭제 추정)")
        for k in orphan[:5]:
            print(f"  - {unquote(urlparse(k).path)}")
        if len(orphan) > 5:
            print(f"  … 외 {len(orphan) - 5}건")

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
