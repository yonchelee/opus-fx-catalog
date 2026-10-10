"""Actions 커밋·배포 단계 시험 — 실제 GitHub·공개 사이트는 건드리지 않는다.
임시 git 저장소(원격 역할의 bare 저장소 + 작업 클론 둘)와 가짜 gh·curl 로
Pages 실패, 동시 push(Routine 과 Actions) 상황을 흉내 낸다."""
import json, os, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / 'skill' / 'opus-fx-scout' / 'scripts' / 'ci'
sys.path.insert(0, str(ROOT / 'skill' / 'opus-fx-scout' / 'scripts'))

GIT_ENV = {'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}


def sh(cwd, *cmd, env=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **GIT_ENV, **(env or {})})
    if check and r.returncode:
        raise AssertionError(f'{cmd} → {r.returncode}\n{r.stdout}\n{r.stderr}')
    return r


class Repo:
    """bare 원격 + 클론. 파일: catalog.json(생성물), status.json, README.md(사람·Routine 편집)."""
    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.origin = self.tmp / 'origin.git'
        sh(self.tmp, 'git', 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        seed = self.clone('seed')
        self.write(seed, {'catalog.json': '{"items": [1, 2]}\n', 'status.json': '{"run_id": "100"}\n', 'README.md': '# 출처\n- a\n'})
        sh(seed, 'git', 'add', '-A'); sh(seed, 'git', 'commit', '-qm', 'seed'); sh(seed, 'git', 'push', '-q', 'origin', 'HEAD:main')

    def clone(self, name):
        d = self.tmp / name
        sh(self.tmp, 'git', 'clone', '-q', str(self.origin), str(d))
        return d

    @staticmethod
    def write(d, files):
        for k, v in files.items():
            (d / k).write_text(v)

    def show(self, path):
        return sh(self.tmp, 'git', '--git-dir', str(self.origin), 'show', f'main:{path}').stdout

    def log(self):
        return sh(self.tmp, 'git', '--git-dir', str(self.origin), 'log', '--format=%s', 'main').stdout.split('\n')[:-1]


def commit_push(cwd, msg):
    out = Path(cwd).parent / (Path(cwd).name + '.gh_output')
    out.write_text('')
    r = sh(cwd, 'bash', str(CI / 'commit_push.sh'), msg, env={'GITHUB_OUTPUT': str(out), 'PUSH_SLEEP': '0'}, check=False)
    return r, out.read_text()


class ConcurrentPush(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Repo(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_routine_pushes_other_file_mid_run_both_kept(self):
        actions, routine = self.repo.clone('actions'), self.repo.clone('routine')
        # Actions 가 생성하는 동안 Routine 이 README(출처 목록)를 고쳐 먼저 push
        Repo.write(routine, {'README.md': '# 출처\n- a\n- b(Routine)\n'})
        sh(routine, 'git', 'commit', '-qam', 'routine: 출처 추가'); sh(routine, 'git', 'push', '-q', 'origin', 'HEAD:main')
        Repo.write(actions, {'catalog.json': '{"items": [1, 2, 3]}\n', 'status.json': '{"run_id": "200"}\n'})
        r, out = commit_push(actions, 'catalog: daily (run 200)')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('pushed=true', out)
        self.assertIn('b(Routine)', self.repo.show('README.md'))
        self.assertIn('3', self.repo.show('catalog.json'))
        self.assertEqual(self.repo.log()[:2], ['catalog: daily (run 200)', 'routine: 출처 추가'], '이력은 일직선, 강제 push 없음')

    def test_conflict_on_generated_file_keeps_routine_change_and_fails(self):
        actions, routine = self.repo.clone('actions'), self.repo.clone('routine')
        Repo.write(routine, {'catalog.json': '{"items": [1, 2, "routine"]}\n'})
        sh(routine, 'git', 'commit', '-qam', 'routine: 항목 추가'); sh(routine, 'git', 'push', '-q', 'origin', 'HEAD:main')
        Repo.write(actions, {'catalog.json': '{"items": [1, 2, 3]}\n', 'status.json': '{"run_id": "200"}\n'})
        r, out = commit_push(actions, 'catalog: daily (run 200)')
        self.assertEqual(r.returncode, 1, '충돌은 성공으로 끝나면 안 된다')
        self.assertIn('pushed=false', out)
        self.assertIn('routine', self.repo.show('catalog.json'), 'Routine 의 변경이 그대로 남는다')
        self.assertEqual(self.repo.show('status.json'), '{"run_id": "100"}\n', '반쯤 합쳐진 결과가 올라가지 않는다')
        self.assertFalse((actions / '.git' / 'rebase-merge').exists() or (actions / '.git' / 'rebase-apply').exists())
        # 다음 회차: 최신 main 에서 다시 생성하면 두 변경이 모두 들어간다
        nxt = self.repo.clone('next')
        Repo.write(nxt, {'catalog.json': '{"items": [1, 2, "routine", 3]}\n', 'status.json': '{"run_id": "300"}\n'})
        r, out = commit_push(nxt, 'catalog: daily (run 300)')
        self.assertEqual(r.returncode, 0)
        self.assertIn('"routine", 3', self.repo.show('catalog.json'))
        self.assertEqual(self.repo.log()[:2], ['catalog: daily (run 300)', 'routine: 항목 추가'])

    def test_routine_after_actions_conflict_does_not_push(self):
        """Routine 프롬프트의 절차: pull --rebase 충돌이면 push 하지 않고 보고."""
        actions, routine = self.repo.clone('actions'), self.repo.clone('routine')
        Repo.write(actions, {'catalog.json': '{"items": [1, 2, 3]}\n', 'status.json': '{"run_id": "200"}\n'})
        self.assertEqual(commit_push(actions, 'catalog: daily (run 200)')[0].returncode, 0)
        Repo.write(routine, {'catalog.json': '{"items": [1, 2, "routine"]}\n'})
        sh(routine, 'git', 'commit', '-qam', 'routine: 항목 추가')
        r = sh(routine, 'git', 'pull', '--rebase', 'origin', 'main', check=False)
        self.assertNotEqual(r.returncode, 0)
        sh(routine, 'git', 'rebase', '--abort')
        self.assertEqual(self.repo.log()[0], 'catalog: daily (run 200)')
        self.assertIn('3', self.repo.show('catalog.json'))

    def test_no_change_is_not_a_push(self):
        actions = self.repo.clone('actions')
        r, out = commit_push(actions, 'x')
        self.assertEqual(r.returncode, 0)
        self.assertIn('pushed=false', out)


STUB = textwrap.dedent('''\
    #!/usr/bin/env python3
    """가짜 {name}. 동작은 $STUB_DIR/plan.json, 호출 기록은 $STUB_DIR/calls."""
    import json, os, sys
    d = os.environ['STUB_DIR']; plan = json.load(open(os.path.join(d, 'plan.json')))
    open(os.path.join(d, 'calls'), 'a').write('{name} ' + ' '.join(sys.argv[1:]) + '\\n')
    def nxt(key):
        n = os.path.join(d, key + '.n'); i = int(open(n).read()) if os.path.exists(n) else 0
        open(n, 'w').write(str(i + 1)); seq = plan[key]; return seq[min(i, len(seq) - 1)]
    a = sys.argv[1:]
    if '{name}' == 'gh':
        if '-X' in a: sys.exit(0 if plan['post_ok'] else 1)
        print(nxt('latest').replace('SHA', os.environ['STUB_SHA'])); sys.exit(0)
    if '-w' in a: print(plan['github_json'], end=''); sys.exit(0)
    print(json.dumps({{'run_id': nxt('live')}}))
''')


class PagesPublish(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Repo(self.t.name)
        self.work = self.repo.clone('actions')
        self.stub = Path(self.t.name) / 'stub'; self.bin = self.stub / 'bin'
        self.bin.mkdir(parents=True)
        for name in ('gh', 'curl'):
            p = self.bin / name; p.write_text(STUB.format(name=name)); p.chmod(0o755)
        self.sha = sh(self.work, 'git', 'rev-parse', 'HEAD').stdout.strip()

    def tearDown(self):
        self.t.cleanup()

    def run_publish(self, **plan):
        plan = {'post_ok': True, 'latest': ['built SHA'], 'live': ['500'], 'github_json': '200', **plan}
        (self.stub / 'plan.json').write_text(json.dumps(plan))
        env = {'PATH': f'{self.bin}:{os.environ["PATH"]}', 'STUB_DIR': str(self.stub), 'STUB_SHA': self.sha,
               'PAGES_TRIES': '5', 'PAGES_SLEEP': '0', 'LIVE_TRIES': '3', 'LIVE_SLEEP': '0'}
        return sh(self.work, 'bash', str(CI / 'pages_publish.sh'), 'o/r', '500', env=env, check=False)

    def test_success(self):
        r = self.run_publish()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('공개 사이트 확인', r.stdout)

    def test_post_fails_but_build_from_push_succeeds(self):
        r = self.run_publish(post_ok=False, latest=['building SHA', 'built SHA'])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('빌드 요청 실패', r.stdout)

    def test_old_errored_build_does_not_fail_new_one(self):
        """지난 회차 빌드가 실패한 채 '최신'으로 남아 있어도, 이번 커밋 빌드를 기다린다 (회복 경로)."""
        r = self.run_publish(latest=['errored oldsha', 'errored oldsha', 'built SHA'])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_this_build_errored_fails(self):
        r = self.run_publish(latest=['building SHA', 'errored SHA'])
        self.assertEqual(r.returncode, 1)
        self.assertIn('Pages 빌드 실패', r.stdout)

    def test_post_fails_and_no_build_fails_after_bounded_polls(self):
        r = self.run_publish(post_ok=False, latest=['built oldsha'])
        self.assertEqual(r.returncode, 1)
        self.assertIn('확인하지 못함', r.stdout)
        polls = [l for l in (self.stub / 'calls').read_text().splitlines() if 'latest' in l]
        self.assertEqual(len(polls), 5, '재시도는 정해진 횟수만')

    def test_built_but_site_still_old_fails(self):
        r = self.run_publish(live=['400'])
        self.assertEqual(r.returncode, 1)
        self.assertIn('이번 실행이 아님', r.stdout)

    def test_github_json_missing_fails(self):
        r = self.run_publish(github_json='404')
        self.assertEqual(r.returncode, 1)


class PublishRecovery(unittest.TestCase):
    """Pages 실패 회차 다음 실행: 실패를 기록하고(성공으로 남기지 않음), 다시 배포되면 기록을 걷는다."""
    def test_missed_then_recovered(self):
        import pipeline
        orig = pipeline.urllib.request.urlopen
        class R:
            def __init__(self, rid): self.rid = rid
            def read(self): return json.dumps({'run_id': self.rid}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): return False
        try:
            stages = {'publish': {'ok': True, 'last_success': '2026-10-11T00:00:00Z'}}
            # 회차 200 은 push 됐지만 Pages 실패 → 사이트는 여전히 100
            pipeline.urllib.request.urlopen = lambda req, timeout=20: R('100')
            pipeline.reconcile_publish(stages, {'run_id': '200', 'updated': '2026-10-11T21:20:00Z'}, '2026-10-12T21:17:00Z')
            self.assertFalse(stages['publish']['ok'])
            self.assertEqual(stages['publish']['missed_run'], '200')
            self.assertEqual(stages['publish']['last_success'], '2026-10-11T00:00:00Z', '실패 회차를 성공 시각으로 올리지 않는다')
            # 회차 300 이 다시 배포 → 그 다음 회차가 확인
            pipeline.urllib.request.urlopen = lambda req, timeout=20: R('300')
            pipeline.reconcile_publish(stages, {'run_id': '300', 'updated': '2026-10-12T21:25:00Z'}, '2026-10-13T21:17:00Z')
            self.assertTrue(stages['publish']['ok'])
            self.assertNotIn('missed_run', stages['publish'])
            self.assertEqual(stages['publish']['last_success'], '2026-10-12T21:25:00Z')
        finally:
            pipeline.urllib.request.urlopen = orig


class WorkflowWiring(unittest.TestCase):
    def test_workflow_calls_scripts(self):
        wf = (ROOT / '.github/workflows/catalog-update.yml').read_text()
        self.assertIn('scripts/ci/commit_push.sh', wf)
        self.assertIn('scripts/ci/pages_publish.sh', wf)
        self.assertIn("if: steps.commit.outputs.pushed == 'true'", wf)
        self.assertIn('git checkout -B main origin/main', wf)


if __name__ == '__main__':
    unittest.main()
