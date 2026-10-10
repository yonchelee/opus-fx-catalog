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
