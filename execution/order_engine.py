# execution/order_engine.py
import time, logging
from datetime import datetime

log = logging.getLogger(__name__)

MARKET_OPEN  = (9, 15)
MARKET_CLOSE = (15, 20)

def is_market_open():
    now = datetime.now().time()
    open_time  = now.replace(hour=MARKET_OPEN[0],  minute=MARKET_OPEN[1],  second=0)
    close_time = now.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0)
    return open_time <= now <= close_time

def should_square_off():
    now = datetime.now()
    return now.hour == 15 and now.minute >= 20

def place_order(kite, tradingsymbol, qty, side, max_retries=3):
    txn = kite.TRANSACTION_TYPE_BUY if side == "BUY" \
          else kite.TRANSACTION_TYPE_SELL
    params = {
        "tradingsymbol":    tradingsymbol,
        "exchange":         kite.EXCHANGE_NFO,
        "transaction_type": txn,
        "quantity":         qty,
        "order_type":       kite.ORDER_TYPE_MARKET,
        "product":          kite.PRODUCT_MIS,
        "variety":          kite.VARIETY_REGULAR,
    }
    for attempt in range(1, max_retries + 1):
        try:
            order_id = kite.place_order(**params)
            log.info(f"[ORDER] {side} {qty} {tradingsymbol} | ID: {order_id}")
            return order_id
        except Exception as e:
            err = str(e).lower()
            log.warning(f"[ORDER] Attempt {attempt} failed: {e}")
            if "volume freeze" in err:
                log.warning("[ORDER] Volume freeze — waiting 5s")
                time.sleep(5)
            elif "token" in err or "session" in err:
                log.error("[ORDER] Session expired — restart bot")
                raise
            elif attempt == max_retries:
                log.error(f"[ORDER] All {max_retries} attempts failed")
                raise
            time.sleep(2)

def get_open_positions(kite):
    try:
        positions = kite.positions()
        day = positions.get("day", [])
        open_pos = [p for p in day if p["quantity"] != 0]
        return open_pos
    except Exception as e:
        log.error(f"[POSITIONS] Error: {e}")
        return []

def square_off_all(kite):
    positions = get_open_positions(kite)
    if not positions:
        log.info("[EOD] No open positions to square off")
        return
    for pos in positions:
        side = "SELL" if pos["quantity"] > 0 else "BUY"
        qty  = abs(pos["quantity"])
        try:
            place_order(kite, pos["tradingsymbol"], qty, side)
            log.info(f"[EOD] Squared off {pos['tradingsymbol']}")
        except Exception as e:
            log.error(f"[EOD] Failed to square off {pos['tradingsymbol']}: {e}")