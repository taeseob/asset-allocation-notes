"""동적자산배분 점검 문서 2장(백테스트 결과)의 숫자를 계산합니다."""
from engine import (END, SIGNAL, abs_momentum, above_sma, asset_returns, buy_hold, cagr_mdd, dual_momentum,
                    fmt_month, mdd_period, months_between, nxt, period_cagr, prev, sma_rule, simulate, static,
                    year_return)

DECADES = [((2000, 1), (2009, 12)), ((2010, 1), (2019, 12)), ((2020, 1), END)]


def row(name, strategy, krw=True):
    path, switches, _ = simulate(strategy, krw=krw)
    cagr, mdd = cagr_mdd(path)
    decades = " ".join(f"{period_cagr(path, a, b):6.1%}" for a, b in DECADES)
    print(f"  {name:34} 연평균 {cagr:6.1%}  최대낙폭 {mdd:6.1%}  전환 {switches:3} | "
          f"00-09/10-19/20-26 {decades} | 2008 {year_return(path, 2008):6.1%}  2022 {year_return(path, 2022):6.1%}")


def section_2_1_and_2_3():
    print("[2-1, 2-2, 2-3] 2000.01~2026.09 원화 기준")
    print(" S&P500")
    row("계속 보유", buy_hold("spx"))
    row("정적 60:40 (미국 중기국채)", static({"spx": 0.6, "mid": 0.4}))
    row("정적 70:30 (달러 단기국채)", static({"spx": 0.7, "tb": 0.3}))
    for n in (6, 8, 10, 12):
        row(f"{n}개월 이동평균", sma_rule("spx", n))
    row("12개월 절대 모멘텀", abs_momentum("spx"))
    row("10개월, 빠질 때 미국 중기국채", sma_rule("spx", 10, "mid"))
    row("10개월, 빠질 때 미국 장기국채", sma_rule("spx", 10, "long"))
    row("듀얼 모멘텀", dual_momentum)
    print(" 나스닥100")
    row("계속 보유", buy_hold("ndx"))
    for n in (6, 10, 12):
        row(f"{n}개월 이동평균", sma_rule("ndx", n))
    row("12개월 절대 모멘텀", abs_momentum("ndx"))
    print(" (참고) 달러 기준")
    row("S&P500 계속 보유", buy_hold("spx"), krw=False)
    row("나스닥100 계속 보유", buy_hold("ndx"), krw=False)
    path, _, _ = simulate(sma_rule("spx", 10))
    mdd, (peak, trough) = mdd_period(path)
    print(f" S&P500 10개월 규칙 최대 낙폭 {mdd:.1%}: {fmt_month(peak)} 고점 → {fmt_month(trough)} 저점")


def section_2_2_rolling():
    print("\n[2-2] 10년 굴림 구간 (시작월 2000.01~2016.09, 원화 기준)")
    starts = months_between((2000, 1), (2016, 9))
    for asset in ("spx", "ndx"):
        base = dict(simulate(buy_hold(asset))[0])
        for n in (10, 12):
            rule = dict(simulate(sma_rule(asset, n))[0])
            diffs = []
            for s in starts:
                e = s
                for _ in range(119):
                    e = nxt(e)
                c_base = (base[e] / base.get(prev(s), 100.0)) ** 0.1 - 1
                c_rule = (rule[e] / rule.get(prev(s), 100.0)) ** 0.1 - 1
                diffs.append((s, c_rule - c_base))
            wins = sum(1 for _, d in diffs if d > 0)
            buckets = {}
            for s, d in diffs:
                buckets.setdefault(s[0] // 5 * 5, []).append(d)
            by_start = ", ".join(f"{k}~ {sum(v) / len(v):+.1%}p" for k, v in sorted(buckets.items()))
            print(f"  {asset} {n}개월: 이긴 구간 {wins}/{len(diffs)} ({wins / len(diffs):.0%}) | 시작 시점별 평균 차이 {by_start}")


def section_2_2_trades():
    print("\n[2-2] 10개월 규칙의 매도 → 재매수 (원화 기준, 빠져 있던 동안 현금 대비 자산 성과)")
    for asset in ("spx", "ndx"):
        months = months_between((1999, 12), END)
        state, log = above_sma(SIGNAL[asset], 10, months[0]), []
        for m in months[1:-1]:
            x = above_sma(SIGNAL[asset], 10, m)
            if x != state:
                log.append((m, x))
                state = x
        returns = asset_returns(True)
        helped, hurt = [], []
        for (m1, x1), (m2, x2) in zip(log, log[1:]):
            if not x1 and x2:
                r = c = 1.0
                for mm in months_between(nxt(m1), m2):
                    r *= 1 + returns[asset](mm)
                    c *= 1 + returns["tb"](mm)
                rel = c / r - 1  # 양(+)이면 빠져 있던 것이 이득
                (helped if rel > 0 else hurt).append((m1, m2, rel))
        print(f"  {asset}: 전환 {len(log)}회, 매도→재매수 {len(helped) + len(hurt)}회, 이득 {len(helped)}회, "
              f"손해 {len(hurt)}회 (손해 평균 {sum(x[2] for x in hurt) / len(hurt):+.1%})")
        print("    이득 구간: " + ", ".join(f"{fmt_month(a)}~{fmt_month(b)}" for a, b, _ in helped))
        print("    전환 내역: " + " ".join(f"{fmt_month(m)}{'매수' if x else '매도'}" for m, x in log))


def section_2_4():
    print("\n[2-4] 코스피 (원화, 빠질 때 원화 현금)")
    row("코스피 계속 보유", buy_hold("ks"), krw=False)
    row("코스피 10개월 이동평균", sma_rule("ks", 10, "krc"), krw=False)
    row("코스피 12개월 이동평균", sma_rule("ks", 12, "krc"), krw=False)


if __name__ == "__main__":
    section_2_1_and_2_3()
    section_2_2_rolling()
    section_2_2_trades()
    section_2_4()
