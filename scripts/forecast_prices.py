#!/usr/bin/env python3
# 시세 예측공시 오프라인 생성기 (offline only — 브라우저/서버리스에서 실행 안 함)
# data/prices.json 의 단지별 월별 median 시계열 → Chronos-Bolt(결정적) 예측 + 백테스트
# → data/forecasts.json 생성. 정적 사이트는 이 JSON만 읽는다(CLAUDE.md 정적 락 준수).
#
# 실행:  ~/Desktop/pai-lab/.venv/bin/python scripts/forecast_prices.py
# 의존:  chronos-forecasting · torch · numpy (pai-lab venv). repo 런타임 의존성 아님.
import json, os, datetime
import numpy as np, torch
from chronos import BaseChronosPipeline

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(HERE, "data", "prices.json")
OUT  = os.path.join(HERE, "data", "forecasts.json")

HORIZON = 3          # 예측 개월
BACKTEST = 3         # 되맞춰볼 개월(오차이력)
MODEL = "amazon/chronos-bolt-small"   # 결정적=재현 가능(같은 입력→같은 JSON)
QUANTILES = [0.1, 0.5, 0.9]

# --- 자기검열(데이터 정직): 이 기준 미달이면 예측 표시 안 함 ---
MIN_MONTHS = 12          # 표본 최소 12개월
MAX_BAND_RATIO = 0.30    # 마지막 예측달 (P90-P10)/P50 이 30% 넘으면 보류

def next_ym(ym):
    y, m = int(ym[:4]), int(ym[4:])
    m += 1
    if m > 12: y, m = y + 1, 1
    return f"{y}{m:02d}"

def mape(actual, pred):
    a = np.asarray(actual, float); p = np.asarray(pred, float)
    return float(np.mean(np.abs((a - p) / a)) * 100)

def forecast_series(pipe, values, h, qs):
    ctx = torch.tensor(np.asarray(values, dtype="float32"))
    q, _ = pipe.predict_quantiles(inputs=ctx, prediction_length=h, quantile_levels=qs)
    return q[0].numpy()   # shape (h, len(qs))

def main():
    d = json.load(open(SRC, encoding="utf-8"))
    pipe = BaseChronosPipeline.from_pretrained(MODEL, device_map="mps", torch_dtype=torch.float32)
    out = {
        "meta": {
            "model": MODEL,
            "generated": datetime.date.today().isoformat(),
            "source_asof": d.get("meta", {}).get("downloaded"),
            "horizon_months": HORIZON,
            "basis": "월별 실거래 median(평형 혼재) · 국토부",
            "self_censor": {"min_months": MIN_MONTHS, "max_band_ratio": MAX_BAND_RATIO},
        },
        "forecasts": {},
    }
    for name, z in d["forecasts" if "forecasts" in d else "prices"].items():
        m = z.get("monthly", [])
        if len(m) < 4:
            out["forecasts"][name] = {"show": False, "reason": "표본 극소", "n_months": len(m)}
            continue
        yms = [r["ym"] for r in m]
        vals = [float(r["median"]) for r in m]

        # 예측
        fq = forecast_series(pipe, vals, HORIZON, QUANTILES)  # (H,3): P10,P50,P90
        fym = []
        cur = yms[-1]
        for _ in range(HORIZON):
            cur = next_ym(cur); fym.append(cur)
        forecast = [{"ym": fym[i],
                     "p10": round(float(fq[i, 0])), "p50": round(float(fq[i, 1])),
                     "p90": round(float(fq[i, 2]))} for i in range(HORIZON)]

        # 백테스트(오차이력): 마지막 BACKTEST개월 가리고 되맞춤 → MAPE, 베이스라인 대비
        bt = None
        if len(vals) >= BACKTEST + 4:
            ctx_bt, hold = vals[:-BACKTEST], vals[-BACKTEST:]
            bq = forecast_series(pipe, ctx_bt, BACKTEST, QUANTILES)
            p50_bt = bq[:, 1]
            base = [ctx_bt[-1]] * BACKTEST  # 베이스라인=마지막값 반복
            bt = {"held_out": BACKTEST,
                  "mape": round(mape(hold, p50_bt), 1),
                  "baseline_mape": round(mape(hold, base), 1)}

        last = forecast[-1]
        band_ratio = (last["p90"] - last["p10"]) / last["p50"] if last["p50"] else 9.9
        show = (len(vals) >= MIN_MONTHS) and (band_ratio <= MAX_BAND_RATIO)
        reason = None
        if not show:
            reason = "표본 부족" if len(vals) < MIN_MONTHS else "불확실 범위 과대"

        out["forecasts"][name] = {
            "show": show,
            "reason": reason,
            "n_months": len(vals),
            "band_ratio": round(band_ratio, 2),
            "history": [{"ym": yms[i], "median": round(vals[i])} for i in range(len(vals))],
            "forecast": forecast,
            "backtest": bt,
        }
        tag = "SHOW" if show else f"hold({reason})"
        print(f"[{name}] {len(vals)}개월 · band_ratio {band_ratio:.2f} · {tag}"
              + (f" · backtest MAPE {bt['mape']}% (baseline {bt['baseline_mape']}%)" if bt else ""))

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("→ 저장:", os.path.relpath(OUT, HERE))

if __name__ == "__main__":
    main()
