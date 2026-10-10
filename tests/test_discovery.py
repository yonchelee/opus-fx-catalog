"""GitHub 후보 발굴 시험. 가짜 API 응답만 쓴다 — 실제 저장소의 별 수를 건드리지 않는다.
python3 -m unittest discover -s tests"""
import json, shutil, sys, tempfile, unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'skill' / 'opus-fx-scout' / 'scripts'))
import discover  # noqa: E402
import ghapi  # noqa: E402
import judge  # noqa: E402
import popularity  # noqa: E402

TODAY = date(2026, 10, 10)
NOW = '2026-10-10T06:00:00Z'


def repo(i, name, desc='', topics=(), stars=10, fork=False, lic='MIT', home='', lang='JavaScript', owner='maker'):
    return {'id': i, 'node_id': f'N{i}', 'full_name': f'{owner}/{name}', 'html_url': f'https://github.com/{owner}/{name}',
            'name': name, 'owner': {'login': owner}, 'description': desc, 'topics': list(topics), 'language': lang,
            'default_branch': 'main', 'homepage': home, 'license': {'spdx_id': lic} if lic else None,
            'created_at': '2026-10-05T00:00:00Z', 'pushed_at': '2026-10-09T00:00:00Z', 'fork': fork,
            'stargazers_count': stars, 'archived': False, 'mirror_url': None}


EFFECT = repo(101, 'aurora-shader', 'Aurora borealis WebGL shader demo', ['shader', 'webgl'], 40, home='https://maker.github.io/aurora-shader/')
LIB = repo(102, 'motionkit', 'Animation library for React components', ['animation', 'library'], 9000)
LIST = repo(103, 'awesome-shaders', 'A curated list of shader resources', ['shader', 'awesome-list'], 5000)
NOLIC = repo(104, 'glitch-text', 'Glitch text effect animation', ['css-animation'], 12, lic=None, home='https://maker.github.io/glitch-text/')
OFFTOPIC = repo(105, 'todo-app', 'A todo list app', ['react'], 50)
LOWSTAR = repo(106, 'tiny-particles', 'Particle animation canvas experiment', ['particles'], 1, home='https://maker.github.io/tiny/')

READMES = {
    'maker/aurora-shader': '# Aurora\n![preview](media/aurora.gif)\n[Live demo](https://maker.github.io/aurora-shader/)\n',
    'maker/motionkit': '# MotionKit\n![badge](https://img.shields.io/x)\n```\nnpm install motionkit\n```\n',
    'maker/awesome-shaders': '# Awesome\n' + '\n'.join(f'- [x{i}](https://example.com/{i})' for i in range(80)),
    'maker/glitch-text': '# Glitch\n![shot](shot.png)\n',
    'maker/tiny-particles': '# Tiny\n![t](t.gif)\n',
}
CONTENTS = {'maker/aurora-shader': ['index.html', 'main.js', 'shader.frag', 'media'], 'maker/motionkit': ['package.json', 'src', 'README.md'],
            'maker/awesome-shaders': ['README.md', 'LICENSE'], 'maker/glitch-text': ['index.html', 'style.css'],
            'maker/tiny-particles': ['index.html', 'app.js']}


class Resp:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


class FakeClient:
    """search_repos 는 검색어 안의 낱말로 결과를 고른다. 실패·예산 초과도 흉내 낸다."""
    def __init__(self, results, stars=None, fail_stars=False, search_budget=10**6, totals=None):
        self.results, self.star_nodes, self.fail_stars = results, stars or {}, fail_stars
        self.search_budget, self.totals = search_budget, totals or {}
        self.used = {'search': 0, 'core': 0, 'graphql': 0}
        self.waits, self.queries = [], []

    def search_repos(self, q, sort='stars', page=1, per_page=100):
        if self.used['search'] >= self.search_budget:
            raise ghapi.Budget('search')
        self.used['search'] += 1
        self.queries.append(q)
        items = []
        for key, rs in self.results.items():
            if key in q:
                items += rs
        total = next((t for k, t in self.totals.items() if k in q), len(items))
        return {'total_count': total, 'items': items if per_page > 1 else items[:1], 'incomplete_results': False}

    def readme(self, fn):
        self.used['core'] += 1
        return READMES.get(fn, '')

    def root_contents(self, fn):
        self.used['core'] += 1
        return CONTENTS.get(fn, [])

    def repos_by_node(self, ids):
        self.used['graphql'] += 1
        if self.fail_stars:
            raise RuntimeError('graphql down')
        return {i: self.star_nodes[i] for i in ids if i in self.star_nodes}

    def open(self, req, timeout=15):
        return Resp()


