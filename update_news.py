# -*- coding: utf-8 -*-
"""
daoukiwoom.ai sitemap.xml + 이 리포의 AI 활용팁 자료를 읽어
hub-news.json을 갱신하는 스크립트. GitHub Actions에서 매일 실행됨.
표준 라이브러리만 사용 (별도 설치 불필요).

[2026-08 변경]
- 사내포털 유입 측정을 위해 URL에 UTM 파라미터 자동 부착
- 자료 HTML에 GA4 태그가 빠졌는지 검사해 경고 출력
- 경로에 앞뒤 공백이 섞인 폴더/파일 검출 경고
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
MAX_ITEMS = 8          # JSON에 담을 최대 글 수 (위젯은 이 중 5개 표시)
FETCH_TITLES = True    # 각 글 페이지에서 정확한 제목(og:title)을 가져올지 여부

PAGES_BASE = "https://axplanningteam.github.io/AI_Hub/"
TIP_CATEGORY = "활용팁"

# 활용팁 카드 목록 (공식 소스): 여기 등록된 자료만 위젯에 노출
TIP_CARDS_FILE = "ai-tip-cards.json"

# (폴백용) 단일 HTML 자료를 모아두는 폴더 (AI_Tip/자료명.html)
TIP_DIRS = ["AI_Tip"]

# 자료 폴더가 아닌 폴더 (스캔 제외)
SKIP_DIRS = {".github", ".git", "scripts", "node_modules"}

# 위젯뿐 아니라 JSON 단계에서도 제외할 카테고리/경로 키워드
EXCLUDE_KEYWORDS = ["아카데미", "academy"]

# ===== 사내포털 유입 측정 =====
GA4_ID = "G-VFLVE5CVHM"          # 자료 HTML에 심겨 있어야 하는 측정 ID
ADD_UTM = True                    # False로 두면 UTM 부착 안 함
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
    """URL에 UTM 파라미터를 붙인다. 이미 있는 파라미터는 덮어쓰지 않는다.
    경로에 공백 등이 섞여 있으면 인코딩해 링크가 깨지지 않게 한다."""
    parts = urlsplit(url)
    # 이미 인코딩된 경로(%xx)는 그대로 두고, 공백 등 미인코딩 문자만 처리
    path = quote(parts.path, safe="/%:@!$&'()*+,;=~-._")
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if ADD_UTM:
        for k, v in UTM_PARAMS.items():
            q.setdefault(k, v)
    return urlunsplit((parts.scheme, parts.netloc, path,
                       urlencode(q), parts.fragment))


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
        if not path.startswith("/contents/"):
            continue
        lastmod = mod_el.text.strip() if (mod_el is not None and mod_el.text) else ""
        entries.append((loc, lastmod))
    return entries


def slug_info(url):
    """URL 슬러그를 디코딩해 (카테고리, 대략적 제목)을 추출."""
    slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
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
    title = re.split(r"\s*[|–—-]\s*DAOUKIWOOM", title, flags=re.I)[0].strip()
    return title or None


def git_last_commit_date(path):
    """해당 경로의 마지막 커밋 날짜(ISO). 실패 시 빈 문자열."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", path],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def git_first_commit_date(path):
    """해당 경로가 처음 등록된 커밋 날짜(ISO). 실패 시 빈 문자열."""
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


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def make_tip_item(file_path, url, fallback_name):
    """자료 파일 하나를 hub-news 항목으로 변환."""
    title = extract_title_from_html(read_text(file_path))
    date = git_first_commit_date(file_path)
    return {
        "category": TIP_CATEGORY,
        "title": f"[{TIP_CATEGORY}] " + (title or fallback_name.replace("-", " ")),
        "url": add_utm(url),
        "date": date[:10] if date else "",
        "_sort": date or "",
        "_path": file_path,
    }


def warn_bad_path(rel):
    """경로 구성요소에 앞뒤 공백이 있으면 경고 (URL 404의 흔한 원인)."""
    for seg in rel.split("/"):
        if seg != seg.strip():
            print(f"WARNING: 경로에 공백이 있습니다 -> '{rel}' (세그먼트: '{seg}')", file=sys.stderr)
            return True
    return False


def get_tip_items():
    """AI 활용팁 자료 수집.
    1순위: ai-tip-cards.json (활용팁 페이지 카드 목록 = 공식 소스)
    폴백 : 카드 JSON이 없거나 깨졌으면 리포 스캔."""
    if os.path.isfile(TIP_CARDS_FILE):
        return get_tip_items_from_cards()
    return get_tip_items_from_scan()


