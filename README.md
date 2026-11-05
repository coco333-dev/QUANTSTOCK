# QUANTSMART VN — Streamlit Research Workstation

Ứng dụng nghiên cứu định lượng cổ phiếu Việt Nam, triển khai bằng Streamlit Community Cloud.

## Chạy local
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy miễn phí
1. Mở https://share.streamlit.io/ và đăng nhập GitHub.
2. Chọn **Create app**.
3. Repository: `coco333-dev/QUANTSTOCK`.
4. Branch: `streamlit-migration`.
5. Main file path: `app.py`.
6. Deploy.

## Chức năng
- Overview: giá gần nhất, RSI, EMA trend.
- Market Data: lấy OHLCV qua VNStock v5 hoặc upload CSV.
- Technical Lab: EMA20/EMA50, RSI14, MACD.
- Strategy & Backtest: EMA crossover, EMA + RSI filter, RSI mean reversion; phí và trượt giá; equity curve, drawdown, CSV.
- Portfolio Lab: random long-only minimum-volatility search.
- Research Notes: ghi chú và xuất CSV (chỉ lưu trong session).

## CSV format
Cần các cột: `date, open, high, low, close, volume`. Giá CSV được hiểu là VND.

## Giới hạn quan trọng
Prototype dùng dữ liệu ngày, chiến lược long-only, tín hiệu được áp dụng trễ một phiên. Chưa mô phỏng đầy đủ lô giao dịch, thuế/phí theo từng CTCK, biên độ giá, đình chỉ giao dịch, thanh khoản/market impact, T+2.5, cổ tức, quyền mua và điều chỉnh corporate actions. Kết quả quá khứ không phải dự báo hay khuyến nghị đầu tư.

Không đưa API key, mật khẩu hoặc dữ liệu khách hàng vào repository công khai. Ứng dụng không đặt lệnh.
