#!/usr/bin/env python3
"""Like counts for X posts, so the gallery can sort by what people liked.

  python3 likes.py --dir <clone>          # refresh rows whose count is older than 6 days
  python3 likes.py --dir <clone> --all    # refresh every row

Reads X's public embed endpoint (the one tweet embeds use; no login or key),
falling back to api.fxtwitter.com. A row that can't be read keeps its old
count, so a blocked network never wipes data. Rows that aren't X posts
(reddit, linux.do) get no count and sort last.
"""
import argparse, concurrent.futures, datetime, json, math, re, sys, time, urllib.request
from pathlib import Path

TODAY = datetime.date.today().isoformat()
UA = {'User-Agent': 'Mozilla/5.0 (opus-fx-catalog likes)'}
STATUS = re.compile(r'(?:x|twitter)\.com/[^/]+/status/(\d+)')


def tweet_id(url):
    m = STATUS.search(url or '')
    return m.group(1) if m else None


def _token(tid):
    # Same token the embed widget computes: (id / 1e15 * pi) in base 36, zeros and dot removed.
    n = int(tid) / 1e15 * math.pi
    whole, frac, digits = int(n), n - int(n), '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while whole:
        whole, r = divmod(whole, 36)
        s = digits[r] + s
    s = (s or '0') + '.'
    for _ in range(12):
        frac *= 36
        s += digits[int(frac)]
        frac -= int(frac)
    return re.sub(r'(0+|\.)', '', s)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def fetch(tid):
    """Like count or None."""
    try:
        d = _get(f'https://cdn.syndication.twimg.com/tweet-result?id={tid}&token={_token(tid)}&lang=en')
        if isinstance(d.get('favorite_count'), int):
            return d['favorite_count']
    except Exception:  # noqa: BLE001 - deleted post, rate limit, blocked host
        pass
    try:
        t = _get(f'https://api.fxtwitter.com/status/{tid}').get('tweet') or {}
        if isinstance(t.get('likes'), int):
            return t['likes']
    except Exception:  # noqa: BLE001
        pass
    return None


def stale(row, max_age):
    at = row.get('likes_at')
    if not at:
        return True
    return (datetime.date.fromisoformat(TODAY) - datetime.date.fromisoformat(at)).days >= max_age


def refresh(items, max_age=6, workers=4):
    """Update likes / likes_at in place. Returns (updated, failed, skipped)."""
    todo = [r for r in items if tweet_id(r.get('post_url')) and stale(r, max_age)]
    skipped = len(items) - len(todo)
    updated = failed = 0

    def one(r):
        time.sleep(0.15)  # gentle on the endpoint
        return r, fetch(tweet_id(r['post_url']))

    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        for r, n in ex.map(one, todo):
            if n is None:
                failed += 1
            else:
                r['likes'], r['likes_at'] = n, TODAY
                updated += 1
    return updated, failed, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='clone of the catalog repo (has catalog.json)')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    path = Path(a.dir) / 'catalog.json'
    cat = json.loads(path.read_text())
    up, bad, skip = refresh(cat['items'], max_age=0 if a.all else 6)
    # Same layout as store.save_to_dir so diffs stay small.
    cat['items'] = sorted(cat['items'], key=lambda r: r['id'])
    path.write_text(json.dumps(cat, ensure_ascii=False, indent=0))
    print(f'likes: updated {up} · failed {bad} · skipped {skip}')
    return 0 if up or not bad else 1


if __name__ == '__main__':
    sys.exit(main())
