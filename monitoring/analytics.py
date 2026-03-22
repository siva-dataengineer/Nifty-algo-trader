# monitoring/analytics.py
import pandas as pd
import numpy as np
import logging

log = logging.getLogger(__name__)
TRADE_LOG = "logs/trades.csv"

def log_trade(trade: dict):
    df = pd.DataFrame([trade])
    try:
        existing = pd.read_csv(TRADE_LOG)
        df = pd.concat([existing, df], ignore_index=True)
    except FileNotFoundError:
        pass
    df.to_csv(TRADE_LOG, index=False)
    log.info(f"[LOG] Trade saved: {trade}")

def calc_metrics(csv_path=TRADE_LOG):
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        log.warning("[ANALYTICS] No trade log found yet")
        return {}

    if df.empty or "pnl" not in df.columns:
        return {}

    pnl    = df["pnl"]
    equity = pnl.cumsum()
    dd     = equity - equity.cummax()
    ann    = 252

    sharpe  = (pnl.mean() / pnl.std() * np.sqrt(ann)) if pnl.std() > 0 else 0
    losses  = pnl[pnl < 0]
    sortino = (pnl.mean() / losses.std() * np.sqrt(ann)) if len(losses) > 1 else 0
    max_dd  = dd.min()
    wins    = (pnl > 0).sum()
    win_pct = round(wins / len(pnl) * 100, 1)

    metrics = {
        "total_trades":  len(pnl),
        "total_pnl":     round(pnl.sum(), 2),
        "win_pct":       win_pct,
        "sharpe":        round(sharpe, 2),
        "sortino":       round(sortino, 2),
        "max_drawdown":  round(max_dd, 2),
        "avg_pnl":       round(pnl.mean(), 2),
        "best_trade":    round(pnl.max(), 2),
        "worst_trade":   round(pnl.min(), 2),
    }
    log.info(f"[ANALYTICS] {metrics}")
    return metrics