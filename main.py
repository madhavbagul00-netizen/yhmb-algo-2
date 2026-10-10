"""YHMB ALGO APP - Android/desktop app (Kivy)."""
import os, json
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from engine import Engine, Risk, DEFAULT_CODE
from brokers import BROKERS, PaperFeed

# Marathi/Devanagari साठी assets/font.ttf (Noto Sans Devanagari) ठेवा
FONT = os.path.join(os.path.dirname(__file__), "assets", "font.ttf")
if os.path.exists(FONT):
    LabelBase.register(name="Roboto", fn_regular=FONT, fn_bold=FONT)

Window.clearcolor = (0.04, 0.06, 0.12, 1)

KV = '''
#:import dp kivy.metrics.dp
<Card@BoxLayout>:
    padding: dp(12)
    spacing: dp(8)
    size_hint_y: None
    canvas.before:
        Color:
            rgba: .09, .12, .22, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
<Lbl@Label>:
    color: .62, .67, .85, 1
    font_size: '12sp'
    size_hint_y: None
    height: dp(22)
    text_size: self.width, None
    halign: 'left'
<In@TextInput>:
    multiline: False
    size_hint_y: None
    height: dp(42)
    background_color: .13, .17, .3, 1
    foreground_color: 1, 1, 1, 1
    cursor_color: 0, .8, 1, 1
    padding: dp(10), dp(10)
<Btn@Button>:
    background_normal: ''
    background_color: .42, .36, .91, 1
    bold: True
    size_hint_y: None
    height: dp(46)

BoxLayout:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: dp(56)
        padding: dp(14), 0
        canvas.before:
            Color:
                rgba: .42, .36, .91, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: '📈 YHMB ALGO APP'
            bold: True
            font_size: '19sp'
            halign: 'left'
            text_size: self.size
            valign: 'middle'
        Label:
            text: app.mode
            bold: True
            size_hint_x: None
            width: dp(80)
    ScreenManager:
        id: sm
        Screen:
            name: 'home'
            ScrollView:
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(12)
                    spacing: dp(10)
                    Card:
                        orientation: 'vertical'
                        height: dp(150)
                        Lbl:
                            text: 'आजचा P&L (₹)'
                        Label:
                            id: pnl
                            text: app.pnl_text
                            font_size: '34sp'
                            bold: True
                            color: app.pnl_color
                        Lbl:
                            text: app.status_text
                    BoxLayout:
                        size_hint_y: None
                        height: dp(46)
                        spacing: dp(8)
                        Btn:
                            text: '📝 PAPER'
                            on_release: app.set_mode('PAPER')
                        Btn:
                            text: '⚡ LIVE'
                            background_color: .85, .55, .1, 1
                            on_release: app.set_mode('LIVE')
                    BoxLayout:
                        size_hint_y: None
                        height: dp(50)
                        spacing: dp(8)
                        Btn:
                            text: '▶ START'
                            background_color: 0, .72, .5, 1
                            on_release: app.start()
                        Btn:
                            text: '■ STOP / EXIT'
                            background_color: 1, .3, .43, 1
                            on_release: app.stop()
                    Card:
                        orientation: 'vertical'
                        height: dp(110)
                        Lbl:
                            text: 'Open Position'
                        Label:
                            text: app.pos_text
                            halign: 'left'
                            text_size: self.size
                    Card:
                        orientation: 'vertical'
                        height: dp(230)
                        Lbl:
                            text: 'Trades'
                        Label:
                            text: app.trades_text
                            font_size: '12sp'
                            halign: 'left'
                            valign: 'top'
                            text_size: self.size
                    Card:
                        orientation: 'vertical'
                        height: dp(200)
                        Lbl:
                            text: 'Log'
                        Label:
                            text: app.log_text
                            font_size: '11sp'
                            color: .62, .67, .85, 1
                            halign: 'left'
                            valign: 'top'
                            text_size: self.size
        Screen:
            name: 'strategy'
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(8)
                Lbl:
                    text: '🐍 Python Strategy  (def on_tick(ctx, tick))'
                TextInput:
                    id: code
                    text: app.code
                    font_name: 'RobotoMono-Regular'
                    font_size: '12sp'
                    background_color: .06, .08, .15, 1
                    foreground_color: .3, .85, 1, 1
                    cursor_color: 1, 1, 1, 1
                BoxLayout:
                    size_hint_y: None
                    height: dp(46)
                    spacing: dp(8)
                    Btn:
                        text: '💾 Save'
                        on_release: app.save_code(code.text)
                    Btn:
                        text: '↺ Default'
                        background_color: .3, .35, .55, 1
                        on_release: code.text = app.default_code
        Screen:
            name: 'risk'
            ScrollView:
                BoxLayout:
                    id: riskbox
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(12)
                    spacing: dp(4)
        Screen:
            name: 'broker'
            ScrollView:
                BoxLayout:
                    id: brbox
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(12)
                    spacing: dp(4)
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        canvas.before:
            Color:
                rgba: .09, .12, .22, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Button:
            text: '🏠 Home'
            background_color: 0, 0, 0, 0
            on_release: sm.current = 'home'
        Button:
            text: '🐍 Strategy'
            background_color: 0, 0, 0, 0
            on_release: sm.current = 'strategy'
        Button:
            text: '🛡 Risk'
            background_color: 0, 0, 0, 0
            on_release: sm.current = 'risk'
        Button:
            text: '🔗 Broker'
            background_color: 0, 0, 0, 0
            on_release: sm.current = 'broker'
'''

