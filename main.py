# main.py
import schedule, time, logging
from datetime import datetime

from execution.auth         import load_session
from data.fetcher           import fetch_ohlc, get_vix, get_spot, get_atm_strike, get_options_chain
from signals.generator      import get_current_signal
from risk.manager           import RiskManager, atr_trailing_sl
from execution.order_engine import place_order, should_square_off, square_off_all, is_market_open
from monitoring.telegram    import trade_entry, trade_exit, daily_summary, error_alert, bot_started, bot_stopped
from monitoring.analytics   import log_trade, calc_metrics

# ── logging setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── global state ─────────────────────────────────────────────
risk     = RiskManager(capital=500_000)
position = None   # holds current open trade info
kite     = None

def get_next_expiry():
    """Returns nearest weekly NIFTY expiry — update this weekly."""
    return "2025-03-27"   # <-- update every week

def run_cycle():
    global position, kite

    try:
        # refresh session
        kite = load_session()

        # EOD square off check
        if should_square_off():
            if position:
                log.info("[EOD] Squaring off all positions")
                square_off_all(kite)
                trade_exit(
                    position["symbol"],
                    position["qty"],
                    position["entry"],
                    pnl=0   # actual PnL fetched from positions
                )
                position = None
            metrics = calc_metrics()
            daily_summary(
                pnl    = metrics.get("total_pnl", 0),
                trades = metrics.get("total_trades", 0),
                sharpe = metrics.get("sharpe")
            )
            risk.reset_daily()
            return

        if not is_market_open():
            log.info("[BOT] Market not open yet")
            return

        # fetch data
        df   = fetch_ohlc(kite, days=30)
        vix  = get_vix(kite)
        spot = get_spot(kite)
        sig  = get_current_signal(df, vix)

        log.info(f"[CYCLE] Signal={sig['direction']} | "
                 f"Spot={spot} | VIX={vix:.1f} | ADX={sig['adx']}")

        # ── EXIT logic ───────────────────────────────────────
        if position:
            sl_long, sl_short = atr_trailing_sl(df)
            sl = sl_long if position["side"] == 1 else sl_short

            # check if signal flipped or SL hit
            signal_flipped = (sig["signal"] != 0 and
                              sig["signal"] != position["side"])
            sl_hit = (position["side"] ==  1 and spot <= sl) or \
                     (position["side"] == -1 and spot >= sl)

            if signal_flipped or sl_hit:
                reason = "signal_flip" if signal_flipped else "sl_hit"
                log.info(f"[EXIT] Reason: {reason}")
                place_order(kite, position["symbol"], position["qty"], "SELL")
                pnl = (spot - position["entry"]) * position["qty"]
                if position["side"] == -1:
                    pnl = -pnl
                pnl -= 40  # brokerage estimate
                trade_exit(position["symbol"], position["qty"], spot, pnl)
                log_trade({
                    "entry_time":  position["entry_time"],
                    "exit_time":   str(datetime.now()),
                    "symbol":      position["symbol"],
                    "side":        position["side"],
                    "entry":       position["entry"],
                    "exit":        spot,
                    "qty":         position["qty"],
                    "pnl":         pnl,
                    "reason":      reason
                })
                risk.update_pnl(pnl)
                position = None

        # ── ENTRY logic ──────────────────────────────────────
        if sig["signal"] != 0 and not position and risk.can_trade():
            expiry = get_next_expiry()
            chain  = get_options_chain(kite, expiry, spot)

            # pick ATM CE or PE based on signal
            opt_type = "CE" if sig["signal"] == 1 else "PE"
            atm      = get_atm_strike(spot)
            row      = chain[
                (chain["strike"] == atm) &
                (chain["instrument_type"] == opt_type)
            ]

            if row.empty:
                log.warning(f"[ENTRY] No {opt_type} found for strike {atm}")
                return

            symbol    = row.iloc[0]["tradingsymbol"]
            lot_size  = int(row.iloc[0]["lot_size"])
            premium   = 150   # estimate — replace with live LTP
            lots      = risk.get_lots(premium, lot_size)
            qty       = lots * lot_size

            order_id  = place_order(kite, symbol, qty, "BUY")
            position  = {
                "symbol":     symbol,
                "side":       sig["signal"],
                "entry":      spot,
                "qty":        qty,
                "order_id":   order_id,
                "entry_time": str(datetime.now())
            }
            sl_long, sl_short = atr_trailing_sl(df)
            sl = sl_long if sig["signal"] == 1 else sl_short
            trade_entry(symbol, opt_type, qty, premium, sl)
            log.info(f"[ENTRY] {opt_type} {symbol} | Qty={qty} | SL={sl}")

    except Exception as e:
        log.error(f"[ERROR] {e}", exc_info=True)
        error_alert("run_cycle", str(e))

# ── scheduler ────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("[BOT] Starting Nifty Algo Trader")
    bot_started()

    # run every 15 minutes
    schedule.every(15).minutes.do(run_cycle)

    # also run immediately on start
    run_cycle()

    while True:
        schedule.run_pending()
        time.sleep(30)