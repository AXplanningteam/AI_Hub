# AI_Hub

다우키움 **AI 허브**(https://daoukiwoom.ai) 운영용 저장소입니다.
디지털R&D센터 AX기획팀에서 관리합니다.

---

## 1. 이 저장소가 하는 일

두 가지뿐입니다.

| 역할 | 결과물 | 어디서 쓰이나 |
|---|---|---|
| ① AI 활용팁 **자료 HTML 호스팅** | `AI_Tip/*.html` | 노션 페이지가 이 주소를 embed → daoukiwoom.ai 안에서 열림 |
| ② 사내포털 위젯용 **최신글 목록 생성** | `hub-news.json` | 사내포털 위젯이 30분마다 읽어감 |

### 전체 흐름

```
[GitHub]  AI_Tip/자료명.html
             │  GitHub Pages
             ▼
   https://axplanningteam.github.io/AI_Hub/AI_Tip/자료명.html
             │  노션 embed 블록
             ▼
[노션]  CONTENTS DB  ─ 제목: "[활용팁] 자료명"
             │  Super.so
             ▼
[웹]  https://daoukiwoom.ai/ai-tips  (갤러리)
      https://daoukiwoom.ai/contents/... (자료 본문)
             │  sitemap.xml
             ▼
[GitHub Actions] update_news.py ── hub-news.json ──▶ [사내포털 위젯]
```

> **중요** — 사용자가 실제로 보는 주소는 언제나 `daoukiwoom.ai` 입니다.
> `github.io` 주소는 노션 embed 의 내부 소스일 뿐, 사내포털 위젯도
> `daoukiwoom.ai` 를 가리킵니다.

---

## 2. 파일 구성

```
AI_Hub/
├── .github/workflows/
│   └── update-news.yml        30분마다 update_news.py 실행
├── AI_Tip/
│   └── gemini-hallucination.html   자료 본문 (노션이 embed 하는 원본)
├── update_news.py             sitemap → hub-news.json 생성
├── hub-news.json              위젯이 읽는 최신글 목록 (자동 생성 · 직접 수정 금지)
├── news-first-seen.json       글별 최초 발견일 기록 (N 배지 판정 · 자동 생성 · 삭제 금지)
├── widget.html                사내포털에 붙인 위젯 원본
├── ai-hub-character.png       위젯 이미지
└── README.md                  이 문서
```

### 손대면 안 되는 파일

- **`hub-news.json`** — Actions 가 덮어씁니다. 수동 수정은 다음 실행에 사라집니다.
- **`news-first-seen.json`** — 지우면 전체 글이 "과거 글"로 리셋되어 **N 배지가 전부 사라집니다.**

---

## 3. 새 자료 올리기

### STEP 1. HTML 을 `AI_Tip/` 에 업로드

1. 저장소 → `AI_Tip` 폴더 → **Add file → Upload files**
2. 파일명은 **영문 소문자 + 하이픈**, 확장자 `.html`
   - 예: `excel-automation.html`
   - ❌ 한글, 공백, 대문자 확장자(`.HTML`) 금지 — 링크가 깨집니다
3. Commit changes

### STEP 2. 자료 HTML 에 embed 보정 블록 넣기

자료를 iframe 안에 띄우면 `position: fixed` 요소(좌우 이동 화살표 등)가
화면이 아니라 **iframe 전체 높이**를 기준으로 잡혀 맨 아래로 밀립니다.
아래 두 블록을 넣으면 **iframe 안일 때만** 보정됩니다. 직접 열었을 때는 그대로입니다.

**(a) `</style>` 바로 앞**

```css
/* ===== embed(iframe) 전용 보정 ===== */
.in-embed .wrap { position: relative; }
.in-embed .side-arrow {
  position: absolute !important;
  top: 50% !important;
  bottom: auto !important;
  transform: translateY(-50%) !important;
  width: 44px !important; height: 44px !important;
}
.in-embed .side-arrow.left  { left: 4px !important;  right: auto !important; }
.in-embed .side-arrow.right { right: 4px !important; left: auto !important; }
@media (max-width: 700px) {
  .in-embed .side-arrow { width: 38px !important; height: 38px !important; }
  .in-embed .side-arrow.left  { left: 2px !important; }
  .in-embed .side-arrow.right { right: 2px !important; }
}
```

**(b) `<body>` 바로 다음**

```html
<script>if (window.self !== window.top) document.documentElement.classList.add('in-embed');</script>
```

> **GA4 태그는 넣지 마세요.** 부모 페이지(daoukiwoom.ai)가 이미 측정합니다.
> 자료 안에 또 넣으면 `page_view` 가 이중 집계되고, iframe 높이가 고정이라
> 스크롤이 없어서 완독 이벤트가 로드 즉시 발사됩니다.

### STEP 3. 주소가 살아있는지 확인

배포까지 1~2분 걸립니다. 새 탭에서 직접 열어보세요.

```
https://axplanningteam.github.io/AI_Hub/AI_Tip/파일명.html
```

404 면 → 파일명 오타 / `AI_Tip/` 누락 / 아직 배포 중.
Actions 탭 → **pages build and deployment** 가 초록불인지 확인.

### STEP 4. 필요 높이 측정

자료를 직접 연 상태에서 **F12 → Console** 에 붙여넣고 실행합니다.

```js
console.log('필요 높이:', Math.max(
  document.documentElement.scrollHeight,
  document.body.scrollHeight
), 'px');
```

인터랙티브 자료라면 **모든 단계를 눌러본 뒤** 다시 실행해 가장 큰 값을 씁니다.
현재 기준값은 `1700px` (측정 1630 + 여유). 이보다 크면 STEP 7 참고.

### STEP 5. 노션 CONTENTS DB 에 등록

1. 노션 **CONTENTS** 데이터베이스 → 새 페이지
2. **제목을 `[활용팁] 자료 이름` 형식으로** 작성
   - 이 접두어로 사내포털 위젯이 활용팁을 분류합니다. **빼면 위젯에서 사라집니다.**
3. 커버 이미지 / 태그 등 다른 자료와 동일하게 채우기
4. 본문에 `/embed` → STEP 3 의 `github.io` 주소 붙여넣기
   - ⚠️ HTML **파일**을 노션에 올리는 게 아닙니다. **주소**를 embed 해야 합니다

### STEP 6. Super 재배포 & 확인

Super 대시보드에서 재배포(또는 자동 동기화 대기) 후 확인합니다.

- https://daoukiwoom.ai/ai-tips → 갤러리에 카드가 뜨는가
- 카드 클릭 → 본문이 **daoukiwoom.ai 안에서** 열리는가
- 스크롤바 없이 다 보이는가 / 좌우 화살표가 세로 중앙에 있는가

### STEP 7. (높이가 모자랄 때만) 전체 CSS 조정

Super → **Settings → Code Injection → CSS** 맨 위 값을 올립니다.

```css
:root {
  --tip-embed-h: 1700px;          /* PC */
  --tip-embed-h-tablet: 1800px;
  --tip-embed-h-mobile: 2000px;
}
```

이 값은 **모든 자료에 공통 적용**됩니다. 특정 자료만 유난히 길면
그 자료를 나누는 편이 낫습니다.

---

## 4. 자동화 (GitHub Actions)

### `update-news.yml`

- **30분마다** + Actions 탭에서 **수동 실행(Run workflow)** 가능
- 하는 일: `update_news.py` 실행 → 변경 있으면 자동 커밋 & 푸시

### `update_news.py`

`https://daoukiwoom.ai/sitemap.xml` 의 `/contents/` 글을 읽어
최신 8건을 `hub-news.json` 으로 저장합니다.

| 설정 | 기본값 | 설명 |
|---|---|---|
| `MAX_ITEMS` | 8 | JSON 에 담을 글 수 (위젯은 5개 표시) |
| `RESERVE_TIP_SLOTS` | 0 | 활용팁 자리를 최소 몇 개 보장할지. 1~2 로 올리면 일반 글이 몰려도 활용팁이 밀리지 않음 |
| `EXCLUDE_KEYWORDS` | 아카데미, academy | 위젯에서 뺄 카테고리 |
| `ADD_UTM` | True | 사내포털 유입 측정용 UTM 부착 |

**활용팁 판별** — 제목이 `[활용팁] ` 로 시작하면 카테고리를 `활용팁` 으로 잡습니다.
폴더 위치가 아니라 **노션 제목**이 기준입니다.

**N 배지 날짜** — sitemap 의 `lastmod` 는 *수정일*이라 배지 판정에 쓸 수 없습니다.
그래서 스크립트가 30분마다 전체 글을 `news-first-seen.json` 에 기록하고,
**최초 발견일 = 사실상 작성일**로 사용합니다. 이후 글을 수정해도 날짜는 안 바뀝니다.

---

## 5. Super.so 설정 위치

| 설정 | 위치 | 내용 |
|---|---|---|
| embed 높이 · 자료 스타일 | Settings → **Code Injection → CSS** | `--tip-embed-h` 및 `notion-embed` 래퍼 보정 |
| 사이트 공통 스크립트 | Settings → **Code Injection → Body** | CTA 등 |
| `/ai-tips` 갤러리 훅 | `/ai-tips` 페이지 → **Code → Body** | `.custom-tip-grid` 클래스 부착 |
| `/ai-tips` 그리드 | `/ai-tips` 페이지 → **Code → CSS** | 3열 고정, 뷰탭 숨김 |

---

## 6. 문제 대응

<details>
<summary><b>/ai-tips 에서 자료를 눌렀는데 본문이 잘려 보인다</b></summary>

전체 CSS 의 `--tip-embed-h` 가 자료 실제 높이보다 작습니다.
STEP 4 로 필요 높이를 측정해 STEP 7 에서 값을 올리세요.
</details>

<details>
<summary><b>iframe 안에 스크롤바가 생긴다</b></summary>

위와 같은 원인입니다. 높이를 늘리면 사라집니다.
반대로 값이 너무 크면 본문 아래 회색 여백이 생깁니다.
</details>

<details>
<summary><b>좌우 이동 화살표가 맨 아래에 붙어 있다</b></summary>

STEP 2 의 embed 보정 블록이 빠졌습니다.
자료의 `.side-arrow` 가 `position: fixed` 인데, iframe 안에서는
브라우저 창이 아니라 **iframe 전체 높이**를 기준으로 잡히기 때문입니다.
</details>

<details>
<summary><b>사내포털 위젯에 새 자료가 안 뜬다</b></summary>

순서대로 확인:

1. **노션 제목에 `[활용팁] ` 접두어가 있는가** — 가장 흔한 원인
2. 노션 페이지가 **공개(Published)** 상태인가
3. `https://daoukiwoom.ai/sitemap.xml` 에 해당 주소가 있는가 — Super 배포 후 반영까지 시간이 걸립니다
4. Actions → **Update hub news** 를 수동 실행하고 로그에서 확인:
   ```
   item: [활용팁] ... 
   활용팁 1건 확인
   ```
   `활용팁 0건` 이면 1~3 번 중 하나가 원인입니다.
5. 위젯 캐시 — 사내포털에서 강력 새로고침(Ctrl+Shift+R)
</details>

<details>
<summary><b>github.io 주소가 404 다</b></summary>

- 폴더명/파일명 **앞뒤 공백** 확인 (`sovereign-ai ` 처럼 끝에 공백이 있으면 404)
- 확장자 대소문자 (`.HTML` → `.html`)
- 경로에 `AI_Tip/` 이 빠지지 않았는지
- Actions → **pages build and deployment** 초록불 확인
</details>

<details>
<summary><b>GA4 에 조회수가 안 잡힌다</b></summary>

측정은 **daoukiwoom.ai (부모 페이지)** 에서 합니다. 자료 HTML 에는 GA4 를 넣지 않습니다.
GA4 실시간 보고서에서 `/contents/...` 경로가 잡히는지 확인하세요.
사내포털 유입은 `utm_source=portal` 로 구분됩니다.
</details>

<details>
<summary><b>Actions 가 빨간불이다</b></summary>

로그를 열어 마지막 에러를 봅니다. 흔한 것:

- `ERROR: sitemap 에서 콘텐츠를 찾지 못했습니다` — daoukiwoom.ai 가 일시적으로 응답하지 않음. 잠시 후 재실행
- `push rejected` — 동시 실행 충돌. 재실행하면 해결
</details>

---

## 7. 담당

디지털R&D센터 AX기획팀
