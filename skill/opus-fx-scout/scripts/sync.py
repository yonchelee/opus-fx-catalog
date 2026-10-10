#!/usr/bin/env python3
"""Pull registered sources, classify what's new, report it.

  python3 sync.py                      # sync all active sources into the overlay
  python3 sync.py --dry-run            # only report what would be added
  python3 sync.py --add entries.json   # add rows found by hand (web search etc.)
  python3 sync.py --register src.json  # register a new source definition
  python3 sync.py --out <clone dir>    # write the full catalog into a clone of the
                                       # shared repo, then commit + push it
  python3 sync.py --write-bundle       # maintainers: write into the skill's data/

entries.json for --add is a list of objects with at least:
  source, slug, author, post_url, prompt  (optional: video_url, prompt_url,
  category, tech_tags, prompt_partial, added, model)
category must be one of: motion, explainer, 3d, interactive.
'added' is the date the row entered the catalog, not the post date.
"""
import argparse, datetime, json, os, signal, subprocess, sys, tempfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import classify, FX_NAME, LEVEL_NAME  # noqa: E402
import store  # noqa: E402

TODAY = datetime.date.today().isoformat()


def fetch_text(src):
    """Raw URL first; fall back to a shallow git clone (some sandboxes only allow git)."""
    raw = f"https://raw.githubusercontent.com/{src['repo']}/{src.get('branch', 'main')}/{src['path']}"
    try:
        with urllib.request.urlopen(raw, timeout=30) as r:
            return r.read().decode('utf-8')
    except Exception as e:  # noqa: BLE001
        err = e
    with tempfile.TemporaryDirectory() as t:
        res = subprocess.run(['git', 'clone', '--depth', '1', '-q', f"https://github.com/{src['repo']}", t],
                             capture_output=True, text=True, env={**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1'})
        if res.returncode == 0:
            return (Path(t) / src['path']).read_text()
        raise RuntimeError(f"fetch failed ({err}); git: {res.stderr.strip()[:200]}")


def normalize(src_id, v, tpl=None, model=None):
    fx, needs, level = classify(v.get('prompt', ''), v.get('tech_tags', []))
    slug = v['slug']
    return {
        'id': f'{src_id}:{slug}', 'src': src_id, 'slug': slug,
        'author': v.get('author', ''), 'post_url': v.get('post_url', ''),
        'video_url': v.get('video_url') or v.get('skillry_url', ''),
        'prompt_url': v.get('prompt_url') or (tpl.format(slug=slug) if tpl else ''),
        'model': v.get('model') or model or '',
        'category': v.get('category', ''), 'tech': v.get('tech_tags', []),
        'prompt': v.get('prompt', ''), 'partial': bool(v.get('prompt_partial', False)),
        'added': v.get('added') or TODAY, 'fx': fx, 'needs': needs, 'level': level,
    }


def merge(current, incoming):
    by_id = {r['id']: r for r in current}
    new, changed = [], []
    for r in incoming:
        old = by_id.get(r['id'])
        if old is None:
            new.append(r)
        elif old != r:
            changed.append(r)
        by_id[r['id']] = r
    return list(by_id.values()), new, changed


def report(new, changed):
    print(f'NEW {len(new)} · UPDATED {len(changed)}')
    for r in sorted(new, key=lambda r: r['added'], reverse=True):
        fx = ','.join(FX_NAME[f] for f in r['fx'])
        flag = ' [일부 공개]' if r['partial'] else ''
        print(f"+ {r['id']} @{r['author']} {r['added']} · {LEVEL_NAME[r['level']]} · {fx}{flag}")
        print('    ' + r['prompt'][:160].replace('\n', ' '))
    for r in changed:
        print(f"~ {r['id']} (내용 갱신)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--add')
    ap.add_argument('--register')
    ap.add_argument('--write-bundle', action='store_true')
    ap.add_argument('--out', help='clone of the shared catalog repo to write into')
    a = ap.parse_args()

    if a.register:
        extra = json.loads(Path(a.register).read_text())
        extra = extra if isinstance(extra, list) else [extra]
        ids = {e['id'] for e in extra}
        if a.out:
            out = Path(a.out) / 'sources.json'
            cur = [s for s in store._read(out, store.load_sources()) if s['id'] not in ids]
            out.write_text(json.dumps(sorted(cur + extra, key=lambda s: s['id']), ensure_ascii=False, indent=1))
            print('registered in', out, ':', ', '.join(ids))
        else:
            mine = [s for s in store._read(store.OVERLAY_SOURCES, []) if s['id'] not in ids]
            store.save_overlay_sources(mine + extra)
            print('registered (this session only):', ', '.join(ids))
        return

    catalog = store.load_catalog()
    incoming, errors = [], []
    if a.add:
        for v in json.loads(Path(a.add).read_text()):
            incoming.append(normalize(v['source'], v, model=v.get('model')))
    else:
        for src in store.load_sources():
            if src.get('status') != 'active' or src.get('type') != 'videos_json':
                continue
            try:
                rows = json.loads(fetch_text(src))
                incoming += [normalize(src['id'], v, src.get('prompt_url_tpl'), src.get('model')) for v in rows]
                print(f"source {src['id']}: {len(rows)} rows")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{src['id']}: {e}")

    merged, new, changed = merge(catalog, incoming)
    # Save first, print second: a reader that closes the pipe early
    # (`| head`) must not cost us the write.
    if not a.dry_run and (new or changed or a.out):
        if a.out:
            store.save_to_dir(a.out, merged, store.load_sources(), TODAY)
            store.save_overlay([], TODAY)  # now durable in the repo clone
            where = f'wrote {a.out}/catalog.json ({len(merged)} rows) - commit and push it'
        elif a.write_bundle:
            store.save_bundle(merged, TODAY)
            where = f'wrote bundle {store.BUNDLE}'
        else:
            base = store.base_items()
            overlay = [r for r in merged if base.get(r['id']) != r]
            store.save_overlay(overlay, TODAY)
            where = f'wrote overlay {store.OVERLAY} ({len(overlay)} rows, this session only)'
    else:
        where = 'dry run, nothing written' if a.dry_run else 'nothing to write'
    report(new, changed)
    for e in errors:
        print('ERROR', e)
    print(where)

if __name__ == '__main__':
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
