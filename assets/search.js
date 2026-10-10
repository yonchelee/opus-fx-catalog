/* 검색. 순수 함수만 둔다 — 브라우저(app.js)와 node 시험(tests/search.test.mjs)이 같이 쓴다.

   - 대소문자·전각·공백을 정규화한다.
   - 검색어를 띄어쓰기로 나눠 모두 맞아야 결과에 든다(AND).
   - 각 검색어는 동의어 묶음(editorial.json synonyms)으로 넓힌다: 지도 → map, globe …
     한국어 조사(을·를·에 …)가 붙어도 묶음을 찾는다.
   - 영문 동의어는 단어 앞 경계에서만 맞춘다(map 이 bitmap 에 걸리지 않게).
   - 점수: 편집 제목·검색어·용도 10 > 영문 제목·효과·장르 6 > 작성자 3 > 프롬프트 본문 1.
     같은 점수 안에서는 호출한 쪽의 정렬을 그대로 둔다(정렬은 안정적이다). */

import {FXN, CAT, LV} from './data.js';

export const normalize = s => String(s ?? '').normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();

const PARTICLES = ['으로', '에서', '에게', '처럼', '같은', '을', '를', '이', '가', '은', '는', '에', '의', '로', '와', '과', '도'];
const ASCII = /^[\x00-\x7f]+$/;
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

export function synonymIndex(groups) {
  const byTerm = new Map();
  (groups || []).forEach(g => {
    const norm = [...new Set(g.map(normalize).filter(Boolean))];
    norm.forEach(t => byTerm.set(t, norm));
  });
  return byTerm;
}

/* 한 검색어 → 맞춰 볼 낱말들 */
export function expand(term, syn) {
  const t = normalize(term);
  if (!t) return [];
  if (syn.has(t)) return syn.get(t);
  for (const p of PARTICLES) {
    if (t.length > p.length + 1 && t.endsWith(p)) {
      const base = t.slice(0, -p.length);
      if (syn.has(base)) return syn.get(base);
    }
  }
  return [t];
}

function matcher(alt) {
  if (ASCII.test(alt)) {
    const re = new RegExp('(^|[^a-z0-9])' + reEsc(alt));
    return s => re.test(s);
  }
  return s => s.includes(alt);
}

/* 작품 하나를 검색용 칸으로 미리 나눠 둔다 */
export function prepare(r, uses) {
  const ed = r.ed || {};
  const useTitles = (ed.uses || []).map(u => (uses && uses[u] && uses[u].title) || u);
  return {
    r,
    f: [
      [10, normalize([ed.title_ko, ed.summary_ko, ...(ed.keywords || []), ...useTitles].filter(Boolean).join(' | '))],
      [6, normalize([r.title, ...(r.fx || []).map(f => FXN[f] + ' ' + f), CAT[r.category], r.category, LV[r.level], ...(r.tech || [])].filter(Boolean).join(' | '))],
      [3, normalize('@' + (r.author || '') + ' ' + (r.author || ''))],
      [1, normalize(r.prompt)]
    ]
  };
}

/* 0 이면 안 맞음. 아니면 점수. */
export function score(p, terms) {
  let total = 0;
  for (const alts of terms) {
    const ms = alts.map(matcher);
    let best = 0;
    for (const [w, text] of p.f) {
      if (w > best && ms.some(m => m(text))) best = w;
    }
    if (!best) return 0;
    total += best;
  }
  return total;
}

export function parseQuery(q, syn) {
  return normalize(q).split(' ').filter(Boolean).map(t => expand(t, syn));
}

/* prepared 배열과 검색어 → 점수 높은 순(같으면 들어온 순서) */
export function search(prepared, q, syn) {
  const terms = parseQuery(q, syn);
  if (!terms.length) return prepared.map(p => p.r);
  return prepared
    .map((p, i) => ({p, i, s: score(p, terms)}))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .map(x => x.p.r);
}
