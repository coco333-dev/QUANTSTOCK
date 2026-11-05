from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="QUANTSMART VN", page_icon="📈", layout="wide")

# ---------- Theme ----------
st.markdown("""
<style>
.stApp {background:#0b1220;color:#eef4ff}
[data-testid="stSidebar"] {background:#101b2d}
.block-container {padding-top:1.6rem;max-width:1500px}
.metric-card {background:#111f33;border:1px solid #263954;border-radius:14px;padding:16px}
.small-muted {color:#9aabc3;font-size:0.85rem}
h1,h2,h3 {letter-spacing:-.02em}
</style>
""", unsafe_allow_html=True)

# ---------- Data and analytics ----------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market(symbol: str, start: str, end: str, kind: str = "equity") -> pd.DataFrame:
    from vnstock import Market
    market = Market()
    raw = market.index(symbol).ohlcv(start=start, end=end, interval="1D") if kind == "index" else market.equity(symbol).ohlcv(start=start, end=end, interval="1D")
    d = pd.DataFrame(raw).copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    aliases = {"time":"date","trading_date":"date","datetime":"date","tradingdate":"date","vol":"volume"}
    d = d.rename(columns={c:aliases.get(c,c) for c in d.columns})
    if "date" not in d:
        d = d.reset_index().rename(columns={"index":"date"})
    required = ["date","open","high","low","close","volume"]
    missing = [c for c in required if c not in d]
    if missing: raise ValueError(f"Thiếu cột dữ liệu: {missing}")
    d = d[required]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    for c in required[1:]: d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["date","close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    d["volume"] = d["volume"].fillna(0)
    if kind == "equity" and len(d) and d["close"].median() < 1000:
        d[["open","high","low","close"]] *= 1000
    return d

def indicators(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    c = x.close.astype(float)
    x["EMA20"] = c.ewm(span=20, adjust=False).mean()
    x["EMA50"] = c.ewm(span=50, adjust=False).mean()
    delta = c.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    al = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = ag / al.replace(0, np.nan)
    x["RSI14"] = 100 - 100/(1+rs)
    x.loc[(al == 0) & (ag > 0), "RSI14"] = 100
    e12, e26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    x["MACD"] = e12-e26
    x["MACD_signal"] = x.MACD.ewm(span=9, adjust=False).mean()
    return x

def backtest(d, strategy, fast, slow, fee_bps, slip_bps, capital):
    x = indicators(d)
    if strategy == "EMA crossover":
        signal = (x.EMA20 > x.EMA50).astype(int)
    elif strategy == "EMA + RSI filter":
        signal = ((x.EMA20 > x.EMA50) & (x.RSI14 > 50)).astype(int)
    else:
        signal = (x.RSI14 < 30).astype(int)
    x["position"] = signal.shift(1).fillna(0)
    x["asset_return"] = x.close.pct_change().fillna(0)
    x["turnover"] = x.position.diff().abs().fillna(x.position.abs())
    x["strategy_return"] = x.position*x.asset_return - x.turnover*(fee_bps+slip_bps)/10000
    x["equity"] = capital*(1+x.strategy_return).cumprod()
    x["buy_hold"] = capital*(1+x.asset_return).cumprod()
    x["drawdown"] = x.equity/x.equity.cummax()-1
    r = x.strategy_return
    vol = r.std()*np.sqrt(252)
    years = max(len(r)/252, 1/252)
    total = x.equity.iloc[-1]/capital-1
    metrics = {
        "Total return": total,
        "CAGR": (1+total)**(1/years)-1 if total > -1 else -1,
        "Max drawdown": x.drawdown.min(),
        "Sharpe": r.mean()*252/vol if vol and np.isfinite(vol) else np.nan,
        "Exposure": x.position.mean(),
        "Trading days": len(x)
    }
    return x, metrics

def line_chart(d, series, title):
    fig = go.Figure()
    for col, label in series:
        if col in d: fig.add_trace(go.Scatter(x=d.date, y=d[col], name=label, mode="lines"))
    fig.update_layout(title=title, template="plotly_dark", paper_bgcolor="#0b1220", plot_bgcolor="#0b1220", margin=dict(l=10,r=10,t=50,b=10), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sidebar ----------
st.sidebar.markdown("## 📈 QUANTSMART VN")
st.sidebar.caption("Vietnam Equity Research Workstation")
page = st.sidebar.radio("WORKSPACE", ["Overview","Market Data","Technical Lab","Strategy & Backtest","Portfolio Lab","Research Notes"])
st.sidebar.divider()
symbol = st.sidebar.text_input("Mã cổ phiếu", "FPT").strip().upper()
end_date = st.sidebar.date_input("Ngày kết thúc", date.today())
start_date = st.sidebar.date_input("Ngày bắt đầu", end_date-timedelta(days=730))
if start_date >= end_date: st.sidebar.error("Ngày bắt đầu phải trước ngày kết thúc.")
st.sidebar.caption("Dữ liệu ngày · Mục đích nghiên cứu/giáo dục")

@st.cache_data(show_spinner=False)
def load_uploaded(file_bytes):
    from io import BytesIO
    d = pd.read_csv(BytesIO(file_bytes))
    d.columns = [str(c).strip().lower() for c in d.columns]
    d = d.rename(columns={"time":"date","datetime":"date","vol":"volume"})
    if "date" not in d: raise ValueError("CSV cần cột date.")
    for c in ["open","high","low","close","volume"]:
        if c not in d: raise ValueError(f"CSV thiếu cột {c}.")
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    for c in ["open","high","low","close","volume"]: d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.dropna(subset=["date","close"]).sort_values("date").reset_index(drop=True)

def get_data():
    upload = st.session_state.get("market_csv")
    if upload is not None:
        return load_uploaded(upload.getvalue())
    return fetch_market(symbol, start_date.isoformat(), end_date.isoformat())

# ---------- Pages ----------
st.title("QUANTSMART VN")
st.caption("Quantitative research · Vietnamese equities · Strategy testing")

if page == "Overview":
    st.subheader("Market overview")
    c1,c2 = st.columns([1,2])
    with c1:
        st.markdown("#### Workspace status")
        st.markdown('<div class="metric-card"><b>Research mode</b><p class="small-muted">Daily OHLCV · Long-only · No order execution</p></div>', unsafe_allow_html=True)
        st.write("**Selected ticker:**", symbol)
        st.write("**Period:**", f"{start_date} → {end_date}")
        st.info("Chuyển sang Market Data để tải dữ liệu hoặc nạp CSV.")
    with c2:
        try:
            d = indicators(get_data())
            if d.empty: st.warning("Không có dữ liệu trong khoảng thời gian đã chọn.")
            else:
                last = d.iloc[-1]
                a,b,c = st.columns(3)
                a.metric("Latest close", f"{last.close:,.0f} VND")
                b.metric("RSI 14", f"{last.RSI14:.1f}" if pd.notna(last.RSI14) else "N/A")
                c.metric("EMA trend", "Bullish" if last.EMA20 > last.EMA50 else "Bearish")
                line_chart(d,[("close","Close"),("EMA20","EMA 20"),("EMA50","EMA 50")],f"{symbol} · Price & EMA")
        except Exception as e: st.error(f"Chưa tải được dữ liệu: {e}")

elif page == "Market Data":
    st.subheader("Market data terminal")
    st.file_uploader("Tải CSV OHLCV (date, open, high, low, close, volume)", type=["csv"], key="market_csv")
    if st.button("Fetch market data", type="primary"):
        try:
            with st.spinner("Đang tải dữ liệu..."): d = get_data()
            st.success(f"Đã tải {len(d):,} phiên.")
            st.dataframe(d.tail(300), use_container_width=True)
            st.download_button("Download cleaned CSV", d.to_csv(index=False).encode("utf-8-sig"), f"{symbol}_ohlcv.csv","text/csv")
        except Exception as e: st.error(str(e))
    st.caption("Có thể dùng CSV tự chuẩn hóa hoặc nguồn VNStock v5.")

elif page == "Technical Lab":
    st.subheader("Technical indicator laboratory")
    try:
        d = indicators(get_data())
        if d.empty: st.warning("Không có dữ liệu.")
        else:
            line_chart(d,[("close","Close"),("EMA20","EMA 20"),("EMA50","EMA 50")],f"{symbol} · Trend")
            line_chart(d,[("RSI14","RSI 14")],"Relative Strength Index")
            line_chart(d,[("MACD","MACD"),("MACD_signal","Signal")],"MACD")
            st.dataframe(d.tail(100),use_container_width=True)
    except Exception as e: st.error(f"Lỗi dữ liệu: {e}")

elif page == "Strategy & Backtest":
    st.subheader("Strategy laboratory")
    c1,c2,c3 = st.columns(3)
    strategy = c1.selectbox("Strategy",["EMA crossover","EMA + RSI filter","RSI mean reversion"])
    capital = c2.number_input("Initial capital (VND)",min_value=1_000_000,value=100_000_000,step=10_000_000)
    fee = c3.number_input("Fee (bps)",min_value=0.0,value=15.0,step=1.0)
    slip = st.number_input("Slippage (bps)",min_value=0.0,value=5.0,step=1.0)
    if st.button("Run backtest",type="primary"):
        try:
            d = get_data()
            if len(d)<60: st.warning("Nên có tối thiểu 60 phiên dữ liệu.")
            else:
                result, metrics = backtest(d,strategy,20,50,fee,slip,capital)
                cols=st.columns(4)
                for col,(name,value) in zip(cols,list(metrics.items())[:4]):
                    col.metric(name, f"{value:.2%}" if name!="Trading days" and np.isfinite(value) else str(value))
                line_chart(result,[("equity","Strategy"),("buy_hold","Buy & hold")],"Equity curve")
                line_chart(result,[("drawdown","Drawdown")],"Drawdown")
                st.dataframe(result.tail(100),use_container_width=True)
                st.download_button("Download backtest results",result.to_csv(index=False).encode("utf-8-sig"),f"{symbol}_backtest.csv","text/csv")
        except Exception as e: st.error(f"Backtest failed: {e}")
    st.caption("Tín hiệu xác nhận tại cuối phiên và áp dụng từ phiên kế tiếp; kết quả chưa bao gồm đầy đủ thuế, T+2.5, lô giao dịch và corporate actions.")

elif page == "Portfolio Lab":
    st.subheader("Portfolio risk explorer")
    symbols = st.text_input("Danh sách mã, phân tách bằng dấu phẩy","FPT,VCB,HPG")
    lookback = st.slider("Lookback sessions",60,500,250,10)
    if st.button("Estimate portfolio",type="primary"):
        try:
            names=list(dict.fromkeys(s.strip().upper() for s in symbols.split(",") if s.strip()))
            if len(names)<2: raise ValueError("Cần ít nhất hai mã.")
            prices=[]
            for s in names:
                z=fetch_market(s,(end_date-timedelta(days=int(lookback*2.2))).isoformat(),end_date.isoformat())
                prices.append(z.set_index("date").close.pct_change().rename(s))
            rets=pd.concat(prices,axis=1).dropna().tail(lookback)
            if len(rets)<40: raise ValueError("Không đủ dữ liệu giao dịch đồng thời.")
            cov=rets.cov().values*252; mu=rets.mean().values*252; n=len(names)
            rng=np.random.default_rng(7); w=rng.dirichlet(np.ones(n),size=6000)
            vols=np.sqrt(np.maximum(np.einsum("ij,jk,ik->i",w,cov,w),0))
            best=w[np.argmin(vols)]
            weights=pd.DataFrame({"Ticker":names,"Weight":best})
            st.dataframe(weights.style.format({"Weight":"{:.2%}"}),use_container_width=True)
            st.metric("Estimated annual volatility",f"{vols.min():.2%}")
            st.metric("Estimated annual return",f"{best@mu:.2%}")
            st.caption("Random long-only minimum-volatility search; not a guaranteed global optimum.")
        except Exception as e: st.error(str(e))

elif page == "Research Notes":
    st.subheader("Research notebook")
    if "notes" not in st.session_state: st.session_state.notes=[]
    with st.form("note_form"):
        title=st.text_input("Research question / hypothesis")
        body=st.text_area("Observation, method, limitation, next step",height=160)
        submitted=st.form_submit_button("Save note")
        if submitted and title.strip():
            st.session_state.notes.append({"date":str(date.today()),"title":title,"body":body})
            st.success("Đã lưu trong phiên làm việc hiện tại.")
    if st.session_state.notes:
        st.dataframe(pd.DataFrame(st.session_state.notes),use_container_width=True)
        st.download_button("Export notes",pd.DataFrame(st.session_state.notes).to_csv(index=False).encode("utf-8-sig"),"research_notes.csv","text/csv")
    else: st.info("Chưa có ghi chú nghiên cứu.")

st.divider()
st.caption("QUANTSMART VN · Educational research prototype · Không phải khuyến nghị đầu tư.")