def get_tip_items_from_cards():
    """카드 JSON의 각 항목을 hub-news 항목으로 변환.
    카드의 path(실제 파일/폴더 경로)를 우선 사용, 없으면 slug.
    - path가 .html로 끝나면 단일 파일 자료 (예: AI_Tip/gemini-hallucination.html)
    - 아니면 폴더형 자료 (예: sovereign-ai -> .../sovereign-ai/)
    카드에 없는 파일(test.html 등)은 위젯에 노출되지 않음."""
    try:
        with open(TIP_CARDS_FILE, encoding="utf-8") as f:
            cards = json.load(f)
    except Exception as e:
        print(f"WARNING: {TIP_CARDS_FILE} 파싱 실패({e}) -> 리포 스캔으로 폴백", file=sys.stderr)
        return get_tip_items_from_scan()
    if not isinstance(cards, list):
        cards = cards.get("items", [])

    items = []
    for card in cards:
        ref = (card.get("path") or card.get("slug") or "").strip().strip("/")
        title = (card.get("title") or "").strip()
        if not ref or not title:
            continue
        warn_bad_path(ref)
        if ref.endswith(".html"):
            url = PAGES_BASE + ref
            local = ref
        else:
            url = PAGES_BASE + ref + "/"
            local = ref + "/index.html"
        # 자료 등록일 = 해당 경로의 최초 커밋일. 경로를 못 찾으면 카드 JSON 변경일로 폴백
        date = git_first_commit_date(ref) if os.path.exists(ref) else ""
        if not date:
            date = git_last_commit_date(TIP_CARDS_FILE)
            print(f"WARNING: '{ref}' 경로를 찾지 못해 카드 JSON 변경일로 대체", file=sys.stderr)
        items.append({
            "category": TIP_CATEGORY,
            "title": f"[{TIP_CATEGORY}] {title}",
            "url": add_utm(url),
            "date": date[:10] if date else "",
            "_sort": date or "",
            "_path": local if os.path.isfile(local) else None,
        })
        print(f"tip(card): {items[-1]['title']} -> {items[-1]['url']} ({items[-1]['date']})")
    return items


def get_tip_items_from_scan():
    """(폴백) 리포 스캔 방식.

    A) 단일 HTML  : AI_Tip/자료명.html          -> /AI_Hub/AI_Tip/자료명.html
    B) 폴더형 자료 : 폴더명/index.html           -> /AI_Hub/폴더명/
       (이미지 등 부속 파일이 있어 폴더로 분리한 자료)
    """
    items = []

    # A) TIP_DIRS 안의 *.html
    for tdir in TIP_DIRS:
        if not os.path.isdir(tdir):
            continue
        for name in sorted(os.listdir(tdir)):
            if not name.lower().endswith(".html"):
                continue
            if name.startswith("_"):
                # _template.html 처럼 밑줄로 시작하는 파일은 자료가 아님
                continue
            rel = f"{tdir}/{name}"
            warn_bad_path(rel)
            stem = name.rsplit(".", 1)[0]
            items.append(make_tip_item(rel, PAGES_BASE + rel, stem))
            print(f"tip(file): {items[-1]['title']} -> {items[-1]['url']}")

    # B) index.html 을 가진 폴더 (TIP_DIRS 하위는 A에서 처리했으므로 제외)
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS
        )
        rel_dir = os.path.relpath(dirpath, ".").replace(os.sep, "/")
        if rel_dir == ".":
            continue
        if rel_dir.split("/")[0] in TIP_DIRS:
            continue
        if "index.html" not in filenames:
            continue
        warn_bad_path(rel_dir)
        folder_name = rel_dir.rsplit("/", 1)[-1]
        items.append(make_tip_item(
            os.path.join(dirpath, "index.html"),
            PAGES_BASE + rel_dir + "/",
            folder_name,
        ))
        print(f"tip(dir) : {items[-1]['title']} -> {items[-1]['url']}")

    return items


def check_ga4(tip_items):
    """자료 HTML에 GA4 태그가 들어있는지 검사. 없으면 경고만 출력(빌드는 계속)."""
    missing = []
    for it in tip_items:
        path = it.get("_path")
        if path and GA4_ID not in read_text(path):
            missing.append(path)
    if missing:
        print("", file=sys.stderr)
        print(f"WARNING: 아래 자료에 GA4 태그({GA4_ID})가 없습니다. 조회수가 집계되지 않습니다.",
              file=sys.stderr)
        for p in missing:
            print(f"  - {p}", file=sys.stderr)
        print("", file=sys.stderr)
    else:
        print(f"GA4: 모든 자료에 태그({GA4_ID}) 확인됨")
    return missing


def is_excluded(category, url):
    text = (category + " " + url).lower()
    return any(k.lower() in text for k in EXCLUDE_KEYWORDS)


def main():
    entries = get_sitemap_entries()
    if not entries:
        print("ERROR: sitemap에서 콘텐츠를 찾지 못했습니다.", file=sys.stderr)
        sys.exit(1)

    entries.sort(key=lambda e: e[1], reverse=True)

    # 1) 허브 사이트 글 (sitemap 기준)
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
            "url": add_utm(url),
            "date": lastmod[:10] if lastmod else "",
            "_sort": lastmod or "",
        })
        print(f"site: [{category}] {site_items[-1]['title']} ({site_items[-1]['date']})")

    # 2) AI 활용팁 자료 (리포 스캔)
    tip_items = get_tip_items()
    check_ga4(tip_items)

    # 3) 병합 후 최신순 상위 N개
    items = site_items + tip_items
    items.sort(key=lambda it: it["_sort"], reverse=True)
    items = items[:MAX_ITEMS]
    for it in items:
        it.pop("_sort", None)
        it.pop("_path", None)

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