RISK_FIELDS = [("qty", "Quantity"), ("sl", "Stop Loss (points)"), ("target", "Target (points)"),
               ("lock_at", "Lock Profit: profit किती points झाल्यावर"), ("lock_val", "Lock केलेला profit (points)"),
               ("trail_x", "Trail: प्रत्येक X points वर"), ("trail_y", "Trail: SL Y points ने हलवा"),
               ("max_profit", "Max Profit / दिवस (₹)"), ("max_loss", "Max Loss / दिवस (₹)")]
BROKER_FIELDS = [("symbol", "Symbol  (Angel: NSE:NIFTY:99926000 | Zerodha: NSE:NIFTY 50)"),
                 ("client_id", "Client ID"), ("api_key", "API Key"),
                 ("password", "Password/PIN (Zerodha: API Secret)"), ("totp", "TOTP Secret (Angel)"),
                 ("request_token", "Zerodha request_token"), ("access_token", "Zerodha access_token (असल्यास)"),
                 ("gateway_url", "VPS Gateway URL (https://algo.yourdomain.com)"), ("gateway_token", "Gateway Token"),
                 ("static_ip", "Static IP (फक्त नोंद - broker portal वर whitelist करा)")]

class YHMBApp(App):
    mode = StringProperty("PAPER")
    pnl_text = StringProperty("0.00"); pnl_color = ListProperty([1, 1, 1, 1])
    status_text = StringProperty("Idle"); pos_text = StringProperty("कोणतीही पोझिशन नाही")
    trades_text = StringProperty(""); log_text = StringProperty("")
    code = StringProperty(DEFAULT_CODE); default_code = DEFAULT_CODE

    def build(self):
        self.title = "YHMB ALGO APP"
        self.engine = None; self.broker = PaperFeed(); self.broker_name = "Paper (No broker)"
        self.cfg_path = os.path.join(self.user_data_dir, "yhmb.json")
        self.cfg = self._load()
        self.code = self.cfg.get("code", DEFAULT_CODE)
        self.root_w = Builder.load_string(KV)
        self._build_risk(); self._build_broker()
        return self.root_w

    # ---- storage (ॲपच्या private folder मध्ये) ----
    def _load(self):
        try: return json.load(open(self.cfg_path))
        except Exception: return {}
    def _save(self):
        try: json.dump(self.cfg, open(self.cfg_path, "w"))
        except Exception: pass

    # ---- forms ----
    def _field(self, box, label, value, password=False):
        from kivy.factory import Factory
        box.add_widget(Factory.Lbl(text=label)); t = Factory.In(text=str(value), password=password); box.add_widget(t); return t
    def _build_risk(self):
        box = self.root_w.ids.riskbox; box.add_widget(Label(text="🛡 Risk Management", size_hint_y=None, height=40, bold=True))
        saved = self.cfg.get("risk", {}); d = Risk().__dict__
        self.risk_in = {k: self._field(box, lbl, saved.get(k, d[k])) for k, lbl in RISK_FIELDS}
        from kivy.factory import Factory
        box.add_widget(Factory.Btn(text="💾 Save Risk", on_release=lambda *_: self.save_risk()))
    def _build_broker(self):
        from kivy.factory import Factory
        from kivy.uix.spinner import Spinner
        box = self.root_w.ids.brbox; box.add_widget(Label(text="🔗 Broker API Login", size_hint_y=None, height=40, bold=True))
        self.sp = Spinner(text=self.cfg.get("broker", "Paper (No broker)"), values=list(BROKERS), size_hint_y=None, height=44)
        box.add_widget(self.sp); saved = self.cfg.get("broker_cfg", {})
        self.br_in = {k: self._field(box, lbl, saved.get(k, ""), password=k in ("api_key", "password", "totp", "access_token", "gateway_token")) for k, lbl in BROKER_FIELDS}
        box.add_widget(Factory.Btn(text="🔗 Connect", on_release=lambda *_: self.connect()))

    def save_risk(self):
        self.cfg["risk"] = {k: w.text for k, w in self.risk_in.items()}; self._save(); self.toast("Risk saved ✔")
    def save_code(self, text):
        self.code = text; self.cfg["code"] = text; self._save(); self.toast("Strategy saved ✔")

    def connect(self):
        import threading
        name = self.sp.text; cfg = {k: w.text.strip() for k, w in self.br_in.items()}
        self.cfg["broker"] = name; self.cfg["broker_cfg"] = cfg; self._save()
        def work():
            try:
                b = BROKERS[name](); b.login(cfg); self.broker, self.broker_name = b, name
                self.toast(f"{name} connected ✔")
            except Exception as e: self.toast(f"Login failed: {e}")
        threading.Thread(target=work, daemon=True).start()

    # ---- run control ----
    def set_mode(self, m):
        if self.engine and self.engine.running: return self.toast("आधी Stop करा")
        if m == "LIVE" and isinstance(self.broker, PaperFeed): return self.toast("Live साठी आधी broker connect करा")
        self.mode = m
    def start(self):
        if self.engine and self.engine.running: return
        try:
            risk = Risk.from_dict({k: w.text for k, w in self.risk_in.items()})
            symbol = self.br_in["symbol"].text.strip() or "NIFTY"
            self.engine = Engine(self.broker, symbol, risk, self.code, self.mode, on_update=self.refresh)
            self.engine.start(); self.status_text = f"Running • {self.mode} • {self.broker_name}"
        except Exception as e: self.toast(f"Error: {e}")
    def stop(self):
        if self.engine: self.engine.stop(); self.status_text = "Stopped"

    @mainthread
    def refresh(self, e):
        t = e.total_pnl; self.pnl_text = f"{t:+.2f}"; self.pnl_color = [0, .85, .55, 1] if t >= 0 else [1, .3, .43, 1]
        p = e.pos; self.pos_text = (f"{p.side} {p.qty} @ {p.entry:.2f}\nLTP {e.ltp:.2f}\nSL {p.sl:.2f} | Target {p.target:.2f}") if p else f"कोणतीही पोझिशन नाही\nLTP {e.ltp:.2f}"
        self.trades_text = "\n".join(f"{x['t']} {x['side']} {x['entry']:.1f}→{x['exit']:.1f} {x['why']} {x['pnl']:+.0f}" for x in e.trades[:12])
        self.log_text = "\n".join(e.logs[-12:][::-1])

    @mainthread
    def toast(self, msg):
        Popup(title="", content=Label(text=str(msg), text_size=(Window.width * .7, None), halign="center"),
              size_hint=(.85, .25), separator_height=0).open()

if __name__ == "__main__":
    YHMBApp().run()
