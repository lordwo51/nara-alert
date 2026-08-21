# -*- coding: utf-8 -*-
"""
실행 스케줄 판단 모듈

cron은 "10분마다 항상 실행"으로 단순하게 걸어두고, 이 모듈이 "지금 API를
호출할 타이밍인지"를 판단합니다. 이렇게 하면 자정 넘어가는 경계, 평일/주말
전환 같은 복잡한 조건을 crontab 문법이 아니라 읽기 쉬운 파이썬 코드로 관리할
수 있습니다.

규칙 요약 (판단 기준은 항상 "오늘"의 실제 요일):
  - 평일 08:00~19:59  : 10분마다 (cron 틱마다 그대로 실행)
  - 평일 20:00~다음날 07:59 (단, 그 시각의 "오늘"이 평일일 때) : 매 정각(1시간마다)
  - 주말 08:00~19:59  : 3시간마다 (08/11/14/17시 정각)
  - 주말 20:00~23:59  : 23:50 딱 한 번
  - 주말 00:00~07:59 (그 시각의 "오늘"이 주말일 때) : 실행 안 함

자정이 지나는 순간 "오늘"이 바뀌므로, 예를 들어
  - 금요일(평일) 20:00~23:59 -> 1시간마다 실행되다가, 자정이 지나 토요일이 되면
    토요일 00:00~07:59는 "오늘=토요일=주말"의 새벽 규칙(실행 안 함)이 적용됩니다.
  - 일요일(주말) 20:00~23:59 -> 23:50 한 번만 실행되고, 자정이 지나 월요일이 되면
    월요일 00:00~07:59는 "오늘=월요일=평일"의 새벽 규칙(1시간마다)이 적용됩니다.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from config import (
    DAY_PERIOD_START_HOUR,
    DAY_PERIOD_END_HOUR,
    WEEKEND_DAY_ANCHOR_HOURS,
    WEEKEND_NIGHT_RUN_HOUR,
    WEEKEND_NIGHT_RUN_MINUTE,
)

KST = ZoneInfo("Asia/Seoul")


def should_run_now(now: datetime = None) -> tuple:
    """
    반환값: (실행여부: bool, 사유설명: str)
    사유설명은 로그 확인용입니다.
    """
    now = now or datetime.now(KST)
    hour, minute = now.hour, now.minute
    is_weekend = now.weekday() >= 5  # 월=0 ... 토=5, 일=6

    is_day_period = DAY_PERIOD_START_HOUR <= hour < DAY_PERIOD_END_HOUR

    if is_day_period:
        if is_weekend:
            ok = hour in WEEKEND_DAY_ANCHOR_HOURS and minute == 0
            return ok, f"주말 낮 시간대(3시간마다) - {'실행' if ok else '대기'}"
        else:
            return True, "평일 낮 시간대(10분마다) - 실행"
    else:
        if is_weekend:
            ok = hour == WEEKEND_NIGHT_RUN_HOUR and minute == WEEKEND_NIGHT_RUN_MINUTE
            return ok, f"주말 밤 시간대(자정 직전 1회) - {'실행' if ok else '대기'}"
        else:
            ok = minute == 0
            return ok, f"평일 밤 시간대(1시간마다) - {'실행' if ok else '대기'}"
