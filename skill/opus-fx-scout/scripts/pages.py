"""정적 페이지 본문. build_site.py 가 부른다 (표준 라이브러리만).

- fx/<src>/<slug>/index.html : 편집이 끝난 작품(editorial guide 가 있는 것)만. 검색으로 들어와도 내용이 HTML 에 그대로 있다.
- use/<topic>/index.html     : 용도별 진입 페이지. 편집에서 그 용도로 고른 작품이 3개 이상일 때만 만든다.
- use/index.html             : 용도 목록
- sitemap.xml                : 위 페이지와 갤러리 루트

내부 링크는 상대경로(하위 경로 /opus-fx-catalog/ 에서도 동작), canonical·OG 는 SITE 기준 절대 주소.
화면 문구·규칙은 assets/app.js 상세 화면과 같게 유지한다(둘을 함께 고친다).
"""
import json
from html import escape as h
from urllib.parse import quote

SITE = 'https://yonchelee.github.io/opus-fx-catalog/'
MIN_USE_ITEMS = 3

CAT = {'motion': '모션그래픽', 'explainer': '설명 영상', '3d': '3D 씬', 'interactive': '게임·인터랙티브'}
LV = {1: '채팅에서 바로', 2: 'Claude Code', 3: '외부 프로그램', 4: '외부 AI·API'}
LV_LONG = {1: 'Claude 채팅 미리보기에서 바로 볼 수 있음', 2: 'Claude Code 같은 개발 환경에서 파일을 만들어 실행',
           3: 'Blender·게임엔진 같은 외부 프로그램 필요', 4: '영상·이미지 생성 AI 같은 외부 서비스 필요'}
NEED = {'render': 'MP4 렌더링', 'remotion': 'Remotion', 'node': 'Node.js 프로젝트', 'python': 'Python', 'blender': 'Blender',
        'engine': '게임엔진', 'figma': 'Figma', 'genvideo': '영상 생성 AI', 'genimage': '이미지 생성 AI',
        'genaudio': '음성·음악 생성 AI', 'assets': '내 자료 필요'}
VERIFY = {'unverified': ('미검증', '이 사이트에서 직접 실행해 보지 않았습니다.'),
          'partial': ('일부 확인', '일부 효과만 같은 방식으로 나오는 것을 확인했습니다.'),
          'reproduced': ('재현 확인', '같은 프롬프트로 비슷한 결과가 나오는 것을 확인했습니다.')}


FXN = {'3d': '3D 씬·카메라', 'shader': '셰이더·글로우', 'reel': '모션 쇼릴', 'game': '플레이어블 게임', 'paint': '페인터리·손그림',
       'ui': 'UI·제품 데모', 'particles': '파티클·입자', 'audio': '사운드 동기화', 'liquid': '유체·물리', 'cosmic': '우주·자연',
       'pixel': '픽셀아트', 'morph': '모핑·트랜지션', 'glitch': '글리치·레트로', 'kinetic': '키네틱 타이포', 'data': '데이터·지도', 'etc': '기타'}
ENVS = {'chat': 'Claude 채팅 미리보기에서 바로 볼 수 있는 HTML 한 장 (외부 라이브러리는 CDN 으로)',
        'code': 'Claude Code 로 만드는 프로젝트 파일 (실행 방법까지 알려 주기)',
        'video': 'MP4 영상 파일로 내보낼 수 있는 구성 (Remotion 등, 렌더링 명령까지 알려 주기)'}
ENV_LABEL = {'chat': 'Claude 채팅 (HTML 한 장)', 'code': 'Claude Code (프로젝트)', 'video': '영상 파일 (MP4)'}