def node(i, name, stars, owner='maker'):
    return {'id': f'N{i}', 'databaseId': i, 'nameWithOwner': f'{owner}/{name}', 'url': f'https://github.com/{owner}/{name}',
            'stargazerCount': stars, 'pushedAt': '2026-10-09T00:00:00Z', 'isArchived': False}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'discovery').mkdir()
        cfg = json.loads((ROOT / 'discovery/config.json').read_text())
        cfg['queries'] = [{'id': 'q1', 'q': 'topic:shader'}, {'id': 'q2', 'q': 'topic:webgl'}]
        (self.d / 'discovery/config.json').write_text(json.dumps(cfg))
        self.cfg = cfg
        (self.d / 'catalog.json').write_text(json.dumps({'synced': '2026-10-10', 'items': [
            {'id': 'yihui:x-1', 'prompt': 'built with https://github.com/maker/aurora-shader', 'title': 'Aurora'}]}))
        shutil.copy(ROOT / 'editorial.json', self.d / 'editorial.json')

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_once(self, client, mode='daily', now=NOW, today=TODAY):
        return discover.Run(self.d, mode, client, today=today, now=now).run()

    def cands(self):
        return json.loads((self.d / 'discovery/candidates.json').read_text())['items']

    def public(self):
        return {r['id']: r for r in json.loads((self.d / 'github.json').read_text())['items']}


