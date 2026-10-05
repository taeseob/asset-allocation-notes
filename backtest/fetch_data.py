"""백테스트에 쓰는 월간 가격·금리·환율 데이터를 backtest/data/ 에 내려받습니다.

* Yahoo Finance: 지수·펀드 월간 종가와 수정 종가 (분배금 재투자)
* FRED: 원·달러 환율, 미국 3개월 국채 금리, 한국 3개월 금리
"""
import csv
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

YAHOO = {
    "^SP500TR": "S&P500 배당 포함 지수",
    "^NDX": "나스닥100 지수 (신호용)",
    "QQQ": "나스닥100 ETF (수익률용)",
    "VFITX": "미국 중기국채 펀드",
    "VUSTX": "미국 장기국채 펀드",
    "VBMFX": "미국 종합채권 펀드",
    "VGTSX": "미국 외 주식 펀드",
    "^KS11": "코스피 지수",
}
FRED = {
    "DEXKOUS": "원·달러 환율 (일간)",
    "DTB3": "미국 3개월 국채 금리 (일간)",
    "IR3TIB01KRM156N": "한국 3개월 금리 (월간)",
}
UA = {"User-Agent": "Mozilla/5.0"}


def fetch_yahoo(symbol):
    period2 = int(time.time())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
        f"?period1=0&period2={period2}&interval=1mo&events=div,split"
    )
    req = urllib.request.Request(url, headers=UA)
    result = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    adjs = result["indicators"].get("adjclose", [{}])[0].get("adjclose", closes)
    rows = []
    for ts, close, adj in zip(result["timestamp"], closes, adjs):
        if close is None:
            continue
        # 월간 봉의 타임스탬프는 그달 첫 거래일이므로 날짜만 취해 연·월로 씁니다.
        day = dt.datetime.fromtimestamp(ts + 43200, tz=dt.timezone.utc).date()
        rows.append((day.year, day.month, close, adj if adj is not None else close))
    return rows


def fetch_fred(series_id, retries=3):
    # FRED는 브라우저 User-Agent 요청을 끊으므로 기본 User-Agent로 요청합니다.
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    for symbol, label in YAHOO.items():
        rows = fetch_yahoo(symbol)
        path = DATA_DIR / f"{symbol.lstrip('^')}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["y", "m", "close", "adj"])
            writer.writerows(rows)
        print(f"{symbol:10} {rows[0][0]}-{rows[0][1]:02d} ~ {rows[-1][0]}-{rows[-1][1]:02d}  {label}")
        time.sleep(0.5)
    for series_id, label in FRED.items():
        text = fetch_fred(series_id)
        (DATA_DIR / f"{series_id}.csv").write_text(text, encoding="utf-8")
        lines = text.strip().splitlines()
        print(f"{series_id:16} {lines[1].split(',')[0]} ~ {lines[-1].split(',')[0]}  {label}")


if __name__ == "__main__":
    main()
