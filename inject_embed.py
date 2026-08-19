# -*- coding: utf-8 -*-
"""
AI_Tip 폴더의 자료 HTML에 공통 스크립트 블록을 넣거나 최신으로 갱신한다.
GitHub Actions에서 update_news.py 앞에 실행. 표준 라이브러리만 사용.

[현재 구조]
자료는 노션 페이지에 embed 되어 daoukiwoom.ai 안에서 열린다.
부모 페이지(Super)에 이미 GA4 가 있으므로 자료 HTML 안의 GA4 는
  - page_view 를 이중 집계하고
  - 높이 자동 확장 때문에 완독을 즉시 발사(완독률 왜곡)
따라서 ENABLE_GA4 = False 로 두고, 이미 들어간 GA4 블록은 제거한다.

삽입/관리하는 블록
  1) 높이 보고 (필수) : iframe 안에서 자기 높이를 부모에 알려 잘림 방지
  2) GA4 측정 (기본 꺼짐) : ENABLE_GA4 = True 로 바꾸면 다시 삽입됨

특징
  - 블록마다 시작·끝 주석 마커가 있어, 내용이 바뀌면 자동으로 교체된다
  - ENABLE_GA4 = False 이면 마커 블록과 구버전 블록을 모두 제거한다
  - 밑줄로 시작하는 파일(_template.html)은 제외
  - 폴더형 자료(폴더/index.html)도 대상에 포함
"""
import os
import re
import sys

# 자료 HTML 안에 GA4 를 넣을지 여부.
# 노션 embed 구조에서는 부모 페이지가 이미 측정하므로 False 권장.
# 자료 URL 을 단독으로 공유·배포한다면 True 로 바꾸세요.
ENABLE_GA4 = False

GA4_ID = "G-VFLVE5CVHM"
TIP_DIRS = ["AI_Tip"]
SKIP_DIRS = {".github", ".git", "scripts", "node_modules"}

# ---- 블록 마커 (내용을 바꿔도 이 마커는 유지해야 자동 갱신이 동작) ----
GA4_START = "<!-- AIHUB:GA4:START -->"
GA4_END = "<!-- AIHUB:GA4:END -->"
FRAME_START = "<!-- AIHUB:FRAME:START -->"
FRAME_END = "<!-- AIHUB:FRAME:END -->"

# 예전 버전 블록(마커 없던 시절) — 발견하면 통째로 걷어낸다
LEGACY_RE = re.compile(
    r"[ \t]*<!--\s*=+\s*GA4 측정 블록.*?-->.*?<!--\s*=+\s*GA4 측정 블록 끝\s*=+\s*-->\s*",
    re.S,
)

GA4_BLOCK = """%(S)s
  <!-- GA4 측정 (자동 삽입 · 직접 수정하지 마세요) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=%(ID)s"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '%(ID)s');
  </script>
  <script>
  (function () {
    var INTERNAL_HOSTS = ['axplanningteam.github.io', 'daoukiwoom.ai'];
    function isInternal(host) {
      for (var i = 0; i < INTERNAL_HOSTS.length; i++) {
        if (host === INTERNAL_HOSTS[i] || host.indexOf('.' + INTERNAL_HOSTS[i]) >= 0) return true;
      }
      return false;
    }
    var readFired = false;
    function onScroll() {
      var doc = document.documentElement, body = document.body;
      var full = Math.max(doc.scrollHeight, body ? body.scrollHeight : 0);
      var seen = (window.pageYOffset || doc.scrollTop) + window.innerHeight;
      if (full <= 0) return;
      if (!readFired && (seen / full > 0.9 || full <= window.innerHeight + 40)) {
        readFired = true;
        gtag('event', 'article_read_complete', {
          page_title: document.title,
          page_location: location.href
        });
        window.removeEventListener('scroll', onScroll);
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('load', onScroll);

    document.addEventListener('click', function (e) {
      var link = e.target && e.target.closest ? e.target.closest('a') : null;
      if (!link || !link.href) return;
      if (/^(mailto:|tel:|javascript:)/i.test(link.getAttribute('href') || '')) return;
      var external = !isInternal(link.hostname);
      var text = (link.innerText || link.textContent || '').trim().slice(0, 50);
      gtag('event', 'link_click', {
        link_text: text,
        link_url: link.href,
        link_type: external ? 'external' : 'internal',
        page_title: document.title
      });
      var cta = link.getAttribute('data-cta');
      if (cta) {
        gtag('event', 'cta_click', {
          cta_name: cta,
          link_url: link.href,
          page_title: document.title
        });
      }
    }, true);
  })();
  </script>
  %(E)s""" % {"ID": GA4_ID, "S": GA4_START, "E": GA4_END}