class Discovery(Base):
    def test_same_repo_from_many_searches_is_one_candidate(self):
        c = FakeClient({'topic:shader': [EFFECT], 'topic:webgl': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        log = self.run_once(c)
        cs = self.cands()
        self.assertEqual(list(cs), ['101'])
        self.assertGreaterEqual(len(cs['101']['sources']), 2)
        self.assertGreater(log['counts']['seen_again'], 0)
        self.assertEqual(log['counts']['new_candidates'], 1)

    def test_publish_and_hold_rules(self):
        c = FakeClient({'topic:shader': [EFFECT, LIB, LIST, NOLIC, OFFTOPIC, LOWSTAR]},
                       stars={f'N{i}': node(i, n, s) for i, n, s in [(101, 'aurora-shader', 40), (102, 'motionkit', 9000), (104, 'glitch-text', 12), (106, 'tiny-particles', 1)]})
        self.run_once(c)
        cs = self.cands()
        self.assertEqual(cs['101']['status'], 'published')
        self.assertEqual((cs['102']['status'], cs['102']['kind']), ('held', 'library'), '인기 라이브러리를 작품으로 공개하지 않는다')
        self.assertEqual((cs['103']['status'], cs['103']['kind']), ('source', 'list'), '자료집은 출처 후보')
        self.assertEqual(cs['104']['status'], 'held')
        self.assertTrue(any('라이선스' in r for r in cs['104']['reasons']))
        self.assertEqual(cs['105']['status'], 'rejected')
        self.assertEqual(cs['106']['status'], 'held', '별이 적은 신작은 찾되(후보) 공개 기준 미만이면 보류')
        self.assertEqual(set(self.public()), {'gh:101'})

    def test_public_item_has_no_invented_prompt(self):
        c = FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)
        r = self.public()['gh:101']
        self.assertEqual(r['prompt'], '')
        self.assertFalse(r['has_prompt'])
        self.assertEqual(r['kind'], 'effect')
        self.assertTrue(r['thumb'].startswith('https://raw.githubusercontent.com/maker/aurora-shader/main/media/aurora.gif'))
        self.assertEqual(r['x_ids'], ['yihui:x-1'], 'X 게시물에 언급된 저장소는 서로 잇는다')
        self.assertEqual(r['repo']['license'], 'MIT')
        self.assertEqual(r['first_seen'], NOW)

    def test_first_seen_never_changes_and_published_not_deleted(self):
        c = FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)
        later = '2026-10-11T06:00:00Z'
        c2 = FakeClient({}, stars={'N101': node(101, 'aurora-shader', 41)})  # 검색에서 빠져도
        self.run_once(c2, now=later, today=TODAY + timedelta(days=1))
        r = self.public()['gh:101']
        self.assertEqual(r['first_seen'], NOW)
        self.assertEqual(r['repo']['stars'], 41)

    def test_rename_keeps_identity(self):
        c = FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)
        c2 = FakeClient({}, stars={'N101': node(101, 'northern-lights', 42, owner='newowner')})
        log = self.run_once(c2, now='2026-10-11T06:00:00Z', today=TODAY + timedelta(days=1))
        cs = self.cands()
        self.assertEqual(list(cs), ['101'])
        self.assertEqual(cs['101']['full_name'], 'newowner/northern-lights')
        self.assertIn('maker/aurora-shader', cs['101']['former_names'])
        self.assertEqual(self.public()['gh:101']['id'], 'gh:101', '공유 링크·즐겨찾기 id 유지')
        self.assertEqual(log['counts']['renamed'], 1)

    def test_api_failure_keeps_last_value_not_zero(self):
        c = FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)
        before = self.public()
        c2 = FakeClient({}, fail_stars=True)
        log = self.run_once(c2, now='2026-10-11T06:00:00Z', today=TODAY + timedelta(days=1))
        after = self.public()
        self.assertEqual(after['gh:101']['repo']['stars'], 40)
        self.assertEqual(after['gh:101']['repo']['stars_at'], before['gh:101']['repo']['stars_at'])
        self.assertGreater(log['counts']['stars_failed'], 0)
        series = json.loads((self.d / 'discovery/stars.json').read_text())['101']
        self.assertEqual(len(series), 1, '실패한 날은 기록하지 않는다(0 을 적지 않는다)')

    def test_search_failure_keeps_existing_data(self):
        c = FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)

        class Broken(FakeClient):
            def search_repos(self, *a, **k):
                raise RuntimeError('search down')
        log = self.run_once(Broken({}, stars={'N101': node(101, 'aurora-shader', 40)}), now='2026-10-11T06:00:00Z')
        self.assertIn('gh:101', self.public())
        self.assertTrue(any(e.startswith('search:') for e in log['errors']))

    def test_budget_stop_resumes_next_time(self):
        c = FakeClient({'topic:shader': [EFFECT]}, search_budget=1, stars={'N101': node(101, 'aurora-shader', 40)})
        log = self.run_once(c)
        self.assertIn('search', log['stop'])
        st = json.loads((self.d / 'discovery/state.json').read_text())
        self.assertNotIn('q2', st.get('new', {}), '처리하지 못한 검색은 진행 위치를 올리지 않는다')

    def test_large_window_is_split(self):
        c = FakeClient({'topic:shader': [EFFECT]}, totals={'created:2026-09-26..2026-10-10': 4000},
                       stars={'N101': node(101, 'aurora-shader', 40)})
        self.run_once(c)
        created = [q for q in c.queries if 'topic:shader' in q and 'created:' in q]
        self.assertTrue(any('created:2026-09-26..2026-10-03' in q for q in created), created[:6])

    def test_rules_change_withdraws_wrongly_published_but_same_rules_keep(self):
        app = repo(107, 'snap-clone-demo', 'Snapchat clone demo with face filter animation', ['shader'], 50, home='https://maker.github.io/snap/')
        READMES['maker/snap-clone-demo'] = '![s](s.gif)'
        CONTENTS['maker/snap-clone-demo'] = ['index.html']
        stars = {'N107': node(107, 'snap-clone-demo', 50)}
        old = dict(self.cfg); old['judge'] = dict(self.cfg['judge'], app_words=[], rules_version=1)
        (self.d / 'discovery/config.json').write_text(json.dumps(old))
        self.run_once(FakeClient({'topic:shader': [app]}, stars=stars))
        self.assertIn('gh:107', self.public(), '옛 규칙으로는 공개')
        # 같은 규칙에서 별이 기준 아래로 떨어져도 내리지 않는다
        stale = '2026-10-30T06:00:00Z'
        self.run_once(FakeClient({}, stars={'N107': node(107, 'snap-clone-demo', 1)}), now=stale, today=date(2026, 10, 30))
        self.assertIn('gh:107', self.public())
        # 규칙이 고쳐지면 다시 판정해 내린다
        (self.d / 'discovery/config.json').write_text(json.dumps(self.cfg))
        log = self.run_once(FakeClient({}, stars=stars), now='2026-10-31T06:00:00Z', today=date(2026, 10, 31))
        self.assertNotIn('gh:107', self.public())
        c = self.cands()['107']
        self.assertEqual((c['status'], c['kind']), ('held', 'app'))
        self.assertIn('withdrawn', c)
        self.assertEqual(log['counts'].get('withdrawn'), 1)

    def test_human_override_wins(self):
        ed = json.loads((self.d / 'editorial.json').read_text())
        ed['discovery_overrides'] = {'items': {'gh:101': {'status': 'held', 'reason': '라이브러리'}}}
        (self.d / 'editorial.json').write_text(json.dumps(ed))
        self.run_once(FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)}))
        self.assertNotIn('gh:101', self.public())
        self.assertTrue(self.cands()['101']['reasons'][0].startswith('사람이 정함'))

    def test_one_bad_candidate_does_not_stop_others(self):
        bad = repo(108, 'bad-readme-effect', 'Broken readme shader effect demo', ['shader'], 50)
        READMES['maker/bad-readme-effect'] = '[demo](http://[::1/x) ![p](p.gif)'
        CONTENTS['maker/bad-readme-effect'] = ['index.html']
        orig = judge.demo_url
        def boom(repo, readme, cfg):
            if repo['name'] == 'bad-readme-effect':
                raise ValueError('Invalid IPv6 URL')
            return orig(repo, readme, cfg)
        judge.demo_url = boom
        try:
            log = self.run_once(FakeClient({'topic:shader': [bad, EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40), 'N108': node(108, 'bad-readme-effect', 50)}))
        finally:
            judge.demo_url = orig
        cs = self.cands()
        self.assertEqual(cs['101']['status'], 'published', '다른 후보는 계속 처리')
        self.assertEqual(cs['108'].get('judge_errors'), 1)
        self.assertTrue(any('bad-readme-effect' in e for e in log['errors']))

    def test_broken_url_in_readme_is_safe(self):
        cfg = json.loads((ROOT / 'discovery/config.json').read_text())['judge']
        self.assertIsNone(judge.demo_url({'homepage': 'http://[::1'}, '[live demo](http://[::1/x)', cfg))

    def test_copy_without_fork_flag_is_duplicate(self):
        copy = repo(109, 'aurora-shader', 'Aurora borealis WebGL shader demo ---', ['shader', 'webgl'], 30, owner='copier', home='')
        copy['created_at'] = '2026-10-07T00:00:00Z'  # 원본보다 나중에 생김
        READMES['copier/aurora-shader'] = READMES['maker/aurora-shader'].replace('maker.github.io', 'copier.github.io')
        CONTENTS['copier/aurora-shader'] = CONTENTS['maker/aurora-shader']
        log = self.run_once(FakeClient({'topic:shader': [EFFECT, copy]}, stars={'N101': node(101, 'aurora-shader', 40), 'N109': node(109, 'aurora-shader', 30, owner='copier')}))
        cs = self.cands()
        self.assertEqual(cs['101']['status'], 'published')
        self.assertEqual(cs['109']['status'], 'held')
        self.assertEqual(cs['109']['duplicate_of'], 'gh:101')
        self.assertEqual(log['counts']['duplicates'], 1)

    def test_already_published_copy_is_withdrawn_on_rules_change(self):
        # 실제 사례: 원본·복사본 둘 다 공개된 뒤, 각자 데모 주소를 가진 상태에서 규칙이 바뀌어 다시 판정
        orig = repo(110, 'three-examples', 'WebGL Three.js Examples And Demo ---', ['threejs', 'webgl'], 2000, owner='a', home='https://a.github.io/three-examples/')
        orig['created_at'] = '2024-07-02T00:00:00Z'
        copy = repo(111, 'three-examples', 'WebGL Three.js Examples And Demo ---', ['threejs', 'webgl'], 30, owner='b', home='https://b.github.io/three-examples/')
        copy['created_at'] = '2025-01-02T00:00:00Z'
        for o in ('a', 'b'):
            READMES[f'{o}/three-examples'] = '![p](p.gif)'
            CONTENTS[f'{o}/three-examples'] = ['index.html']
        stars = {'N110': node(110, 'three-examples', 2000, owner='a'), 'N111': node(111, 'three-examples', 30, owner='b')}
        old = dict(self.cfg); old['judge'] = dict(self.cfg['judge'], rules_version=0)
        (self.d / 'discovery/config.json').write_text(json.dumps(old))
        self.run_once(FakeClient({'topic:shader': [copy]}, stars=stars))           # 복사본이 먼저 발견돼 공개
        self.run_once(FakeClient({'topic:shader': [orig]}, stars=stars), now='2026-10-10T07:00:00Z')
        self.assertEqual({'gh:110', 'gh:111'} & set(self.public()), {'gh:110', 'gh:111'})
        (self.d / 'discovery/config.json').write_text(json.dumps(self.cfg))
        self.run_once(FakeClient({}, stars=stars), now='2026-10-11T06:00:00Z', today=date(2026, 10, 11))
        self.assertIn('gh:110', self.public(), '먼저 생긴 원본은 유지')
        self.assertNotIn('gh:111', self.public(), '나중에 생긴 복사본은 내림')
        self.assertEqual(self.cands()['111']['duplicate_of'], 'gh:110')

    def test_editorial_untouched(self):
        before = (self.d / 'editorial.json').read_bytes()
        self.run_once(FakeClient({'topic:shader': [EFFECT]}, stars={'N101': node(101, 'aurora-shader', 40)}))
        self.assertEqual((self.d / 'editorial.json').read_bytes(), before)


