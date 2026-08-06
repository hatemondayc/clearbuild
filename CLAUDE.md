# CLAUDE.md — clearbuild-site

CLEARBUILD = 정비사업(재개발·재건축·리모델링·가로주택) **매수 대기자**를 위한 판단·데이터 인프라.
이 repo는 그 **무료 정보 진입점(단지 페이지)** 웹사이트다. AI가 이 파일을 먼저 읽고 아래 규칙대로 작업한다.

## 스택 (중요: 프레임워크 없음)
- **정적 HTML/CSS/JS** 멀티페이지. 빌드 스텝 없음, 번들러 없음. `<script>` 인라인 + CDN.
- **Supabase**(supabase-js CDN, anon 키 하드코딩=RLS로 안전), **Vercel**(git push → 자동 배포), **Umami**(계측), **NAVER 지도**(Client ID `a4kxw68xe0`).
- ⚠️ **Next.js 전면 이관은 발표 후**(계산엔진 회귀 위험). 지금은 정적 유지.

## 파일 지도
| 파일 | 역할 |
|---|---|
| `index.html` | 홈 진입점 — 사전신청·ABOUT·FAQ·SEO + "시뮬레이션 경험하기" → danji · 검색·정비구역 통합 지도 |
| `danji.html` | ★느티마을3 완성형 데모 — 계산엔진·시점별 필요현금 타임라인·예측공시 박제·자금조달/알림 CTA·판정보드·커버리지 지도 |
| `detail.html` | 단지별 정보판(`?complex=`) — 실거래·월별 거래량·미니맵·알림폼 |
| `admin.html` | 관리 화면(`?key=cb-owen-2026` = 가림막, 서버 인증 아님) |
| `order.html`·`report.html` | **부트캠프 학습본**(리포트 주문/신청) — 실제 제품과 분리(두 lane) |
| `agent.html` + `api/extract.js` | 운영자 **확정값 수집 Agent**(`?key=cb-owen-2026` 게이트) → 총회 문서 붙여넣기 → 렛서 게이트웨이로 추출 → `disclosure_facts` 저장(예측공시 해자 연료) |
| `recorder.html` + `data/minutes_demo.json` | **총회 기록기 데모**(`?key=cb-owen-2026` 게이트·`noindex`) → 오프라인 Whisper 전사 타임라인 + 의사록 초안(예시=env 없이 뷰, "재생성"=`/api/extract` `mode=minutes` 라이브). 전사 정본=`scripts/transcribe_minutes.py`(오프라인·repo 런타임 의존성 아님) |
| `complexes.json`(118)·`prices.json`(국토부 실거래 3단지)·`gg_zones.json`(수도권 정비구역 1,116) | 데이터 |

**서버리스 예외**: `api/extract.js`가 repo 유일 Vercel Node 서버리스 함수(CommonJS·`fetch` 내장·**의존성 0**·package.json 없음 유지). 렛서 게이트웨이(Anthropic 호환) `/v1/messages` 호출. 키는 **Vercel 환경변수에서만**: `ANTHROPIC_BASE_URL=https://gw.letsur.ai` · `ANTHROPIC_AUTH_TOKEN=sk-…`(클라 노출 금지). Supabase 테이블 `disclosure_facts`(anon INSERT RLS, ?key 게이트가 유일 가림막). **`mode` 분기**: default(무지정)=확정값 추출(`facts`, agent.html), `mode:'minutes'`=의사록 초안(`minutes`, recorder.html). 확정값 경로는 **무회귀 락**(수정 시 default 동작 회귀 검증).

