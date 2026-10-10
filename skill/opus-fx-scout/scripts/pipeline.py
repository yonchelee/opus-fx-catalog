#!/usr/bin/env python3
"""카탈로그 갱신 파이프라인 — 예약 실행(GitHub Actions)과 수동 실행이 같이 쓴다.

  python3 pipeline.py --dir <clone> --mode daily|weekly [--skip-sync] [--skip-discover]

순서: 등록 출처 동기화(sync.py --out, 좋아요·페이지 생성 포함) → GitHub 후보 발굴(discover) → 정적 페이지 생성
      → 데이터 검증 → 상태·실행 기록. 커밋·배포·공개 확인은 작업 흐름(.github/workflows/catalog-update.yml)이 한다.

종료 코드
  0  정상 또는 부분 실패(성공한 단계의 자료는 보존, 실패는 status.json 에 기록) → 커밋해도 된다
  3  수집 단계가 모두 실패 → 커밋하지 않는다
  4  생성·검증 실패 → 커밋하지 않는다(불완전한 결과를 배포하지 않는다)
"""
import argparse, json, os, subprocess, sys, traceback, urllib.request
from pathlib import Path

SITE_STATUS = 'https://yonchelee.github.io/opus-fx-catalog/status.json'


def reconcile_publish(stages, local_status, now):
    """지난 실행 결과가 공개 사이트에 실제로 올라갔는지 본다(Pages 빌드 실패·확인 실패 회복용).
    사이트의 status.json run_id 가 저장소의 것과 다르면 지난 공개는 실패한 것 — 성공으로 남기지 않는다.
    이번 실행이 다시 커밋·빌드하므로 미배포 변경은 여기서 회복된다."""
    prev = local_status.get('run_id')
    if not prev:
        return
    try:
        with urllib.request.urlopen(urllib.request.Request(SITE_STATUS + '?v=' + now.replace(':', ''), headers={'Cache-Control': 'no-cache'}), timeout=20) as r:
            live = json.loads(r.read().decode()).get('run_id')
    except Exception as e:  # noqa: BLE001 — 사이트를 못 읽으면 판단하지 않는다
        stages['publish'] = stage_status(stages, 'publish', stages.get('publish', {}).get('ok', False), now, f'공개 사이트 확인 불가: {type(e).__name__}')
        stages['publish']['ok'] = stages.get('publish', {}).get('ok', False)
        return
    ok = live == prev
    s = stage_status(stages, 'publish', ok, now, f'지난 실행 {prev} 공개됨' if ok else f'지난 실행 {prev} 이 공개 사이트에 반영되지 않음(사이트는 {live}) — 이번 실행이 다시 배포')
    if ok:
        s['last_success'] = local_status.get('updated', now)
    stages['publish'] = s

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_site  # noqa: E402
import discover  # noqa: E402

KEEP_RUNS = 90


def stage_status(prev, name, ok, now, message=''):
    s = dict(prev.get(name) or {})
    s['last_attempt'] = now
    s['ok'] = ok
    s['message'] = message[:300]
    if ok:
        s['last_success'] = now
    return s


