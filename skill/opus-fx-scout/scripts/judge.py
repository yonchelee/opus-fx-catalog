"""GitHub 후보 판정 (순수 함수, 외부 호출 없음).

후보 하나 = 저장소 하나. 판정 결과
  kind   : effect(개별 효과·데모) | collection(예제 모음) | library(제작용 라이브러리·프레임워크·도구) | app(앱·게임·학습 서비스) | list(링크 자료집) | unknown
  status : published(자동 공개) | held(보류 — 사유 기록) | source(자료집 → 추가 발굴 출처 후보) | rejected(시각 효과와 무관)
라이브러리와 자료집은 완성된 작품처럼 공개하지 않는다. 원본에 없는 프롬프트를 만들지 않는다.
"""
import re
from urllib.parse import urljoin, urlparse

IMG = re.compile(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)|<img[^>]+src=["\']([^"\']+)["\']', re.I)
LINK = re.compile(r'\[([^\]]*)\]\((https?://[^)\s]+)\)|(https?://[^\s)<>"\']+)', re.I)
BADGE = re.compile(r'shields\.io|badge|badgen|travis-ci|circleci|codecov|github\.com/.+/workflows|/actions/workflows|star-history|contrib\.rocks|buymeacoffee|ko-fi|sponsor|vercel\.com/button|deploy-button|netlify\.com/img|forthebadge|visitor', re.I)
MEDIA_EXT = re.compile(r'\.(gif|png|jpe?g|webp|apng|avif|mp4|webm)(\?|#|$)', re.I)
CODE_FILES = re.compile(r'\.(html?|js|mjs|ts|tsx|jsx|glsl|frag|vert|wgsl|py|cs|cpp|c|rs|swift|kt|java|gd|pde|vue|svelte)$', re.I)
PROMPT_FILE = re.compile(r'^prompts?(\.|-|_|$)|prompt\.(md|txt)$', re.I)


def words(text):
    return ' ' + re.sub(r'[^a-z0-9.#+ -]+', ' ', (text or '').lower()) + ' '


def has_word(text, w):
    return re.search(r'(^|[^a-z0-9])' + re.escape(w) + r'($|[^a-z0-9])', text) is not None


def raw_base(full_name, branch):
    return f'https://raw.githubusercontent.com/{full_name}/{branch or "HEAD"}/'


def readme_media(readme, full_name, branch):
    """README 의 첫 미리보기 이미지·영상(배지 제외) → 절대 주소."""
    for m in IMG.finditer(readme or ''):
        url = (m.group(1) or m.group(2) or '').strip()
        if not url or BADGE.search(url) or url.startswith('data:'):
            continue
        if url.startswith('http'):
            if 'github.com/' in url and '/blob/' in url:
                url = url.replace('github.com/', 'raw.githubusercontent.com/').replace('/blob/', '/')
            if MEDIA_EXT.search(url) or 'user-images.githubusercontent.com' in url or 'github.com/user-attachments' in url:
                return url
            continue
        if MEDIA_EXT.search(url):
            return urljoin(raw_base(full_name, branch), url.lstrip('./'))
    return None


def demo_url(repo, readme, cfg):
    hosts = cfg['demo_hosts']
    home = (repo.get('homepage') or '').strip()
    if home.startswith('http') and any(urlparse(home).netloc.endswith(h) for h in hosts):
        return home
    for m in LINK.finditer(readme or ''):
        label, url = (m.group(1) or '').lower(), m.group(2) or m.group(3) or ''
        if not url or BADGE.search(url):
            continue
        host = urlparse(url).netloc
        if any(host.endswith(h) for h in hosts) and ('github.com' not in host):
            if re.search(r'demo|live|preview|try|play|view|site|open', label) or label == '' and 'github.io' in host:
                return url.rstrip('.,')
    return home if home.startswith('http') and 'github.com' not in home else None


