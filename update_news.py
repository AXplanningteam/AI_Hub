# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml 을 읽어 hub-news.json 을 갱신하는 스크립트.
GitHub Actions 에서 30분마다 실행됨. 표준 라이브러리만 사용 (설치 불필요).

[2026-08 구조 변경]
AI 활용팁 자료도 노션 CONTENTS 데이터베이스에 등록되어
daoukiwoom.ai 안에서 열리도록 바뀌었다.
→ 사내포털 위젯이 가리키는 주소도 github.io 가 아니라 daoukiwoom.ai 다.
→ 따라서 이 스크립트는 더 이상 리포의 HTML 을 스캔하지 않고,
   sitemap 하나만 보면 된다. (활용팁도 sitemap 에 함께 들어옴)

  · 제거: 리포 스캔 / ai-tip-cards.json / GA4 태그 검사 / git 커밋일 조회
  · 활용팁 판별: 노션 원본 제목의 "[활용팁] " 접두어
  · UTM 이 이제 GA4 가 붙은 도메인(daoukiwoom.ai)에 그대로 도착하므로
    사내포털 유입이 정상 집계된다 (예전 github.io 는 교차도메인이라 끊겼음)
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

SITEMAP_URL = "https://daoukiwoom.ai/sitemap.xml"
OUTPUT_FILE = "hub-news.json"
FIRST_SEEN_FILE = "news-first-seen.json"   # 글별 "처음 발견한 날" 기록 (N 배지 판정용)

MAX_ITEMS = 8          # JSON 에 담을 최대 글 수 (위젯은 이 중 5개 표시)
FETCH_TITLES = True    # 각 글 페이지에서 정확한 제목(og:title)을 가져올지 여부
                       # ※ 활용팁 판별이 제목 접두어에 의존하므로 True 유지 필수

TIP_CATEGORY = "활용팁"
TIP_PREFIX_RE = re.compile(r"^\s*\[\s*활용팁\s*\]\s*")

# 활용팁 자리를 최소 몇 개 보장할지. 0 이면 순수 최신순.
# 일반 콘텐츠가 몰리는 날에도 활용팁을 위젯에 남기고 싶으면 1~2 로.
RESERVE_TIP_SLOTS = 0

# 위젯뿐 아니라 JSON 단계에서도 제외할 카테고리/경로 키워드
EXCLUDE_KEYWORDS = ["아카데미", "academy"]

# ===== 사내포털 유입 측정 =====
ADD_UTM = True                     # False 로 두면 UTM 부착 안 함
UTM_PARAMS = {
    "utm_source": "portal",
    "utm_medium": "widget",
    "utm_campaign": "ai_hub_news",
}

HEADERS = {"User-Agent": "DaouKiwoom-AXTeam-HubWidget/1.0 (internal)"}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def add_utm(url):
    """URL 에 UTM 파라미터를 붙인다. 이미 있는 파라미터는 덮어쓰지 않는다."""
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@!$&'()*+,;=~-._")
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if ADD_UTM:
        for k, v in UTM_PARAMS.items():
            q.setdefault(k, v)
    return urlunsplit((parts.scheme, parts.netloc, path,
                       urlencode(q), parts.fragment))


def get_sitemap_entries():
    """sitemap 에서 /contents/ 하위 글 목록을 (url, lastmod) 리스트로 반환."""
    raw = fetch(SITEMAP_URL)
    root = ET.fromstring(raw)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entries = []
    for url_el in root.findall("sm:url", ns):
        loc_el = url_el.find("sm:loc", ns)
        mod_el = url_el.find("sm:lastmod", ns)
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        path = urlparse(loc).path
        if not path.startswith("/contents/"):
            continue
        lastmod = mod_el.text.strip() if (mod_el is not None and mod_el.text) else ""
        entries.append((loc, lastmod))
    return entries


def slug_info(url):
    """URL 슬러그를 디코딩해 (카테고리, 대략적 제목) 추출. 제목을 못 가져올 때의 폴백."""
    slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    slug = re.sub(r"-\d+$", "", slug)
    parts = slug.split("-", 1)
    category = parts[0] if parts else ""
    title = parts[1].replace("-", " ").strip() if len(parts) > 1 else slug.replace("-", " ")
    return category, title


def fetch_page_title(url):
    """글 페이지의 og:title 또는 <title> 에서 정확한 제목을 가져옴. 실패 시 None."""
    try:
        html = fetch(url).decode("utf-8", errors="ignore")
    except Exception:
        return None
    return extract_title_from_html(html)


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


