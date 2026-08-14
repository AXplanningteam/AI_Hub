# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml에서 최신 콘텐츠를 읽어 hub-news.json을 갱신하는 스크립트.
GitHub Actions에서 매일 실행됨. 표준 라이브러리만 사용 (별도 설치 불필요).
"""
import html as html_lib
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

# AI 활용팁 자료: 이 리포 안의 폴더(폴더명/index.html)로 올라오므로 리포를 직접 스캔
PAGES_BASE = "https://axplanningteam.github.io/AI_Hub/"
TIP_CATEGORY = "활용팁"
# 자료 폴더가 아닌 폴더 (스캔 제외)
SKIP_DIRS = {".github", ".git", "scripts"}

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
    return extract_title_from_html(html)


def extract_title_from_html(html):
    """HTML 문자열에서 og:title 또는 <title> 추출."""
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html)
    if not m:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html)
    if not m:
        return None
    title = html_lib.unescape(m.group(1)).strip()
    title = re.split(r"\s*[|\u2013\u2014-]\s*DAOUKIWOOM", title, flags=re.I)[0].strip()
    return title or None


def git_first_commit_date(path):
    """해당 경로가 처음 등록된 커밋 날짜(ISO)를 반환. 실패 시 빈 문자열.
    최초 커밋 기준이라 이후 오타 수정 등으로는 날짜가 안 바뀜."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--format=%cI", "--", path],
            capture_output=True, text=True, timeout=20,
        )
        lines = out.stdout.strip().splitlines()
        return lines[0] if lines else ""
    except Exception:
        return ""


def get_tip_items():
    """리포 안에서 index.html을 가진 폴더 = AI 활용팁 자료.
    AI_Tip/자료명/index.html 같은 중첩 구조를 포함해 재귀적으로 탐색."""
    import os
    items = []
    for dirpath, dirnames, filenames in os.walk("."):
        # 숨김 폴더·시스템 폴더는 탐색에서 제외
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS
        )
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, ".").replace(os.sep, "/")
        if rel == ".":
            continue  # 리포 루트의 index.html은 자료가 아님
        index_path = os.path.join(dirpath, "index.html")
        try:
            with open(index_path, encoding="utf-8", errors="ignore") as f:
                title = extract_title_from_html(f.read())
        except Exception:
            title = None
        date = git_first_commit_date(rel)
        folder_name = rel.rsplit("/", 1)[-1]
        items.append({
            "category": TIP_CATEGORY,
            "title": f"[{TIP_CATEGORY}] " + (title or folder_name.replace("-", " ")),
            "url": PAGES_BASE + rel + "/",
            "date": date[:10] if date else "",
            "_sort": date or "",
        })
        print(f"tip: {items[-1]['title']} -> {items[-1]['url']}")
    return items


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

    # 1) 허브 사이트 글 (sitemap 기준, 위젯 표시분 이상만 수집)
    site_items = []
    for url, lastmod in entries:
        if len(site_items) >= MAX_ITEMS:
            break
        category, rough_title = slug_info(url)
        if is_excluded(category, url):
            print(f"skip (excluded): {url}")
            continue
        title = fetch_page_title(url) if FETCH_TITLES else None
        site_items.append({
            "category": category,
            "title": title or rough_title,
            "url": url,
            "date": lastmod[:10] if lastmod else "",
            "_sort": lastmod or "",
        })
        print(f"site: [{category}] {site_items[-1]['title']} ({site_items[-1]['date']})")

    # 2) AI 활용팁 자료 (리포 폴더 스캔)
    tip_items = get_tip_items()

    # 3) 병합 후 최신순 상위 N개
    items = site_items + tip_items
    items.sort(key=lambda it: it["_sort"], reverse=True)
    items = items[:MAX_ITEMS]
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