def classify_repo(repo, readme, contents, cfg):
    """kind 와 관련성 판단. repo = 검색 결과 항목(dict)."""
    name = (repo.get('name') or '').lower()
    desc = repo.get('description') or ''
    topics = [t.lower() for t in repo.get('topics') or []]
    head = words(f"{name.replace('-', ' ')} {desc} {' '.join(t.replace('-', ' ') for t in topics)}")
    body = words((readme or '')[:4000])
    strong = sorted(set(topics) & set(cfg['strong_topics']))
    hits = sorted({w for w in cfg['vocab'] if has_word(head, w)})
    body_hits = sorted({w for w in cfg['vocab'] if has_word(body, w)})
    relevant = bool(strong) or len(hits) >= 2 or (len(hits) == 1 and len(body_hits) >= 3)

    links = len(LINK.findall(readme or ''))
    files = [c.lower() for c in contents]
    code_files = [c for c in files if CODE_FILES.search(c)] + [c for c in files if c in ('src', 'lib', 'shaders', 'sketches', 'demos', 'examples', 'public', 'app')]
    only_docs = bool(files) and all(f.endswith(('.md', '.txt', '.yml', '.yaml', '.json', '.png', '.jpg', '.gif', '.svg')) or f.startswith('.') or f in ('license', 'licence') for f in files)

    def any_word(ws, text):
        return [w for w in ws if has_word(text, w)]

    namedesc = words(name.replace('-', ' ').replace('_', ' ') + ' ' + desc)
    tool = any_word(cfg['library_words'], namedesc)
    # 설명이 '만들어 준다'는 동사로 시작하거나, 특정 프레임워크용 부품·특정 언어 구현이면 도구
    d0 = re.sub(r'^[^a-z0-9]+', '', desc.lower())
    tool += [m.group(0).strip() for pat in cfg.get('tool_patterns', []) for m in [re.search(pat, d0)] if m]
    # 패키지 설치 안내(npm install --save 이름 등)가 있으면 라이브러리. 이름 없는 'npm install'(데모 의존성 설치)은 제외
    npm_pkg = ('package.json' in files and re.search(r'\b(?:npm|yarn|pnpm) (?:i|install|add)(?: -{1,2}[\w-]+)* [@a-z][\w./@-]*', readme or '', re.I) is not None) \
        or '.npmignore' in files
    # README 첫 문단의 자기소개("X is a component/library…")도 도구 신호
    intro = re.sub(r'!\[[^\]]*\]\([^)]*\)|<[^>]+>', ' ', (readme or '')[:800])
    self_tool = re.search(r'\b(is|are) an? (\w+ ){0,3}(component|library|framework|plugin|tool|toolkit|engine|sdk|package|module|wrapper)\b', intro, re.I) is not None
    # 작품 신호: 이름·설명에 있거나, 주제에만 있다면 시각 기술 주제(셰이더·파티클 등)와 함께 있을 때만
    effect_sig = any_word(cfg['effect_words'], namedesc) or (
        any_word(cfg['effect_words'], words(' '.join(t.replace('-', ' ') for t in topics))) if set(topics) & set(cfg.get('visual_topics', [])) else [])
    app = any_word(cfg.get('app_words', []), namedesc + ' ' + ' '.join(topics).replace('-', ' ') + ' ')
    if 'awesome' in name or 'awesome-list' in topics or 'awesome' in topics or any_word(cfg['list_words'], namedesc) or (links > 60 and (only_docs or not code_files)):
        kind = 'list'
    elif tool or set(topics) & set(cfg['library_topics']) or npm_pkg or self_tool:
        # 도구·라이브러리·플랫폼·앱. 효과를 '만드는' 쪽이지 완성된 효과가 아니다.
        kind = 'library'
    elif app:
        kind = 'app'  # 앱·게임·학습 서비스 — 시각 효과를 보여 주려고 만든 작품이 아니다
    elif any_word(cfg['collection_words'], head) or (effect_sig and re.search(r'collection of|^#{1,3}\s*(examples|demos|experiments|sketches|gallery)\b', (readme or '')[:3000], re.I | re.M)):
        kind = 'collection'
    elif effect_sig and (code_files or repo.get('language')):
        kind = 'effect'
    else:
        kind = 'unknown'  # 작품이라는 신호가 없다 — 보류
    return {'kind': kind, 'relevant': relevant, 'strong_topics': strong, 'hits': hits, 'tool_words': tool or app, 'effect_words': effect_sig,
            'has_code': bool(code_files) or (bool(repo.get('language')) and not only_docs), 'links': links}