def build_request(r, o, uses):
    """assets/apply.js buildRequest 와 글자 하나까지 같아야 한다(tests/apply.test.mjs 가 생성 페이지로 대조)."""
    ed = r.get('ed') or {}
    g = ed.get('guide') or {}
    ref = g.get('brief') or ' — '.join(x for x in [title_of(r), ', '.join(FXN[f] for f in r.get('fx') or [] if f != 'etc')] if x)
    lines = ['다음 효과를 참고해서 내 용도에 맞게 새로 만들어 주세요.', '',
             '[참고한 효과]', ref, f'(출처: @{r["author"]}{", " + r["post_url"] if r.get("post_url") else ""})', '',
             f'[내 용도] {o.get("use") or (uses[0] if uses else "자유롭게 정해 주세요")}',
             f'[들어갈 문구] {o.get("text") or "임의로 정해 주세요"}',
             f'[색상] {o.get("color") or "원본 분위기를 유지해 주세요"}',
             f'[실행 환경] {ENVS.get(o.get("env")) or ENVS["chat"]}', '',
             '[조건]',
             '- 원본을 그대로 복제하지 말고, 위 용도와 문구에 맞게 구성을 바꿔 주세요.',
             '- 문구·색상·크기·속도처럼 바꾸기 쉬운 값은 맨 위에 변수로 모아 주세요.',
             '- 움직임 줄이기 설정(prefers-reduced-motion)에서는 정지 화면이나 단순한 전환을 보여 주세요.']
    if not g.get('brief') and r.get('prompt'):
        p = r['prompt']
        lines += ['', '[원본 프롬프트 — 일부만 공개됨, 빠진 부분은 알아서 채워 주세요]' if r.get('partial') else '[원본 프롬프트 — 기법 참고용]',
                  p[:1200] + (' …' if len(p) > 1200 else '')]
    return '\n'.join(lines)


def default_env(r):
    return 'chat' if level_of(r) in (0, 1) else 'code'


def apply_section(r, use_titles):
    env = default_env(r)
    uses = [t for _, t in use_titles]
    opts = ''.join(f'<option value="{k}"{" selected" if k == env else ""}>{t}</option>' for k, t in ENV_LABEL.items())
    return (f'<section class="dsec" id="apply"><h3><span class="n">7</span>적용용 요청문 만들기</h3>'
            '<p class="note">아래 칸을 채우면 내 작업에 맞춘 요청문이 만들어집니다. 틀에 값을 채운 것이라 원본과 같은 결과를 보장하지 않습니다. 입력한 내용은 이 화면 밖으로 보내지 않습니다.</p>'
            '<div class="apply">'
            f'<label>용도<input id="ap-use" placeholder="{h(uses[0] if uses else "예: 랜딩 페이지 첫 화면")}"></label>'
            '<label>들어갈 문구<input id="ap-text" placeholder="예: 우리 카페 그랜드 오픈"></label>'
            '<label>색상<input id="ap-color" placeholder="예: 크림 바탕에 진한 주황"></label>'
            f'<label>실행 환경<select id="ap-env">{opts}</select></label></div>'
            f'<pre class="prompt" id="ap-out" aria-live="polite">{h(build_request(r, {"env": env}, uses))}</pre>'
            '<div class="acts"><button type="button" class="btn primary" id="cp-req">적용용 요청문 복사</button></div></section>')


def item_path(item_id):
    src, slug = item_id.split(':', 1)
    return f'fx/{quote(src, safe="")}/{quote(slug, safe="")}/'


def has_page(r):
    return bool((r.get('ed') or {}).get('guide'))


def fmt_likes(n):
    if n is None:
        return ''
    if n >= 10000:
        s = f'{n / 10000:.{0 if n >= 100000 else 1}f}'.rstrip('0').rstrip('.')
        return s + '만'
    return f'{n:,}'


def level_of(r):
    lv = ((r.get('ed') or {}).get('env') or {}).get('level')
    return lv if lv in LV else r['level']


def verify_of(r):
    s = ((r.get('ed') or {}).get('verify') or {}).get('status')
    return s if s in VERIFY else 'unverified'


def title_of(r):
    ed = r.get('ed') or {}
    return ed.get('title_ko') or r.get('title') or ' '.join((r.get('prompt') or '').split())[:70] or r['slug']


def head(title, desc, canonical, root, image=None, kind='website', extra=''):
    img = image or SITE + 'og.png'
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{h(title)}</title>
<meta name="description" content="{h(desc)}">
<link rel="canonical" href="{h(canonical)}">
<meta name="referrer" content="no-referrer">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="효과 갤러리">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(desc)}">
<meta property="og:url" content="{h(canonical)}">
<meta property="og:image" content="{h(img)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFF3E2">
<script>(function(){{try{{var d=document.documentElement,t=localStorage.getItem('yl-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');d.dataset.theme=t}}catch(e){{}}}})();</script>
<link rel="icon" href="https://www.yonchelee.com/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{root}assets/site.css">
{extra}</head>
<body>
<nav class="nav">
  <a class="logo" href="https://www.yonchelee.com/">이영채 작업실</a>
  <a class="here" href="{root}">/ Effect Gallery</a>
  <span class="sp"></span>
  <a class="navbtn" href="{root}">갤러리</a>
  <button class="theme-toggle" type="button" id="theme" aria-label="다크 모드 전환">
    <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg>
    <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
  </button>
