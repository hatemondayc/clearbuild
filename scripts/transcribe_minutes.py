#!/usr/bin/env python3
# 총회 기록기 데모 — 오프라인 전사 생성기 (offline only · 브라우저/서버리스 실행 안 함)
# macOS `say`(한국어)로 샘플 총회 오디오 합성 → Whisper 전사 → data/minutes_demo.json.
# 정적 사이트(recorder.html)는 이 JSON만 읽는다(CLAUDE.md 정적 락 준수).
# 실행: ~/Desktop/pai-lab/.venv/bin/python scripts/transcribe_minutes.py  (+ macOS say, ffmpeg)
# 의존: whisper·soundfile·numpy(pai-lab venv) · say·ffmpeg(시스템). repo 런타임 의존성 아님.
import os, json, subprocess, tempfile, datetime
import numpy as np, whisper, soundfile as sf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "minutes_demo.json")

# 데모용 총회 스크립트(합성 음성으로 읽힘 — 실제 녹음 아님)
SCRIPT = (
    "제38차 정기총회를 시작하겠습니다. 오늘 안건은 세 가지입니다. "
    "첫째, 시공사 선정 변경 건입니다. 공사비 인상으로 조합원 분담금이 평균 십팔 퍼센트 오를 전망입니다. "
    "김 조합원 발언하겠습니다. 저는 분담금 인상 폭이 너무 크다고 봅니다. 재검토를 요청합니다. "
    "둘째, 관리처분계획 변경 건은 대의원회 의결로 넘기겠습니다. "
    "셋째, 이주비 대출 조건 안건은 다음 총회로 연기합니다. "
    "표결 결과 시공사 선정 변경 건은 찬성 이백삼십 표로 가결되었습니다. 이상으로 총회를 마칩니다."
)
PROMPT = "재건축 조합 정기총회 회의록. 분담금, 조합원, 대의원, 분양가, 관리처분계획, 시공사, 이주비, 표결 안건."

def synth_audio(text, wav_path):
    aiff = wav_path.replace(".wav", ".aiff")
    try:  # macOS 한국어 음성 Yuna, 없으면 기본
        subprocess.run(["say", "-v", "Yuna", "-o", aiff, text], check=True)
    except Exception:
        subprocess.run(["say", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", aiff, "-ar", "16000", "-ac", "1", wav_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def main():
    with tempfile.TemporaryDirectory() as td:
        wav = synth_audio(SCRIPT, os.path.join(td, "meeting.wav"))
        audio, sr = sf.read(wav); audio = np.asarray(audio, dtype="float32")
        model = whisper.load_model("base")
        r = model.transcribe(audio, language="ko", fp16=False, beam_size=5, initial_prompt=PROMPT)
    segs = [{"start": round(float(s["start"]), 1), "end": round(float(s["end"]), 1),
             "text": s["text"].strip()} for s in r["segments"]]
    out = {
        "meta": {
            "generated": datetime.date.today().isoformat(),
            "model": "whisper-base (제로샷 · 디코딩 beam5+정비 initial_prompt)",
            "source": "데모용 합성 음성(macOS say) — 실제 총회 녹음 아님",
            "note": "오프라인 전사(offline only). 정적 사이트는 이 JSON만 읽음.",
        },
        "segments": segs,
        "full_text": r["text"].strip(),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("전사 세그먼트:", len(segs), "→", os.path.relpath(OUT, HERE))
    for s in segs:
        print(f"  [{s['start']:>5.1f}s] {s['text']}")

if __name__ == "__main__":
    main()
