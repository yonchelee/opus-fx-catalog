"""별 수 시계열과 '최근 상승' 계산 (순수 함수).

- 측정은 하루 한 점. 같은 날 다시 재면 그 날 값을 바꾼다.
- 측정 실패는 기록하지 않는다(0 으로 적지 않는다). 마지막 정상 값과 시각이 그대로 남는다.
- 최근 상승 = 지금 값 − (window_days 이상 지난 측정 중 가장 최근 값). 그 측정이 max_window_days 안에 있어야 한다.
  측정이 한 번뿐이거나 기간이 모자라면 None('집계 중'). 비교한 두 시각을 함께 돌려준다.
- 별이 적은 저장소의 증가율 과장을 막기 위해 비율이 아니라 증가량으로 순위를 매기고, min_stars·min_delta 를 둔다.
"""
from datetime import datetime, timedelta, timezone


def parse(ts):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def add_point(series, ts, stars, keep=180):
    """series = [[iso, stars], ...] (시간순). stars 가 None 이면 아무것도 하지 않는다."""
    if stars is None:
        return series
    s = list(series or [])
    if s and s[-1][0][:10] == ts[:10]:
        s[-1] = [ts, int(stars)]
    else:
        s.append([ts, int(stars)])
    return s[-keep:]


def trend(series, now_ts, cfg):
    """{'delta', 'from', 'to', 'days'} 또는 None."""
    if not series or len(series) < 2:
        return None
    now = parse(series[-1][0])
    lo, hi = now - timedelta(days=cfg['max_window_days']), now - timedelta(days=cfg['window_days'])
    base = None
    for ts, n in series[:-1]:
        t = parse(ts)
        if lo <= t <= hi:
            base = (ts, n, t)  # 조건을 만족하는 것 중 가장 최근 것
    if not base:
        return None
    cur = series[-1][1]
    return {'delta': cur - base[1], 'from': base[0], 'to': series[-1][0],
            'days': round((now - base[2]).total_seconds() / 86400, 1)}


def rankable(t, stars, cfg):
    return bool(t) and stars is not None and stars >= cfg['min_stars'] and t['delta'] >= cfg['min_delta']
