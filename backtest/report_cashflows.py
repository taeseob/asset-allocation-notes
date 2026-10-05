"""동적자산배분 점검 문서 3장(세금과 현금흐름)의 숫자를 계산합니다."""
from engine import (END, KR, NDX, SPX, above_sma, asset_returns, buy_hold, last_n, momentum, months_between, nxt,
                    prev, simulate, simulate_tax, sma_rule, static)


def section_3_1_tax():
    print("[3-1] 일반 계좌 세금 (매도할 때마다 이익의 15.4%, 손실 상계 없음, 마지막 달 전부 매도)")
    for asset in ("spx", "ndx"):
        for start in ((1999, 12), (2009, 12)):
            cells = []
            for name, strategy in (("계속 보유", buy_hold(asset)), ("10개월", sma_rule(asset, 10)),
                                   ("12개월", sma_rule(asset, 12))):
                path, _, _ = simulate(strategy, start=start)
                years = len(path) / 12
                pre = (path[-1][1] / 100) ** (1 / years) - 1
                post = (simulate_tax(strategy, start=start) / 100) ** (1 / years) - 1
                cells.append(f"{name} {pre:.1%} → {post:.1%}")
            print(f"  {asset} {start[0] + 1}년~: " + " | ".join(cells))


def money_mdd(path):
    peak, mdd = 0.0, 0.0
    for _, x in path:
        peak = max(peak, x)
        if peak > 0:
            mdd = min(mdd, x / peak - 1)
    return mdd


def section_3_2_contributions():
    print("\n[3-2] 거치 100 + 해마다 처음 금액의 일정 비율을 매달 나눠 추가 투입 (최종 평가액 ÷ 총 투입액 / 최대 낙폭)")
    for asset in ("spx", "ndx"):
        for start in ((1999, 12), (2007, 10), (2009, 12)):
            for pct in (0, 10, 25):
                flows = (lambda i, pct=pct: pct / 12) if pct else None
                cells = []
                for name, strategy in (("계속 보유", buy_hold(asset)), ("10개월", sma_rule(asset, 10)),
                                       ("12개월", sma_rule(asset, 12))):
                    path, _, paid = simulate(strategy, start=start, flows=flows)
                    cells.append(f"{name} {path[-1][1] / (100 + paid):5.2f}배 / {money_mdd(path):4.0%}")
                print(f"  {asset} {nxt(start)[0]}.{nxt(start)[1]:02d} 시작 +{pct:2}%/년: " + " | ".join(cells))
    print("  0에서 시작해 매달 1씩 적립만 (최종 평가액 ÷ 총 투입액 / 최대 낙폭)")
    for asset in ("spx", "ndx"):
        for start in ((1999, 12), (2009, 12)):
            cells = []
            for name, strategy in (("계속 보유", buy_hold(asset)), ("10개월", sma_rule(asset, 10)),
                                   ("정적 60:40", static({asset: 0.6, "mid": 0.4}))):
                path, _, paid = simulate(strategy, start=start, flows=lambda i: 1.0, w0=0.0)
                cells.append(f"{name} {path[-1][1] / paid:5.2f}배 / {money_mdd(path):4.0%}")
            print(f"  {asset} {start[0] + 1}년~: " + " | ".join(cells))


def section_3_3_withdrawal():
    print("\n[3-3] 100에서 시작해 매년 5(고정)를 매달 나눠 인출, S&P500 원화 기준 (최종 / 최저)")
    for start in ((1999, 12), (2007, 10), (2009, 12)):
        cells = []
        for name, strategy in (("계속 보유", buy_hold("spx")), ("10개월", sma_rule("spx", 10)),
                               ("12개월", sma_rule("spx", 12)), ("정적 60:40", static({"spx": 0.6, "mid": 0.4}))):
            path, _, _ = simulate(strategy, start=start, flows=lambda i: -5 / 12)
            cells.append(f"{name} {path[-1][1]:.0f} / {min(x for _, x in path):.0f}")
        print(f"  {nxt(start)[0]}.{nxt(start)[1]:02d} 시작: " + " | ".join(cells))


def entry(start, method, horizon):
    """월말 start에 100을 준비해 method대로 투입하고, horizon개월 뒤 평가액을 돌려줍니다.

    투입을 기다리는 돈은 원화 현금으로 둡니다.
    """
    stock = asset_returns(True)["spx"]
    months = [start]
    for _ in range(horizon):
        months.append(nxt(months[-1]))
    cash, invested = 100.0, 0.0
    for i, m in enumerate(months):
        if i > 0:
            invested *= 1 + stock(m)
            cash *= 1 + KR[prev(m)] / 100 / 12
        if i == len(months) - 1:
            break
        above = above_sma(SPX, 10, m)
        if method == "일시":
            amount = cash if i == 0 else 0.0
        elif method.endswith("개월 분할"):
            n = int(method[:-5])
            amount = (cash if i == n - 1 else 100.0 / n) if i < n else 0.0
        elif method == "추세 대기":
            amount = cash if above else 0.0
        elif method == "추세 혼합":  # 추세 위면 즉시 전액, 아래면 12개월 분할
            amount = cash if (i == 0 and above) else (cash / (12 - i) if i < 12 else 0.0)
        amount = min(amount, cash)
        cash -= amount
        invested += amount
    return invested + cash


def section_3_4_entry(horizon=36):
    starts = months_between((2000, 1), (2023, 9))
    methods = ["일시", "6개월 분할", "12개월 분할", "추세 대기", "추세 혼합"]
    results = {k: [entry(prev(s), k, horizon) for s in starts] for k in methods}

    def pct(values, q):
        v = sorted(values)
        return v[int(q * (len(v) - 1))]

    print(f"\n[3-4] 거치 자금 투입 방식: {len(starts)}개 시작월, {horizon}개월 뒤 평가액 (시작 100, S&P500 원화 기준)")
    for k in methods:
        v = results[k]
        wins = sum(1 for x, y in zip(v, results["일시"]) if x > y)
        print(f"  {k:8} 평균 {sum(v) / len(v):6.1f}  하위10% {pct(v, 0.1):6.1f}  최악 {min(v):6.1f}  "
              f"일시 투입을 이긴 횟수 {wins}/{len(v)}")
    for cond, label in ((True, "추세 위에서 시작"), (False, "추세 아래에서 시작")):
        idx = [i for i, s in enumerate(starts) if above_sma(SPX, 10, prev(s)) == cond]
        cells = " | ".join(f"{k} 평균 {sum(results[k][i] for i in idx) / len(idx):.1f} 최악 "
                           f"{min(results[k][i] for i in idx):.1f}" for k in methods)
        print(f"  {label} ({len(idx)}개): {cells}")
    print(f"  현재 신호 ({END[0]}.{END[1]:02d} 말, 달러 기준 지수)")
    for name, series in (("S&P500", SPX), ("나스닥100", NDX)):
        sma10 = sum(series[k] for k in last_n(END, 10)) / 10
        sma12 = sum(series[k] for k in last_n(END, 12)) / 12
        print(f"    {name}: 10개월 이동평균 대비 {series[END] / sma10 - 1:+.1%}, "
              f"12개월 이동평균 대비 {series[END] / sma12 - 1:+.1%}, 최근 12개월 {momentum(series, 12, END):+.1%}")


if __name__ == "__main__":
    section_3_1_tax()
    section_3_2_contributions()
    section_3_3_withdrawal()
    section_3_4_entry()