FRAME_BLOCK = """%(S)s
  <!-- 노션 embed(iframe) 높이 보고 (자동 삽입 · 직접 수정하지 마세요) -->
  <script>
  (function () {
    if (window.self === window.top) return;      // iframe 안에서만 동작
    var last = 0;
    function measure() {
      var d = document.documentElement, b = document.body;
      return Math.max(
        d ? d.scrollHeight : 0, d ? d.offsetHeight : 0,
        b ? b.scrollHeight : 0, b ? b.offsetHeight : 0
      );
    }
    function send() {
      var v = measure();
      if (!v || Math.abs(v - last) < 8) return;
      last = v;
      try {
        parent.postMessage({ type: 'aihub:height', height: v, src: location.href }, '*');
      } catch (e) {}
    }
    window.addEventListener('load', send);
    window.addEventListener('resize', send);
    document.addEventListener('DOMContentLoaded', send);
    if (window.ResizeObserver) {
      try { new ResizeObserver(send).observe(document.documentElement); } catch (e) {}
    }
    setInterval(send, 1000);
    send();
  })();
  </script>
  %(E)s""" % {"S": FRAME_START, "E": FRAME_END}


def target_files():
    """대상 자료 HTML 목록."""
    files = []
    for tdir in TIP_DIRS:
        if not os.path.isdir(tdir):
            continue
        for name in sorted(os.listdir(tdir)):
            if name.lower().endswith((".html", ".htm")) and not name.startswith("_"):
                files.append(f"{tdir}/{name}")

    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = sorted(
            d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS
        )
        rel_dir = os.path.relpath(dirpath, ".").replace(os.sep, "/")
        if rel_dir == "." or rel_dir.split("/")[0] in TIP_DIRS:
            continue
        if "index.html" in filenames:
            files.append(f"{rel_dir}/index.html")
    return files


def insert_point(html):
    """<title> 바로 앞. 없으면 <head> 바로 뒤. 둘 다 없으면 None."""
    m = re.search(r"<title[\s>]", html, re.I)
    if m:
        return m.start()
    m = re.search(r"<head[^>]*>", html, re.I)
    if m:
        return m.end()
    return None


def ensure_block(html, start, end, block, skip_if=None):
    """블록이 있으면 최신 내용으로 교체, 없으면 삽입.
    skip_if 가 html 에 있으면 삽입하지 않음(중복 방지용).
    반환: (새 html, 'updated' | 'inserted' | 'ok' | 'skipped' | 'nohead')"""
    if start in html and end in html:
        pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
        cur = pat.search(html).group(0)
        if cur.strip() == block.strip():
            return html, "ok"
        return pat.sub(lambda _: block, html, count=1), "updated"

    if skip_if and skip_if in html:
        return html, "skipped"

    pos = insert_point(html)
    if pos is None:
        return html, "nohead"
    return html[:pos] + block + "\n\n  " + html[pos:], "inserted"


def remove_block(html, start, end):
    """마커 블록을 통째로 제거."""
    if start not in html or end not in html:
        return html, False
    pat = re.compile(r"[ \t]*" + re.escape(start) + r".*?" + re.escape(end) + r"\s*", re.S)
    return pat.sub("", html, count=1), True


def process(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        original = f.read()

    html = original
    notes = []

    if ENABLE_GA4:
        # 예전 마커 없는 자동 삽입 블록은 새 블록으로 대체
        if GA4_START not in html:
            html, n = LEGACY_RE.subn("", html)
            if n:
                notes.append("구버전블록제거")
        html, s1 = ensure_block(html, GA4_START, GA4_END, GA4_BLOCK, skip_if=GA4_ID)
        if s1 != "ok":
            notes.append("GA4:" + s1)
    else:
        # GA4 를 쓰지 않는 구조 — 이미 들어간 블록을 걷어낸다
        html, removed = remove_block(html, GA4_START, GA4_END)
        if removed:
            notes.append("GA4:제거")
        html, n = LEGACY_RE.subn("", html)
        if n:
            notes.append("구버전GA4:제거")

    html, s2 = ensure_block(html, FRAME_START, FRAME_END, FRAME_BLOCK)
    if s2 != "ok":
        notes.append("높이:" + s2)

    if html != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return True, notes
    return False, notes


def main():
    files = target_files()
    if not files:
        print("대상 HTML이 없습니다.")
        return

    changed = 0
    for p in files:
        did, notes = process(p)
        if did:
            changed += 1
            print(f"갱신: {p}  ({', '.join(notes)})")
        else:
            print(f"유지: {p}")
        if "GA4:nohead" in notes or "높이:nohead" in notes:
            print(f"WARNING: <head> 를 찾지 못했습니다 -> {p}", file=sys.stderr)
        if "GA4:skipped" in notes:
            print(f"NOTE: {p} 는 GA4 를 수동으로 넣은 파일로 보여 GA4 블록은 건너뛰었습니다.",
                  file=sys.stderr)

    if not ENABLE_GA4:
        print("(자료 HTML 내 GA4 는 꺼져 있습니다 — 부모 페이지가 측정)")

    print(f"\n총 {len(files)}건 · 변경 {changed}건 · 유지 {len(files) - changed}건")


if __name__ == "__main__":
    main()
