"""동적자산배분 백테스트 엔진.

* 월 단위. 월(month)은 (연, 월) 튜플로 표현합니다.
* 전략은 "월말 m에 정한 다음 달 비중"을 돌려주는 함수입니다. 예: {"spx": 1}
* 원화 기준(krw=True)이면 달러 자산 수익률에 원·달러 환율 변동을 곱합니다(환노출).
"""
import csv
import datetime as dt
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
START = (1999, 12)  # 첫 신호를 계산하는 월말. 수익률은 2000년 1월부터
END = (2026, 9)     # 문서 기준 마지막 월. 데이터를 새로 받아도 이 기간으로 계산합니다


def prev(m):
    return (m[0] - 1, 12) if m[1] == 1 else (m[0], m[1] - 1)


def nxt(m):
    return (m[0] + 1, 1) if m[1] == 12 else (m[0], m[1] + 1)


def months_between(a, b):
    out = [a]
    while out[-1] < b:
        out.append(nxt(out[-1]))
    return out


def last_n(m, n):
    out = [m]
    for _ in range(n - 1):
        out.append(prev(out[-1]))
    return out


# ---- 데이터 로드
def load_yahoo(name, col="adj"):
    with open(DATA_DIR / f"{name}.csv") as f:
        rows = csv.DictReader(f)
        return {(int(r["y"]), int(r["m"])): float(r[col]) for r in rows if (int(r["y"]), int(r["m"])) <= END}


def load_fred(name):
    """일간·월간 시계열을 월말 값(그달 마지막 관측치)으로 바꾸고, END까지 빈 달은 직전 값으로 채웁니다."""
    out = {}
    with open(DATA_DIR / f"{name}.csv") as f:
        for r in csv.DictReader(f):
            date, value = list(r.values())[:2]
            if value in ("", "."):
                continue
            d = dt.date.fromisoformat(date)
            out[(d.year, d.month)] = float(value)
    m = max(out)
    while m < END:
        out[nxt(m)] = out[m]
        m = nxt(m)
    return out


SPX = load_yahoo("SP500TR", "close")  # S&P500 배당 포함 지수
NDX = load_yahoo("NDX", "close")      # 나스닥100 지수 (신호용)
QQQ = load_yahoo("QQQ")               # 나스닥100 ETF 수정 종가 (수익률용)
VFITX = load_yahoo("VFITX")           # 미국 중기국채
VUSTX = load_yahoo("VUSTX")           # 미국 장기국채
VBMFX = load_yahoo("VBMFX")           # 미국 종합채권
VGTSX = load_yahoo("VGTSX")           # 미국 외 주식
KS = load_yahoo("KS11", "close")      # 코스피 지수 (배당 미포함)
FX = load_fred("DEXKOUS")             # 원·달러 환율
TB = load_fred("DTB3")                # 미국 3개월 국채 금리 (연 %)
KR = load_fred("IR3TIB01KRM156N")     # 한국 3개월 금리 (연 %)


# ---- 월간 수익률 (m은 그달 말, prev(m) 말 대비 수익률)
def ret(series, m):
    return series[m] / series[prev(m)] - 1


def fx_ret(m):
    return FX[m] / FX[prev(m)] - 1


ASSETS = {
    "spx": lambda m: ret(SPX, m),
    # QQQ 상장(1999년 3월) 이전 구간에만 지수 + 배당 연 0.7% 근사 사용
    "ndx": lambda m: ret(QQQ, m) if prev(m) in QQQ else ret(NDX, m) + 0.007 / 12,
    "tb": lambda m: TB[prev(m)] / 100 / 12,
    "mid": lambda m: ret(VFITX, m),
    "long": lambda m: ret(VUSTX, m),
    "agg": lambda m: ret(VBMFX, m),
    "intl": lambda m: ret(VGTSX, m),
    # 원화 자산: krw=False로 계산합니다
    "ks": lambda m: ret(KS, m) + 0.015 / 12,  # 배당 연 1.5% 근사
    "krc": lambda m: KR[prev(m)] / 100 / 12,  # 원화 현금
}
SIGNAL = {"spx": SPX, "ndx": NDX, "intl": VGTSX, "ks": KS}