</nav>
'''


FOOT = '''<footer>
  <div class="in">
    <p>모든 영상과 프롬프트의 권리는 각 원작자에게 있습니다. 미리보기는 원본 게시물의 공개 주소를 그대로 불러오며, 원본이 지워지면 보이지 않을 수 있습니다.</p>
    <p>데이터 출처: <a href="https://github.com/yihui-dev/awesome-opus5-5-videos">yihui-dev/awesome-opus5-5-videos</a> (MIT) · <a href="https://github.com/Li-Evan/awesome-opus-5.5-video-prompts">Li-Evan/awesome-opus-5.5-video-prompts</a> (CC BY 4.0). 카탈로그: <a href="https://github.com/yonchelee/opus-fx-catalog">yonchelee/opus-fx-catalog</a></p>
    <div class="legal"><span>© 2026 YOUNGCHAE LEE</span><a href="https://www.yonchelee.com/">YONCHELEE.COM</a></div>
  </div>
</footer>
'''


def badges(r):
    v = verify_of(r)
    return (f'<div class="badges"><span class="b env{level_of(r)}">{LV[level_of(r)]}</span>'
            f'<span class="b{" partial" if r.get("partial") else ""}">{"프롬프트 일부 공개" if r.get("partial") else "프롬프트 전체 공개"}</span>'
            f'<span class="b v-{v}">{VERIFY[v][0]}</span></div>')


def sec(n, title, body):
    return f'<section class="dsec"><h3><span class="n">{n}</span>{title}</h3>{body}</section>' if body else ''


def media(r):
    link = f'<a href="{h(r["post_url"])}" target="_blank" rel="noopener">원본 게시물에서 보기</a>' if r.get('post_url') else ''
    none = f'<div class="none" hidden><span>미리보기를 불러오지 못했습니다.</span>{link}</div>'
    src = r.get('mp4_hd') or r.get('mp4')
    if src:
        return (f'<video controls muted playsinline loop preload="none" poster="{h(r.get("thumb") or "")}" '
                f'src="{h(src)}" data-media="1"></video>{none}')
    if r.get('thumb') or r.get('preview'):
        return f'<img src="{h(r.get("preview") or r.get("thumb"))}" alt="" referrerpolicy="no-referrer" data-media="1">{none}'
    return none.replace(' hidden', '')


def item_page(r, uses, related, root='../../../'):
    ed, g = r['ed'], r['ed']['guide']
    env, vr, v = ed.get('env') or {}, ed.get('verify') or {}, verify_of(r)
    title = title_of(r)
    url = SITE + item_path(r['id'])
    use_titles = [(u, uses[u]['title']) for u in ed.get('uses') or [] if u in uses]
    desc = ed.get('summary_ko') or g.get('what', '')[:120]
    needs = list(env.get('tools') or []) + [NEED.get(n, n) for n in r.get('needs') or []]
    ld = {'@context': 'https://schema.org', '@type': 'CreativeWork', 'name': title, 'description': desc, 'url': url,
          'inLanguage': 'ko', 'author': {'@type': 'Person', 'name': r['author']},
          **({'isBasedOn': r['post_url']} if r.get('post_url') else {}), **({'image': r['thumb']} if r.get('thumb') else {})}
    data = {k: r.get(k) for k in ('id', 'author', 'post_url', 'prompt', 'partial', 'level', 'fx', 'title')}
    data['ed'] = {'guide': {'brief': g.get('brief', '')}, 'title_ko': ed.get('title_ko')}
    data['uses'] = [t for _, t in use_titles]
    data['level'] = level_of(r)
    crumbs = ' › '.join([f'<a href="{root}">효과 갤러리</a>'] + [f'<a href="{root}use/{u}/">{h(t)}</a>' for u, t in use_titles[:1]])
    rel = ''.join(
        f'<li><a class="row" href="{root}{item_path(x["id"])}">{thumb_img(x)}<div><b>{h(title_of(x))}</b>'
        f'<span>{h((x["ed"].get("summary_ko") or ""))}</span></div></a></li>' for x in related)
    vline = (f'검증: <b>{VERIFY[v][0]}</b> — {h(vr.get("note") or VERIFY[v][1])}'
             + (f' ({h(vr["date"])}{", " + h(vr["env"]) if vr.get("env") else ""})' if vr.get('date') else '')
             + (f' · <a href="{root}{h(vr["evidence"])}">만들어 본 결과 화면</a>' if vr.get('evidence') else ''))
    body = f'''<main class="wrap doc">
