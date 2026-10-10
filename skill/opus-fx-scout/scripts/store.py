"""Catalog storage.

Three layers, later ones win on the same id:
  1. bundle  - data/catalog.json shipped inside the skill (always there)
  2. remote  - catalog.json in the shared GitHub repo (REMOTE_REPO), the
               durable copy that the weekly update commits to
  3. overlay - this session's local additions in OPUS_FX_HOME, for sessions
               that can't push (they are lost when the session ends)

The remote is fetched once per session and cached next to the overlay.
"""
import json, os, time, urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BUNDLE = SKILL / 'data' / 'catalog.json'
BUNDLE_SOURCES = SKILL / 'data' / 'sources.json'
REMOTE_REPO = os.environ.get('OPUS_FX_REPO', 'yonchelee/opus-fx-catalog')
REMOTE_RAW = f'https://raw.githubusercontent.com/{REMOTE_REPO}/main'
HOME = Path(os.environ.get('OPUS_FX_HOME', Path.home() / '.cache' / 'opus-fx-scout'))
OVERLAY = HOME / 'overlay.json'
OVERLAY_SOURCES = HOME / 'sources.json'
REMOTE_CACHE = HOME / 'remote'
CACHE_TTL = 6 * 3600


def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _remote(name):
    """Fetch <repo>/main/<name>, cached for CACHE_TTL. None if unreachable."""
    cache = REMOTE_CACHE / name
    if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_TTL:
        return _read(cache, None)
    try:
        with urllib.request.urlopen(f'{REMOTE_RAW}/{name}', timeout=20) as r:
            text = r.read().decode('utf-8')
        data = json.loads(text)
    except Exception:  # noqa: BLE001 - offline, blocked, repo missing: fall back
        return _read(cache, None)
    REMOTE_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(text)
    return data


def layers():
    """(name, synced date, items) for each layer that exists."""
    out = []
    for name, data in (('bundle', _read(BUNDLE, None)), ('remote', _remote('catalog.json')),
                       ('overlay', _read(OVERLAY, None))):
        if data:
            out.append((name, data.get('synced'), data.get('items', [])))
    return out


def load_catalog():
    rows = {}
    for _, _, items in layers():
        rows.update({r['id']: r for r in items})
    return list(rows.values())


def describe():
    """One line saying which layers fed the catalog, e.g. for answers."""
    return ' + '.join(f'{n} {d}' for n, d, _ in layers())


def base_items():
    """bundle + remote, i.e. what is already durable; overlay stores only the rest."""
    rows = {}
    for n, _, items in layers():
        if n != 'overlay':
            rows.update({r['id']: r for r in items})
    return rows


def load_sources():
    src = {s['id']: s for s in _read(BUNDLE_SOURCES, [])}
    src.update({s['id']: s for s in (_remote('sources.json') or [])})
    src.update({s['id']: s for s in _read(OVERLAY_SOURCES, [])})
    return list(src.values())


def save_overlay(items, synced):
    HOME.mkdir(parents=True, exist_ok=True)
    OVERLAY.write_text(json.dumps({'synced': synced, 'items': items}, ensure_ascii=False))


def save_bundle(items, synced):
    BUNDLE.write_text(json.dumps({'synced': synced, 'items': items}, ensure_ascii=False))


def save_overlay_sources(sources):
    HOME.mkdir(parents=True, exist_ok=True)
    OVERLAY_SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=1))


def save_to_dir(out_dir, items, sources, synced):
    """Write a full catalog + sources into a directory (a clone of REMOTE_REPO)."""
    out = Path(out_dir)
    items = sorted(items, key=lambda r: r['id'])
    (out / 'catalog.json').write_text(json.dumps({'synced': synced, 'items': items}, ensure_ascii=False, indent=0))
    (out / 'sources.json').write_text(json.dumps(sorted(sources, key=lambda s: s['id']), ensure_ascii=False, indent=1))