class Trend(unittest.TestCase):
    cfg = {'window_days': 7, 'max_window_days': 10, 'min_delta': 5, 'min_stars': 20}

    def test_single_measurement_is_not_ranked(self):
        s = popularity.add_point([], NOW, 100)
        self.assertIsNone(popularity.trend(s, NOW, self.cfg))

    def test_needs_full_window(self):
        s = popularity.add_point([], '2026-10-05T06:00:00Z', 100)
        s = popularity.add_point(s, NOW, 160)
        self.assertIsNone(popularity.trend(s, NOW, self.cfg), '5일 차이는 7일 비교 기간 미달')

    def test_seven_day_delta_with_times(self):
        s = popularity.add_point([], '2026-10-02T06:00:00Z', 100)
        s = popularity.add_point(s, NOW, 160)
        t = popularity.trend(s, NOW, self.cfg)
        self.assertEqual((t['delta'], t['from'], t['to']), (60, '2026-10-02T06:00:00Z', NOW))
        self.assertTrue(popularity.rankable(t, 160, self.cfg))

    def test_small_repo_ratio_not_exaggerated(self):
        s = popularity.add_point([], '2026-10-02T06:00:00Z', 2)
        s = popularity.add_point(s, NOW, 8)  # 4배지만 증가량 6, 별 8개
        self.assertFalse(popularity.rankable(popularity.trend(s, NOW, self.cfg), 8, self.cfg))

    def test_same_day_replaces_and_none_ignored(self):
        s = popularity.add_point([], '2026-10-10T01:00:00Z', 10)
        s = popularity.add_point(s, '2026-10-10T09:00:00Z', 12)
        s = popularity.add_point(s, '2026-10-11T09:00:00Z', None)
        self.assertEqual(s, [['2026-10-10T09:00:00Z', 12]])


