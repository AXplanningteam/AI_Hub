# AI_Hub

다우키움 **AI 허브 — AI 활용팁** 자료 저장소입니다.
여기에 HTML을 올리고 카드 목록에 등록하면, 허브 사이트와 사내포털 위젯 두 곳에 자동으로 노출됩니다.

| 노출 위치 | 주소 |
| --- | --- |
| 허브 사이트 참고자료 탭 | https://daoukiwoom.ai/ai-tips |
| 사내포털 최신소식 위젯 | (포털 내 위젯) |
| 자료 원본 (GitHub Pages) | https://axplanningteam.github.io/AI_Hub/ |


---

## 목차

- [빠른 시작](#빠른-시작)
- [저장소 구조](#저장소-구조)
- [ai-tip-cards.json 스펙](#ai-tip-cardsjson-스펙)
- [자동화](#자동화)
- [측정 (GA4)](#측정-ga4)
- [자료 수정·삭제·이름 변경](#자료-수정삭제이름-변경)
- [트러블슈팅](#트러블슈팅)
- [자주 하는 실수](#자주-하는-실수)

---

## 빠른 시작

새 자료를 올리는 절차는 **3단계**입니다.

### 1. HTML을 `AI_Tip/` 에 올린다

1. `AI_Tip` 폴더를 **클릭해서 들어간다** ← 가장 흔한 실수 지점
2. **Add file → Upload files** → 파일 드래그 (여러 개 가능)
3. 화면 **맨 아래** `Commit changes`

파일명 규칙 — **파일명이 곧 URL**입니다.

| 규칙 | 예시 |
| --- | --- |
| 영문 소문자 + 하이픈 | `prompt-guide.html` ✅ |
| 공백·한글·대문자 금지 | `Prompt Guide.html`, `프롬프트.html` ❌ |
| 확장자는 `.html` | `.htm` ❌ |
| 밑줄로 시작 금지 | `_draft.html` ❌ (자료로 취급 안 함) |

> GA4 측정 태그는 직접 넣지 않아도 됩니다. Actions가 자동 삽입합니다.

### 2. 배포 확인 — 건너뛰지 마세요

**Actions** 탭에서 초록 체크 확인 후 (1~2분), 브라우저에서 **직접 접속**합니다.

```
https://axplanningteam.github.io/AI_Hub/AI_Tip/prompt-guide.html
```

**404면 3단계로 넘어가지 마세요.**

### 3. `ai-tip-cards.json` 에 항목 추가

저장소 루트의 `ai-tip-cards.json` → 연필 아이콘 → 배열 안에 추가 → Commit

```json
  {
    "file": "AI_Tip/prompt-guide.html",
    "new": true,
    "thumb": "doc",
    "kicker": "GUIDE",
    "thumbTitle": "프롬프트 작성\n기본 가이드",
    "cat": "ChatGPT",
    "badges": ["프롬프트", "업무활용"],
    "title": "프롬프트 작성 기본 가이드",
    "desc": "업무에 바로 쓰는 프롬프트 작성 원칙을 정리했습니다."
  }
```

> ⚠️ 앞 항목의 `}` 뒤에 **쉼표** 필수. 마지막 항목 뒤에는 **쉼표 금지**.
> 커밋 전 [jsonlint.com](https://jsonlint.com) 검증 권장.

### 4. 확인

- 허브 사이트 https://daoukiwoom.ai/ai-tips → **Ctrl + Shift + R**
- 사내포털 위젯은 30분 이내 자동 반영. 바로 보려면 **Actions → Update hub news → Run workflow**

---

## 저장소 구조

```
AI_Hub/
├── ai-tip-cards.json           # 카드 목록 (손으로 수정)
├── hub-news.json               # 위젯 데이터 (자동 생성 · 수정 금지)
├── update_news.py              # 위젯 데이터 생성 스크립트
├── inject_ga4.py               # GA4 태그 자동 삽입 스크립트
├── .github/workflows/
│   └── update-news.yml         # 30분마다 자동 실행
└── AI_Tip/                     # 자료 HTML 모음
    ├── gemini-hallucination.html
    ├── sovereign-ai.html
```

이미지 등 **부속 파일이 있는 자료만** 폴더로 분리합니다.(추후 필요시 폴더 생성 예정)

```
AI_Hub/
└── file-hosting/
    ├── index.html              # → /AI_Hub/excel-automation/
    └── img/screenshot.png
```

| 파일 | 성격 |
| --- | --- |
| `ai-tip-cards.json` | **전체 목록 파일 1개** (자료마다 만드는 것이 아님) |
| `hub-news.json` | 자동 생성. 손으로 고쳐도 30분 뒤 덮어써짐 |
| `_` 로 시작하는 파일 | 자료로 취급 안 함 (위젯 노출·GA4 삽입 모두 제외) |

---

## ai-tip-cards.json 스펙

### 링크 지정 — 셋 중 하나만

| 키 | 쓸 때 | 예시 | 만들어지는 링크 |
| --- | --- | --- | --- |
| `file` | **기본.** 단일 HTML 자료 | `"AI_Tip/prompt-guide.html"` | `/AI_Hub/AI_Tip/prompt-guide.html` |
| `slug` | 부속 파일이 있어 폴더로 분리한 자료 | `"excel-automation"` | `/AI_Hub/excel-automation/` |
| `url` | 노션 글 등 외부 페이지 | `"https://daoukiwoom.ai/ai-agent"` | 입력한 주소 그대로 |

세 방식을 섞어 써도 됩니다.

> ⚠️ **`path` 는 쓰지 마세요.** 구버전 키입니다. `path` 로 쓰면 **위젯에는 나오는데 허브 카드는 404** 가 됩니다.

> ⚠️ **`app.notion.com/...` 원본 링크 금지.** 로그인·권한이 필요해 대부분 열리지 않습니다. Super로 공개된 `daoukiwoom.ai/...` 주소를 쓰세요.

### 전체 필드

| 키 | 필수 | 설명 |
| --- | --- | --- |
| `file` / `slug` / `url` | ✅ | 위 표 참고 (셋 중 하나) |
| `title` | ✅ | 카드 제목. **위젯 제목으로도 사용** |
| `desc` | | 1~2문장 설명 |
| `new` | | `true` = NEW 배지 / `false` = 숨김 |
| `thumb` | | 썸네일 색상 (아래 표). 기본값 `doc` |
| `kicker` | | 썸네일 안 영문 라벨: `TUTORIAL` / `GUIDE` / `TEMPLATE` / `REPORT` |
| `thumbTitle` | | 썸네일 큰 글씨. 줄바꿈은 **`\n`**. 2줄 이내 권장 |
| `cat` | | 대표 카테고리 배지 (보라 테두리) |
| `badges` | | 세부 키워드 배열. 없으면 `[]` |

> ⚠️ **줄바꿈은 `\n`** 입니다. `<br>` 아니고, `\t` 는 탭 문자가 됩니다.
> ⚠️ **`AI_Tip` 대소문자 정확히.** `ai_tip`, `AI_tip` 은 404입니다. 타이핑하지 말고 복사하세요.

### 썸네일 색상 프리셋

| 값 | 색상 | 추천 용도 |
| --- | --- | --- |
| `gemini` | 남색→보라 | Gemini, 생성형 AI |
| `doc` | 청록 | 문서·업무 가이드 |
| `guide` | 빨강→주황 | 필수·주의사항 |
| `data` | 짙은 회색 | 데이터·기술 |
| `chatgpt` | 초록 | ChatGPT |
| `claude` | 테라코타 | Claude |
| `copilot` | 하늘 | Copilot · MS 365 |
| `video` | 자홍 | 영상·교육 |
| `template` | 앰버 | 템플릿·양식 |

목록에 없는 값을 쓰면 **썸네일 배경이 흰색으로 비어 보입니다.**

### 순서

**배열 앞쪽 = 페이지 위쪽.** 새 자료를 맨 위에 두려면 배열 첫 번째에 넣으세요.

---

## 자동화

`.github/workflows/update-news.yml` 이 **30분마다** 실행됩니다. 수동 실행은 **Actions → Update hub news → Run workflow**.

| 순서 | 스크립트 | 하는 일 |
| --- | --- | --- |
| 1 | `inject_ga4.py` | 자료 HTML에 GA4 태그가 없으면 자동 삽입 (중복 삽입 없음) |
| 2 | `update_news.py` | `ai-tip-cards.json` + daoukiwoom.ai 사이트맵 → `hub-news.json` 생성, UTM 부착 |
| 3 | git | 변경분 커밋 & 푸시 |

### 정상 로그

```
GA4 삽입됨: AI_Tip/prompt-guide.html
총 2건 · 삽입 1건 · 기존 1건

tip(card): [활용팁] 프롬프트 작성 기본 가이드 -> .../AI_Tip/prompt-guide.html?utm_source=portal&...
GA4: 모든 자료에 태그(G-VFLVE5CVHM) 확인됨
OK: 8건 저장 -> hub-news.json
```

> ⚠️ **GitHub Actions는 저장소에 60일간 커밋이 없으면 스케줄을 자동 중단합니다.**
> 자료를 두 달 이상 안 올리면 위젯 갱신이 조용히 멈춥니다. Actions 탭에서 `Enable workflow` 로 재활성화하세요.

---

## 측정 (GA4)

측정 ID: **`G-VFLVE5CVHM`** (허브 사이트와 자료 HTML 공용)

| 발생 위치 | 수집 이벤트 | 태그 위치 |
| --- | --- | --- |
| `daoukiwoom.ai/*` | `page_view` `link_click` `article_read_complete` | Super → Code Injection → Head |
| 자료 HTML | `page_view` `link_click` `article_read_complete` `cta_click` | **자동 삽입** |

### 유입 경로 구분

```
?utm_source=portal&utm_medium=widget&...  → 사내포털 위젯
?from=hub                                  → /ai-tips 카드 클릭
(쿼리 없음)                                 → 직접 접속·북마크·메신저
```

### CTA 버튼 측정

자료 안 주요 버튼에 `data-cta` 를 붙이면 `cta_click` 이벤트가 따로 수집됩니다.

```html
<a href="https://daoukiwoom.ai/ai-tips" data-cta="cta_read_full">전문 읽기 →</a>
```

### 보고서

| 알고 싶은 것 | GA4 경로 |
| --- | --- |
| 어떤 자료를 **클릭**했나 | 탐색 → 자유 형식 → 측정기준 `link_text`, 필터 `이벤트 이름 = link_click` |
| 어떤 자료를 **열람**했나 | 보고서 → 참여도 → 페이지 및 화면 → 측정기준 **페이지 제목** |
| **유입 경로** 구분 | 위와 같은 화면 → **페이지 경로 및 쿼리 문자열** |
| **완독률** | `article_read_complete` ÷ 해당 자료 `page_view` |

---

## 자료 수정·삭제·이름 변경

<details>
<summary><b>내용만 수정 (URL 유지)</b></summary>

1. `AI_Tip` → 해당 `.html` → 연필 아이콘 → 수정 → Commit
2. 1~2분 후 `Ctrl + Shift + R`

JSON도 Super도 건드릴 필요 없습니다. GA4 블록도 지우지 마세요 (지워도 자동으로 다시 들어갑니다).
</details>

<details>
<summary><b>카드 정보만 수정 (제목·설명·색상·NEW 배지)</b></summary>

`ai-tip-cards.json` 에서 해당 항목의 값만 고치고 Commit → `Ctrl + Shift + R`
</details>

<details>
<summary><b>자료 삭제</b></summary>

1. `ai-tip-cards.json` 에서 해당 `{ }` 덩어리 삭제 → **앞뒤 쉼표 정리** → Commit
2. (선택) HTML 파일 삭제 — 파일 화면 → `···` → Delete file

**순서가 중요합니다.** HTML을 먼저 지우면 그사이 카드는 보이는데 클릭 시 404가 납니다.

JSON에서만 지워도 사이트·위젯에서는 사라집니다. 다만 저장소가 Public이라 **URL을 아는 사람은 계속 접근 가능**합니다.
</details>

<details>
<summary><b>파일명(URL) 변경</b></summary>

1. 파일 Edit → 파일명 칸 수정 → Commit
2. 새 URL **단독 접속으로 확인**
3. `ai-tip-cards.json` 의 `file` 값도 **반드시 함께 수정**

기존 URL은 즉시 404가 됩니다. 이미 공유된 링크가 있는지 먼저 확인하세요.
</details>

<details>
<summary><b>이름과 내용을 둘 다 바꿀 때 (무중단 순서)</b></summary>

1. 새 이름으로 파일 먼저 업로드 (기존 파일은 그대로)
2. 새 URL 단독 확인
3. JSON의 `file` 값 교체
4. `/ai-tips` 확인
5. 마지막에 기존 파일 삭제
</details>

---

## 트러블슈팅

### 진단 순서

1. `https://axplanningteam.github.io/AI_Hub/ai-tip-cards.json` → JSON이 보이는가?
2. `https://axplanningteam.github.io/AI_Hub/AI_Tip/파일명.html` → 자료가 열리는가?
3. `/ai-tips` 에서 **F12 → Console** → 에러 확인
4. Console에 `document.querySelectorAll('.ref-card').length` 입력

<details>
<summary><b>카드가 하나도 안 보임 (0개)</b></summary>

| 콘솔 메시지 | 원인 | 조치 |
| --- | --- | --- |
| `로드 실패: Unexpected token` | **JSON 문법 오류 (쉼표)** — 가장 흔함 | 항목 사이 `,` 추가 / 마지막 `,` 삭제 |
| `로드 실패: HTTP 404` | JSON 위치·이름 오류, 배포 미완료 | 파일이 저장소 **루트**에 있는지, Actions 초록인지 |
| 에러 없는데 안 보임 | 브라우저 캐시 | `Ctrl + Shift + R` |
| 에러 없는데 안 보임 | Super Body 코드 미적용 | Super Save/Publish 여부, 유료 플랜인지 확인 |
</details>

<details>
<summary><b>허브 카드는 되는데 위젯에 안 나옴 (또는 반대)</b></summary>

두 시스템이 인식하는 키가 달라서 생기는 문제입니다.

| 쓴 키 | 허브 카드 | 포털 위젯 |
| --- | --- | --- |
| `file` | ✅ | ✅ |
| `slug` | ✅ | ✅ |
| `url` | ✅ | ✅ |
| `path` | ❌ 404 | ✅ |
| 키 없음 | ❌ | ❌ |

→ **`file` / `slug` / `url` 만 쓰세요.**
</details>

<details>
<summary><b>카드 클릭 시 404</b></summary>

| 확인 항목 | 조치 |
| --- | --- |
| `file` 값의 **대소문자** | `AI_Tip` 이 정확한지 |
| 경로에 **공백** | `AI_Tip /` 처럼 공백이 섞였는지. 눈에 안 보이니 복사해서 대조 |
| `.html` 누락 | `file` 값 끝에 확장자가 있는지 |
| `path` 키 사용 | `file` 로 변경 |
| 파일이 루트에 올라감 | `AI_Tip` 폴더에 들어가서 업로드했는지 |
| 배포 미완료 | Actions 초록 체크, 1~2분 대기 |
</details>

<details>
<summary><b>JSON을 수정해도 카드가 안 바뀜</b></summary>

Super Body 코드 맨 위에 예전 하드코딩 블록(`<div id="ref-mount">...</div>`)이 남아 있는 경우입니다. 스크립트가 그 정적 블록을 쓰고 JSON을 무시합니다.

→ Body에는 `<script>` 로 시작해 `</script>` 로 끝나는 부분만 남기세요.
</details>

<details>
<summary><b>썸네일 배경이 흰색으로 비어 보임</b></summary>

`thumb` 값이 프리셋 목록(9개)에 없는 이름입니다. 오타를 확인하세요.
</details>

<details>
<summary><b>자료 페이지에 GA4가 안 들어감</b></summary>

| 확인 항목 | 조치 |
| --- | --- |
| Actions **Inject GA4** 스텝 로그 | `GA4 삽입됨:` 이 나왔는지 |
| 워크플로우 커밋 대상 | `git add -A` 인지 (`git add hub-news.json` 이면 HTML이 커밋 안 됨) |
| 파일명 | 밑줄로 시작하면 대상에서 제외 |
| `<head>` 유무 | `<head>` 없는 HTML은 건너뜀 (로그에 WARNING) |
</details>

<details>
<summary><b>워크플로우 빨간 X</b></summary>

`Canceling Pages deployment... The operation was canceled` 는 **실패가 아닙니다.**
짧은 시간에 커밋을 두 번 하면 나중 run이 이전 run을 취소하면서 생깁니다.
**최신 run이 초록이면 정상**입니다.
</details>

<details>
<summary><b>위젯이 며칠째 갱신 안 됨</b></summary>

| 확인 항목 | 조치 |
| --- | --- |
| 60일 무커밋으로 스케줄 중단 | Actions에서 **Enable workflow** |
| 워크플로우 실패 | 최근 run 로그 확인 |
| 사이트맵 접근 불가 | 로그에 `ERROR: sitemap에서 콘텐츠를 찾지 못했습니다` |
</details>

<details>
<summary><b>GitHub Pages 자체가 안 뜸</b></summary>

| 확인 항목 | 조치 |
| --- | --- |
| 저장소가 Private | Settings → Danger Zone → Change to public |
| Pages 설정 | Settings → Pages → Branch `main`, `/(root)` → Save |
| 브랜치 이름 | `main` 이 아니라 `master` 일 수 있음 |
</details>

<details>
<summary><b>다른 탭 갔다 오면 카드가 사라짐</b></summary>

Super가 SPA라 본문 교체 시 카드가 삭제되는 현상입니다. Body 코드 하단 `setInterval` 스크립트가 감지해 재삽입하므로 **지우지 마세요.**

```js
location.pathname   // '/ai-tips' 가 나와야 정상
```

다른 값이면 스크립트의 `var SLUG = 'ai-tips';` 를 실제 값에 맞게 수정하세요.
</details>

<details>
<summary><b>카드가 노션 안내문 위에 나옴</b></summary>

Super는 Body 주입 코드를 노션 콘텐츠보다 앞에 삽입합니다. 스크립트가 아래로 이동시키는데, 컨테이너 셀렉터를 못 찾으면 실패합니다.

```js
document.querySelector('.notion-root')
```

`null` 이면 Elements에서 실제 클래스명을 찾아 스크립트 셀렉터 목록에 추가하세요.
</details>

---

## 자주 하는 실수

1. **JSON 항목 사이 쉼표 누락** → 카드가 **전부** 사라짐 (한 건이 아니라)
2. **`path` 키 사용** → 위젯엔 나오는데 허브 카드는 404
3. **`AI_Tip` 폴더에 안 들어가고 루트에서 업로드** → 경로 불일치로 404
4. **경로 대소문자·공백** (`ai_tip`, `AI_Tip /`) → 눈에 안 보여서 원인 찾기 어려움
5. **`thumbTitle` 줄바꿈에 `\t` 사용** → 탭 문자로 깨짐. `\n` 이 정답
6. **강력 새로고침(`Ctrl + Shift + R`) 안 함** → 캐시 때문에 "안 된다"고 오판

---

## 관련 링크

| 항목 | 주소 |
| --- | --- |
| 서비스 | https://daoukiwoom.ai/ai-tips |
| 자료 원본 | https://axplanningteam.github.io/AI_Hub/ |
| 카드 데이터 | https://axplanningteam.github.io/AI_Hub/ai-tip-cards.json |
| 위젯 데이터 | https://axplanningteam.github.io/AI_Hub/hub-news.json |

카드 디자인(CSS)과 렌더링 코드(Body)는 이 저장소가 아니라 **Super.so 대시보드**에 있습니다.
백업과 재구축 절차는 별도 인수인계 문서를 참고하세요.

---

<sub>운영: 디지털R&D센터 AX기획팀</sub>
