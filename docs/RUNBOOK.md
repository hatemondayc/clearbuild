# CLEARBUILD 운영 런북 (Runbook)

솔로 운영자용. 사고 나면 **당황 말고 해당 항목의 절차대로**. 고급반 D18(보안·개인정보·런북) 적용.
최종 갱신: 2026-08-04

---

## 0. 비밀값이 어디 있나 (외우기)
| 키 | 어디 | 클라이언트 노출 |
|---|---|---|
| Supabase **anon 키** | HTML에 하드코딩(index·danji·detail·admin·agent) | **OK** — RLS로 안전(익명 INSERT만) |
| Supabase **service_role 키** | Supabase 대시보드에만 | **절대 클라·git 금지** (RLS 우회 = 전권) |
| 렛서 토큰(`ANTHROPIC_AUTH_TOKEN`) | **Vercel 환경변수만** | 절대 클라·git 금지 |
| admin/agent 접근 키(`?key=`) | HTML 상수 | 가림막일 뿐(인증 아님) — URL 아는 사람은 통과 |

**원칙**: 클라이언트(=공개 소스)에 들어가도 되는 건 anon 키뿐. 나머지는 전부 서버(Vercel env)·Supabase 대시보드에만.

---

## 1. 보안 점검표 10항목 (배포·변경 전 훑기)
1. [ ] service_role·렛서 토큰이 HTML/git에 안 들어갔나 (`git grep service_role` / `sk-` 확인)
2. [ ] 새 Supabase 테이블 = RLS 켜짐 + 익명은 INSERT만, 읽기는 public 뷰(PII 마스킹)로만
3. [ ] 원장(base table)에 anon SELECT/UPDATE/DELETE 정책 안 열었나 (Day14 유출 사고 재발 방지)
4. [ ] 공개 화면에 실제 이메일·휴대폰·이름 안 보이나
5. [ ] `innerHTML`에 외부·DB 값 넣을 때 escape 했나(XSS)
6. [ ] 폼: 연타 방지 + 타임아웃 + 실패해도 버튼 복구
7. [ ] 에러 메시지에 내부 정보(SQL·키·경로) 노출 안 하나 — 사용자엔 한국어 친절 문구, 상세는 `console.error`
8. [ ] 서버리스 함수(api/*)는 키를 `process.env`에서만 읽나
9. [ ] 개인정보 새 항목 수집 시작하면 privacy.html·이 런북 갱신했나
10. [ ] 배포 후 라이브 HTTP 200 + 핵심 흐름(계산·저장) 1회 확인

---

## 2. 인시던트 대응 (증상 → 원인 → 절차 → 검증 → 도움)

### A. 라이브 사이트가 안 열림 / 500
- **원인 후보**: Vercel 배포 실패 · CDN(supabase/naver) 장애 · 함수 오류
- **절차**: ① Vercel 대시보드 → Deployments 최신 상태·로그 확인 ② 직전 정상 배포로 **Rollback**(Deployments → ⋯ → Promote/Redeploy) ③ CDN 장애면 페이지는 가드로 살아있어야 정상(흰 화면이면 defer/가드 회귀)
- **검증**: `curl -I https://clearbuild-site-theta.vercel.app/` → 200
- **도움**: Vercel Status(status.vercel.com) · Supabase Status

### B. 저장이 401/RLS 오류
- **증상**: 사전신청·CTA 저장 실패, `42501 violates row-level security`
- **원인**: RLS 정책 누락, 또는 되읽기(`.select()`/`return=representation`)가 SELECT 정책 검사에 걸림(Day17 교훈)
- **절차**: ① 해당 테이블 `anon can insert` 정책 존재 확인(Supabase → Authentication → Policies) ② 코드가 `.insert()` **minimal**인지(되읽기 `.select()` 붙었으면 제거) ③ 스키마 캐시: SQL에서 `notify pgrst, 'reload schema';`
- **검증**: 익명 INSERT curl → 201
- **도움**: CLAUDE.md "데이터·배관" 섹션

### C. 개인정보(PII) 유출 의심
- **증상**: 공개 화면·API 응답·공개 뷰에 실제 이메일/휴대폰/이름 노출
- **절차**: ① 즉시 원인 경로 차단(정책 원복/배포 롤백) ② 노출 범위·기간 파악 ③ Supabase에서 노출 데이터 확인 ④ 필요 시 정보주체 통지 ⑤ 원인=원장 anon SELECT 열림이면 정책 삭제 후 public 뷰로 복귀
- **검증**: `curl "…/rest/v1/<원장>?select=email"`(anon) → 0행/권한거부 · 공개 뷰는 마스킹만
- **도움**: privacy.html · 개인정보 보호책임자(오원기)

### D. 렛서(확정값 Agent) 추출 실패
- **증상**: `/api/extract` 401/403/500/504
- **원인**: 토큰 만료·한도 · Vercel env 누락 · 문서 과대
- **절차**: ① Vercel env `ANTHROPIC_BASE_URL`·`ANTHROPIC_AUTH_TOKEN` 확인(변경 시 **재배포 필요**) ② 렛서 대시보드 토큰 유효·한도 확인 ③ 504면 문서 분할
- **검증**: `/api/extract` POST에 짧은 샘플 → `ok:true`
- **도움**: agent.html · CLAUDE.md 서버리스 예외

### E. 스팸·어뷰징 INSERT (티커·리드 오염)
- **원인**: 익명 INSERT라 URL 아는 제3자가 임의 등록 가능
- **절차**: ① Supabase에서 스팸 행 삭제 ② 필요 시 컬럼 길이 제약·레이트리밋 추가 ③ 발표·시연일엔 공개 티커 화이트리스트/off
- **검증**: 공개 화면·admin에 정상 데이터만

---

## 3. 개인정보 열람·삭제 요청 대응
1. 요청자 본인 확인(요청 이메일 = 등록 이메일 대조)
2. Supabase 대시보드 → Table Editor에서 해당 행 열람/수정/삭제
3. 처리 결과 회신, 처리 일자 기록
4. (Agent) `disclosure_facts`는 총회 공개자료 기반이라 PII 아님 — 대상 아님

---

## 4. 정기 점검 (주 1회 5분)
- Vercel 배포 상태·에러 로그
- Supabase 신규 리드 확인·팔로업(원본 PII는 **Supabase 대시보드**에서, 인증된 접근)
- 자금조달 연결 신청(척추 지표) 수 확인
- 본인 트래픽 Umami 필터 유지

---

## 5. 관리자 데이터 접근 원칙
- 공개 `admin.html`(`?key=`)은 **가림막**이지 인증이 아니다 → **원본 PII를 여기로 끌어오지 않는다.**
- 리드 원본(이메일·휴대폰) 열람·상태 관리 = **Supabase 대시보드**(실제 인증) 사용.
- 정식 관리자 인증(Supabase Auth)은 발표 후 로드맵.
