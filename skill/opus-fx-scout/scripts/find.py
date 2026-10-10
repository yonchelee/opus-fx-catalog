#!/usr/bin/env python3
"""Search the effect catalog.

  python3 find.py --kw building archive watercolor --any-fx paint 3d --top 15
  python3 find.py --fx paint 3d --max-level 2 --full
  python3 find.py --show yihui:alexalbert-274839          # full prompt + needs
  python3 find.py --since 2026-09-28                       # recently added
  python3 find.py --board ID ID ...                        # numbered board + gallery link
  python3 find.py --stats

Scoring is a rough first pass so you read the right 10-15 prompts in full;
the actual pick should come from reading them, not from the score.
"""
import argparse, re, signal, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import FX, FX_NAME, NEED_NAME, LEVEL_NAME  # noqa: E402
import store  # noqa: E402

CAT = {'motion': '모션그래픽', 'explainer': '설명 영상', '3d': '3D 씬', 'interactive': '게임·인터랙티브'}


def score(r, kws, any_fx):
    p = r['prompt'].lower()
    hits = [k for k in kws if re.search(r'\b' + re.escape(k.lower()), p)]
    # Where a keyword appears matters more than that it appears: a prompt's
    # subject is stated up front, while long briefs mention almost anything
    # in passing somewhere.
    early = [k for k in hits if re.search(r'\b' + re.escape(k.lower()), p[:500])]
    s = 3 * len(hits) + 2 * len(early) + 2 * len(set(any_fx) & set(r['fx']))
    s += 0 if r['partial'] else 1
    s -= 3 if len(p) > 3000 and len(hits) <= 1 else 0
    s -= 2 if r['fx'] == ['reel'] else 0  # generic "go all out" prompts teach little
    return s, hits


def line(r, hits=()):
    fx = ','.join(FX_NAME[f] for f in r['fx'])
    tag = ' [일부 공개]' if r['partial'] else ''
    h = f" kw={'/'.join(hits)}" if hits else ''
    return (f"{r['id']} @{r['author']} · {CAT.get(r['category'], r['category'])} · {LEVEL_NAME[r['level']]} · "
            f"{fx}{tag} · {len(r['prompt'])}자{h}\n    {r['prompt'][:180].replace(chr(10), ' ')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kw', nargs='*', default=[], help='English keywords, prefix match')
    ap.add_argument('--fx', nargs='*', default=[], help='must have ALL of these effects')
    ap.add_argument('--any-fx', nargs='*', default=[], help='boost rows with any of these')
    ap.add_argument('--cat', choices=list(CAT))
    ap.add_argument('--max-level', type=int, default=4)
    ap.add_argument('--full', action='store_true', help='full prompts only')
    ap.add_argument('--since')
    ap.add_argument('--top', type=int, default=15)
    ap.add_argument('--show', nargs='*')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--board', nargs='*', help='ids in the order to show them')
    a = ap.parse_args()

    rows = store.load_catalog()
    src = store.describe()
    if a.stats:
        print(f'catalog {len(rows)} rows · {src}')
        for k, n, _, _ in FX:
            print(f'  {k:9} {n:12} {sum(k in r["fx"] for r in rows)}')
        for lv, n in LEVEL_NAME.items():
            print(f'  level {lv} {n}: {sum(r["level"] == lv for r in rows)}')
        return
    if a.board:
        by = {r['id']: r for r in rows} | {r['slug']: r for r in rows}
        picked = [by[i] for i in a.board if i in by]
        for n, r in enumerate(picked, 1):
            title = r.get('title') or r['prompt'].replace(chr(10), ' ')[:70]
            vis = '영상' if r.get('mp4') else ('미리보기' if r.get('thumb') else '미리보기 없음')
            print(f"{n}. {title} — @{r['author']} · {LEVEL_NAME[r['level']]} · {vis} · {r['id']}")
        print('\nGALLERY ' + store.GALLERY + '?pick=' + ','.join(r['id'] for r in picked))
        missing = [i for i in a.board if i not in by]
        if missing:
            print('not found:', ' '.join(missing))
        return
    if a.show:
        by = {r['id']: r for r in rows} | {r['slug']: r for r in rows}
        for i in a.show:
            r = by.get(i)
            if not r:
                print('not found:', i); continue
            print('=' * 70)
            print(line(r).split('\n')[0])
            print('post:', r['post_url'], '\nvideo:', r['video_url'], '\nprompt:', r['prompt_url'] or '-')
            print('tech:', ', '.join(r['tech']) or '-', '\nneeds:', ', '.join(NEED_NAME[n] for n in r['needs']) or '없음 (HTML 하나)')
            print('-' * 70); print(r['prompt'])
        return

    out = [r for r in rows
           if (not a.cat or r['category'] == a.cat) and r['level'] <= a.max_level
           and (not a.full or not r['partial']) and all(f in r['fx'] for f in a.fx)
           and (not a.since or r['added'] >= a.since)]
    ranked = sorted(((score(r, a.kw, a.any_fx), r) for r in out), key=lambda x: (-x[0][0], x[1]['id']))
    print(f'{len(out)} matched (catalog {len(rows)}: {src}) · top {min(a.top, len(out))}')
    for (s, hits), r in ranked[:a.top]:
        print(f'[{s}] ' + line(r, hits))


if __name__ == '__main__':
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
