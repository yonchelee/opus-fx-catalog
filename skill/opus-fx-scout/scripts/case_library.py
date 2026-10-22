"""Source type `case_library`: a repo whose data/library/<post id>.json files each
describe one X post (LeaddeOpenLab/awesome-opus-5-5-video-prompts layout).

Only rows whose prompt disclosure is listed in the source's `filter.prompt_status`
(default: full_original) are taken: those are the prompts the collection marks as
copied in full from the author's post. `fragment` rows are left out.

Media: the author's own X thumbnail / mp4 recorded in the case file (same as
lievan rows). Nothing is hotlinked from the collection's repo.
"""
import glob, json, os, re, subprocess, tempfile
from pathlib import Path

# collection topic / task → catalog category (motion / explainer / 3d / interactive)
TOPIC = {'motion-graphics': 'motion', 'music-storytelling': 'motion', '3d-scenes': '3d',
         'games-interactive': 'interactive', 'canvas-interactive': 'interactive', 'explainers': 'explainer'}
TASK = {'canvas-interactive': 'interactive', 'games-interactive': 'interactive', 'blender': '3d',
        '3d-scenes': '3d', 'explainers': 'explainer'}
# tool name (lowercased, substring) → catalog tech tag (same vocabulary as yihui rows)
TOOL_TAG = [('three.js', 'threejs'), ('threejs', 'threejs'), ('webgpu', 'shader'), ('wgsl', 'shader'), ('glsl', 'shader'),
            ('webgl', 'webgl'), ('remotion', 'remotion'), ('blender', 'blender'), ('playwright', 'playwright'),
            ('ffmpeg', 'ffmpeg'), ('claude code', 'claude-code'), ('claude artifacts', 'claude-app'),
            ('python', 'python'), ('numpy', 'python'), ('p5.js', 'p5js'), ('p5js', 'p5js'), ('gsap', 'gsap'),
            ('canvas', 'canvas'), ('svg', 'svg'), ('css', 'css'), ('elevenlabs', 'elevenlabs'), ('suno', 'suno'),
            ('edge-tts', 'tts'), ('web audio', 'webaudio'), ('manim', 'manim'), ('seedance', 'seedance')]
SKIP_TOOL_STATUS = {'prohibited'}
MP4 = re.compile(r'^https://video(?:-s)?\.twimg\.com/.+\.mp4(?:\?.*)?$')
STATUS = re.compile(r'(?:x|twitter)\.com/[^/]+/status/(\d+)')


def fetch_files(src):
    """Clone only the library folder (blobless + sparse, so the repo's gifs are never downloaded).
    Returns [(file name, text)] sorted by name."""
    pattern = src['path']
    folder = str(Path(pattern).parent)
    url = f"https://github.com/{src['repo']}"
    with tempfile.TemporaryDirectory() as t:
        env = {**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1'}
        steps = [['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--no-checkout',
                  '-b', src.get('branch', 'main'), url, t],
                 ['git', '-C', t, 'sparse-checkout', 'set', '--no-cone', folder],
                 ['git', '-C', t, 'checkout', '-q']]
        for cmd in steps:
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if r.returncode:
                raise RuntimeError(f"{' '.join(cmd[:3])} failed: {r.stderr.strip()[:200]}")
        files = sorted(glob.glob(str(Path(t) / pattern)))
        return [(Path(f).name, Path(f).read_text()) for f in files]


def post_id(url):
    m = STATUS.search(url or '')
    return m.group(1) if m else None


def category(ce):
    topic = ((ce.get('purpose') or {}).get('topic') or '').lower()
    return TOPIC.get(topic) or TASK.get((ce.get('task') or '').lower(), 'motion')


def tech_tags(ce):
    tags = set()
    for tool in ce.get('tools') or []:
        if tool.get('status') in SKIP_TOOL_STATUS:
            continue
        name = (tool.get('name') or '').lower()
        tags.update(tag for key, tag in TOOL_TAG if key in name)
    return sorted(tags)


def row(case, added=None):
    """One case file (parsed JSON) → the videos_json-like dict sync.normalize takes. None if unusable."""
    ce = (case.get('analysis') or {}).get('caseEvidence') or {}
    post = case.get('post') or {}
    pid = post.get('id') or post_id(case.get('xUrl'))
    prompt = (case.get('prompt') or '').strip()
    author = (post.get('author') or {}).get('username') or ''
    url = post.get('canonicalUrl') or case.get('xUrl') or ''
    if not (pid and prompt and author and url):
        return None
    v = {'slug': pid, 'author': author, 'author_url': (post.get('author') or {}).get('profileUrl', ''),
         'post_url': url, 'video_url': url, 'prompt': prompt, 'prompt_partial': False,
         'category': category(ce), 'tech_tags': tech_tags(ce)}
    title = case.get('summaryEn') or ce.get('title')
    if title:
        v['title'] = title
    if case.get('coverUrl', '').startswith('https://pbs.twimg.com/'):
        v['thumb'] = case['coverUrl']
    mp4 = [m for m in case.get('mediaFingerprints') or [] if MP4.match(m)]
    if mp4:
        v['mp4'] = mp4[0]
    if added:
        v['added'] = added
    return v


def rows(src, files, catalog):
    """Filter by prompt disclosure, drop posts another source already has, keep each row's
    first 'added' date. Returns (rows, stats dict)."""
    want = set((src.get('filter') or {}).get('prompt_status') or ['full_original'])
    mine = {r['id']: r for r in catalog if r.get('src') == src['id']}
    others = {post_id(r.get('post_url')) for r in catalog if r.get('src') != src['id']}
    out, stats = [], {'files': len(files), 'kept': 0, 'filtered': 0, 'dup': 0, 'bad': 0}
    for name, text in files:
        try:
            case = json.loads(text)
        except ValueError:
            stats['bad'] += 1
            continue
        status = ((((case.get('analysis') or {}).get('caseEvidence') or {}).get('prompt') or {}).get('status'))
        if status not in want:
            stats['filtered'] += 1
            continue
        old = mine.get(f"{src['id']}:{(case.get('post') or {}).get('id', '')}")
        v = row(case, added=old.get('added') if old else None)
        if v is None:
            stats['bad'] += 1
            continue
        if v['slug'] in others:
            stats['dup'] += 1
            continue
        out.append(v)
        stats['kept'] += 1
    return out, stats