def validate(root):
    """공개 데이터 검증. 문제 목록(비면 통과)."""
    problems = []
    cat = json.loads((root / 'catalog.json').read_text())
    gh = json.loads((root / 'github.json').read_text()) if (root / 'github.json').exists() else {'items': []}
    ids = [r['id'] for r in cat['items']] + [r['id'] for r in gh['items']]
    if len(ids) != len(set(ids)):
        problems.append('id 중복')
    for r in gh['items']:
        for k in ('id', 'author', 'title', 'kind', 'repo', 'first_seen', 'added', 'level'):
            if r.get(k) in (None, ''):
                problems.append(f"{r.get('id')}: {k} 없음")
        if r.get('kind') not in ('effect', 'collection'):
            problems.append(f"{r['id']}: 공개할 수 없는 유형 {r.get('kind')}")
        if r.get('prompt'):
            problems.append(f"{r['id']}: GitHub 작품에 프롬프트 문자열(만들어 넣지 않는다)")
        st = (r.get('repo') or {}).get('stars')
        if st is not None and st < 0:
            problems.append(f"{r['id']}: 별 수 음수")
    if len(cat['items']) < 600:  # catalog.json(X 수집분)만 센다
        problems.append(f"catalog.json 이 {len(cat['items'])}개로 줄었다 — 수집 실패로 삭제됐을 수 있음")
    if build_site.build(root, check=True) != 0:
        problems.append('생성 페이지가 원천과 다름')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--mode', choices=['daily', 'weekly'], default='daily')
    ap.add_argument('--skip-sync', action='store_true')
    ap.add_argument('--skip-discover', action='store_true')
    ap.add_argument('--run-id', default=os.environ.get('GITHUB_RUN_ID', ''))
    ap.add_argument('--check-site', action='store_true', help='공개 사이트 status.json 과 대조해 지난 배포 결과를 기록(Actions 에서는 자동)')
    a = ap.parse_args()
    root = Path(a.dir).resolve()
    now = discover.now_iso()
    run_id = a.run_id or 'local-' + now.replace(':', '').replace('-', '')
    status = discover.read_json(root / 'status.json', {})
    stages = status.get('stages', {})
    if os.environ.get('GITHUB_ACTIONS') or a.check_site:
        reconcile_publish(stages, status, now)
    log = {'run_id': run_id, 'mode': a.mode, 'started': now, 'where': 'github-actions' if os.environ.get('GITHUB_ACTIONS') else 'local'}
    collected = []

    if not a.skip_sync:
        r = subprocess.run([sys.executable, str(HERE / 'sync.py'), '--out', str(root)], capture_output=True, text=True,
                           env={**os.environ, 'OPUS_FX_HOME': os.environ.get('OPUS_FX_HOME', str(root / '.cache-opus-fx'))})
        ok = r.returncode == 0 and 'ERROR' not in r.stdout
        log['sync'] = {'code': r.returncode, 'out': r.stdout[-2000:], 'err': r.stderr[-1500:]}
        stages['sync'] = stage_status(stages, 'sync', ok, now, (r.stdout.strip().splitlines() or [''])[-1])
        collected.append(ok)

    if not a.skip_discover:
        try:
            cfg = discover.read_json(root / 'discovery/config.json', None)
            dl = discover.Run(root, a.mode, discover.make_client(cfg, a.mode)).run()
            log['discover'] = dl
            ok = not [e for e in dl['errors'] if e.startswith('search:')]
            stages['discover'] = stage_status(stages, 'discover', ok, now,
                                              f"후보 {dl['counts']['new_candidates']} 새로 · 공개 {dl['counts']['published_new']} · 보류 {dl['counts']['held_new']}"
                                              + (f" · 중단 {dl['stop']}" if dl['stop'] else '')
                                              + (f" · 확인 오류 {len([e for e in dl['errors'] if e.startswith('judge')])}건" if any(e.startswith('judge') for e in dl['errors']) else ''))
            stars_ok = dl['counts']['stars_failed'] == 0 and not [e for e in dl['errors'] if e.startswith('stars')]
            stages['stars'] = stage_status(stages, 'stars', stars_ok, now, f"별 기록 {dl['counts']['stars_updated']}")
            collected.append(ok)
        except Exception as e:  # noqa: BLE001
            log['discover'] = {'error': traceback.format_exc()[-2000:]}
            stages['discover'] = stage_status(stages, 'discover', False, now, f'{type(e).__name__}: {e}')
            collected.append(False)

    code = 0
    if collected and not any(collected):
        code = 3
    try:
        build_site.build(root)
        problems = validate(root)
    except Exception as e:  # noqa: BLE001
        problems = [f'{type(e).__name__}: {e}']
    log['validate'] = problems
    if problems:
        code = 4
    stages['build'] = stage_status(stages, 'build', not problems, now, '; '.join(problems) or '생성·검증 통과')

    log['finished'] = discover.now_iso()
    log['exit'] = code
    dc = (log.get('discover') or {}).get('counts') or {}
    last_run = {'run_id': run_id, 'mode': a.mode, 'at': log['finished'], 'exit': code,
                'candidates_new': dc.get('new_candidates', 0), 'published_new': dc.get('published_new', 0), 'held_new': dc.get('held_new', 0),
                'withdrawn': dc.get('withdrawn', 0), 'source_new': dc.get('source_new', 0), 'rejected_new': dc.get('rejected_new', 0),
                'stars_updated': dc.get('stars_updated', 0), 'stars_failed': dc.get('stars_failed', 0),
                'stop': (log.get('discover') or {}).get('stop'), 'errors': len((log.get('discover') or {}).get('errors') or [])}
    status = {'updated': log['finished'], 'run_id': run_id, 'mode': a.mode, 'stages': stages, 'last_run': last_run,
              'published_github': len(json.loads((root / 'github.json').read_text())['items']) if (root / 'github.json').exists() else 0}
    discover.write_json(root / 'status.json', status)
    runs = root / 'discovery/runs'
    discover.write_json(runs / f'{log["started"][:10]}_{run_id}.json', log)
    for old in sorted(runs.glob('*.json'))[:-KEEP_RUNS]:
        old.unlink()
    print(json.dumps({'exit': code, 'stages': {k: {'ok': v['ok'], 'message': v['message']} for k, v in stages.items()}}, ensure_ascii=False, indent=1))
    sys.exit(code)


if __name__ == '__main__':
    main()
