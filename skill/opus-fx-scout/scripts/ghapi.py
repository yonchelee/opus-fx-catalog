"""GitHub API 최소 클라이언트 (표준 라이브러리만).

호출 예산(검색·REST·GraphQL 각각)과 실행 시간 상한을 지킨다. 한도에 걸리면 문서 권고대로
retry-after / x-ratelimit-reset 만큼 기다리되, max_wait 를 넘으면 기다리지 않고 Budget 예외로
이번 회차를 끝낸다(다음 실행이 state 에서 이어 간다). 한도를 우회하지 않는다.
토큰: 환경변수 GITHUB_TOKEN (Actions 기본 토큰 또는 로컬 gh auth token).
"""
import json, os, time, urllib.error, urllib.parse, urllib.request

API = 'https://api.github.com'


class Budget(Exception):
    """예산·시간·한도 때문에 이번 회차를 멈춘다. 오류가 아니라 '다음에 이어서'."""


class Client:
    def __init__(self, token=None, budget=None, minutes=20, search_interval=2.2, max_wait=90, opener=None):
        self.token = token if token is not None else os.environ.get('GITHUB_TOKEN', '')
        self.budget = dict(budget or {'search': 60, 'core': 300, 'graphql': 20})
        self.used = {'search': 0, 'core': 0, 'graphql': 0}
        self.deadline = time.time() + minutes * 60
        self.search_interval = search_interval
        self.max_wait = max_wait
        self._last_search = 0.0
        self.open = opener or urllib.request.urlopen  # 시험에서 가짜로 바꾼다
        self.waits = []

    def _check(self, kind):
        if time.time() > self.deadline:
            raise Budget('time')
        if self.used[kind] >= self.budget.get(kind, 0):
            raise Budget(kind)

    def _req(self, kind, url, data=None, accept='application/vnd.github+json'):
        self._check(kind)
        if kind == 'search':
            gap = self._last_search + self.search_interval - time.time()
            if gap > 0:
                time.sleep(gap)
            self._last_search = time.time()
        headers = {'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'opus-fx-catalog-discovery'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        body = json.dumps(data).encode() if data is not None else None
        if body:
            headers['Content-Type'] = 'application/json'
        for attempt in range(3):
            self.used[kind] += 1
            try:
                with self.open(urllib.request.Request(url, data=body, headers=headers), timeout=30) as r:
                    raw = r.read()
                    return raw if accept.endswith('raw') else json.loads(raw.decode() or 'null')
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in (403, 429):
                    wait = self._wait_seconds(e.headers)
                    if wait is None or wait > self.max_wait or time.time() + wait > self.deadline:
                        raise Budget(f'rate-limit {kind} wait={wait}')
                    self.waits.append(wait)
                    time.sleep(wait)
                    continue
                if e.code >= 500 and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
        raise Budget(f'retries {kind}')

    @staticmethod
    def _wait_seconds(h):
        if h is None:
            return 60
        if h.get('retry-after'):
            return int(h.get('retry-after'))
        if h.get('x-ratelimit-remaining') == '0' and h.get('x-ratelimit-reset'):
            return max(1, int(h.get('x-ratelimit-reset')) - int(time.time()) + 1)
        return 60  # 문서 권고: 그 밖에는 최소 1분

    # --- 검색 ---
    def search_repos(self, q, sort='stars', page=1, per_page=100):
        url = f'{API}/search/repositories?' + urllib.parse.urlencode({'q': q, 'sort': sort, 'order': 'desc', 'per_page': per_page, 'page': page})
        return self._req('search', url) or {'total_count': 0, 'items': [], 'incomplete_results': False}

    # --- 후보 확인 ---
    def readme(self, full_name):
        raw = self._req('core', f'{API}/repos/{full_name}/readme', accept='application/vnd.github.raw')
        return raw.decode('utf-8', 'replace') if raw else ''

    def root_contents(self, full_name):
        r = self._req('core', f'{API}/repos/{full_name}/contents/')
        return [x.get('name', '') for x in r] if isinstance(r, list) else []

    # --- 별 수: GraphQL nodes 로 100개씩. 이름이 바뀌어도 node id 로 찾는다 ---
    def repos_by_node(self, node_ids):
        out = {}
        for i in range(0, len(node_ids), 100):
            chunk = node_ids[i:i + 100]
            q = ('query($ids:[ID!]!){nodes(ids:$ids){... on Repository{id databaseId nameWithOwner url stargazerCount '
                 'pushedAt isArchived isFork homepageUrl licenseInfo{spdxId}}}}')
            r = self._req('graphql', f'{API}/graphql', {'query': q, 'variables': {'ids': chunk}})
            for n in ((r or {}).get('data') or {}).get('nodes') or []:
                if n:
                    out[n['id']] = n
        return out
