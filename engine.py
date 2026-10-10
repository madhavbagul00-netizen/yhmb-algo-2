"""YHMB ALGO - trading engine (UI-independent). Paper + Live, risk manager, user Python strategy."""
import time, threading, traceback, datetime

DEFAULT_CODE = '''# YHMB strategy - on_tick प्रत्येक price tick वर चालते
# ctx.prices (list), ctx.position (None / dict), ctx.buy(), ctx.sell(), ctx.exit(), ctx.log()
def on_tick(ctx, tick):
    p = ctx.prices
    if len(p) < 6:
        return
    sma = sum(p[-5:]) / 5
    if ctx.position is None:
        if tick > sma + 2:
            ctx.buy()
        elif tick < sma - 2:
            ctx.sell()
'''

class Risk:
    """Points-based SL/Target/Lock/Trail + daily max profit/loss in Rs."""
    def __init__(self, qty=50, sl=15, target=30, lock_at=12, lock_val=4,
                 trail_x=5, trail_y=5, max_profit=5000, max_loss=3000):
        self.qty, self.sl, self.target = qty, sl, target
        self.lock_at, self.lock_val = lock_at, lock_val
        self.trail_x, self.trail_y = trail_x, trail_y
        self.max_profit, self.max_loss = max_profit, max_loss

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: float(v) for k, v in d.items() if k in cls().__dict__})

class Position:
    def __init__(self, side, entry, qty, risk):
        self.side, self.entry, self.qty = side, entry, qty
        self.d = 1 if side == "BUY" else -1
        self.sl = entry - self.d * risk.sl
        self.target = entry + self.d * risk.target
        self.trail_ref, self.locked = entry, False
    def pts(self, ltp): return (ltp - self.entry) * self.d
    def as_dict(self):
        return dict(side=self.side, entry=self.entry, qty=self.qty, sl=self.sl, target=self.target)

class Ctx:
    """Object passed to the user's strategy."""
    def __init__(self, eng): self._e = eng; self.prices = []; self.params = {}
    @property
    def position(self): return self._e.pos.as_dict() if self._e.pos else None
    def buy(self): self._e.enter("BUY")
    def sell(self): self._e.enter("SELL")
    def exit(self): self._e.close("Strategy exit")
    def log(self, m): self._e.log(str(m))

class Engine:
    def __init__(self, broker, symbol, risk, code, mode="PAPER", on_update=None, interval=1.0):
        self.broker, self.symbol, self.risk, self.mode = broker, symbol, risk, mode
        self.code, self.on_update, self.interval = code, on_update, interval
        self.pos = None; self.day_pnl = 0.0; self.trades = []; self.logs = []
        self.ltp = 0.0; self.running = False; self.ctx = Ctx(self); self._fn = None

    def log(self, m):
        self.logs.append(f"{datetime.datetime.now():%H:%M:%S} {m}"); self.logs = self.logs[-200:]
    def _notify(self):
        if self.on_update: self.on_update(self)

    def compile(self):
        ns = {}
        exec(compile(self.code, "<strategy>", "exec"), ns)
        if "on_tick" not in ns: raise ValueError("on_tick(ctx, tick) function आवश्यक आहे")
        self._fn = ns["on_tick"]

    @property
    def open_pnl(self): return self.pos.pts(self.ltp) * self.pos.qty if self.pos else 0.0
    @property
    def total_pnl(self): return self.day_pnl + self.open_pnl

    def enter(self, side):
        if self.pos or not self.running: return
        if self.total_pnl >= self.risk.max_profit or self.total_pnl <= -self.risk.max_loss: return
        q = int(self.risk.qty)
        fill = self.broker.place_order(self.symbol, side, q, self.ltp, live=(self.mode == "LIVE"))
        self.pos = Position(side, fill, q, self.risk); self.log(f"{self.mode} {side} {q} @ {fill:.2f}")

    def close(self, why):
        if not self.pos: return
        side = "SELL" if self.pos.side == "BUY" else "BUY"
        try:
            fill = self.broker.place_order(self.symbol, side, self.pos.qty, self.ltp, live=(self.mode == "LIVE"))
        except Exception as e:   # exit fail झाल्यास position उघडी मानली जाते; पुढच्या tick ला पुन्हा प्रयत्न
            self.log(f"⚠ EXIT FAILED ({e}) - पुन्हा प्रयत्न / broker मध्ये तपासा"); return False
        pnl = (fill - self.pos.entry) * self.pos.d * self.pos.qty
        self.day_pnl += pnl
        self.trades.insert(0, dict(t=f"{datetime.datetime.now():%H:%M:%S}", side=self.pos.side,
                                   entry=self.pos.entry, exit=fill, why=why, pnl=pnl))
        self.log(f"EXIT {why} @ {fill:.2f}  P&L {pnl:.0f}"); self.pos = None; return True

    def risk_check(self):
        p, r = self.pos, self.risk
        if not p: return
        pf = p.pts(self.ltp)
        if not p.locked and r.lock_at > 0 and pf >= r.lock_at:       # lock profit
            p.locked = True; p.sl = p.entry + p.d * r.lock_val; self.log(f"Profit locked, SL {p.sl:.2f}")
        if r.trail_x > 0 and (self.ltp - p.trail_ref) * p.d >= r.trail_x:  # trail profit
            p.trail_ref += p.d * r.trail_x; p.sl += p.d * r.trail_y; self.log(f"Trail SL -> {p.sl:.2f}")
        if (self.ltp - p.sl) * p.d <= 0: return self.close("Stop Loss" if not p.locked else "Lock/Trail SL")
        if (self.ltp - p.target) * p.d >= 0: return self.close("Target")
        if self.total_pnl >= r.max_profit: return self.close("Max Profit")
        if self.total_pnl <= -r.max_loss: return self.close("Max Loss")

    def start(self):
        self.compile(); self.running = True
        threading.Thread(target=self._loop, daemon=True).start(); self.log(f"Started ({self.mode})")

    def stop(self, square_off=True):
        if square_off and not self.close("Manual stop") and self.pos:
            self.log("⚠ पोझिशन अजून उघडी आहे - broker app मध्ये manually बंद करा")
        self.running = False; self.log("Stopped"); self._notify()

    def _loop(self):
        while self.running:
            try:
                self.ltp = self.broker.ltp(self.symbol); self.ctx.prices.append(self.ltp)
                self.ctx.prices = self.ctx.prices[-500:]
                self.risk_check()
                if self.running: self._fn(self.ctx, self.ltp)
            except Exception:
                self.log("ERROR: " + traceback.format_exc().splitlines()[-1])
            self._notify(); time.sleep(self.interval)
