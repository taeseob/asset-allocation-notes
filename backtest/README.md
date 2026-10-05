# 동적자산배분 백테스트

[동적자산배분 점검](../Dynamic_Asset_Allocation_Review.md) 문서 2·3장의 숫자를 계산하는 스크립트입니다. Python 표준 라이브러리만 사용합니다.

## 실행
```
cd backtest
python fetch_data.py        # data/ 에 데이터 내려받기
python report_returns.py    # 문서 2장
python report_cashflows.py  # 문서 3장
```
* 출력을 파일이나 Git Bash로 받을 때 한글이 깨지면 `PYTHONIOENCODING=utf-8`을 설정합니다.

## 파일
| 파일 | 내용 |
|---|---|
| `fetch_data.py` | Yahoo Finance·FRED 월간 데이터 다운로드 |
| `engine.py` | 데이터 로드, 전략(계속 보유·정적 배분·이동평균·절대 모멘텀·듀얼 모멘텀), 시뮬레이션, 지표 |
| `report_returns.py` | 문서 2장: 26년 성과, 기간별·10년 굴림 비교, 매매 내역, 2022년과 빠질 때 옮기는 자산, 코스피 |
| `report_cashflows.py` | 문서 3장: 일반 계좌 세금, 거치 + 적립, 인출, 거치 자금 투입 방식, 현재 신호 |

## 참고
* 계산 기간은 `engine.py`의 `START`·`END`(1999년 12월 말 첫 신호 ~ 2026년 9월)로 고정되어 있습니다. 기간을 늘리려면 `END`를 바꿉니다.
* 내려받은 데이터(`data/`)는 저장소에 올리지 않습니다.
* Yahoo Finance 수정 종가와 FRED 자료는 나중에 수정될 수 있어, 다시 내려받으면 문서 숫자와 소수점 아래가 조금 다를 수 있습니다. 2026년 10월 3일에 내려받은 데이터와 Python 3.12에서 문서 숫자와 일치함을 확인했습니다.
* 문서의 가정(원화 기준 환노출, 월말 신호, 세금 모델, 배당 근사 등)은 문서 1-2와 6장에 정리되어 있습니다.