def environment(repo, contents, cfg):
    """실행 환경. 갤러리 단계: 2(개발 환경에서 내려받아 실행) 또는 3(외부 프로그램)."""
    topics = set(t.lower() for t in repo.get('topics') or [])
    files = set(c.lower() for c in contents)
    if repo.get('language') in cfg['native_languages'] or topics & set(cfg['native_topics']):
        return 3, '외부 프로그램·네이티브 환경 (' + (repo.get('language') or ', '.join(sorted(topics & set(cfg['native_topics'])))) + ')'
    if 'package.json' in files:
        return 2, 'Node.js 프로젝트 (내려받아 npm 설치 후 실행)'
    if 'index.html' in files:
        return 2, '정적 웹 페이지 (내려받아 index.html 을 브라우저로 열기)'
    return 2, '코드 저장소 (실행 방법은 README 확인)'


def prompt_info(readme, contents, full_name, branch):
    """공개 프롬프트가 '파일로' 있을 때만 있다고 본다. 원본에 없는 프롬프트를 만들지 않는다."""
    for c in contents:
        if PROMPT_FILE.search(c):
            return True, f'https://github.com/{full_name}/blob/{branch or "HEAD"}/{c}'
    if re.search(r'^#{1,4}\s*prompts?\b', readme or '', re.I | re.M):
        return True, f'https://github.com/{full_name}#readme'
    return False, None


def license_ok(repo):
    spdx = ((repo.get('license') or {}).get('spdx_id') or '').strip()
    return spdx if spdx and spdx != 'NOASSERTION' else None


def decide(c, cfg, homepage_owner=None):
    """c = 후보 레코드(확인 정보 포함). status 와 reasons 를 정한다."""
    reasons = []
    if not c['relevant']:
        return 'rejected', ['시각 효과와 관련 낮음 (주제·설명에서 효과 어휘 부족)']
    if c['kind'] == 'list':
        return 'source', ['링크 자료집 — 작품이 아니라 추가 발굴 출처 후보']
    if c['kind'] == 'app':
        return 'held', ['앱·게임·학습 서비스 — 시각 효과 작품이 아님' + (f" ({', '.join(c.get('tool_words') or [])})" if c.get('tool_words') else '')]
    if c['kind'] == 'library':
        return 'held', ['제작용 라이브러리·프레임워크·도구 — 완성된 작품으로 공개하지 않음' + (f" ({', '.join(c.get('tool_words') or [])})" if c.get('tool_words') else '')]
    if c.get('fork'):
        reasons.append('포크 저장소')
    if c.get('mirror'):
        reasons.append('미러 저장소')
    if c.get('duplicate_of'):
        reasons.append('중복 의심: ' + c['duplicate_of'])
    if not c.get('owner'):
        reasons.append('원작자 확인 불가')
    if not (c.get('thumb') or c.get('demo_url')):
        reasons.append('미리보기·데모 없음')
    if not c.get('has_code'):
        reasons.append('코드 확인 불가')
    if not c.get('license'):
        reasons.append('라이선스 미표시 — 코드 재사용 조건 불명')
    if (c.get('stars') or 0) < cfg['min_stars_publish']:
        reasons.append(f"별 {c.get('stars') or 0}개 — 공개 기준 {cfg['min_stars_publish']}개 미만")
    if c['kind'] == 'unknown':
        reasons.append('작품 유형 판단 불가 — 이름·설명·주제에 데모·효과·애니메이션 같은 작품 신호가 없음')
    return ('held', reasons) if reasons else ('published', ['필수 조건 충족: 관련성·미리보기 또는 데모·코드·라이선스·원작자'])


def norm_url(u):
    if not u:
        return ''
    p = urlparse(u.strip().lower())
    return (p.netloc.removeprefix('www.') + p.path).rstrip('/')
