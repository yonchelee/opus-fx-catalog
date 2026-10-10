// 적용용 요청문 시험.  node --test
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildRequest} from '../assets/apply.js';

const base = {id: 'x:1', author: 'maker', post_url: 'https://x.com/maker/status/1', fx: ['data'], level: 1, title: 'Map', prompt: 'draw a hand drawn map'};

test('편집 brief 가 있으면 원본 프롬프트를 붙이지 않는다', () => {
  const t = buildRequest({...base, ed: {guide: {brief: '손그림 지도 위에 데이터를 겹친다'}}}, {use: '보고서', text: '서울 강수량', color: '파랑', env: 'chat'}, []);
  assert.match(t, /손그림 지도 위에 데이터를 겹친다/);
  assert.match(t, /\[내 용도\] 보고서/);
  assert.match(t, /\[들어갈 문구\] 서울 강수량/);
  assert.match(t, /\[색상\] 파랑/);
  assert.match(t, /HTML 한 장/);
  assert.doesNotMatch(t, /draw a hand drawn map/);
  assert.match(t, /@maker/);
});

test('brief 가 없으면 원본 프롬프트를 참고용으로 붙인다', () => {
  const t = buildRequest(base, {}, ['지도·데이터 시각화']);
  assert.match(t, /원본 프롬프트 — 기법 참고용/);
  assert.match(t, /draw a hand drawn map/);
  assert.match(t, /\[내 용도\] 지도·데이터 시각화/);
});

test('일부 공개 프롬프트는 그 사실을 요청문에 적는다', () => {
  const t = buildRequest({...base, partial: true}, {}, []);
  assert.match(t, /일부만 공개됨/);
});

test('긴 프롬프트는 잘라서 붙인다', () => {
  const t = buildRequest({...base, prompt: 'a'.repeat(5000)}, {}, []);
  assert.ok(t.length < 2500);
});

test('입력이 비면 기본 안내로 채운다', () => {
  const t = buildRequest(base, {}, []);
  assert.match(t, /임의로 정해 주세요/);
  assert.match(t, /원본 분위기를 유지/);
});

// 생성 페이지(파이썬 pages.build_request)의 기본 요청문이 브라우저 buildRequest 와 같은지
import {readdirSync, readFileSync, statSync} from 'node:fs';
const unescape = s => s.replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const root = new URL('../fx/', import.meta.url);
const pages = [];
for (const src of readdirSync(root)) for (const slug of readdirSync(new URL(src + '/', root))) pages.push(new URL(`${src}/${slug}/index.html`, root));
test('생성 페이지마다 7번 칸이 HTML 에 있고, 기본 요청문이 브라우저 함수와 같다', () => {
  assert.ok(pages.length >= 12);
  for (const p of pages) {
    const html = readFileSync(p, 'utf8');
    const data = JSON.parse(html.match(/<script type="application\/json" id="item">([\s\S]*?)<\/script>/)[1].replace(/<\\\//g, '</'));
    const out = html.match(/<pre class="prompt" id="ap-out"[^>]*>([\s\S]*?)<\/pre>/);
    assert.ok(out, `${p.pathname}: 7번 칸 없음`);
    const env = data.level <= 1 ? 'chat' : 'code';
    assert.equal(unescape(out[1]), buildRequest(data, {env}, data.uses), p.pathname);
  }
});
