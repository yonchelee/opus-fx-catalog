/* 원본(catalog.json)과 편집(editorial.json)을 합친다. 브라우저와 node 시험이 같이 쓴다.
   파이썬 쪽 같은 규칙: skill/opus-fx-scout/scripts/build_site.py 의 merge(). 둘을 함께 고친다.

   규칙
   - 편집 정보는 id 가 정확히 같을 때만 붙는다. 비슷한 slug 로 추정하지 않는다.
   - 원본에서 사라진 id 의 편집 정보는 버리고 orphans 로 알린다.
   - 원본 값은 덮지 않는다. 편집 정보는 r.ed 아래에만 둔다. */

export const FX = [['3d','3D 씬·카메라'],['shader','셰이더·글로우'],['reel','모션 쇼릴'],['game','플레이어블 게임'],['paint','페인터리·손그림'],['ui','UI·제품 데모'],['particles','파티클·입자'],['audio','사운드 동기화'],['liquid','유체·물리'],['cosmic','우주·자연'],['pixel','픽셀아트'],['morph','모핑·트랜지션'],['glitch','글리치·레트로'],['kinetic','키네틱 타이포'],['data','데이터·지도'],['etc','기타']];
export const FXN = Object.fromEntries(FX);
export const CAT = {motion:'모션그래픽', explainer:'설명 영상', '3d':'3D 씬', interactive:'게임·인터랙티브'};
export const LV = {0:'환경 확인 필요', 1:'채팅에서 바로', 2:'Claude Code', 3:'외부 프로그램', 4:'외부 AI·API'};
export const LV_LONG = {
  0: '자동 분류로는 채팅만으로 되는지 확실하지 않습니다. 프롬프트가 영상(MP4) 같은 결과물을 요구해, 원작처럼 만들려면 Claude Code와 렌더링 도구가 필요할 수 있습니다. 채팅 미리보기로는 움직임만 확인될 수 있습니다.',
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

/* 실행 단계(화면 표시용). 편집에서 확인한 작품은 편집 값(ed.env.level, 없으면 자동 분류)을 따른다.
   편집하지 않은 작품이 자동으로 1(채팅)인데 영상 결과물을 요구하면 0(환경 확인 필요).
   규칙은 editorial.json level_check 한 곳. 파이썬 쪽: pages.py level_of(). */
const checkRe = new WeakMap();
export function levelOf(r, check) {
  if (r._level !== undefined) return r._level;
  if (r.ed) return (r.ed.env && LV[r.ed.env.level] && r.ed.env.level > 0) ? r.ed.env.level : r.level;
  if (r.level === 1 && check && check.re) {
    if (!checkRe.has(check)) checkRe.set(check, new RegExp(check.re, 'i'));
    if (checkRe.get(check).test((r.title || '') + ' ' + (r.prompt || ''))) return 0;
  }
  return r.level;
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
  const text = (r.title || '') + ' ' + (r.prompt || '') + ' ' + (r.desc || '') + ' ' + (r.topics || []).join(' ');
  return rulesOf(uses).filter(u =>
    (u.re && u.re.test(text)) || u.fx.some(f => (r.fx || []).includes(f)) ||
    (u.level.length && !isGH(r) && u.level.includes(levelOf(r)) && (!u.full || !r.partial))
  ).map(u => u.k);
}

/* ---------- GitHub 작품·정렬 ---------- */
export const KIND = {effect: '개별 효과', collection: '예제 모음', library: '라이브러리', list: '자료집'};
export const CHECK = {discovered: '자동 발굴', preview: '미리보기 확인'};
export const isGH = r => r.src === 'gh';
export const repoStars = r => (r.repo && r.repo.stars != null ? r.repo.stars : null);

/* 정렬. 대상이 다른 인기 지표(X 좋아요 = 게시물, 저장소 별 = 저장소)는 섞어 합산하지 않는다.
   각 정렬은 그 지표가 없는 작품을 뒤로 보낸다(0 으로 치지 않는다). 같으면 들어온 순서(안정 정렬).
   trend: 비교 기간을 채운 저장소만(r.trend). 나머지는 뒤에 '집계 중'. */
export const SORTS = {
  likes: (a, b) => (b.likes ?? -1) - (a.likes ?? -1),
  stars: (a, b) => (repoStars(b) ?? -1) - (repoStars(a) ?? -1),
  trend: (a, b) => ((b.trend && b.trend.delta) ?? -Infinity) - ((a.trend && a.trend.delta) ?? -Infinity),
  new: (a, b) => (b.first_seen || b.added || '').localeCompare(a.first_seen || a.added || '')
};
export function sortRows(rows, mode) {
  return SORTS[mode] ? rows.slice().sort(SORTS[mode]) : rows.slice();
}
