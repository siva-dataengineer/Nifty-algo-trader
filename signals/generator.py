# signals/generator.py
import pandas_ta as ta
import logging

log = logging.getLogger(__name__)

def compute_signals(df, vix, adx_threshold=20, vix_threshold=18):
    # EMA Golden Cross
    df["ema50"]  = ta.ema(df["close"], length=50)
    df["ema200"] = ta.ema(df["close"], length=200)

    # ADX trend strength filter
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    df["adx"] = adx[f"ADX_14"]

    # raw signal
    df["signal"] = 0
    df.loc[df["ema50"] > df["ema200"], "signal"] =  1  # bullish → buy Call
    df.loc[df["ema50"] < df["ema200"], "signal"] = -1  # bearish → buy Put

    # ADX gate — no trade in sideways market
    df.loc[df["adx"] < adx_threshold, "signal"] = 0

    # VIX gate — no trade in high volatility
    if vix > vix_threshold:
        df["signal"] = 0
        log.warning(f"[GATE] VIX={vix:.1f} > {vix_threshold} — all signals blocked")

    return df

def get_current_signal(df, vix):
    if len(df) < 200:
        log.warning("Not enough data for EMA200 — need at least 200 bars")
        return {"signal": 0, "reason": "insufficient_data"}

    df = compute_signals(df, vix)
    last = df.iloc[-1]

    signal_map = {1: "CALL", -1: "PUT", 0: "FLAT"}
    reason = "ok"
    if vix > 18:
        reason = f"vix_high({vix:.1f})"
    elif last["adx"] < 20:
        reason = f"adx_weak({last['adx']:.1f})"

    result = {
        "signal":  int(last["signal"]),
        "direction": signal_map[int(last["signal"])],
        "ema50":   round(last["ema50"], 2),
        "ema200":  round(last["ema200"], 2),
        "adx":     round(last["adx"], 2),
        "close":   round(last["close"], 2),
        "time":    str(df.index[-1]),
        "reason":  reason
    }

    log.info(f"[SIGNAL] {result['direction']} | EMA50={result['ema50']} "
             f"EMA200={result['ema200']} ADX={result['adx']} VIX={vix}")
    return result