class JudgeUnits(unittest.TestCase):
    def test_npm_package_install_means_library(self):
        cfg = json.loads((ROOT / 'discovery/config.json').read_text())['judge']
        r = {'name': 'vizceral', 'description': 'WebGL visualization for displaying animated traffic graphs', 'topics': [], 'language': 'JavaScript'}
        self.assertEqual(judge.classify_repo(r, 'npm install --save vizceral', ['package.json', 'src'], cfg)['kind'], 'library')
        self.assertEqual(judge.classify_repo(r, 'run `npm install` then `npm start`', ['package.json', 'src'], cfg)['kind'], 'effect')
        self.assertEqual(judge.classify_repo(r, 'vizceral is a component for displaying traffic data', ['src'], cfg)['kind'], 'library', 'README 자기소개')
        self.assertEqual(judge.classify_repo(r, '', ['.npmignore', 'src'], cfg)['kind'], 'library', 'npm 배포 파일')

    def test_single_effect_not_collection_from_reference_links(self):
        cfg = json.loads((ROOT / 'discovery/config.json').read_text())['judge']
        r = {'name': 'WebGL-Fluid-Simulation', 'description': 'Play with fluids in your browser (works even on mobile)', 'topics': ['fluid', 'webgl', 'simulation'], 'language': 'JavaScript'}
        md = '# WebGL Fluid\n[Play here](https://x.github.io/)\n## References\nhttps://github.com/haxiomic/GPU-Fluid-Experiments'
        self.assertEqual(judge.classify_repo(r, md, ['index.html', 'script.js'], cfg)['kind'], 'effect')

    def test_popular_tools_are_not_effects(self):
        cfg = json.loads((ROOT / 'discovery/config.json').read_text())['judge']
        tools = [('p5.js', 'p5.js is a client-side JS platform that empowers artists', ['creative-coding']),
                 ('xterm.js', 'A terminal for the web', ['webgl']), ('wgpu', 'A cross-platform, safe, pure-Rust graphics API.', ['webgpu']),
                 ('olive', 'Free open-source non-linear video editor', ['animation']), ('umbrella', 'Broadly scoped ecosystem & mono-repository of 215 TypeScript projects', ['generative-art']),
                 ('cobe', '5KB WebGL globe lib.', ['webgl']), ('glslViewer', 'Console-based GLSL Sandbox for 2D/3D shaders', ['shader']),
                 ('three-mesh-bvh', 'A BVH implementation to speed up raycasting and enable spatial queries', ['threejs']),
                 ('vox-director', 'Turn one topic into a finished Vox-style paper-collage explainer/ad video. Claude Code skill', ['motion-graphics'])]
        for name, desc, topics in tools:
            k = judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'JavaScript'}, '## Examples\nexamples below', ['index.html'], cfg)['kind']
            self.assertIn(k, ('library', 'unknown'), f'{name} → {k}')
        apps = [('snapchat-clone', 'A Snapchat clone built with React and Redux', ['demo', 'clone', 'face-filters']),
                ('k8sgames', 'Learn Kubernetes by playing. 3D browser game, simulation', ['browser-game', 'education'])]
        for name, desc, topics in apps:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'TypeScript'}, '', ['index.html'], cfg)['kind'], 'app', name)
        for name, desc, topics in [('zig-gamedev', 'Dev repo for @zig-gamedev libs and sample applications', ['demos']),
                                   ('remocn', 'Production-ready animations, transitions, backgrounds, and scenes for Remotion', ['remotion', 'shadcn'])]:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'TypeScript'}, '', ['index.html'], cfg)['kind'], 'library', name)
        for name, desc, topics in [('prettymaps', 'Draw pretty maps from OpenStreetMap data!', ['generative-art']),
                                   ('triangula', 'Generate high-quality triangulated art from images.', ['generative-art']),
                                   ('KinoBloom', 'Bloom effect for Unity', ['effect', 'shader', 'unity']),
                                   ('Sticker', 'Holographic sticker effects for SwiftUI views.', ['shader']),
                                   ('generativeart', 'Generative Art in Go', ['generative-art']),
                                   ('stable-diffusion-docker', 'Run the official Stable Diffusion releases in a Docker container', ['generative-art']),
                                   ('drawsvg', 'Programmatically generate SVG (vector) images, animations, and interactive Jupyter widgets', ['animation'])]:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'Python'}, '', ['index.html'], cfg)['kind'], 'library', name)
        for name, desc, topics in [('aurora', 'A source-level GameCube & Wii compatibility layer', ['graphics']),
                                   ('livecanvas', '一句话做成 Live 图。Turn a sentence into a Live Photo with animation', ['animation']),
                                   ('ossos', 'Webbased Character Animation System', ['animation', 'webgl']),
                                   ('creative-viewpager', 'Creative View Pager easy to use in Android', ['animation']),
                                   ('podcast-maker', 'Fully automated video maker using motion graphics', ['motion-graphics']),
                                   ('animate', 'Procedural animation in any style for Claude Code: short single-file scenes', ['animation']),
                                   ('p5.capture', 'super easy recording for p5.js animations', ['p5js', 'animation']),
                                   ('ShapeUp-public', 'A 3D Modeler Made in a Week', ['3d', 'graphics']),
                                   ('webgpu-dummy', 'A rendering engine', ['webgpu']),
                                   ('libossia', 'A modern C++, cross-environment distributed object model for creative coding', ['creative-coding']),
                                   ('quokka', 'Two-moment AMR radiation hydrodynamics (with self-gravity, particles, chemistry)', ['simulation', 'particles']),
                                   ('keyloom', 'Design Beautiful Motion Graphics Videos', ['motion-graphics']),
                                   ('Text_Effects', 'Add dynamic text animations to your Minecraft world', ['animation']),
                                   ('BAGEL', 'ROS Bag Visualizer', ['visualization', 'webgl']),
                                   ('OpenGemCutting', 'Open-source parametric gemstone faceting workbench', ['threejs', 'animation']),
                                   ('stampstudio', 'An online, open source stamp creator.', ['animation', 'canvas']),
                                   ('jit-motion', '把任意产品简介，一键生成单文件 HTML 宣传动画视频', ['gsap', 'animation']),
                                   ('WinUI.Composition.Hlsl', 'HLSL Composition effects and liquid glass brushes for WinUI', ['shader'])]:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'TypeScript'}, '', ['index.html'], cfg)['kind'], 'library', name)
        self.assertEqual(judge.decide({'relevant': True, 'kind': 'effect', 'owner': 'o', 'description': '', 'thumb': 'x', 'has_code': True, 'license': 'MIT', 'stars': 500}, cfg)[0], 'held', '설명 없음')
        self.assertIn('미러 저장소', judge.decide({'relevant': True, 'kind': 'effect', 'owner': 'o', 'description': 'Read-only mirror of https://codeberg.org/x/y', 'thumb': 'x', 'has_code': True, 'license': 'MIT', 'stars': 500}, cfg)[1])
        self.assertEqual(judge.classify_repo({'name': 'portfolio', 'description': 'Personal portfolio (2018)', 'topics': ['threejs', 'animation'], 'language': 'JavaScript'}, '', ['index.html'], cfg)['kind'], 'app')
        for name, desc, topics in [('fieldplay', 'A vector field explorer', ['glsl', 'particles', 'webgl']),
                                   ('moyun', '墨韵 · 实时 GPU 水墨流体', ['webgl']),
                                   ('iwrzwr-visual-archive', '160+ experimental visualization studies across 25+ categories', ['generative-art', 'creative-coding']),
                                   ('WebGPU-Ocean', 'A real-time 3D fluid simulation implemented in WebGPU', ['webgpu', 'fluid-simulation']),
                                   ('HologramShader', 'Test of an hologram material made in Unity.', ['effect', 'shader'])]:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'GLSL'}, '', ['index.html'], cfg)['kind'], 'effect', name)
        effects = [('WebGL-Fluid-Simulation', 'Play with fluids in your browser (works even on mobile)', ['webgl', 'fluid-simulation']),
                   ('matrix', 'matrix (web-based green code rain, made with love)', ['webgl'])]
        for name, desc, topics in effects:
            self.assertEqual(judge.classify_repo({'name': name, 'description': desc, 'topics': topics, 'language': 'JavaScript'}, '', ['index.html'], cfg)['kind'], 'effect', name)

    def test_badges_are_not_previews(self):
        md = '![ci](https://img.shields.io/badge/x)\n![demo](https://user-images.githubusercontent.com/1/a.gif)'
        self.assertEqual(judge.readme_media(md, 'a/b', 'main'), 'https://user-images.githubusercontent.com/1/a.gif')

    def test_prompt_only_from_real_file(self):
        self.assertEqual(judge.prompt_info('no prompt here', ['index.html'], 'a/b', 'main'), (False, None))
        self.assertTrue(judge.prompt_info('', ['PROMPT.md'], 'a/b', 'main')[0])


