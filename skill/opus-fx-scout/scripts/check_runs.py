#!/usr/bin/env python3
"""예약 실행 점검.  python3 skill/opus-fx-scout/scripts/check_runs.py [--since 2026-10-11T00:00:00Z]

확인하는 것
  1. GitHub Actions catalog-update 의 최근 실행: 원인(schedule / workflow_dispatch), 결과
  2. 예약(schedule) 실행마다: main 의 discovery/runs 기록, status.json run_id, 단계별 ok
  3. 공개 사이트 status.json 의 run_id 가 마지막 성공 실행과 같은지(배포 반영)
필요: gh 로그인, 저장소 클론(이 스크립트 위치 기준). 네트워크만 읽는다. 아무것도 바꾸지 않는다.
"""
import argparse, json, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPO = 'yonchelee/opus-fx-catalog'
SITE = 'https://yonchelee.github.io/opus-fx-catalog/'


def gh(*args):
    return json.loads(subprocess.check_output(['gh', *args], text=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', default='')
    ap.add_argument('--limit', type=int, default=12)
    a = ap.parse_args()
    runs = gh('run', 'list', '-R', REPO, '-w', 'catalog-update.yml', '-L', str(a.limit), '--json', 'databaseId,event,status,conclusion,createdAt,headSha')
    subprocess.run(['git', '-C', str(ROOT), 'fetch', '-q', 'origin', 'main'], check=False)
    print('최근 실행 (원인 / 결과 / 시작 UTC)')
    sched = []
    for r in runs:
        if a.since and r['createdAt'] < a.since:
            continue
        print(f"  {r['databaseId']}  {r['event']:18} {r['status']:10} {str(r['conclusion']):8} {r['createdAt']}")
        if r['event'] == 'schedule':
            sched.append(r)
    if not sched:
        print('\n예약(schedule) 실행 없음 — 아직 시각이 안 됐거나 GitHub 지연. 수동 실행만으로 "예약 실행 성공"이라 적지 말 것.')
    for r in sched:
        rid = str(r['databaseId'])
        print(f"\n== 예약 실행 {rid} ({r['createdAt']}) {r['status']} {r['conclusion']}")
        try:
            files = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '--name-only', 'origin/main', 'discovery/runs/'], text=True).split()
            mine = [f for f in files if rid in f]
            if mine:
                log = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', f'origin/main:{mine[0]}'], text=True))
                d = log.get('discover') or {}
                print('  기록:', mine[0], '| exit', log.get('exit'), '| 동기화 code', (log.get('sync') or {}).get('code'))
                print('  발굴:', {k: v for k, v in (d.get('counts') or {}).items() if v}, '| 중단', d.get('stop'), '| 오류', len(d.get('errors') or []))
                print('  검증 문제:', log.get('validate'))
            else:
                print('  main 에 이 실행의 기록 없음 → 커밋되지 않음(변경 없음 종료이거나 실패)')
            st = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'origin/main:status.json'], text=True))
            print('  main status.json run_id:', st.get('run_id'), '| 단계:', {k: v.get('ok') for k, v in (st.get('stages') or {}).items()})
        except subprocess.CalledProcessError as e:
            print('  git 조회 실패:', e)
    try:
        with urllib.request.urlopen(SITE + 'status.json?v=check', timeout=20) as r:
            live = json.loads(r.read().decode())
        print('\n공개 사이트 status.json: run_id', live.get('run_id'), '| 갱신', live.get('updated'),
              '| 단계', {k: v.get('ok') for k, v in (live.get('stages') or {}).items()})
        last_ok = next((r for r in runs if r['conclusion'] == 'success'), None)
        if last_ok:
            same = str(last_ok['databaseId']) == str(live.get('run_id'))
            print('  마지막 성공 실행', last_ok['databaseId'], '과', '같음 ✓' if same else '다름 ✗ — 배포 미반영 또는 Pages 지연')
    except Exception as e:  # noqa: BLE001
        print('\n공개 사이트 status.json 읽기 실패:', e)
    return 0


if __name__ == '__main__':
    sys.exit(main())
