#!/usr/bin/env python3
"""Fill title/thumb/mp4 from Li-Evan/awesome-opus-5.5-video-prompts YAML,
matched by X post id. Run against a clone of that repo:

  python3 enrich_media.py <li-evan clone> <catalog.json to update>
"""
import json, re, sys
from pathlib import Path
import yaml

src, cat = Path(sys.argv[1]), Path(sys.argv[2])
pid = lambda u: (re.search(r'/status/(\d+)', u or '') or [None, None])[1]
found = {}
for f in sorted((src / 'data').glob('*.yaml')):
    for e in (yaml.safe_load(f.read_text()) or {}).get('entries') or []:
        m = e.get('media') or {}
        if pid(e.get('url')):
            found[pid(e['url'])] = {'title': e.get('title'), 'thumb': m.get('thumb'),
                                   'mp4': m.get('video'), 'mp4_hd': m.get('video_hd')}
data = json.loads(cat.read_text())
n = 0
for r in data['items']:
    extra = found.get(pid(r['post_url']))
    if extra:
        for k, v in extra.items():
            if v and not r.get(k):
                r[k] = v
        n += 1
cat.write_text(json.dumps(data, ensure_ascii=False, indent=0))
print(f'matched {n}/{len(data["items"])} rows from {len(found)} Li-Evan entries')