if __name__ == '__main__':
    unittest.main()


class StarsPartial(Base):
    """별 갱신 부분 실패·추적 범위."""
    def _seed_two_published(self):
        other = repo(120, 'ink-shader', 'Ink bleed shader effect demo', ['shader'], 60, home='https://maker.github.io/ink/')
        READMES['maker/ink-shader'] = '![p](p.gif)'
        CONTENTS['maker/ink-shader'] = ['index.html']
        stars = {'N101': node(101, 'aurora-shader', 40), 'N120': node(120, 'ink-shader', 60)}
        self.run_once(FakeClient({'topic:shader': [EFFECT, other]}, stars=stars))
        return stars

    def test_budget_mid_way_keeps_fetched_and_old_values(self):
        stars = self._seed_two_published()
        cfg = json.loads((self.d / 'discovery/config.json').read_text())
        cfg['budget']['graphql_chunk'] = 1  # 1개씩 물어 두 번째에서 예산이 끊기게
        (self.d / 'discovery/config.json').write_text(json.dumps(cfg))

        class OneThenBudget(FakeClient):
            n = 0
            def repos_by_node(self, ids):
                OneThenBudget.n += 1
                if OneThenBudget.n >= 2:
                    raise ghapi.Budget('graphql')
                return super().repos_by_node(ids)
        c2 = OneThenBudget({}, stars={'N101': node(101, 'aurora-shader', 45), 'N120': node(120, 'ink-shader', 70)})
        log = self.run_once(c2, now='2026-10-11T06:00:00Z', today=TODAY + timedelta(days=1))
        self.assertIn('stars', log['stop'] or '')
        self.assertEqual((log['counts']['stars_updated'], log['counts']['stars_failed']), (1, 1))
        pub = self.public()
        at = sorted(r['repo']['stars_at'] for r in pub.values())
        self.assertEqual(at, [NOW, '2026-10-11T06:00:00Z'], '받은 묶음은 반영, 못 받은 묶음은 옛 값과 옛 시각')
        self.assertTrue(all(r['repo']['stars'] > 0 for r in pub.values()), '0 으로 적지 않는다')
        series = json.loads((self.d / 'discovery/stars.json').read_text())
        self.assertEqual(sorted(len(v) for v in series.values()), [1, 2], '못 받은 쪽은 점을 추가하지 않는다')

    def test_tracked_excludes_held_libraries(self):
        self.run_once(FakeClient({'topic:shader': [EFFECT, LIB, LOWSTAR]},
                                 stars={'N101': node(101, 'aurora-shader', 40), 'N102': node(102, 'motionkit', 9000), 'N106': node(106, 'tiny-particles', 1)}))
        run = discover.Run(self.d, 'daily', FakeClient({}), today=TODAY, now=NOW)
        names = sorted(c['full_name'] for c in run.tracked_for_stars())
        self.assertIn('maker/aurora-shader', names)
        self.assertIn('maker/tiny-particles', names, '보류된 효과(별 부족)는 계속 잰다')
        self.assertNotIn('maker/motionkit', names, '보류된 라이브러리는 재지 않는다')


    def test_republished_item_is_tracked_again_and_rejudge_is_counted(self):
        stars = {'N101': node(101, 'aurora-shader', 40), 'N102': node(102, 'motionkit', 9000)}
        self.run_once(FakeClient({'topic:shader': [EFFECT, LIB]}, stars=stars))
        lib = next(c for c in self.cands().values() if c['full_name'] == 'maker/motionkit')
        self.assertEqual(lib['status'], 'held')
        series = json.loads((self.d / 'discovery/stars.json').read_text())
        self.assertNotIn(str(lib['repo_id']), series, '보류된 라이브러리는 별을 재지 않는다')
        # 사람이 공개로 되돌리고 규칙도 바뀐 다음 회차
        (self.d / 'editorial.json').write_text(json.dumps({'discovery_overrides': {'items': {lib['id']: {'status': 'published', 'reason': '시험'}}}}))
        cfg = json.loads((self.d / 'discovery/config.json').read_text())
        cfg['judge']['rules_version'] = cfg['judge']['rules_version'] + 1
        (self.d / 'discovery/config.json').write_text(json.dumps(cfg))
        log = self.run_once(FakeClient({}, stars={'N101': node(101, 'aurora-shader', 41), 'N102': node(102, 'motionkit', 9001)}),
                            now='2026-10-11T06:00:00Z', today=TODAY + timedelta(days=1))
        lib = next(c for c in self.cands().values() if c['full_name'] == 'maker/motionkit')
        self.assertEqual(lib['status'], 'published')
        self.assertEqual(log['counts']['rejudged'], 2)
        self.assertEqual(log['counts']['rejudge_left'], 0)
        series = json.loads((self.d / 'discovery/stars.json').read_text())
        self.assertEqual(series[str(lib['repo_id'])][-1][1], 9001, '공개로 돌아오면 같은 회차부터 다시 잰다')


    def test_override_counts_follow_human_decision(self):
        stars = {'N101': node(101, 'aurora-shader', 40)}
        self.run_once(FakeClient({'topic:shader': [EFFECT]}, stars=stars))
        eff = next(c for c in self.cands().values() if c['full_name'] == 'maker/aurora-shader')
        self.assertEqual(eff['status'], 'published')
        # 사람이 보류로 정함 — 같은 규칙 버전이어도 내려가야 하고, 철회·공개 집계에 섞이지 않는다
        (self.d / 'editorial.json').write_text(json.dumps({'discovery_overrides': {'items': {eff['id']: {'status': 'held', 'reason': '시험'}}}}))
        cfg = json.loads((self.d / 'discovery/config.json').read_text())
        cfg['judge']['enrich_stale_days'] = 0
        (self.d / 'discovery/config.json').write_text(json.dumps(cfg))
        log = self.run_once(FakeClient({}, stars=stars), now='2026-10-11T06:00:00Z', today=TODAY + timedelta(days=1))
        eff = next(c for c in self.cands().values() if c['full_name'] == 'maker/aurora-shader')
        self.assertEqual(eff['status'], 'held')
        self.assertNotIn(eff['id'], self.public())
        self.assertEqual((log['counts']['published_new'], log['counts'].get('withdrawn', 0)), (0, 0))
        # 다시 확인해도 자동 판정(공개)이 공개 수로 세어지지 않는다
        log = self.run_once(FakeClient({}, stars=stars), now='2026-10-12T06:00:00Z', today=TODAY + timedelta(days=2))
        self.assertEqual(log['counts']['published_new'], 0)
        self.assertIn('자동 판정은 published', ' '.join(next(c for c in self.cands().values() if c['full_name'] == 'maker/aurora-shader')['reasons']))


