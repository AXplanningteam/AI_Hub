# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml에서 최신 콘텐츠를 읽어 hub-news.json을 갱신하는 스크립트.
GitHub Actions에서 매일 실행됨. 표준 라이브러리만 사용 (별도 설치 불필요).
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

SITEMAP_URL = "https://daoukiwoom.ai/sitemap.xml"
OUTPUT_FILE = "hub-news.json"
MAX_ITEMS = 8          # JSON에 담을 최대 글 수 (위젯은 이 중 5개 표시)
FETCH_TITLES = True    # 각 글 페이지에서 정확한 제목(og:title)을 가져올지 여부

# 위젯뿐 아니라 JSON 단계에서도 제외할 카테고리/경로 키워드
EXCLUDE_KEYWORDS = ["아카데미", "academy"]

HEADERS = {"User-Agent": "DaouKiwoom-AXTeam-HubWidget/1.0 (internal)"}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_sitemap_entries():
    """sitemap에서 /contents/ 하위 글 목록을 (url, lastmod) 리스트로 반환."""
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
        # 개별 글만: /contents/슬러그 (섹션 페이지 /contents 자체는 제외)
        if not path.startswith("/contents/"):
            continue
        lastmod = mod_el.text.strip() if (mod_el is not None and mod_el.text) else ""
        entries.append((loc, lastmod))
    return entries


def slug_info(url):
    """URL 슬러그를 디코딩해 (카테고리, 대략적 제목)을 추출."""
    slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    # 뒤에 붙는 -1, -2 같은 중복 방지 숫자 제거
    slug = re.sub(r"-\d+$", "", slug)
    parts = slug.split("-", 1)
    category = parts[0] if parts else ""
    title = parts[1].replace("-", " ").strip() if len(parts) > 1 else slug.replace("-", " ")
    return category, title


def fetch_page_title(url):
    """글 페이지의 og:title 또는 <title>에서 정확한 제목을 가져옴. 실패 시 None."""
    try:
        html = fetch(url).decode("utf-8", errors="ignore")
    except Exception:
        return None
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html)
    if not m:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html)
    if not m:
        return None
    title = m.group(1).strip()
    # "제목 | DAOUKIWOOM AI HUB" 같은 사이트명 꼬리 제거
    title = re.split(r"\s*[|\u2013\u2014-]\s*DAOUKIWOOM", title, flags=re.I)[0].strip()
    return title or None


def is_excluded(category, url):
    text = (category + " " + url).lower()
    return any(k.lower() in text for k in EXCLUDE_KEYWORDS)


def main():
    entries = get_sitemap_entries()
    if not entries:
        print("ERROR: sitemap에서 콘텐츠를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    # 최신순 정렬 (lastmod 없는 항목은 뒤로)
    entries.sort(key=lambda e: e[1], reverse=True)

    items = []
    for url, lastmod in entries:
        if len(items) >= MAX_ITEMS:
            break
        category, rough_title = slug_info(url)
        if is_excluded(category, url):
            print(f"skip (excluded): {url}")
            continue
        title = fetch_page_title(url) if FETCH_TITLES else None
        items.append({
            "category": category,
            "title": title or rough_title,
            "url": url,
            "date": lastmod[:10] if lastmod else "",
        })
        print(f"add: [{category}] {items[-1]['title']} ({items[-1]['date']})")

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
