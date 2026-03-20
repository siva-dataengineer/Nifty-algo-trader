# risk/manager.py
import pandas_ta as ta
import logging

log = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, capital=500_000, max_loss_pct=0.02,
                 target_pct=0.03, risk_per_trade=0.01):
        self.capital       = capital
        self.daily_pnl     = 0.0
        self.max_loss      = capital * max_loss_pct    # ₹10,000
        self.daily_target  = capital * target_pct      # ₹15,000
        self.risk_per_trade = capital * risk_per_trade # ₹5,000
        self.trades_today  = 0
        self.max_trades    = 3  # max 3 trades per day

    def can_trade(self):
        if self.daily_pnl <= -self.max_loss:
            log.warning(f"[RISK] Daily loss limit hit: ₹{self.daily_pnl:.0f}")
            return False
        if self.daily_pnl >= self.daily_target:
            log.info(f"[RISK] Daily target hit: ₹{self.daily_pnl:.0f}")
            return False
        if self.trades_today >= self.max_trades:
            log.warning(f"[RISK] Max trades/day reached: {self.trades_today}")
            return False
        return True

    def get_lots(self, option_premium, lot_size=50):
        if option_premium <= 0:
            return 1
        risk_per_lot = option_premium * lot_size
        lots = int(self.risk_per_trade / risk_per_lot)
        return max(1, lots)

    def update_pnl(self, pnl):
        self.daily_pnl += pnl
        self.trades_today += 1
        log.info(f"[RISK] PnL updated: ₹{self.daily_pnl:.0f} | Trades: {self.trades_today}")

    def reset_daily(self):
        self.daily_pnl    = 0.0
        self.trades_today = 0
        log.info("[RISK] Daily stats reset")

def atr_trailing_sl(df, period=14, multiplier=1.5):
    atr = ta.atr(df["high"], df["low"], df["close"], length=period)
    current_atr = atr.iloc[-1]
    close       = df["close"].iloc[-1]
    sl_long  = round(close - multiplier * current_atr, 2)
    sl_short = round(close + multiplier * current_atr, 2)
    log.info(f"[SL] ATR={current_atr:.2f} | Long SL={sl_long} | Short SL={sl_short}")
    return sl_long, sl_short