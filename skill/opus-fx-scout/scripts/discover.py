#!/usr/bin/env python3
"""GitHub 신규 후보 발굴.  python3 discover.py --dir <clone> [--mode daily|weekly]

흐름(설정: discovery/config.json)
  popular  누적 별이 많은 관련 저장소 (검색어를 회차마다 돌려 가며)
  new      최근 생성된 저장소 — 별 하한을 높이지 않는다. 결과가 1,000개를 넘는 구간은 생성일을 반씩 나눠 다시 찾는다
  updated  최근 갱신된 기존 저장소
  backfill (매주) 생성일 구간을 과거로 넓혀 간다
처리한 구간과 다음 시작 위치는 discovery/state.json 에 남겨 다음 실행이 이어 간다.
GitHub 검색은 검색당 1,000개까지만 돌려주므로 '전체를 빠짐없이' 모으는 것이 아니다.

저장 위치(원본·편집·인기 시계열·실행 기록을 나눈다)
  discovery/candidates.json  모든 후보(공개·보류·출처 후보·제외)와 판정 사유  ← 이 스크립트만 쓴다
  discovery/stars.json       저장소별 별 수 시계열                              ← 이 스크립트만 쓴다
  discovery/state.json       검색 구간 진행 위치
  github.json                갤러리에 싣는 공개 작품(후보에서 만든다)
  editorial.json             손 편집 — 읽기만 한다
외부 후보의 코드를 설치하거나 실행하지 않는다. README·파일 목록·메타데이터만 읽는다.
"""
import argparse, json, re, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ghapi  # noqa: E402
import judge  # noqa: E402
import popularity  # noqa: E402
from classify import classify  # noqa: E402

GH_LINK = re.compile(r'github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)', re.I)


def now_iso():
    return popularity.iso(datetime.now(timezone.utc))


def read_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def write_json(p, data, indent=1):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + '\n')
    tmp.replace(p)  # 중간에 죽어도 반쯤 쓴 파일이 남지 않게


