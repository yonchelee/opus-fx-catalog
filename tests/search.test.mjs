// 검색 시험.  node --test
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalize, synonymIndex, prepare, search, expand} from '../assets/search.js';
import {mergeEditorial} from '../assets/data.js';

const root = new URL('../', import.meta.url);
const cat = JSON.parse(readFileSync(new URL('catalog.json', root)));
const ed = JSON.parse(readFileSync(new URL('editorial.json', root)));
const syn = synonymIndex(ed.synonyms);
const items = mergeEditorial(cat.items, ed).items;
const prepared = items.map(r => prepare(r, ed.uses));
const hits = q => search(prepared, q, syn);
const hay = r => (r.title + ' ' + r.prompt).toLowerCase();

test('정규화: 대소문자·공백·전각', () => {
  assert.equal(normalize('  Ｍap   Logo '), 'map logo');
});

for (const [ko, en] of [['지도', /\bmaps?\b|globe/], ['로고', /\blogo/], ['입자', /particle/], ['손그림', /hand[- ]?drawn|sketch|doodle/]]) {
  test(`한국어 "${ko}" 가 영어 사례를 찾는다`, () => {
    const r = hits(ko);
    assert.ok(r.length >= 3, `${ko}: ${r.length}건`);
    const english = r.filter(x => en.test(hay(x)));
    assert.ok(english.length >= 3, `${ko}: 영어 일치 ${english.length}건`);
  });
}

test('조사가 붙어도 동의어를 찾는다', () => {
  assert.deepEqual(expand('지도를', syn), expand('지도', syn));
  assert.ok(hits('로고를').length === hits('로고').length);
});

test('영문 동의어는 단어 경계에서만 (map 이 bitmap 에 걸리지 않음)', () => {
  const fake = [prepare({id: 'x:1', title: 'bitmap font', prompt: '', fx: [], author: 'a'}, {})];
  assert.equal(search(fake, 'map', syn).length, 0);
  assert.equal(search(fake, 'bitmap', syn).length, 1);
});

test('여러 검색어는 모두 맞아야 한다 (AND)', () => {
  const both = hits('로고 입자');
  for (const r of both) {
    const t = hay(r) + JSON.stringify(r.ed || {}) + (r.fx || []).join(' ');
    assert.ok(/logo|로고|wordmark|brand/.test(t) && /particle|입자|파티클/.test(t), r.id);
  }
});

test('편집 제목 일치가 프롬프트 본문 일치보다 앞선다', () => {
  const a = {id: 'x:prompt', title: '', prompt: 'a long prompt that mentions a logo somewhere', fx: [], author: 'a'};
  const b = {id: 'x:edited', title: '', prompt: 'nothing', fx: [], author: 'b', ed: {title_ko: '로고 그리기'}};
  const r = search([prepare(a, {}), prepare(b, {})], '로고', syn);
  assert.deepEqual(r.map(x => x.id), ['x:edited', 'x:prompt']);
});

test('결과가 없는 검색어는 빈 배열', () => {
  assert.equal(hits('zzzqqq없는말').length, 0);
});

test('빈 검색어는 전체를 그대로 순서대로', () => {
  assert.equal(hits('   ').length, items.length);
});

test('제목에 검색어가 있는 작품이 넓은 분류에만 걸린 작품보다 앞선다 (검토 지적: 지도)', () => {
  const r = hits('지도');
  const pos = id => r.findIndex(x => x.id === id);
  const map = pos('yihui:groundcontrol-230877'), roas = pos('yihui:annacher-433425'), music = pos('yihui:twoclipping-402193');
  assert.ok(map >= 0 && map < 3, `손그림 지도 ${map}위`);
  assert.ok(roas === -1 || roas > map, `ROAS ${roas}위 · 지도 ${map}위`);
  assert.ok(music === -1 || music > map, `음악 플레이어 ${music}위`);
  const titleHit = x => /지도|\bmaps?\b|globe|geographic/i.test(((x.ed && x.ed.title_ko) || '') + ' ' + (x.title || ''));
  const firstNon = r.findIndex(x => !titleHit(x));
  assert.ok(r.slice(firstNon).every(x => !titleHit(x)), '제목 일치 작품이 모두 앞에 모여 있다');
});

test('입력한 말 그대로 일치가 동의어 일치보다 앞선다', () => {
  const a = {id: 'x:syn', title: 'world globe spin', prompt: '', fx: [], author: 'a'};
  const b = {id: 'x:exact', title: 'map reveal', prompt: '', fx: [], author: 'b'};
  assert.deepEqual(search([prepare(a, {}), prepare(b, {})], 'map', syn).map(x => x.id), ['x:exact', 'x:syn']);
});

test('뜻이 갈리는 동의어로 엉뚱한 작품을 올리지 않는다 (geo ≠ 지리, SEO vs GEO)', () => {
  const r = hits('지도').slice(0, 3).map(x => x.title || '');
  assert.ok(!r.some(t => /SEO vs GEO/i.test(t)), r.join(' / '));
});
