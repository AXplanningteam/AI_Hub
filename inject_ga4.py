# -*- coding: utf-8 -*-
"""
AI_Tip 폴더의 자료 HTML에 GA4 측정 블록이 없으면 자동으로 삽입한다.
GitHub Actions에서 update_news.py 앞에 실행. 표준 라이브러리만 사용.

- 이미 GA4_ID 가 들어 있는 파일은 건드리지 않음 (중복 삽입 방지)
- 삽입 위치: <head> 안, <title> 바로 앞. <title> 이 없으면 <head> 바로 뒤
- 밑줄로 시작하는 파일(_template.html)은 제외
- 폴더형 자료(폴더/index.html)도 대상에 포함
"""
import os
import re
import sys

GA4_ID = "G-VFLVE5CVHM"
TIP_DIRS = ["AI_Tip"]
SKIP_DIRS = {".github", ".git", "scripts", "node_modules"}

GA4_BLOCK = """
  <!-- ===== GA4 측정 블록 (자동 삽입 · 수정하지 마세요) ===== -->
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
  <!-- ===== GA4 측정 블록 끝 ===== -->
""" % {"ID": GA4_ID}


def target_files():
    """GA4를 넣어야 할 자료 HTML 목록."""
    files = []
    for tdir in TIP_DIRS:
        if not os.path.isdir(tdir):
            continue
        for name in sorted(os.listdir(tdir)):
            if name.lower().endswith(".html") and not name.startswith("_"):
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


def inject(path):
    """GA4 블록을 삽입. 이미 있으면 False, 넣었으면 True."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    if GA4_ID in html:
        return False

    m = re.search(r"<title[\s>]", html, re.I)
    if m:
        pos = m.start()
    else:
        m = re.search(r"<head[^>]*>", html, re.I)
        if not m:
            print(f"WARNING: <head> 를 찾지 못해 건너뜁니다 -> {path}", file=sys.stderr)
            return False
        pos = m.end()

    new_html = html[:pos] + GA4_BLOCK.strip("\n") + "\n\n  " + html[pos:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return True


def main():
    files = target_files()
    if not files:
        print("대상 HTML이 없습니다.")
        return

    injected, already = [], []
    for p in files:
        (injected if inject(p) else already).append(p)

    for p in already:
        print(f"GA4 있음  : {p}")
    for p in injected:
        print(f"GA4 삽입됨: {p}")

    print(f"\n총 {len(files)}건 · 삽입 {len(injected)}건 · 기존 {len(already)}건")


if __name__ == "__main__":
    main()
