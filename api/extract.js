// api/extract.js — 총회 문서 → 구조화 확정값(JSON) 추출
// Vercel Node 서버리스 함수 (CommonJS, 의존성 0 · fetch 내장).
// 렛서 게이트웨이(Anthropic 호환)의 /v1/messages 호출.
// 키는 클라이언트에 절대 노출 X → Vercel 환경변수에서만 읽음:
//   ANTHROPIC_BASE_URL = https://gw.letsur.ai
//   ANTHROPIC_AUTH_TOKEN = sk-... (렛서 토큰)
//   EXTRACT_MODEL = (선택) 기본 claude-sonnet-4-5-20250929

const MODEL_DEFAULT = 'claude-sonnet-4-5-20250929';
const MAX_INPUT = 40000; // 문서 길이 상한(자)
const CALL_TIMEOUT_MS = 50000;

const SYSTEM = [
  '너는 한국 정비사업(재개발·재건축·리모델링·가로주택) 총회 자료에서 숫자·확정값을 정확히 추출하는 도구다.',
  '규칙:',
  '- 문서에 실제로 있는 값만 뽑는다. 문서에 없는 값은 절대 지어내지 않는다.',
  '- 각 값에 반드시 원문 근거 문장(source_sentence)과 신뢰 등급(grade)을 붙인다.',
  '  · A = 총회에서 "확정"으로 명시된 값',
  '  · B = 근거는 있으나 추정·예상·잠정 표현',
  '  · C = 언급은 있으나 값이 불명확',
  '- 대상 항목 예: 감정가, 비례율, 조합원분양가, 일반분양가, 예상분담금/확정분담금, 이주비, 총투입비, 사업단계, 총회일자, 세대수, 평당 공사비. 문서에 있는 것만.',
  '- value는 문서 표기 그대로 쓴다(예: "3.8억", "112.5%", "750만원/평", "2026-03-15").',
  '출력: 오직 JSON 배열만. 설명·머리말·코드펜스 없이.',
  '형식: [{"item":"항목","value":"값","unit":"단위(선택)","grade":"A|B|C","source_sentence":"원문 근거 문장"}]',
  '값이 하나도 없으면 [] 를 출력한다.'
].join('\n');

function parseFacts(s) {
  if (!s) return null;
  let t = String(s).trim();
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) t = fence[1].trim();
  try { const j = JSON.parse(t); return Array.isArray(j) ? j : (Array.isArray(j.facts) ? j.facts : null); } catch (e) {}
  const a = t.indexOf('['), b = t.lastIndexOf(']');
  if (a >= 0 && b > a) { try { const j = JSON.parse(t.slice(a, b + 1)); return Array.isArray(j) ? j : null; } catch (e) {} }
  return null;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') { res.status(405).json({ ok: false, error: 'POST 요청만 허용됩니다.' }); return; }

  const BASE = process.env.ANTHROPIC_BASE_URL;
  const TOKEN = process.env.ANTHROPIC_AUTH_TOKEN;
  const MODEL = process.env.EXTRACT_MODEL || MODEL_DEFAULT;
  if (!BASE || !TOKEN) {
    res.status(500).json({ ok: false, error: '서버 설정이 아직 안 됐어요. 관리자에게 ANTHROPIC_BASE_URL·ANTHROPIC_AUTH_TOKEN 설정을 요청하세요.' });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  if (!body || typeof body !== 'object') body = {};
  const text = typeof body.text === 'string' ? body.text : '';
  const complex = typeof body.complex === 'string' ? body.complex.slice(0, 100) : '';

  if (!text || text.trim().length < 10) { res.status(400).json({ ok: false, error: '추출할 총회 문서 텍스트를 붙여넣어 주세요.' }); return; }
  if (text.length > MAX_INPUT) { res.status(413).json({ ok: false, error: `문서가 너무 깁니다. ${MAX_INPUT.toLocaleString()}자 이하로 나눠 주세요.` }); return; }

  const userContent = `단지: ${complex || '(미지정)'}\n\n총회 문서:\n"""\n${text}\n"""`;

  const controller = new AbortController();
  const to = setTimeout(function () { controller.abort(); }, CALL_TIMEOUT_MS);
  let resp;
  try {
    resp = await fetch(BASE.replace(/\/$/, '') + '/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'anthropic-version': '2023-06-01',
        'authorization': 'Bearer ' + TOKEN,
        'x-api-key': TOKEN
      },
      body: JSON.stringify({ model: MODEL, max_tokens: 4000, system: SYSTEM, messages: [{ role: 'user', content: userContent }] }),
      signal: controller.signal
    });
  } catch (err) {
    clearTimeout(to);
    if (err && err.name === 'AbortError') { res.status(504).json({ ok: false, error: '추출 응답이 늦어졌어요(50초 초과). 문서를 줄여 다시 시도해 주세요.' }); return; }
    console.error('extract fetch error', err);
    res.status(502).json({ ok: false, error: '추출 서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.' });
    return;
  }
  clearTimeout(to);

  if (!resp.ok) {
    let detail = '';
    try { detail = (await resp.text()).slice(0, 500); } catch (e) {}
    console.error('extract upstream', resp.status, detail);
    if (resp.status === 401 || resp.status === 403) { res.status(502).json({ ok: false, error: '추출 서버 인증에 실패했어요. 토큰 설정을 확인해 주세요.' }); return; }
    if (resp.status === 429) { res.status(429).json({ ok: false, error: '요청이 몰렸어요. 잠시 후 다시 시도해 주세요.' }); return; }
    res.status(502).json({ ok: false, error: '추출 서버가 오류를 반환했어요. 잠시 후 다시 시도해 주세요.' });
    return;
  }

  let data;
  try { data = await resp.json(); } catch (e) { res.status(502).json({ ok: false, error: '추출 응답을 읽지 못했어요.' }); return; }

  if (data && data.stop_reason === 'refusal') { res.status(200).json({ ok: false, error: '모델이 이 문서 처리를 거절했어요. 개인정보·민감정보를 빼고 다시 시도해 주세요.' }); return; }

  const raw = (Array.isArray(data.content) ? data.content : []).filter(function (b) { return b && b.type === 'text'; }).map(function (b) { return b.text || ''; }).join('');
  const facts = parseFacts(raw);
  if (!facts) { res.status(200).json({ ok: false, error: '결과를 JSON으로 해석하지 못했어요. 아래 원문을 보고 수동 정리해 주세요.', raw: raw.slice(0, 2000) }); return; }

  res.status(200).json({ ok: true, facts: facts, model: (data && data.model) || MODEL, usage: (data && data.usage) || null });
};

// Vercel 함수 최대 실행시간(초). Hobby 플랜은 60초 상한.
module.exports.config = { maxDuration: 60 };