def canonical_url(url):
    """UTM 등 쿼리를 뗀 순수 URL (최초 목격일 기록의 키)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def apply_first_seen(items, all_urls):
    """N 배지 판정용 날짜를 '작성일(최초 발견일)'로 교체.

    sitemap 의 lastmod 는 수정일이라 작성일 기준 배지 판정에 쓸 수 없다.
    대신 이 스크립트가 30분마다 돌며 sitemap "전체" 글을 FIRST_SEEN_FILE 에 기록한다.
    → 새 글은 발행 후 30분 안에 발견되므로, 최초 발견일 = 사실상 작성일.

    - 기록에 있는 글 : 기록된 작성일 사용 (이후 수정돼도 절대 안 바뀜)
    - 기록에 없는 글 : 오늘 기록 → 작성 후 7일간 N 배지
    - 기록 파일이 없는 최초 실행 : 현재 sitemap 의 모든 글을 '과거 글'로 시드
    * 정렬(_sort)은 계속 lastmod 기준이라 목록 순서는 그대로다.
    """
    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime("%Y-%m-%d")

    seeding = not os.path.isfile(FIRST_SEEN_FILE)
    registry = {}
    if not seeding:
        try:
            with open(FIRST_SEEN_FILE, encoding="utf-8") as f:
                registry = json.load(f)
        except Exception as e:
            print(f"WARNING: {FIRST_SEEN_FILE} 파싱 실패({e}) -> 새로 생성", file=sys.stderr)
            registry = {}

    for url in all_urls:
        key = canonical_url(url)
        if key in registry:
            continue
        registry[key] = "2026-01-01" if seeding else today
        if not seeding:
            print(f"new: 처음 발견한 글 -> {key}")

    for it in items:
        it["date"] = registry.get(canonical_url(it["url"]), it["date"])

    with open(FIRST_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2, sort_keys=True)

    if seeding:
        print(f"{FIRST_SEEN_FILE} 최초 생성: 기존 {len(registry)}건을 과거 글로 시드")
    return items


def is_excluded(category, url):
    text = (category + " " + url).lower()
    return any(k.lower() in text for k in EXCLUDE_KEYWORDS)


def build_item(url, lastmod):
    """sitemap 항목 하나를 hub-news 항목으로 변환. 제외 대상이면 None."""
    slug_cat, rough_title = slug_info(url)
    title = (fetch_page_title(url) if FETCH_TITLES else None) or rough_title

    # 활용팁 판별: 노션 원본 제목의 "[활용팁] " 접두어
    if TIP_PREFIX_RE.match(title):
        category = TIP_CATEGORY
    else:
        category = slug_cat

    if is_excluded(category, url):
        print(f"skip (excluded): {url}")
        return None

    return {
        "category": category,
        "title": title,
        "url": add_utm(url),
        "date": lastmod[:10] if lastmod else "",
        "_sort": lastmod or "",
    }


def pick(items, limit, reserve_tips):
    """최신순 상위 limit 개. reserve_tips > 0 이면 활용팁 자리를 그만큼 보장."""
    items = sorted(items, key=lambda it: it["_sort"], reverse=True)
    if reserve_tips <= 0:
        return items[:limit]

    top = items[:limit]
    have = sum(1 for it in top if it["category"] == TIP_CATEGORY)
    need = reserve_tips - have
    if need <= 0:
        return top

    spare = [it for it in items[limit:] if it["category"] == TIP_CATEGORY][:need]
    if not spare:
        return top
    # 활용팁이 아닌 항목 중 가장 오래된 것부터 자리를 내준다
    keep = [it for it in top if it["category"] == TIP_CATEGORY]
    others = [it for it in top if it["category"] != TIP_CATEGORY]
    others = others[:max(0, limit - len(keep) - len(spare))]
    print(f"reserve: 활용팁 {len(spare)}건을 끌어올림")
    return sorted(keep + spare + others, key=lambda it: it["_sort"], reverse=True)


def main():
    entries = get_sitemap_entries()
    if not entries:
        print("ERROR: sitemap 에서 콘텐츠를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)
    entries.sort(key=lambda e: e[1], reverse=True)

    # 제목을 가져와야 활용팁을 판별할 수 있으므로, 넉넉히 훑고 나서 자른다
    scan_limit = MAX_ITEMS * 3
    items = []
    for url, lastmod in entries[:scan_limit]:
        it = build_item(url, lastmod)
        if it:
            items.append(it)
            print(f"item: [{it['category']}] {it['title']} ({it['date']})")

    tips = sum(1 for it in items if it["category"] == TIP_CATEGORY)
    if tips == 0:
        print("WARNING: '[활용팁] ' 로 시작하는 글을 sitemap 에서 찾지 못했습니다.\n"
              "         노션 CONTENTS DB 의 제목에 접두어가 남아 있는지,\n"
              "         해당 페이지가 Super 에 공개되어 sitemap 에 올라왔는지 확인하세요.",
              file=sys.stderr)
    else:
        print(f"활용팁 {tips}건 확인")

    # 배지 판정 날짜를 작성일(최초 발견일)로 교체 (sitemap 전체 등재)
    items = apply_first_seen(items, [u for u, _ in entries])

    items = pick(items, MAX_ITEMS, RESERVE_TIP_SLOTS)
    for it in items:
        it.pop("_sort", None)

    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    payload = {
        "updated": datetime.now(kst).isoformat(timespec="seconds"),
        "items": items,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(items)}건 저장 -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