<div class="crumbs">{crumbs}</div>
<h1>{h(title)}</h1>
{f'<div class="orig">{h(r["title"])}</div>' if r.get('title') and ed.get('title_ko') else ''}
<p class="lead">{h(desc)}</p>
{badges(r)}
<div class="dmedia">{media(r)}</div>
<div class="acts" style="margin-top:14px">
  <button type="button" class="btn primary" id="cp-orig">{'원본 프롬프트 복사 (일부 공개)' if r.get('partial') else '원본 프롬프트 복사'}</button>
  <button type="button" class="btn" id="fav" aria-pressed="false">☆ 즐겨찾기</button>
  <button type="button" class="btn" id="share">공유</button>
  <a class="btn" href="{root}?item={quote(r['id'], safe='')}">갤러리에서 보기</a>
</div>
<p class="note" id="favnote">즐겨찾기는 이 브라우저에만 저장됩니다.</p>
{sec('1', '어떤 효과인가', f'<p>{h(g.get("what", ""))}</p>')}
{sec('2', '어디에 쓰면 좋은가', (f'<p>{h(g.get("where", ""))}</p>' + (f'<p class="note">추천 이유: {h(ed["featured_reason"])}</p>' if ed.get('featured_reason') else '')) if g.get('where') else '')}
{sec('3', '필요한 것', '<ul>' + f'<li>{h(LV_LONG[level_of(r)])}</li>' + ''.join(f'<li>{h(n)}</li>' for n in needs) + (f'<li>유료: {h(env["paid"])}</li>' if env.get('paid') else '') + (f'<li>내 자료: {h(env["assets"])}</li>' if env.get('assets') else '') + '</ul>')}
{sec('4', '실행 순서', '<ol>' + ''.join(f'<li>{h(s)}</li>' for s in g.get('steps') or []) + '</ol>' if g.get('steps') else '')}
{sec('5', '바꾸면 좋은 변수', '<div class="vars">' + ''.join(f'<div><b>{h(x.get("name", ""))}</b><span>{h(x.get("hint", ""))}</span></div>' for x in g.get('variables') or []) + '</div>' if g.get('variables') else '')}
{sec('6', '원본 프롬프트', ('<p class="warn">원작자가 프롬프트 일부만 공개했습니다. 아래는 전체가 아닙니다.</p>' if r.get('partial') else '') + f'<pre class="prompt" id="dprompt">{h(r.get("prompt") or "(프롬프트 없음)")}</pre>')}
{apply_section(r, use_titles)}
{sec('8', '출처와 검증', f'<ul><li>원작자 @{h(r["author"])}' + (f' · <a href="{h(r["post_url"])}" target="_blank" rel="noopener">원본 게시물</a>' if r.get('post_url') else '') + (f' · <a href="{h(r["prompt_url"])}" target="_blank" rel="noopener">프롬프트 출처</a>' if r.get('prompt_url') else '') + f'</li><li>{vline}</li>' + (f'<li>부족한 조건: {h(vr["missing"])}</li>' if vr.get('missing') else '') + (f'<li>원본 X 게시물 좋아요 {fmt_likes(r["likes"])} — 이 사이트의 평가가 아닙니다.</li>' if r.get('likes') is not None else '') + f'<li class="note">영상·프롬프트의 권리는 원작자에게 있습니다. 작품 ID {h(r["id"])} · 수집 {h(r.get("added", ""))}</li></ul>')}
{sec('', '같은 용도의 다른 작품', f'<ul class="list">{rel}</ul>') if rel else ''}
</main>
'''
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    script = (f'<script type="application/json" id="item">{payload}</script>\n'
              f'<script type="module" src="{root}assets/page.js"></script>\n')
    return head(f'{title} — 효과 갤러리', desc, url, root, r.get('thumb'), 'article', extra) + body + FOOT + script + '</body>\n</html>\n'


def thumb_img(x):
    return (f'<img src="{h(x["thumb"])}" alt="" loading="lazy" referrerpolicy="no-referrer">' if x.get('thumb')
            else '<img alt="">')


def use_page(key, u, members, all_uses, root='../../'):
    url = SITE + f'use/{key}/'
    rows = ''.join(
        f'<li><a class="row" href="{root}{item_path(x["id"]) if has_page(x) else "?item=" + quote(x["id"], safe="")}">{thumb_img(x)}'
        f'<div><b>{h(title_of(x))}</b><span>{h(x["ed"].get("summary_ko") or "")}</span>'
        f'<span> · {LV[level_of(x)]}{" · 프롬프트 일부 공개" if x.get("partial") else ""}{" · 적용 가이드 있음" if has_page(x) else ""}</span></div></a></li>'
        for x in members)
    others = ' · '.join(f'<a href="../{k}/">{h(v["title"])}</a>' for k, v in all_uses.items() if k != key)
    body = f'''<main class="wrap doc">