## 데이터·배관 (검증된 패턴 — 복사해서 재사용)
- Supabase project ref `lynmnuftfybbegdxjfbz`. 테이블: `reservations`·`orders`·`report_requests`.
- **RLS = 익명(anon)에게 INSERT만.** 원장 anon SELECT/UPDATE/DELETE 차단.
- **읽기는 PII 뺀 public 뷰로만**: `reservations_public`·`orders_public`(연락처·이메일·주소 제외, 이름 마스킹). ⚠️ **원장에 anon SELECT 절대 열지 말 것**(Day14 PII 유출 사고 이력).
- supabase-js `.insert()`는 **minimal 경로 사용**. `.select()`(=`return=representation`)는 INSERT 후 RETURNING → SELECT 정책 검사에 걸림(Day17 401 원인). 되읽기 필요 없으면 붙이지 말 것.
- Umami 이벤트(실제 코드 접두어): **danji** = `danji-view`·`danji-calc-done`·`danji-cta-fund`·`danji-fund-request`(=자금조달 척추 분자)·`danji-pledge`·`danji-cta-alert`·`danji-alert-request` / **detail** = `detail-view`·`detail-cta-alert`·`detail-alert-request` / **index** `sim-run` / `order-submit`·`report-request`. **전환율 = `danji-fund-request` ÷ `danji-calc-done`**. 창업자 본인 트래픽은 지표에서 제외(Umami 대시보드 필터).

## 계산엔진 (danji.html · 회귀 주의)
- 상수: `BASE_COST=750`·`BASE_BUNDAM=38000`·`SENS=0.0018`·`NEWBUILD=170000`.
- **항등식: 타임라인 버킷 합 = 총투입비**(라벨 반올림이 이걸 깨지 않게 — 잔차 흡수). 수정 시 `node --check` + 손계산 검산.
- 포맷: `eok()`(만원→n.n억, 0이면 '—')·`fmtCash()`·`round100()`.
- 입력(호가·공사비·가정값)은 판정보드 바로 위 `#calc` 섹션에 인접 — 입력↔라이브 출력 붙여둠(착시 방지).

## 안 만든다 (락 · 재론 금지)
- 전국 폴리곤 탐색 지도(재뷰 turf) · 실 PG 결제 · **로그인/회원**(무가입 진입점 유지) · **AI 문서파싱을 진입점으로**(총회책자 OCR=로드맵 후반 백엔드) · "사세요/파세요" 단정 문구(**숫자+출처만**, 유사투자자문·금소법 회피).

## 코딩 규칙
1. **성공 흐름·저장 스키마 무변경**(회귀). 기능 추가보다 "정한 범위 안정 완성".
2. 오류는 **한국어 3요소**(무슨 일+어떻게+친절), 영어 코드 노출 X, `console.error`는 개발자용 유지.
3. CDN(supabase·naver)은 **가드/`defer`** — 실패해도 페이지 살아있게.
4. innerHTML에 외부·데이터 값 넣을 땐 **escape**(XSS). 폼은 연타 방지 + 타임아웃 + 항상 버튼 복구.
5. 데이터 정직: "분담금 확인 48단지 / 구조화 3 / 위치 118". **"48 데이터 있다" 금지**, "확인 48·구조화 3, 늘리는 게 과제"만.
6. 배포 = `git add` → commit → `git push origin main` → Vercel 자동. 배포 후 라이브 200 + 핵심 흐름 확인.

## 검증 (커밋 전)
- 인라인 JS `node --check`(ld+json 스크립트 제외하고 추출).
- 중복 id 0 · `<section>` 열림/닫힘 균형 · 라이브 HTTP 200.

## 컨텍스트 (더 깊은 배경)
- 사업 SSOT = 노션 "진입점 HANDOFF v0.1.1" + "7월 모듈1 최종 PRD". 부트캠프 진행 = KAIST OverEdge Handoff.
- 지표 척추 = **계산완료 → 자금조달 연결 요청 전환율**. 해자 = **예측공시**(총회 前 추정 박제 → 확정 대조 오차이력). 다음 관문 = 해커톤(유통 첫 숫자).
- 표기: 부트캠프/발표 = 1인(오원기) · 사업/IR = 2인(+정휘준 CTO).