class PipelineReconcile(unittest.TestCase):
    def test_live_mismatch_marks_publish_failed_not_success(self):
        import pipeline
        stages = {}
        local = {'run_id': '111', 'updated': '2026-10-10T00:00:00Z'}
        orig = pipeline.urllib.request.urlopen
        class R:
            def __init__(self, rid): self.rid = rid
            def read(self): return json.dumps({'run_id': self.rid}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False
        pipeline.urllib.request.urlopen = lambda req, timeout=20: R('100')
        try:
            pipeline.reconcile_publish(stages, local, '2026-10-11T06:00:00Z')
            self.assertFalse(stages['publish']['ok'])
            self.assertIn('반영되지 않음', stages['publish']['message'])
            self.assertNotIn('last_success', stages['publish'])
            pipeline.urllib.request.urlopen = lambda req, timeout=20: R('111')
            pipeline.reconcile_publish(stages, local, '2026-10-11T07:00:00Z')
            self.assertTrue(stages['publish']['ok'])
            self.assertEqual(stages['publish']['last_success'], '2026-10-10T00:00:00Z')
            def boom(req, timeout=20): raise OSError('down')
            pipeline.urllib.request.urlopen = boom
            pipeline.reconcile_publish(stages, local, '2026-10-11T08:00:00Z')
            self.assertTrue(stages['publish']['ok'], '사이트를 못 읽으면 이전 판단을 바꾸지 않는다')
        finally:
            pipeline.urllib.request.urlopen = orig


class JudgeV11(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / 'discovery/config.json').read_text())['judge']

    def cls(self, name, desc, topics, readme='', files=('index.html',), lang='JavaScript'):
        return judge.classify_repo({'name': name, 'description': desc, 'topics': list(topics), 'language': lang}, readme, list(files), self.cfg)

    def test_real_effects_are_relevant(self):
        # 실제로 '관련 없음'으로 버려졌던 작품
        for name, desc in [('RainEffect', 'Some experimental rain and water drop effects in different styles'),
                           ('jquery.ripples', 'Add a water ripple effect to your background using WebGL.'),
                           ('ShaderDemos', 'some shaders for cocos creator')]:
            r = self.cls(name, desc, [])
            # 1차 관문(head_relevant)은 'relevant 또는 hits 있음'이다 — README 를 받기 전이라 설명만으로 판단
            self.assertTrue(r['relevant'] or r['hits'], name)
        # 효과가 맞아도 게임 엔진용 셰이더 모음은 보류(라이브러리)로 가는 것이 맞다 — 관련성과 유형은 다른 판단
        self.assertEqual(self.cls('ShaderDemos', 'some shaders for cocos creator', [])['kind'], 'library')

    def test_real_tools_held(self):
        # 실제로 효과(effect)로 잘못 판정됐던 저장소
        for name, desc, topics in [('easydiffusion', 'An easy 1-click way to create beautiful artwork on your PC', ['generative-art']),
                                   ('discoart', '🪩 Create Disco Diffusion artworks in one line', ['generative-art']),
                                   ('ParticleTextView', '一个用粒子动画显示文字的 Android 自定义 View', ['particles', 'animation']),
                                   ('Noble', 'A Minecraft shader pack that enhances your experience', ['glsl', 'shaders']),
                                   ('MBTwitterScroll', "Recreate Twitter's profile page scrolling animation for UITableView and UIScrollView", ['animation'])]:
            self.assertEqual(self.cls(name, desc, topics)['kind'], 'library', name)

    def test_real_effects_stay_effects(self):
        for name, desc, topics in [('WebGL-Fluid-Simulation', 'Play with fluids in your browser (works even on mobile)', ['webgl']),
                                   ('matrix', 'matrix (web-based green code rain, made with love)', ['webgl']),
                                   ('polygon-shredder', 'The polygon shredder that takes many cubes and turns them into confetti', ['webgl', 'threejs']),
                                   ('differential-line', 'a generative algorithm', ['generative-art', 'animation']),
                                   ('Burn-My-Windows', 'Disintegrate your windows with style.', ['glsl', 'shader-effects']),
                                   ('fieldplay', 'A vector field explorer', ['glsl', 'particles', 'webgl'])]:
            self.assertEqual(self.cls(name, desc, topics)['kind'], 'effect', name)