<div class="crumbs"><a href="{root}">효과 갤러리</a> › <a href="../">용도별로 찾기</a></div>
<h1>{h(u['title'])}</h1>
<p class="lead">{h(u['summary'])}</p>
<section class="dsec"><h3>이런 곳에 씁니다</h3><p>{h(u.get('intro', ''))}</p></section>
<section class="dsec"><h3>고를 때 확인할 것</h3><ul>{''.join(f'<li>{h(c)}</li>' for c in u.get('checks') or [])}</ul></section>
<section class="dsec"><h3>필요한 실행 환경</h3><p>{h(u.get('env', ''))}</p></section>
<section class="dsec"><h3>편집자가 고른 작품 {len(members)}개</h3><ul class="list">{rows}</ul>
<p class="note" style="margin-top:12px">키워드로 찾은 작품까지 더 보려면 <a href="{root}?use={key}">갤러리에서 '{h(u['title'])}' 모아 보기</a>.</p></section>
<section class="dsec"><h3>다른 용도</h3><p>{others}</p></section>
</main>
'''
    return head(f'{u["title"]} — 효과 갤러리', u['summary'], url, root) + body + FOOT + \
        f'<script type="module" src="{root}assets/page.js"></script>\n</body>\n</html>\n'


def use_index(uses, counts, root='../'):
    rows = ''.join(f'<li><a class="row" href="{k}/"><div><b>{h(u["title"])}</b><span>{h(u["summary"])} · 작품 {counts[k]}개</span></div></a></li>'
                   for k, u in uses.items() if k in counts)
    body = f'''<main class="wrap doc">
<div class="crumbs"><a href="{root}">효과 갤러리</a></div>
<h1>용도별로 찾기</h1>
<p class="lead">어디에 쓸지 정해져 있다면 용도부터 고르세요. 각 페이지에 고를 때 확인할 것과 필요한 실행 환경을 정리했습니다.</p>
<ul class="list" style="margin-top:20px">{rows}</ul>
</main>
'''
    return head('용도별로 찾기 — 효과 갤러리', '로고 애니메이션, 웹사이트 배경, 제품 소개, 지도·데이터 시각화 등 용도별로 고른 AI 모션·인터랙션 효과.',
                SITE + 'use/', root) + body + FOOT + f'<script type="module" src="{root}assets/page.js"></script>\n</body>\n</html>\n'


def render(items, editorial, synced):
    uses = editorial.get('uses') or {}
    edited = [r for r in items if r.get('ed')]
    rank = lambda r: (r['ed'].get('featured_rank') or 99, -(r.get('likes') or 0), r['id'])
    files = {}
    pages = sorted((r for r in edited if has_page(r)), key=rank)
    for r in pages:
        mine = set(r['ed'].get('uses') or [])
        related = [x for x in pages if x is not r and mine & set(x['ed'].get('uses') or [])][:4]
        files[item_path(r['id']) + 'index.html'] = item_page(r, uses, related)
    counts = {}
    for key, u in uses.items():
        members = sorted((r for r in edited if key in (r['ed'].get('uses') or [])), key=lambda r: (not has_page(r),) + rank(r))
        if len(members) >= MIN_USE_ITEMS:  # 빈약한 주제는 공개하지 않는다
            files[f'use/{key}/index.html'] = use_page(key, u, members, uses)
            counts[key] = len(members)
    if counts:
        files['use/index.html'] = use_index(uses, counts)
    urls = [SITE] + [SITE + p[:-len('index.html')] for p in sorted(files)]
    files['sitemap.xml'] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                            + ''.join(f'  <url><loc>{h(u)}</loc></url>\n' for u in urls) + '</urlset>\n')
    return files
