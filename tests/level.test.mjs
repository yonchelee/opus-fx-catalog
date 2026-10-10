// 실행 환경 표시 시험.  node --test
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {mergeEditorial, levelOf} from '../assets/data.js';

const root = new URL('../', import.meta.url);
const cat = JSON.parse(readFileSync(new URL('catalog.json', root)));
const ed = JSON.parse(readFileSync(new URL('editorial.json', root)));
const items = mergeEditorial(cat.items, ed).items;
const lv = r => levelOf(r, ed.level_check);

test('제목에만 Blender 가 있는 쇼릴은 채팅이 아니다 (검토 지적)', () => {
  const b = items.find(r => /Blender 3D and self-made/.test(r.title || ''));
  assert.equal(lv(b), 3);
});

test('편집하지 않은 작품이 영상 결과물을 요구하면 "환경 확인 필요"', () => {
  const fake = {id: 'x:1', level: 1, title: '15-second motion graphics video', prompt: 'make it', fx: []};
  assert.equal(levelOf(fake, ed.level_check), 0);
  assert.equal(levelOf({...fake, title: 'interactive canvas toy', prompt: 'drag to play'}, ed.level_check), 1);
});

test('편집에서 확인한 작품은 "환경 확인 필요"로 바뀌지 않는다', () => {
  for (const r of items.filter(r => r.ed)) assert.notEqual(lv(r), 0, r.id);
});

test('"채팅에서 바로"로 남은 작품에는 영상 결과물 요구가 없다(편집 작품 제외)', () => {
  const re = new RegExp(ed.level_check.re, 'i');
  for (const r of items.filter(r => !r.ed && lv(r) === 1)) assert.ok(!re.test((r.title || '') + ' ' + r.prompt), r.id);
});

test('브라우저(data.js)와 생성기(pages.py)가 646개 모두 같은 단계로 판정한다', () => {
  const py = execFileSync('python3', ['-c', `
import json, sys
sys.path.insert(0, 'skill/opus-fx-scout/scripts')
import build_site, pages
cat, ed = build_site.load('.')
items, _ = build_site.merge(cat['items'], ed)
pages.LEVEL_CHECK.update(ed.get('level_check') or {})
print(json.dumps({r['id']: pages.level_of(r) for r in items}))
`], {cwd: new URL('.', root).pathname, encoding: 'utf8'});
  const want = JSON.parse(py);
  const diff = items.filter(r => want[r.id] !== lv(r)).map(r => `${r.id}: js ${lv(r)} py ${want[r.id]}`);
  assert.deepEqual(diff, []);
});
