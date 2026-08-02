# CLEARBUILD — 정비사업 분담금·필요현금 시뮬레이터 (웹)

재개발·재건축·리모델링 조합원/매수희망자가 "내가 결국 얼마를 내야 하는가"를
계산하는 **정적 웹사이트**. Vercel에서 레포 루트를 그대로 서빙한다.

> ℹ️ 이 레포는 **KAIST OverEdge 부트캠프·발표 라인**의 정적 사이트다.
> 실제 제품 백엔드/프런트엔드(`clearbuild-backend`·`clearbuild-frontend`)와는 별개 라인.

- 라이브: https://clearbuild-site-theta.vercel.app/
- 스택: 순수 HTML/CSS/JS (빌드 없음) + Supabase(리드 저장) + NAVER 지도 + Umami(분석)

## 페이지 지도

### 제품 라인 (핵심 — 서로만 링크)
| 파일 | 역할 | URL |
|---|---|---|
| `index.html` | 홈 — 서비스 소개·정비구역 지도·사전신청 폼 | `/` |
| `danji.html` | 단지 데모(느티마을3) — 분담금 계산·필요현금 타임라인·예측공시 | `/danji.html` |
| `detail.html` | 단지별 상세 (danji 지도에서 `?complex=` 로 진입) | `/detail.html?complex=...` |

> sitemap 등재 URL은 `/` 와 `/danji.html` 두 개. **이 두 경로는 피치덱·SEO에
> 박혀 있으므로 변경 금지.**

### 부트캠프 라인 (KAIST 과제 산출물 — 고아 페이지, 제품과 무관)
| 파일 | 역할 | 비고 |
|---|---|---|
| `order.html` | Day17 리포트 주문 미니몰 | 별도 `orders` 테이블, noindex |
| `report.html` | Day16 3만원 리포트 probe | 별도 `report_requests` 테이블, noindex |
| `lp.html` | 전환 랜딩 실험 | `reservations` 공유, 실험용 |
| `admin.html` | 리드 관리 화면(초기 버전) | ⚠️ 아래 "알려진 상태" 참조 |

> 위 4개는 제품 3페이지·sitemap 어디서도 링크되지 않는다. KAIST 제출 URL로
> 살아 있으므로 리뷰 기간 중에는 유지. 리뷰 종료 후 정리 예정.

## 데이터 파일 (프런트가 fetch — 경로 변경 시 HTML 수정 필요)
| 파일 | 내용 | 사용처 |
|---|---|---|
| `complexes.json` | 리모델링 단지 118곳 (세대수·준공연도·계산 파라미터) | index, danji, detail |
| `gg_zones.json` | 경기·서울·인천 정비구역 1,116곳 + 좌표 | danji |
| `prices.json` | 실거래가 | detail |

원천 raw는 `raw/`(git 제외). 재생성 절차는 아래 파이프라인 참조.

## 로컬 실행
```bash
python3 -m http.server 8000   # 레포 루트에서. fetch가 절대경로(/...)라 file:// 로는 안 열림
```

## 배포
`main`에 push → Vercel 자동 배포 (프로젝트: `clearbuild-site`). 빌드 스텝 없음.

## 데이터 파이프라인 (지오코딩)
```bash
python3 scripts/geocode_gg.py <KAKAO_REST_KEY>   # 레포 루트에서 실행 (cwd 기준)
# gg_zones.json에서 좌표 없는 구역만 카카오 지오코딩 후 같은 파일에 덮어씀
# KAKAO REST 키는 인자로만 전달 — 코드·커밋에 넣지 말 것
```

## 키 정책 (중요)
- HTML에 보이는 **Supabase anon key / NAVER `ncpKeyId` / Umami website-id 는
  의도된 공개값**이다. anon key는 RLS로 보호(`reservations`는 anon INSERT만 허용,
  SELECT 거부 확인됨), NAVER 키는 도메인 제한. **지우지 말 것.**
- 시크릿(`service_role`, Kakao REST 키)은 이 레포에 없으며, 커밋 금지.

## 알려진 상태
- 리드 확인은 **Supabase 대시보드 Table Editor** 사용 (`admin.html`은 anon SELECT가
  RLS로 막혀 있어 데이터 로드가 안 될 수 있음 — 필요 시 Supabase Auth 기반 재작성 예정).
- 커스텀 도메인 미도입 — canonical/og/sitemap에 `-theta.vercel.app` 도메인이 박혀 있어
  도메인 도입 시 일괄 치환 필요.