class Run:
    def __init__(self, root, mode, client, today=None, now=None):
        self.root = Path(root)
        self.mode = mode
        self.c = client
        self.cfg = read_json(self.root / 'discovery/config.json', None)
        if not self.cfg:
            raise SystemExit('discovery/config.json 없음')
        self.state = read_json(self.root / 'discovery/state.json', {})
        cands = read_json(self.root / 'discovery/candidates.json', {'items': {}})
        self.cands = cands.get('items', {})
        self.stars = read_json(self.root / 'discovery/stars.json', {})
        self.today = today or date.today()
        self.now = now or now_iso()
        self.log = {'mode': mode, 'started': self.now, 'searches': [], 'errors': [], 'stop': None,
                    'counts': {k: 0 for k in ('hits', 'new_candidates', 'seen_again', 'enriched', 'published_new', 'held_new',
                                              'source_new', 'rejected_new', 'duplicates', 'stars_updated', 'stars_failed',
                                              'renamed', 'gone', 'truncated_windows')}}
        self.xmap = self._x_links()
        ed = read_json(self.root / 'editorial.json', {})
        self.overrides = ((ed.get('discovery_overrides') or {}).get('items')) or {}

    # ---------- 공통 ----------
    def _x_links(self):
        """X 카탈로그 항목이 언급한 GitHub 저장소 → X 작품 id. 같은 작품의 두 링크를 잇는다."""
        out = {}
        for r in read_json(self.root / 'catalog.json', {'items': []}).get('items', []):
            text = ' '.join(str(r.get(k) or '') for k in ('prompt', 'title', 'video_url', 'post_url', 'prompt_url'))
            for o, n in GH_LINK.findall(text):
                n = re.sub(r'\.git$', '', n).rstrip('.')
                if o.lower() in ('yihui-dev', 'li-evan', 'yonchelee'):
                    continue
                out.setdefault(f'{o}/{n}'.lower(), set()).add(r['id'])
        return out

    def ingest(self, item, source):
        """검색 결과 한 건을 후보로 합친다. 저장소 고유 번호(id)가 열쇠라 이름이 바뀌어도 같은 후보다."""
        self.log['counts']['hits'] += 1
        key = str(item['id'])
        c = self.cands.get(key)
        meta = {
            'repo_id': item['id'], 'node_id': item.get('node_id'), 'full_name': item['full_name'], 'url': item['html_url'],
            'owner': (item.get('owner') or {}).get('login'), 'name': item.get('name'), 'description': item.get('description') or '',
            'topics': item.get('topics') or [], 'language': item.get('language'), 'default_branch': item.get('default_branch'),
            'homepage': item.get('homepage') or '', 'license': judge.license_ok(item), 'created_at': item.get('created_at'),
            'pushed_at': item.get('pushed_at'), 'fork': bool(item.get('fork')), 'mirror': bool(item.get('mirror_url')),
            'archived': bool(item.get('archived')),
        }
        if c is None:
            c = {'id': f"gh:{item['id']}", 'first_seen': self.now, 'sources': [], 'status': 'new'}
            self.cands[key] = c
            self.log['counts']['new_candidates'] += 1
        else:
            self.log['counts']['seen_again'] += 1
            if c.get('full_name') and c['full_name'] != meta['full_name']:
                c.setdefault('former_names', []).append(c['full_name'])
                self.log['counts']['renamed'] += 1
        c.update(meta)
        c['last_seen_search'] = self.now
        if source not in c['sources']:
            c['sources'].append(source)
        if item.get('stargazers_count') is not None:
            c['stars'], c['stars_at'] = item['stargazers_count'], self.now
        return c

    def search_all(self, q, sort, source, max_pages=10):
        """한 검색의 모든 페이지(1,000개 한도 안에서). (total, truncated)"""
        page, total = 1, 0
        while True:
            r = self.c.search_repos(q, sort=sort, page=page)
            total = r.get('total_count', 0)
            for it in r.get('items', []):
                self.ingest(it, source)
            self.log['searches'].append({'q': q, 'page': page, 'total': total, 'incomplete': r.get('incomplete_results')})
            if page * 100 >= min(total, 1000) or page >= max_pages or not r.get('items'):
                return total, total > page * 100
            page += 1

    def created_window(self, base, flow_cfg, a, b, source, depth=0):
        """created:a..b 구간을 찾는다. 1,000개를 넘으면 반으로 나눈다. 끝까지 처리하면 True."""
        q = f"{base} created:{a.isoformat()}..{b.isoformat()} stars:{flow_cfg['stars']} fork:false"
        first = self.c.search_repos(q, sort=flow_cfg['sort'], page=1, per_page=1)
        total = first.get('total_count', 0)
        self.log['searches'].append({'q': q, 'page': 0, 'total': total, 'probe': True})
        if total > 1000 and a < b and depth < flow_cfg.get('max_window_split_depth', 6):
            mid = a + (b - a) // 2
            return self.created_window(base, flow_cfg, a, mid, source, depth + 1) and \
                self.created_window(base, flow_cfg, mid + timedelta(days=1), b, source, depth + 1)
        if total == 0:
            return True
        _, truncated = self.search_all(q, flow_cfg['sort'], source)
        if truncated:
            self.log['counts']['truncated_windows'] += 1  # 하루짜리 구간도 1,000개 초과 — 별 많은 순 상위만
        return True

    # ---------- 흐름 ----------
    def flow_new(self):
        f = self.cfg['flows']['new']
        st = self.state.setdefault('new', {})
        for qd in self.cfg['queries']:
            s = st.get(qd['id'], {})
            start = date.fromisoformat(s['until']) if s.get('until') else self.today - timedelta(days=f['first_window_days'])
            if self.created_window(qd['q'], f, start, self.today, f"new:{qd['id']}"):
                st[qd['id']] = {'until': (self.today - timedelta(days=1)).isoformat(), 'at': self.now}

    def flow_updated(self):
        f = self.cfg['flows']['updated']
        st = self.state.setdefault('updated', {})
        for qd in self.cfg['queries']:
            since = st.get(qd['id'], {}).get('since') or (self.today - timedelta(days=7)).isoformat()
            q = f"{qd['q']} pushed:>={since} stars:{f['stars']} fork:false"
            self.search_all(q, f['sort'], f"updated:{qd['id']}", max_pages=f['pages'])
            st[qd['id']] = {'since': (self.today - timedelta(days=1)).isoformat(), 'at': self.now}

    def flow_popular(self):
        f = self.cfg['flows']['popular']
        st = self.state.setdefault('popular', {'cursor': 0})
        qs = self.cfg['queries']
        n = f['queries_per_run'][self.mode]
        for _ in range(min(n, len(qs))):
            qd = qs[st['cursor'] % len(qs)]
            q = f"{qd['q']} stars:{f['stars']} fork:false"
            self.search_all(q, f['sort'], f"popular:{qd['id']}", max_pages=f['pages'])
            st['cursor'] = (st['cursor'] + 1) % len(qs)
            st['at'] = self.now

    def flow_backfill(self):
        f = self.cfg['flows']['backfill']
        st = self.state.setdefault('backfill', {})
        oldest = date.fromisoformat(f['oldest'])
        for qd in self.cfg['queries']:
            before = date.fromisoformat(st.get(qd['id'], {}).get('before') or
                                        (self.today - timedelta(days=self.cfg['flows']['new']['first_window_days'])).isoformat())
            for _ in range(f['windows_per_query']):
                if before <= oldest:
                    break
                a = max(oldest, before - timedelta(days=f['step_days']))
                b = before - timedelta(days=1)
                if self.created_window(qd['q'], f, a, b, f"backfill:{qd['id']}"):
                    before = a
                    st[qd['id']] = {'before': before.isoformat(), 'at': self.now}

    # ---------- 확인·판정 ----------
    def needs_enrich(self, c):
        if c.get('status') in ('new', None):
            return True
        if c.get('rules_version') != self.cfg['judge'].get('rules_version'):
            return True  # 판정 규칙이 바뀌었다 — 다시 판정
        last = c.get('last_checked')
        return not last or (popularity.parse(self.now) - popularity.parse(last)).days >= self.cfg['judge']['enrich_stale_days']

    def head_relevant(self, c):
        cl = judge.classify_repo(c, '', [], self.cfg['judge'])
        return cl['relevant'] or bool(cl['hits'])

    def enrich_and_judge(self):
        jc = self.cfg['judge']
        todo = [c for c in self.cands.values() if self.needs_enrich(c)]
        # 이미 공개한 작품을 먼저 다시 보고(규칙 개정 반영), 그다음 새 후보를 별 많은 순으로
        todo.sort(key=lambda c: ({'published': 0, 'new': 1}.get(c.get('status'), 2), -(c.get('stars') or 0)))
        homes = {judge.norm_url(c.get('demo_url')): c['id'] for c in self.cands.values() if c.get('status') == 'published' and c.get('demo_url')}
        # 포크 표시 없이 통째로 옮긴 복사본: 이름과 설명이 같은 저장소는 먼저 발견한 쪽만 공개
        for c in sorted(self.cands.values(), key=lambda c: (c['first_seen'], c['repo_id'])):
            if c.get('status') == 'published':
                homes.setdefault(self.copy_key(c), c['id'])
        for c in todo:
            try:
                self.judge_one(c, jc, homes)
                c.pop('judge_errors', None)
            except ghapi.Budget:
                raise
            except Exception as e:  # noqa: BLE001 — 후보 하나의 오류가 나머지를 막지 않게
                c['judge_errors'] = c.get('judge_errors', 0) + 1
                self.log['errors'].append(f"judge {c['full_name']}: {type(e).__name__}: {e}")
                if c['judge_errors'] >= 3:
                    c.update(status='held', reasons=[f'자동 확인 3회 실패 ({type(e).__name__}) — 사람 확인 필요'], last_checked=self.now,
                             rules_version=jc.get('rules_version'))

    def judge_one(self, c, jc, homes):
        """후보 하나를 확인·판정한다. 오류는 호출한 쪽이 후보 단위로 받는다."""
        was = c.get('status')
        if not self.head_relevant(c) or c.get('fork'):
            status, reasons = ('rejected', ['시각 효과와 관련 낮음 (이름·설명·주제)']) if not self.head_relevant(c) else ('held', ['포크 저장소'])
            c.update(kind=c.get('kind') or 'unknown', relevant=False if status == 'rejected' else c.get('relevant'))
        else:
            readme = self.c.readme(c['full_name'])
            contents = self.c.root_contents(c['full_name'])
            self.log['counts']['enriched'] += 1
            cl = judge.classify_repo(c, readme, contents, jc)
            has_prompt, prompt_url = judge.prompt_info(readme, contents, c['full_name'], c.get('default_branch'))
            level, env_text = judge.environment(c, contents, jc)
            c.update(kind=cl['kind'], relevant=cl['relevant'], has_code=cl['has_code'], strong_topics=cl['strong_topics'],
                     tool_words=cl['tool_words'], effect_words=cl['effect_words'],
                     hits=cl['hits'], thumb=judge.readme_media(readme, c['full_name'], c.get('default_branch')),
                     demo_url=judge.demo_url(c, readme, jc), has_prompt=has_prompt, prompt_url=prompt_url,
                     level=level, env_text=env_text, ai_made=bool(re.search(r'\b(claude|opus|anthropic)\b', readme or '', re.I)))
            dup = homes.get(judge.norm_url(c.get('demo_url'))) or homes.get(self.copy_key(c))
            c['duplicate_of'] = dup if dup and dup != c['id'] else None
            status, reasons = judge.decide(c, jc)
        rv = self.cfg['judge'].get('rules_version')
        if was == 'published' and status != 'published':
            if c.get('rules_version') == rv:
                # 같은 규칙인데 결과가 바뀜(별 감소·미리보기 일시 실패 등) — 한 번의 변동으로 내리지 않는다. 사유는 남긴다.
                c['recheck'] = {'at': self.now, 'would_be': status, 'reasons': reasons}
                status, reasons = 'published', c.get('reasons', reasons)
            else:
                # 판정 규칙이 고쳐졌다 — 잘못 공개된 작품을 내린다. 기록은 남긴다.
                c['withdrawn'] = {'at': self.now, 'from_rules': c.get('rules_version'), 'to_rules': rv, 'reasons': reasons}
                self.log['counts']['withdrawn'] = self.log['counts'].get('withdrawn', 0) + 1
        else:
            c.pop('recheck', None)
        c['rules_version'] = rv
        if status != was:
            c['status_since'] = self.now
            if was in ('new', None):
                self.log['counts'][{'published': 'published_new', 'held': 'held_new', 'source': 'source_new', 'rejected': 'rejected_new'}[status]] += 1
            elif status == 'published':
                self.log['counts']['published_new'] += 1
        if was in ('new', None) and c.get('duplicate_of'):
            self.log['counts']['duplicates'] += 1
        ov = self.overrides.get(c['id'])
        if ov and ov.get('status') in ('held', 'published'):
            # 사람이 정한 값이 자동 판정보다 우선한다
            status, reasons = ov['status'], ['사람이 정함: ' + (ov.get('reason') or '')] + ([f'자동 판정은 {status}'] if status != ov['status'] else [])
        c['status'], c['reasons'], c['last_checked'] = status, reasons, self.now
        xs = self.xmap.get(c['full_name'].lower())
        c['x_ids'] = sorted(xs) if xs else []
        if status == 'published':
            if c.get('demo_url'):
                homes.setdefault(judge.norm_url(c['demo_url']), c['id'])
            homes.setdefault(self.copy_key(c), c['id'])
            c['preview_ok'] = self.head_ok(c.get('thumb'))
            c['demo_ok'] = self.head_ok(c.get('demo_url'))

    @staticmethod
    def copy_key(c):
        return 'copy:' + (c.get('name') or '').lower() + '|' + re.sub(r'\W+', ' ', (c.get('description') or '').lower()).strip()

    def head_ok(self, url):
        """미리보기·데모 링크가 열리는지만 본다. 열린다고 재현 성공이 아니다."""
        if not url:
            return None
        try:
            req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'opus-fx-catalog-discovery'})
            with self.c.open(req, timeout=15) as r:
                return 200 <= r.status < 400
        except Exception:  # noqa: BLE001
            return False

    # ---------- 별 수 ----------
    def refresh_stars(self):
        tracked = [c for c in self.cands.values() if c.get('status') in ('published', 'held') and c.get('node_id')]
        try:
            nodes = self.c.repos_by_node([c['node_id'] for c in tracked])
        except ghapi.Budget:
            raise
        except Exception as e:  # noqa: BLE001
            self.log['errors'].append(f'stars: {e}')
            self.log['counts']['stars_failed'] += len(tracked)
            return
        for c in tracked:
            n = nodes.get(c['node_id'])
            if not n:
                c['gone'] = True  # 접근 불가 — 지우지 않고 표시만
                self.log['counts']['gone'] += 1
                continue
            c.pop('gone', None)
            if n['nameWithOwner'] != c['full_name']:
                c.setdefault('former_names', []).append(c['full_name'])
                c['full_name'], c['url'] = n['nameWithOwner'], n['url']
                c['owner'], c['name'] = n['nameWithOwner'].split('/', 1)
                self.log['counts']['renamed'] += 1
            c['stars'], c['stars_at'] = n['stargazerCount'], self.now
            c['archived'], c['pushed_at'] = n['isArchived'], n['pushedAt']
            key = str(c['repo_id'])
            self.stars[key] = popularity.add_point(self.stars.get(key), self.now, n['stargazerCount'], self.cfg['trend']['keep_points'])
            self.log['counts']['stars_updated'] += 1

    # ---------- 공개용 ----------
    def public_items(self):
        out = []
        tc = self.cfg['trend']
        for c in sorted(self.cands.values(), key=lambda c: c['first_seen']):
            ov = self.overrides.get(c['id'])
            if (ov.get('status') if ov else c.get('status')) != 'published':
                continue
            t = popularity.trend(self.stars.get(str(c['repo_id'])), self.now, tc)
            fx, _, _ = classify(' '.join([c.get('name') or '', c.get('description') or ''] + c.get('topics', [])), [])
            out.append({
                'id': c['id'], 'src': 'gh', 'slug': c['full_name'], 'author': c['owner'], 'title': c['name'],
                'desc': c.get('description') or '', 'topics': c.get('topics', []), 'kind': c['kind'],
                'repo': {'id': c['repo_id'], 'full_name': c['full_name'], 'url': c['url'], 'license': c.get('license'),
                         'created_at': c.get('created_at'), 'pushed_at': c.get('pushed_at'), 'archived': c.get('archived'),
                         'stars': c.get('stars'), 'stars_at': c.get('stars_at'), 'gone': bool(c.get('gone'))},
                'thumb': c.get('thumb') if c.get('preview_ok') is not False else None, 'demo_url': c.get('demo_url'),
                'demo_ok': c.get('demo_ok'), 'preview_ok': c.get('preview_ok'),
                'has_code': c.get('has_code', True), 'has_prompt': bool(c.get('has_prompt')), 'prompt_url': c.get('prompt_url'),
                'prompt': '', 'partial': False, 'fx': fx, 'needs': [], 'level': c.get('level', 2), 'env_text': c.get('env_text'),
                'first_seen': c['first_seen'], 'last_checked': c.get('last_checked'), 'added': c['first_seen'][:10],
                'check': 'preview' if c.get('preview_ok') or c.get('demo_ok') else 'discovered',
                'trend': t if popularity.rankable(t, c.get('stars'), tc) else None,
                'trend_note': None if t else '집계 중', 'x_ids': c.get('x_ids', []), 'sources': c['sources'],
            })
        return out

    def save(self):
        write_json(self.root / 'discovery/state.json', self.state)
        write_json(self.root / 'discovery/candidates.json', {'updated': self.now, 'items': dict(sorted(self.cands.items(), key=lambda kv: int(kv[0])))}, indent=0)
        write_json(self.root / 'discovery/stars.json', dict(sorted(self.stars.items(), key=lambda kv: int(kv[0]))), indent=0)
        items = self.public_items()
        write_json(self.root / 'github.json', {'updated': self.now, 'items': items}, indent=0)
        st = {}
        for c in self.cands.values():
            st[c.get('status')] = st.get(c.get('status'), 0) + 1
        self.log['totals'] = st
        self.log['published_total'] = len(items)

    def run(self):
        flows = ['new', 'updated', 'popular'] + (['backfill'] if self.mode == 'weekly' else [])
        try:
            for f in flows:
                getattr(self, 'flow_' + f)()
            self.log['flows_done'] = flows
        except ghapi.Budget as e:
            self.log['stop'] = f'search: {e}'  # 다음 회차가 state 에서 이어 간다
        except Exception as e:  # noqa: BLE001
            self.log['errors'].append(f'search: {type(e).__name__}: {e}')
        try:
            self.enrich_and_judge()
        except ghapi.Budget as e:
            self.log['stop'] = (self.log['stop'] or '') + f' / enrich: {e}'
        except Exception as e:  # noqa: BLE001
            self.log['errors'].append(f'judge: {type(e).__name__}: {e}')
        try:
            self.refresh_stars()
        except ghapi.Budget as e:
            self.log['stop'] = (self.log['stop'] or '') + f' / stars: {e}'
            self.log['errors'].append(f'stars: budget {e}')
        self.save()
        self.log['finished'] = now_iso()
        self.log['api_used'] = self.c.used
        self.log['waits'] = self.c.waits
        return self.log


def make_client(cfg, mode, token=None):
    b = cfg['budget'][mode]
    return ghapi.Client(token=token, budget={k: b[k] for k in ('search', 'core', 'graphql')}, minutes=b['minutes'],
                        search_interval=cfg['budget']['search_interval_seconds'], max_wait=cfg['budget']['max_wait_seconds'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--mode', choices=['daily', 'weekly'], default='daily')
    a = ap.parse_args()
    cfg = read_json(Path(a.dir) / 'discovery/config.json', None)
    log = Run(a.dir, a.mode, make_client(cfg, a.mode)).run()
    print(json.dumps({k: log[k] for k in ('counts', 'stop', 'errors', 'api_used', 'totals', 'published_total')}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
