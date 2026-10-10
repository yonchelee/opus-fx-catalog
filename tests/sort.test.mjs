// 정렬 시험 — 별도 테스트 데이터만 쓴다(실제 별 수를 바꾸지 않는다).  node --test
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sortRows} from '../assets/data.js';
import {buildRequest} from '../assets/apply.js';

const gh = (id, stars, extra = {}) => ({id, src: 'gh', repo: {stars, url: `https://github.com/o/${id}`}, first_seen: '2026-10-10T00:00:00Z', ...extra});
const x = (id, likes, added) => ({id, src: 'yihui', likes, added});

test('별 수가 바뀌면 GitHub 별 많은 순이 바뀐다', () => {
  const a = gh('a', 100), b = gh('b', 50);
  assert.deepEqual(sortRows([a, b], 'stars').map(r => r.id), ['a', 'b']);
  b.repo.stars = 500;
  assert.deepEqual(sortRows([a, b], 'stars').map(r => r.id), ['b', 'a']);
});

test('X 좋아요와 저장소 별을 합산하지 않는다 — 각 정렬에서 지표가 없는 쪽은 뒤', () => {
  const rows = [gh('g', 9000), x('x1', 10, '2026-10-01'), x('x2', 500, '2026-10-01')];
  assert.deepEqual(sortRows(rows, 'likes').map(r => r.id), ['x2', 'x1', 'g']);
  assert.deepEqual(sortRows(rows, 'stars').map(r => r.id), ['g', 'x1', 'x2']);
});

test('최근 상승: 비교 기간을 채운 저장소만 앞, 이력 없는 저장소는 뒤', () => {
  const rows = [gh('big', 10000), gh('up', 300, {trend: {delta: 40}}), gh('up2', 50, {trend: {delta: 90}})];
  assert.deepEqual(sortRows(sortRows(rows, 'stars'), 'trend').map(r => r.id), ['up2', 'up', 'big']);
});

test('최근 발견: 발견 시각 순, 새 작품이 누적 인기작보다 앞', () => {
  const rows = [x('old', 9999, '2026-09-26'), gh('new', 3, {first_seen: '2026-10-10T05:00:00Z'}), x('mid', 1, '2026-10-08')];
  assert.deepEqual(sortRows(rows, 'new').map(r => r.id), ['new', 'mid', 'old']);
});

test('코드 기반 작품의 요청문: 저장소 주소·효과·실행 환경, 프롬프트를 지어내지 않음', () => {
  const r = gh('fx', 10, {author: 'o', title: 'fx', desc: 'Ink bleed shader', topics: ['shader'], env_text: '정적 웹 페이지', repo: {stars: 10, url: 'https://github.com/o/fx', license: 'MIT'}});
  const t = buildRequest(r, {use: '포스터'}, []);
  assert.match(t, /\[참고한 저장소\] https:\/\/github\.com\/o\/fx \(라이선스 MIT\)/);
  assert.match(t, /\[구현할 효과\] Ink bleed shader/);
  assert.match(t, /\[원본 실행 환경\] 정적 웹 페이지/);
  assert.match(t, /프롬프트가 아니라 코드로 공개/);
  assert.doesNotMatch(t, /원본 프롬프트 —/);
});
