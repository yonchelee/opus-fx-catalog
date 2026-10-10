#!/usr/bin/env python3
"""갤러리 정적 페이지 생성기 (표준 라이브러리만).

  python3 build_site.py --dir <clone>           # 작품·용도 페이지와 sitemap.xml 생성
  python3 build_site.py --dir <clone> --check   # 생성물이 원천과 같은지만 본다 (다르면 종료 코드 1)

원천은 catalog.json(원본 수집, sync.py 가 씀)과 editorial.json(손으로 편집, 아무 스크립트도 쓰지 않음)이다.
병합 규칙은 assets/data.js 의 mergeEditorial() 과 같다. 둘을 함께 고친다.
- id 가 정확히 같을 때만 붙인다. 원본에서 사라진 id 는 연결하지 않고 경고한다.
- 원본 값은 덮지 않는다. 편집 정보는 r['ed'] 아래에만 둔다.
"""
import argparse, json, sys
from pathlib import Path

SITE = 'https://yonchelee.github.io/opus-fx-catalog/'


def load(root):
    root = Path(root)
    cat = json.loads((root / 'catalog.json').read_text())
    ed = json.loads((root / 'editorial.json').read_text())
    gh = root / 'github.json'  # discover.py 가 만드는 GitHub 공개 작품. 편집 정보는 이것에도 붙을 수 있다
    if gh.exists():
        cat = dict(cat, items=cat['items'] + json.loads(gh.read_text()).get('items', []))
    return cat, ed


def merge(items, editorial):
    ed = (editorial or {}).get('items') or {}
    ids = {r['id'] for r in items}
    orphans = sorted(k for k in ed if k not in ids)
    merged = [dict(r, ed=ed[r['id']]) if r['id'] in ed else r for r in items]
    return merged, orphans


def item_path(item_id):
    """'src:slug' → 'fx/src/slug/' (assets/data.js itemPath 와 같은 규칙)."""
    from urllib.parse import quote
    src, slug = item_id.split(':', 1)
    return f'fx/{quote(src, safe="")}/{quote(slug, safe="")}/'


def render_all(root):
    """{상대경로: 내용} — 생성할 모든 파일. 페이지 본문은 pages.py 가 만든다."""
    cat, ed = load(root)
    items, orphans = merge(cat['items'], ed)
    import pages  # 같은 폴더
    return pages.render(items, ed, cat.get('synced', '')), orphans


def generated_paths(root):
    root = Path(root)
    out = []
    for d in ('fx', 'use'):
        out += [p.relative_to(root).as_posix() for p in (root / d).rglob('index.html')] if (root / d).exists() else []
    if (root / 'sitemap.xml').exists():
        out.append('sitemap.xml')
    return set(out)


def build(root, check=False):
    root = Path(root)
    files, orphans = render_all(root)
    for o in orphans:
        print(f'WARN editorial.json 의 {o} 는 catalog.json 에 없다 — 연결하지 않음', file=sys.stderr)
    stale = sorted(p for p in files if not (root / p).exists() or (root / p).read_text() != files[p])
    extra = sorted(generated_paths(root) - set(files))
    if check:
        for p in stale:
            print('STALE', p)
        for p in extra:
            print('EXTRA', p)
        return 0 if not stale and not extra else 1
    for p in stale:
        (root / p).parent.mkdir(parents=True, exist_ok=True)
        (root / p).write_text(files[p])
    for p in extra:  # 편집에서 빠진 작품의 옛 페이지
        (root / p).unlink()
        try:
            (root / p).parent.rmdir()
        except OSError:
            pass
    print(f'site: {len(files)} files · wrote {len(stale)} · removed {len(extra)} · orphans {len(orphans)}')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    sys.exit(build(a.dir, a.check))


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
