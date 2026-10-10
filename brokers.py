"""Broker adapters. Each: login(cfg), ltp(symbol), place_order(symbol, side, qty, price, live)."""
import random

class Broker:
    name = "Base"; connected = False
    def login(self, cfg): raise NotImplementedError
    def ltp(self, symbol): raise NotImplementedError
    def place_order(self, symbol, side, qty, price, live=False): raise NotImplementedError

class PaperFeed(Broker):
    """Simulated feed + virtual fills (works without any broker)."""
    name = "Paper"; connected = True
    def __init__(self, start=24500.0): self.p = start
    def login(self, cfg): return True
    def ltp(self, symbol):
        self.p += random.gauss(0, 3); return round(self.p, 2)
    def place_order(self, symbol, side, qty, price, live=False): return price

class _Real(Broker):
    """Real broker for market data. Paper mode = real LTP + virtual orders.
    Live mode = real orders (must run from a SEBI-whitelisted static IP)."""
    def place_order(self, symbol, side, qty, price, live=False):
        return self._order(symbol, side, qty) if live else price

class AngelOne(_Real):
    name = "Angel One"
    def login(self, cfg):
        import pyotp
        from SmartApi import SmartConnect          # pip install smartapi-python
        self.api = SmartConnect(api_key=cfg["api_key"])
        r = self.api.generateSession(cfg["client_id"], cfg["password"], pyotp.TOTP(cfg["totp"].replace(" ", "")).now())
        if not r.get("status"): raise RuntimeError(r.get("message", "Angel login failed"))
        self.connected = True; return True
    def _parse(self, symbol):  # "NSE:NIFTY:99926000" -> exch, name, token
        e, n, t = symbol.split(":"); return e, n, t
    def ltp(self, symbol):
        e, n, t = self._parse(symbol)
        return float(self.api.ltpData(e, n, t)["data"]["ltp"])
    def _order(self, symbol, side, qty):
        e, n, t = self._parse(symbol)
        oid = self.api.placeOrder({"variety": "NORMAL", "tradingsymbol": n, "symboltoken": t,
            "transactiontype": side, "exchange": e, "ordertype": "MARKET", "producttype": "INTRADAY",
            "duration": "DAY", "quantity": str(qty)})
        return self.ltp(symbol)

class Zerodha(_Real):
    name = "Zerodha"
    def login(self, cfg):
        from kiteconnect import KiteConnect        # pip install kiteconnect
        self.kite = KiteConnect(api_key=cfg["api_key"])
        # Zerodha रोज login करतो: request_token (किंवा access_token) paste करा
        if cfg.get("access_token"): self.kite.set_access_token(cfg["access_token"])
        else:
            s = self.kite.generate_session(cfg["request_token"], api_secret=cfg["password"])
            self.kite.set_access_token(s["access_token"])
        self.connected = True; return True
    def ltp(self, symbol): return float(self.kite.ltp([symbol])[symbol]["last_price"])   # "NSE:NIFTY 50"
    def _order(self, symbol, side, qty):
        ex, ts = symbol.split(":", 1)
        self.kite.place_order(variety="regular", exchange=ex, tradingsymbol=ts, transaction_type=side,
            quantity=qty, product="MIS", order_type="MARKET")
        return self.ltp(symbol)

class AliceBlue(_Real):
    name = "Alice Blue"
    def login(self, cfg):
        from pya3 import Aliceblue                 # pip install pya3
        self.a = Aliceblue(user_id=cfg["client_id"], api_key=cfg["api_key"])
        self.a.get_session_id(); self.connected = True; return True
    def ltp(self, symbol):
        ex, n = symbol.split(":", 1)
        return float(self.a.get_scrip_info(self.a.get_instrument_by_symbol(ex, n))["LTP"])
    def _order(self, symbol, side, qty):
        from pya3 import TransactionType, OrderType, ProductType
        ex, n = symbol.split(":", 1)
        self.a.place_order(transaction_type=TransactionType.Buy if side == "BUY" else TransactionType.Sell,
            instrument=self.a.get_instrument_by_symbol(ex, n), quantity=qty, order_type=OrderType.Market,
            product_type=ProductType.Intraday)
        return self.ltp(symbol)

class Sahi(_Real):
    name = "Sahi"
    def login(self, cfg):
        raise NotImplementedError("Sahi ची public trading API documentation उपलब्ध झाल्यावर इथे जोडा (login/ltp/_order).")

class Gateway(Broker):
    """ॲप -> तुमचा VPS gateway (static IP). Live orders VPS वरून broker ला जातात; Paper मध्ये फक्त भाव घेतो."""
    name = "VPS Gateway"
    def _req(self, path, body=None):
        import json, urllib.request
        r = urllib.request.Request(self.url + path, headers={"X-Token": self.token, "Content-Type": "application/json"},
                                   data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(r, timeout=10) as f: return json.loads(f.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(json.loads(e.read() or b"{}").get("error", f"HTTP {e.code}"))
    def login(self, cfg):
        self.url = cfg["gateway_url"].rstrip("/"); self.token = cfg["gateway_token"]
        if not self.url.startswith("https://") and "127.0.0.1" not in self.url and "localhost" not in self.url:
            raise RuntimeError("Gateway URL https:// असावा")
        h = self._req("/health"); self.name = "Gateway→" + str(h.get("broker")); self.connected = True; return True
    def ltp(self, symbol):
        from urllib.parse import quote
        return float(self._req("/ltp?symbol=" + quote(symbol))["ltp"])
    def place_order(self, symbol, side, qty, price, live=False):
        if not live: return price
        fill = float(self._req("/order", {"symbol": symbol, "side": side, "qty": qty})["fill"])
        return fill if fill > 0 else price

BROKERS = {"Paper (No broker)": PaperFeed, "Angel One": AngelOne, "Zerodha": Zerodha,
           "Alice Blue": AliceBlue, "Sahi": Sahi, "VPS Gateway": Gateway}
