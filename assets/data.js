/* 원본(catalog.json)과 편집(editorial.json)을 합친다. 브라우저와 node 시험이 같이 쓴다.
   파이썬 쪽 같은 규칙: skill/opus-fx-scout/scripts/build_site.py 의 merge(). 둘을 함께 고친다.

   규칙
   - 편집 정보는 id 가 정확히 같을 때만 붙는다. 비슷한 slug 로 추정하지 않는다.
   - 원본에서 사라진 id 의 편집 정보는 버리고 orphans 로 알린다.
   - 원본 값은 덮지 않는다. 편집 정보는 r.ed 아래에만 둔다. */

export const FX = [['3d','3D 씬·카메라'],['shader','셰이더·글로우'],['reel','모션 쇼릴'],['game','플레이어블 게임'],['paint','페인터리·손그림'],['ui','UI·제품 데모'],['particles','파티클·입자'],['audio','사운드 동기화'],['liquid','유체·물리'],['cosmic','우주·자연'],['pixel','픽셀아트'],['morph','모핑·트랜지션'],['glitch','글리치·레트로'],['kinetic','키네틱 타이포'],['data','데이터·지도'],['etc','기타']];
export const FXN = Object.fromEntries(FX);
export const CAT = {motion:'모션그래픽', explainer:'설명 영상', '3d':'3D 씬', interactive:'게임·인터랙티브'};
export const LV = {1:'채팅에서 바로', 2:'Claude Code', 3:'외부 프로그램', 4:'외부 AI·API'};
export const LV_LONG = {
  1: 'Claude 채팅 미리보기에서 바로 볼 수 있음',
  2: 'Claude Code 같은 개발 환경에서 파일을 만들어 실행',
  3: 'Blender·게임엔진 같은 외부 프로그램 필요',
  4: '영상·이미지 생성 AI 같은 외부 서비스 필요'
};
export const NEED = {render:'MP4 렌더링', remotion:'Remotion', node:'Node.js 프로젝트', python:'Python', blender:'Blender', engine:'게임엔진', figma:'Figma', genvideo:'영상 생성 AI', genimage:'이미지 생성 AI', genaudio:'음성·음악 생성 AI', assets:'내 자료 필요'};
export const VERIFY = {
  unverified: {label:'미검증', note:'이 사이트에서 직접 실행해 보지 않았습니다.'},
  partial: {label:'일부 확인', note:'일부 효과만 같은 방식으로 나오는 것을 확인했습니다.'},
  reproduced: {label:'재현 확인', note:'같은 프롬프트로 비슷한 결과가 나오는 것을 확인했습니다.'}
};
export const SITE = 'https://yonchelee.github.io/opus-fx-catalog/';

export function mergeEditorial(items, editorial) {
  const ed = (editorial && editorial.items) || {};
  const ids = new Set(items.map(r => r.id));
  const orphans = Object.keys(ed).filter(id => !ids.has(id));
  const merged = items.map(r => (ed[r.id] ? {...r, ed: ed[r.id]} : r));
  return {items: merged, orphans};
}

/* 작품의 정적 페이지 경로(편집이 끝난 작품만 있다). id "src:slug" → "fx/src/slug/" */
export function itemPath(id) {
  const i = id.indexOf(':');
  return 'fx/' + encodeURIComponent(id.slice(0, i)) + '/' + encodeURIComponent(id.slice(i + 1)) + '/';
}

export const verifyOf = r => (r.ed && r.ed.verify && VERIFY[r.ed.verify.status]) ? r.ed.verify.status : 'unverified';
export const titleOf = r => (r.ed && r.ed.title_ko) || r.title || (r.prompt || '').replace(/\s+/g, ' ').trim().slice(0, 70) || r.slug;
export const fmtLikes = n => n == null ? '' : (n >= 10000 ? (n / 10000).toFixed(n >= 100000 ? 0 : 1).replace(/\.0$/, '') + '만' : n.toLocaleString('ko-KR'));

/* 용도 판정. 편집에서 고른 용도(ed.uses)가 먼저, 없으면 editorial.json uses[*].match 규칙으로 넓게 찾는다.
   규칙 결과는 "키워드로 찾은" 것이라 정적 용도 페이지에는 싣지 않는다(편집에서 고른 것만).
   파이썬 쪽: pages.py uses_of(). */
const compiled = new WeakMap();
function rulesOf(uses) {
  if (!compiled.has(uses)) {
    compiled.set(uses, Object.entries(uses || {}).map(([k, u]) => {
      const m = u.match || {};
      return {k, re: m.re ? new RegExp(m.re, 'i') : null, fx: m.fx || [], level: m.level || [], full: !!m.full_prompt};
    }));
  }
  return compiled.get(uses);
}
export function usesOf(r, uses) {
  if (r.ed && r.ed.uses && r.ed.uses.length) return r.ed.uses;
  const text = (r.title || '') + ' ' + (r.prompt || '');
  return rulesOf(uses).filter(u =>
    (u.re && u.re.test(text)) || u.fx.some(f => (r.fx || []).includes(f)) ||
    (u.level.length && u.level.includes(r.level) && (!u.full || !r.partial))
  ).map(u => u.k);
}