def in_krw(fn):
    return lambda m: (1 + fn(m)) * (1 + fx_ret(m)) - 1


def asset_returns(krw):
    return {k: in_krw(f) if krw else f for k, f in ASSETS.items()}


# ---- 신호
def above_sma(series, n, m):
    return series[m] > sum(series[k] for k in last_n(m, n)) / n


def momentum(series, n, m):
    a = m
    for _ in range(n):
        a = prev(a)
    return series[m] / series[a] - 1


def tbill_cum(n, m):
    c, a = 1.0, m
    for _ in range(n):
        c *= 1 + TB[prev(a)] / 100 / 12
        a = prev(a)
    return c - 1


# ---- 전략: 월말 m에 정하는 다음 달 비중
def buy_hold(asset):
    return lambda m: {asset: 1}


def static(weights):
    return lambda m: dict(weights)  # 매월 목표 비중으로 리밸런싱


def sma_rule(asset, n, safe="tb"):
    return lambda m: {asset: 1} if above_sma(SIGNAL[asset], n, m) else {safe: 1}


def abs_momentum(asset, n=12, safe="tb"):
    return lambda m: {asset: 1} if momentum(SIGNAL[asset], n, m) > tbill_cum(n, m) else {safe: 1}


def dual_momentum(m):
    """절대 모멘텀이 양(+)이면 미국·미국 외 주식 중 12개월 수익률이 높은 쪽, 아니면 미국 종합채권."""
    if momentum(SPX, 12, m) > tbill_cum(12, m):
        return {"spx": 1} if momentum(SPX, 12, m) >= momentum(VGTSX, 12, m) else {"intl": 1}
    return {"agg": 1}


# ---- 시뮬레이션
def simulate(strategy, start=START, end=END, krw=True, flows=None, w0=100.0):
    """평가액 경로, 전환 횟수, 순 현금흐름 합계를 돌려줍니다.

    flows(i)는 i번째 달 말의 투입(+)·인출(-) 금액입니다.
    """
    returns = asset_returns(krw)
    months = months_between(start, end)
    wealth, path, switches, net_flow = w0, [], 0, 0.0
    weights = strategy(months[0])
    for i, m in enumerate(months[1:], start=1):
        wealth *= 1 + sum(w * returns[k](m) for k, w in weights.items())
        if flows:
            f = flows(i)
            wealth = max(0.0, wealth + f)
            net_flow += f
        path.append((m, wealth))
        new = strategy(m)
        if len(new) == 1 and new != weights:
            switches += 1
        weights = new
    return path, switches, net_flow


def simulate_tax(strategy, rate=0.154, start=START, end=END, krw=True):
    """단일 자산을 오가는 전략의 세후 최종 금액.

    팔 때마다 이익의 rate만큼 과세하고 손실은 상계하지 않습니다. 마지막 달에 전부 팝니다.
    """
    returns = asset_returns(krw)
    months = months_between(start, end)
    wealth = basis = 100.0
    weights = strategy(months[0])
    for i, m in enumerate(months[1:], start=1):
        wealth *= 1 + sum(w * returns[k](m) for k, w in weights.items())
        new = strategy(m)
        if new != weights or i == len(months) - 1:
            wealth -= rate * max(0.0, wealth - basis)
            basis = wealth
        weights = new
    return wealth


# ---- 지표
def cagr_mdd(path, w0=100.0):
    values = [x for _, x in path]
    peak, mdd = w0, 0.0
    for x in values:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    return (values[-1] / w0) ** (12 / len(values)) - 1, mdd


def mdd_period(path, w0=100.0):
    peak, peak_m, mdd, at = w0, None, 0.0, None
    for m, x in path:
        if x > peak:
            peak, peak_m = x, m
        if x / peak - 1 < mdd:
            mdd, at = x / peak - 1, (peak_m, m)
    return mdd, at


def period_cagr(path, a, b, w0=100.0):
    d = dict(path)
    return (d[b] / d.get(prev(a), w0)) ** (12 / len(months_between(a, b))) - 1


def year_return(path, y, w0=100.0):
    d = dict(path)
    return d.get((y, 12), d[max(d)]) / d.get((y - 1, 12), w0) - 1


def fmt_month(m):
    return f"{m[0]}.{m[1]:02d}"
