/* 효과 갤러리 화면. 상태(검색어·용도·필터·정렬)를 하나로 두고, 바뀔 때마다 화면과 주소를 함께 고친다.
   데이터 병합: data.js · 검색: search.js · 생성 페이지: skill/opus-fx-scout/scripts/pages.py */
import {FX, FXN, CAT, LV, LV_LONG, NEED, VERIFY, mergeEditorial, usesOf, verifyOf, levelOf, titleOf, fmtLikes, itemPath, SITE, KIND, CHECK, isGH, repoStars, sortRows} from './data.js';
import {synonymIndex, prepare, search} from './search.js';
import {buildRequest} from './apply.js';
import {shareLink, favs, toggleFav} from './store.js';

const PAGE = 48;
const BASE_TITLE = document.title;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

/* 분석 연결 지점. 지금은 아무 데도 보내지 않는다. 연결하려면 이 함수만 바꾼다.
   원문 프롬프트·사용자가 입력한 문구는 넣지 않는다 — id·개수·용도 키만. */
export function track(event, props = {}) {
  document.dispatchEvent(new CustomEvent('fx:track', {detail: {event, ...props}}));
}

/* 테마는 홈과 같은 키(yl-theme)로 기억한다. 도메인이 달라 홈의 선택이 넘어오지는 않는다. */
$('theme').onclick = () => {
  const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark';
  d.dataset.theme = t;
  try { localStorage.setItem('yl-theme', t); } catch (e) {}
};

let DATA = [], PREP = [], ED = {uses: {}}, SYN = new Map();
const BYID = new Map();
let rows = [], shown = 0;
const S = {q: '', use: '', fx: new Set(), sort: '', src: '', cat: '', lv: '', full: '', vid: '', fav: '', pick: null};
let STATUS = {};

/* ---------- 주소 ↔ 상태 ---------- */
function readURL() {
  const p = new URLSearchParams(location.search);
  S.q = p.get('q') || '';
  S.use = ED.uses[p.get('use')] ? p.get('use') : '';
  S.fx = new Set((p.get('fx') || '').split(',').filter(f => FXN[f]));
  S.sort = ['rel', 'likes', 'stars', 'trend', 'new'].includes(p.get('sort')) ? p.get('sort') : '';
  S.src = ['x', 'gh'].includes(p.get('src')) ? p.get('src') : '';
  S.cat = CAT[p.get('cat')] ? p.get('cat') : '';
  S.lv = ['0', '1', '2'].includes(p.get('lv')) ? p.get('lv') : '';
  S.full = p.get('full') === '1' ? '1' : '';
  S.vid = p.get('vid') === '1' ? '1' : '';
  S.fav = p.get('fav') === '1' ? '1' : '';
  const ids = (p.get('pick') || '').split(',').map(s => s.trim()).filter(Boolean);
  S.pick = ids.length ? ids : null;
}
function stateQuery() {
  const p = new URLSearchParams();
  if (S.pick) p.set('pick', S.pick.join(','));
  if (S.q) p.set('q', S.q);
  if (S.use) p.set('use', S.use);
  if (S.fx.size) p.set('fx', [...S.fx].join(','));
  if (S.sort) p.set('sort', S.sort);
  for (const k of ['src', 'cat', 'lv', 'full', 'vid', 'fav']) if (S[k]) p.set(k, S[k]);
  return p;
}
function writeURL() {
  const qs = stateQuery().toString();
  history.replaceState(history.state, '', location.pathname + (qs ? '?' + qs : ''));
}

/* ---------- 불러오기 ---------- */
function status(html) { $('status').innerHTML = html || ''; }
function load() {
  status('<p>작품 목록을 불러오는 중입니다…</p>');
  Promise.all([
    fetch('catalog.json').then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    fetch('editorial.json').then(r => r.ok ? r.json() : {}).catch(() => ({})),
    /* GitHub 작품·수집 상태는 없거나 못 받아도 X 목록은 보여 준다 */
    fetch('github.json').then(r => r.ok ? r.json() : {items: []}).catch(() => ({items: [], failed: true})),
    fetch('status.json', {cache: 'no-store'}).then(r => r.ok ? r.json() : {}).catch(() => ({}))
  ]).then(([cat, ed, gh, st]) => {
    ED = {uses: {}, items: {}, ...ed};
    STATUS = st || {};
    SYN = synonymIndex(ED.synonyms);
    DATA = mergeEditorial(cat.items.concat(gh.items || []), ED).items
      .sort((a, b) => (b.added || '').localeCompare(a.added || '') || a.id.localeCompare(b.id));
    DATA.forEach(r => { r._level = levelOf(r, ED.level_check); r._uses = usesOf(r, ED.uses); BYID.set(r.id, r); if (!BYID.has(r.slug)) BYID.set(r.slug, r); });
    PREP = DATA.map(r => prepare(r, ED.uses));
    $('total').textContent = DATA.length;
    status('');
    readURL(); syncControls(); buildUses(); buildIndex(); buildFeatured(); buildRecent(); freshness(gh); render();
    openFromURL();
    document.dispatchEvent(new Event('fx:ready'));
  }).catch(() => {
    status('<h3>작품 목록을 불러오지 못했습니다</h3><p>네트워크가 잠시 끊겼거나 파일을 받지 못했습니다.</p><div class="row"><button type="button" id="retry">다시 시도</button></div>');
    $('retry').onclick = load;
  });
}

/* ---------- 컨트롤 ---------- */
function syncControls() {
  $('q').value = S.q; syncSort();
  for (const k of ['src', 'cat', 'lv', 'full', 'vid']) $(k).value = S[k];
  $('fav').checked = !!S.fav;
  document.body.classList.toggle('picking', !!S.pick);
  $('pickbar').classList.toggle('on', !!S.pick);
  if (S.pick) $('pickmsg').textContent = `추천 후보 ${S.pick.length}개`;
}
/* 정렬: 고르지 않았으면 검색 중에는 관련도순, 아니면 X 좋아요순. '관련도순'은 검색 중에만 고를 수 있다. */
const effSort = () => S.sort === 'rel' && !S.q ? 'likes' : (S.sort || (S.q ? 'rel' : 'likes'));
function syncSort() {
  const rel = $('sort').querySelector('option[value="rel"]');
  rel.hidden = rel.disabled = !S.q;
  $('sort').value = effSort();
}
function buildUses() {
  const n = {};
  DATA.forEach(r => r._uses.forEach(u => n[u] = (n[u] || 0) + 1));
  $('uses').innerHTML = Object.entries(ED.uses).map(([k, u]) =>
    `<button type="button" class="use" data-use="${k}" aria-pressed="${S.use === k}">${esc(u.title)}<small>${n[k] || 0}</small></button>`).join('') +
    `<button type="button" class="use" id="favchip" aria-pressed="${!!S.fav}">★ 즐겨찾기<small>${favs().length}</small></button>` +
    '<a class="use" href="use/">용도별 안내 →</a>';
}
function buildIndex() {
  const cnt = {};
  DATA.forEach(r => r.fx.forEach(f => cnt[f] = (cnt[f] || 0) + 1));
  $('index').innerHTML = FX.filter(([k]) => cnt[k]).sort((a, b) => (a[0] === 'etc') - (b[0] === 'etc') || cnt[b[0]] - cnt[a[0]])
    .map(([k, n]) => `<button class="fx" type="button" data-k="${k}" aria-pressed="${S.fx.has(k)}">${n}<span>${cnt[k]}</span></button>`).join('');
}
function featured() {
  return DATA.filter(r => r.ed && r.ed.featured).sort((a, b) => (a.ed.featured_rank || 99) - (b.ed.featured_rank || 99));
}
/* 검색·필터 중에는 대표 효과를 접어 결과가 검색창 바로 아래 오게 한다. */
const narrowing = () => !!(S.q || S.use || S.fx.size || S.src || S.cat || S.lv || S.full || S.vid || S.fav);
function buildFeatured() {
  const f = featured();
  $('featured').hidden = !f.length || narrowing();
  FAVS = new Set(favs());
  $('fgrid').innerHTML = f.slice(0, 6).map(r => card(r)).join('');
  $('ft-all').hidden = f.length <= 6;
}

/* 최근 발견: 카탈로그에 새로 들어온 순(발견일). 누적 인기작에 묻히지 않게 따로 보여 준다.
   최근 상승: 비교 기간(7일)을 채운 저장소가 3개 이상일 때만. */
const rising = () => sortRows(DATA.filter(r => r.trend), 'trend');
function buildRecent() {
  const quiet = narrowing() || !!S.pick;
  const rec = sortRows(DATA, 'new').slice(0, 6), ris = rising();
  $('recent').hidden = quiet || !rec.length;
  $('rgrid').innerHTML = rec.map(r => card(r)).join('');
  $('rising').hidden = quiet || ris.length < 3;
  $('sgrid').innerHTML = ris.slice(0, 6).map(r => card(r)).join('');
}
const when = ts => ts ? new Date(ts).toLocaleString('ko-KR', {month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : '';
/* 마지막 수집 성공 시각. 실패했는데 최신 자료처럼 보이지 않게 실패를 따로 적는다. */
function freshness(gh) {
  const st = STATUS.stages || {}, parts = [];
  for (const [k, name] of [['sync', '출처 동기화'], ['discover', 'GitHub 탐색']]) {
    const s = st[k]; if (!s) continue;
    if (s.ok) parts.push(`${name} ${when(s.last_success)} 성공`);
    else parts.push(`<b class="warnline">${name} 최근 실패(${when(s.last_attempt)})${s.last_success ? ` — ${when(s.last_success)} 자료 기준` : ''}</b>`);
  }
  if (st.publish && st.publish.ok === false) parts.push(`<b class="warnline">공개 반영 실패 기록(${when(st.publish.last_attempt)})</b>`);
  if (gh && gh.failed) parts.push('<b class="warnline">GitHub 작품 목록을 불러오지 못했습니다</b>');
  const lr = STATUS.last_run;
  const run = lr ? ` · 최근 실행(${lr.mode}): 새 후보 ${lr.candidates_new} · 공개 +${lr.published_new} · 보류 +${lr.held_new}${lr.withdrawn ? ` · 철회 ${lr.withdrawn}` : ''}${lr.errors ? ` · <b class="warnline">오류 ${lr.errors}건</b>` : ''}` : '';
  $('fresh').innerHTML = parts.length ? '자료 갱신: ' + parts.join(' · ') + run : '';
}
function changed(why) {
  if (S.pick && why !== 'pick') { S.pick = null; syncControls(); }
  writeURL(); render();
}
$('find').addEventListener('submit', e => {
  e.preventDefault(); S.q = $('q').value.trim(); changed();
  $('all').scrollIntoView({block: 'start', behavior: reduced() ? 'auto' : 'smooth'});
});
$('q').addEventListener('input', () => { S.q = $('q').value.trim(); changed(); });
function setFav(on) { S.fav = on ? '1' : ''; syncControls(); buildUses(); changed(); }
$('fav').addEventListener('change', () => setFav($('fav').checked));
$('uses').addEventListener('click', e => {
  if (e.target.closest('#favchip')) return setFav(!S.fav);
  const b = e.target.closest('.use[data-use]'); if (!b) return;
  S.use = S.use === b.dataset.use ? '' : b.dataset.use;
  [...$('uses').querySelectorAll('[data-use]')].forEach(x => x.setAttribute('aria-pressed', x.dataset.use === S.use));
  changed();
});
$('index').addEventListener('click', e => {
  const b = e.target.closest('.fx'); if (!b) return;
  const k = b.dataset.k; S.fx.has(k) ? S.fx.delete(k) : S.fx.add(k);
  b.setAttribute('aria-pressed', S.fx.has(k)); changed();
});
for (const k of ['src', 'cat', 'lv', 'full', 'vid']) $(k).addEventListener('change', () => { S[k] = $(k).value; changed(); });
$('sort').addEventListener('change', () => { const v = $('sort').value; S.sort = v === (S.q ? 'rel' : 'likes') ? '' : v; changed(); });
$('ftoggle').onclick = () => {
  const open = !$('filters').classList.contains('open');
  $('filters').classList.toggle('open', open); $('ftoggle').setAttribute('aria-expanded', open);
};
$('rc-all').onclick = () => { S.sort = 'new'; changed(); $('all').scrollIntoView({block: 'start'}); };
$('rs-all').onclick = () => { S.sort = 'trend'; changed(); $('all').scrollIntoView({block: 'start'}); };
$('ft-all').onclick = () => {
  S.pick = featured().map(r => r.id); syncControls(); $('pickmsg').textContent = `추천작 ${S.pick.length}개`;
  changed('pick'); $('all').scrollIntoView({block: 'start'});
};
function clearAll() {
  Object.assign(S, {q: '', use: '', src: '', cat: '', lv: '', full: '', vid: '', fav: '', pick: null});
  S.fx.clear(); syncControls(); buildUses(); buildIndex(); changed();
}
$('showall').onclick = clearAll;

/* ---------- 켜진 필터 ---------- */
const OPT = {src: v => v === 'gh' ? 'GitHub 저장소' : 'X 게시물', cat: v => CAT[v], lv: v => ({0: '환경 확인 필요', 1: '채팅에서 바로', 2: 'Claude Code까지'})[v], full: () => '프롬프트 전체 공개', vid: () => '영상 링크 있음', fav: () => '즐겨찾기만'};
function activeChips() {
  const chips = [];
  if (S.q) chips.push(['q', `검색: ${S.q}`]);
  if (S.use) chips.push(['use', `용도: ${ED.uses[S.use]?.title || S.use}`]);
  S.fx.forEach(f => chips.push(['fx:' + f, `효과: ${FXN[f]}`]));
  for (const k of ['src', 'cat', 'lv', 'full', 'vid', 'fav']) if (S[k]) chips.push([k, OPT[k](S[k])]);
  $('active').innerHTML = chips.length ? chips.map(([k, t]) =>
    `<span class="chipx">${esc(t)}<button type="button" data-k="${esc(k)}" aria-label="${esc(t)} 해제">×</button></span>`).join('') +
    (chips.length > 1 ? '<button type="button" class="clearall" id="clearall">전체 해제</button>' : '') : '';
  const n = S.fx.size + ['src', 'cat', 'lv', 'full', 'vid'].filter(k => S[k]).length;
  $('fcount').textContent = n ? ` ${n}` : '';
  $('andnote').innerHTML = S.fx.size > 1 ? `고른 <b>${S.fx.size}개를 모두 포함(AND)</b>한 작품만` : '여러 개 고르면 <b>모두 포함(AND)</b>한 작품만';
}
$('active').addEventListener('click', e => {
  if (e.target.id === 'clearall') return clearAll();
  const b = e.target.closest('button[data-k]'); if (!b) return;
  const k = b.dataset.k;
  if (k === 'q') S.q = ''; else if (k === 'use') S.use = '';
  else if (k.startsWith('fx:')) S.fx.delete(k.slice(3)); else S[k] = '';
  syncControls(); buildUses(); buildIndex(); changed();
});

/* ---------- 목록 ---------- */
function filtered() {
  if (S.pick) return S.pick.map(i => BYID.get(i)).filter(Boolean);
  const F = S.fav ? new Set(favs()) : null;
  let pool = DATA.filter(r => (!F || F.has(r.id)) && (!S.src || (S.src === 'gh') === isGH(r)) && (!S.cat || r.category === S.cat) && (S.lv === '' || (S.lv === '0' ? levelOf(r) === 0 : S.lv === '1' ? levelOf(r) === 1 : [1, 2].includes(levelOf(r)))) && (!S.full || !r.partial) &&
    (!S.vid || r.mp4) && (!S.use || r._uses.includes(S.use)) && [...S.fx].every(f => r.fx.includes(f)));
  const sort = effSort();
  /* 최근 상승은 이력이 모자란 작품을 뒤로(별 많은 순) 보낸다. 관련도순의 같은 점수 안은 X 좋아요순. */
  pool = sort === 'trend' ? sortRows(sortRows(pool, 'stars'), 'trend') : sortRows(pool, sort === 'rel' ? 'likes' : sort);
  if (!S.q) return pool;
  /* 관련도순: 관련도가 먼저, 같으면 X 좋아요순. 다른 정렬을 고르면 검색 결과를 그 정렬로만 늘어놓는다. */
  const order = new Map(pool.map((r, i) => [r, i]));
  const found = search(PREP.filter(p => order.has(p.r)).sort((a, b) => order.get(a.r) - order.get(b.r)), S.q, SYN);
  return sort === 'rel' ? found : found.sort((a, b) => order.get(a) - order.get(b));
}
let FAVS = new Set();
function render() {
  FAVS = new Set(favs());
  syncSort();
  document.body.classList.toggle('searching', !!S.q);
  rows = filtered();
  activeChips();
  $('featured').hidden = !featured().length || narrowing();
  buildRecent();
  const sorted = effSort(), nrise = rising().length;
  $('sortnote').hidden = !['trend', 'stars', 'likes'].includes(sorted);
  $('sortnote').textContent = sorted === 'trend'
    ? (nrise ? `최근 상승: GitHub 저장소 별이 7일 동안 늘어난 수. 비교 기간을 채운 저장소 ${nrise}개만 순위에 넣고, 나머지는 '집계 중'으로 뒤에 둡니다.` : '최근 상승은 별 수 이력이 7일 이상 쌓인 저장소만 계산합니다. 아직 집계 중이라 GitHub 별 많은 순으로 보여 줍니다.')
    : sorted === 'stars' ? 'GitHub 별은 저장소의 인기입니다. 한 저장소에 효과가 여럿이어도 각 효과가 받은 별이 아닙니다. X 게시물 작품은 뒤에 둡니다.'
    : 'X 좋아요는 원본 X 게시물의 인기입니다. GitHub 작품은 뒤에 둡니다.';
  $('all-h').textContent = S.q ? `‘${S.q}’ 검색 결과` : S.pick ? '추천 후보' : narrowing() ? '조건에 맞는 효과' : '전체 효과';
  $('count').textContent = narrowing() || S.pick ? `${rows.length}개 · 전체 ${DATA.length}` : `${rows.length} / ${DATA.length}`;
  $('grid').innerHTML = '';
  if (!rows.length && S.fav && !favs().length) {
    status('<h3>아직 즐겨찾기한 작품이 없습니다</h3><p>작품을 열고 ☆ 즐겨찾기를 누르면 여기에 모입니다. 즐겨찾기는 이 브라우저에만 저장됩니다.</p><div class="row"><button type="button" data-fix="all">전체 작품 보기</button></div>');
  } else if (!rows.length) {
    track('search_empty', {count: 0, use: S.use || undefined});
    status(`<h3>조건에 맞는 작품이 없습니다</h3>
      ${S.q ? `<p>“${esc(S.q)}” 대신 더 짧은 말이나 영어로 찾아보세요. 예: 지도 → map, 로고 → logo.</p>` : ''}
      <p>효과 모양을 여러 개 고르면 모두 포함한 작품만 나옵니다. 하나씩 줄여 보세요.</p>
      <div class="row">${S.q ? '<button type="button" data-fix="q">검색어 지우기</button>' : ''}<button type="button" data-fix="all">필터 모두 해제</button></div>`);
  } else status('');
  shown = 0; draw();
}
$('status').addEventListener('click', e => {
  const b = e.target.closest('[data-fix]'); if (!b) return;
  if (b.dataset.fix === 'q') { S.q = ''; syncControls(); changed(); } else clearAll();
});
function draw() {
  $('grid').insertAdjacentHTML('beforeend', rows.slice(shown, shown + PAGE).map((r, i) => card(r, S.pick ? shown + i + 1 : 0)).join(''));
  shown += PAGE; $('more').hidden = shown >= rows.length;
}
$('more').onclick = draw;

function thumb(r) {
  return r.thumb
    ? `<img src="${esc(r.thumb)}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fallback="1">`
    : '<div class="none">미리보기 없음</div>';
}
const stars = n => n == null ? '' : n.toLocaleString('ko-KR');
function ghCard(r, num) {
  const ed = r.ed || {}, v = verifyOf(r), repo = r.repo || {};
  const status = ed.verify && ed.verify.status && ed.verify.status !== 'unverified' ? VERIFY[v].label : CHECK[r.check] || '자동 발굴';
  return `<button class="card" type="button" data-id="${esc(r.id)}">
    <div class="media">${num ? `<span class="num">${num}</span>` : ''}${ed.featured ? '<span class="pin">추천</span>' : ''}${FAVS.has(r.id) ? '<span class="fav-on" aria-label="즐겨찾기한 작품">★</span>' : ''}${thumb(r)}${r.demo_url ? '<span class="play">데모 링크</span>' : ''}</div>
    <div class="body">
      <div class="title">${esc(titleOf(r))}</div>
      <div class="orig">${esc(r.desc || r.slug)}</div>
      <div class="useline">GitHub · ${esc(KIND[r.kind] || r.kind)}</div>
      <div class="badges"><span class="b env${levelOf(r)}" title="${esc(r.env_text || LV_LONG[levelOf(r)])}">${LV[levelOf(r)]}</span>
        <span class="b partial">${r.has_prompt ? '프롬프트 파일·코드' : '프롬프트 없음·코드 제공'}</span>
        <span class="b v-${status === '자동 발굴' ? 'unverified' : 'partial'}" title="자동 발굴: 검색으로 찾아 조건을 확인 · 미리보기 확인: 미리보기나 데모 링크가 열림 (재현 확인 아님)">${esc(status)}</span></div>
      <div class="foot"><span>@${esc(r.author)}</span>${repo.stars != null ? `<span class="xlikes" title="GitHub 저장소의 별 수 (${esc(when(repo.stars_at))} 측정) — 이 작품이 따로 받은 수가 아닙니다">저장소 ★ ${stars(repo.stars)}${r.trend ? ` · 7일 +${r.trend.delta}` : ''}</span>` : ''}</div>
    </div></button>`;
}
function card(r, num) {
  if (isGH(r)) return ghCard(r, num);
  const ed = r.ed || {}, u = r._uses[0], v = verifyOf(r);
  const useline = u ? (ED.uses[u]?.title || u) : (CAT[r.category] || '');
  return `<button class="card" type="button" data-id="${esc(r.id)}">
    <div class="media">${num ? `<span class="num">${num}</span>` : ''}${ed.featured ? '<span class="pin">추천</span>' : ''}${FAVS.has(r.id) ? '<span class="fav-on" aria-label="즐겨찾기한 작품">★</span>' : ''}${thumb(r)}${r.mp4 ? '<span class="play">▶ 영상 링크</span>' : ''}</div>
    <div class="body">
      <div class="title">${esc(titleOf(r))}</div>
      ${ed.title_ko && r.title ? `<div class="orig">${esc(r.title)}</div>` : ''}
      <div class="useline">${esc(useline)}</div>
      <div class="badges"><span class="b env${levelOf(r)}" title="${esc(LV_LONG[levelOf(r)])}">${LV[levelOf(r)]}</span>
        <span class="b${r.partial ? ' partial' : ''}">${r.partial ? '프롬프트 일부' : '프롬프트 전체'}</span>
        <span class="b v-${v}">${VERIFY[v].label}</span></div>
      <div class="foot"><span>@${esc(r.author)}</span>${r.likes != null ? `<span class="xlikes" title="원본 X 게시물의 좋아요 수 — 이 사이트의 평가가 아닙니다">X ♥ ${fmtLikes(r.likes)}</span>` : ''}</div>
    </div></button>`;
}
/* 썸네일 실패 → 대체 화면 (inline onerror 대신 위임) */
document.addEventListener('error', e => {
  const im = e.target;
  if (im.tagName === 'IMG' && im.dataset.fallback) {
    const d = document.createElement('div'); d.className = 'none'; d.textContent = '미리보기를 불러오지 못했습니다';
    im.replaceWith(d);
  }
}, true);

/* 데스크톱 호버 미리보기 — 한 번에 하나만 재생한다. 터치 기기는 누르면 상세가 열린다. */
let hovering = null;
function stopHover() {
  if (!hovering) return;
  hovering.querySelector('.media video')?.remove();
  const im = hovering.querySelector('img[data-src]'); if (im) { im.src = im.dataset.src; delete im.dataset.src; }
  hovering = null;
}
document.addEventListener('pointerover', e => {
  const c = e.target.closest('.card');
  if (!c || c === hovering || e.pointerType !== 'mouse' || reduced()) return;
  stopHover(); hovering = c;
  const r = BYID.get(c.dataset.id), m = c.querySelector('.media');
  if (r.mp4) {
    const v = Object.assign(document.createElement('video'), {src: r.mp4, muted: true, loop: true, playsInline: true, autoplay: true});
    v.setAttribute('referrerpolicy', 'no-referrer'); v.onerror = () => v.remove(); m.appendChild(v);
  } else if (r.preview) {
    const p = new Image(); p.referrerPolicy = 'no-referrer';
    p.onload = () => { const im = m.querySelector('img'); if (im && hovering === c) { im.dataset.src = im.src; im.src = r.preview; } };
    p.src = r.preview;
  }
});
document.addEventListener('pointerout', e => {
  const c = e.target.closest('.card'); if (c && c === hovering && !c.contains(e.relatedTarget)) stopHover();
});
document.addEventListener('click', e => {
  const c = e.target.closest('.card'); if (c) openItem(BYID.get(c.dataset.id), c);
});

/* ---------- 상세 ---------- */
/* 작품 주소: ?item=<id>. 열 때 기록(pushState)해서 뒤로가기가 창을 닫게 한다.
   직접 들어온 주소(새로고침 포함)는 기록을 더하지 않고, 닫을 때 주소에서 item 만 지운다. */
let opener = null, pushed = null, popClosing = false, favDirty = false;
const itemParam = () => new URLSearchParams(location.search).get('item');
function urlWithItem(id) {
  const p = stateQuery(); if (id) p.set('item', id);
  const qs = p.toString(); return location.pathname + (qs ? '?' + qs : '');
}
export function shareURL(r) {
  return r.ed && r.ed.guide ? SITE + itemPath(r.id) : SITE + '?item=' + encodeURIComponent(r.id);
}
function openFromURL() {
  const id = itemParam(); if (!id) return;
  const r = BYID.get(id);
  if (r) openItem(r, null, true);
  else { status(`<h3>찾는 작품이 없습니다</h3><p>주소의 작품(${esc(id)})이 목록에서 빠졌거나 주소가 바뀌었습니다. 아래 전체 목록에서 찾아 주세요.</p>`);
    history.replaceState(null, '', urlWithItem(null)); }
}
window.addEventListener('popstate', () => {
  const id = itemParam(), dlg = $('dlg');
  if (id && !dlg.open) { const r = BYID.get(id); if (r) openItem(r, null, true); }
  else if (!id && dlg.open) { popClosing = true; dlg.close(); }
});
function openItem(r, from, fromURL) {
  if (!r) return;
  stopHover(); opener = from || document.activeElement;
  if (!fromURL) { history.pushState({fxItem: r.id}, '', urlWithItem(r.id)); pushed = r.id; }
  document.title = titleOf(r) + ' — 효과 갤러리';
  $('dlg').innerHTML = detail(r);
  bindDetail(r);
  $('dlg').showModal();
  $('dtitle').focus();
  track('item_view', {id: r.id});
}
function media(r) {
  const src = r.mp4_hd || r.mp4, poster = r.thumb || '';
  const link = r.post_url ? `<a href="${esc(r.post_url)}" target="_blank" rel="noopener">원본 게시물에서 보기</a>` : '';
  const none = `<div class="none" hidden><span>미리보기를 불러오지 못했습니다.</span>${link}</div>`;
  /* 영상은 저절로 재생하지 않는다(여러 개 동시 재생 방지, 데이터 절약). 사용자가 누르면 재생. */
  if (src) return `<video controls muted playsinline loop preload="metadata" poster="${esc(poster)}" src="${esc(src)}" data-media="1"></video>${none}`;
  if (r.preview || r.thumb) return `<img src="${esc(r.preview || r.thumb)}" alt="" referrerpolicy="no-referrer" data-media="1">${none}`;
  return none.replace(' hidden', '');
}
function sec(n, title, body) { return body ? `<section class="dsec"><h3><span class="n">${n}</span>${title}</h3>${body}</section>` : ''; }
function ghDetail(r) {
  const ed = r.ed || {}, g = ed.guide || {}, repo = r.repo || {}, v = verifyOf(r), vr = ed.verify || {};
  const uses = r._uses.map(u => ED.uses[u]?.title || u);
  const trend = r.trend ? `최근 7일 +${r.trend.delta} (${esc(when(r.trend.from))} → ${esc(when(r.trend.to))})` : '최근 상승: 집계 중 (별 수 이력이 7일 이상 쌓이면 계산)';
  return `<button class="close" type="button" id="dclose" aria-label="닫기">×</button>
  <div class="dmedia">${media(r)}</div>
  <div class="dbody">
    <div class="dhead">
      <div class="meta"><span>@${esc(r.author)}</span><span>GitHub · ${esc(KIND[r.kind] || r.kind)}</span><span>발견 ${esc((r.first_seen || '').slice(0, 10))}</span>${repo.stars != null ? `<span title="GitHub 저장소의 별 수 — 이 작품이 따로 받은 수가 아닙니다">저장소 ★ ${stars(repo.stars)}</span>` : ''}</div>
      <h2 tabindex="-1" id="dtitle">${esc(titleOf(r))}</h2>
      <div class="orig">${esc(r.slug)}</div>
      <div class="badges" style="margin-top:8px"><span class="b env${levelOf(r)}">${LV[levelOf(r)]}</span>
        <span class="b partial">${r.has_prompt ? '프롬프트 파일·코드' : '프롬프트 없음·코드 제공'}</span>
        <span class="b v-unverified">${esc(CHECK[r.check] || '자동 발굴')}</span>${v !== 'unverified' ? `<span class="b v-${v}">${VERIFY[v].label}</span>` : ''}</div>
    </div>
    <div class="acts" id="acts"></div>
    ${sec('1', '어떤 효과인가', `<p>${esc(g.what || ed.summary_ko || r.desc || '저장소 설명이 없습니다.')}</p>${(r.topics || []).length ? `<p class="note">주제: ${esc(r.topics.join(', '))}</p>` : ''}${g.what ? '' : '<p class="note">저장소 설명을 그대로 옮겼습니다. 편집 설명은 아직 없습니다.</p>'}`)}
    ${sec('2', '어디에 쓰면 좋은가', g.where ? `<p>${esc(g.where)}</p>` : (uses.length ? `<p>${esc(uses.join(', '))} <span class="note">(키워드로 자동 분류)</span></p>` : ''))}
    ${sec('3', '필요한 것', `<ul><li>${esc(r.env_text || '실행 방법은 저장소 README 참고')}</li><li>라이선스: ${esc(repo.license || '표시 없음 — 코드 재사용 전 원작자 확인 필요')}</li></ul>`)}
    ${sec('4', '실행 순서', g.steps && g.steps.length ? `<ol>${g.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>` : '')}
    ${sec('5', '바꾸면 좋은 변수', g.variables && g.variables.length ? `<div class="vars">${g.variables.map(x => `<div><b>${esc(x.name)}</b><span>${esc(x.hint || '')}</span></div>`).join('')}</div>` : '')}
    ${sec('6', '원본 프롬프트', r.has_prompt && r.prompt_url
      ? `<p>저장소에 프롬프트 파일이 있습니다. 내용은 원본에서 확인하세요: <a href="${esc(r.prompt_url)}" target="_blank" rel="noopener">프롬프트 파일 열기</a></p>`
      : '<p><b>원본 프롬프트 없음 · 코드 제공</b> — 이 작품은 코드로 공개됐습니다. 이 사이트는 프롬프트를 만들어 넣지 않습니다. 아래 7번 요청문은 사이트가 만든 것이며 원본이 아닙니다.</p>')}
    <div id="applyslot"></div>
    ${sec('8', '출처와 확인 상태', `<ul>
      <li>원작자 @${esc(r.author)} · <a href="${esc(repo.url)}" target="_blank" rel="noopener">저장소</a>${r.demo_url ? ` · <a href="${esc(r.demo_url)}" target="_blank" rel="noopener">데모</a>` : ''}${repo.gone ? ' · <b class="warnline">지금 저장소에 접근할 수 없습니다</b>' : ''}</li>
      <li>저장소 ★ ${stars(repo.stars)} (${esc(when(repo.stars_at))} 측정) · ${trend}</li>
      <li>저장소 생성 ${esc((repo.created_at || '').slice(0, 10))} · 카탈로그 최초 발견 ${esc((r.first_seen || '').slice(0, 10))} · 마지막 확인 ${esc((r.last_checked || '').slice(0, 10))}</li>
      <li>상태: <b>${esc(CHECK[r.check] || '자동 발굴')}</b>${r.check === 'preview' ? ' — 미리보기나 데모 링크가 열리는 것만 확인했습니다. 실제로 실행해 재현한 것은 아닙니다.' : ' — 검색으로 찾아 공개 조건(관련성·미리보기 또는 데모·코드·라이선스)을 자동 확인했습니다.'}${v !== 'unverified' ? ` · 재현: <b>${VERIFY[v].label}</b> ${esc(vr.note || '')}` : ''}</li>
      ${(r.x_ids || []).length ? `<li>같은 작품의 X 게시물: ${r.x_ids.map(id => `<a href="?item=${encodeURIComponent(id)}">${esc(id)}</a>`).join(', ')}</li>` : ''}
      <li class="note">코드·미리보기의 권리는 원작자에게 있습니다. 작품 ID ${esc(r.id)}</li></ul>`)}
  </div>`;
}
function detail(r) {
  if (isGH(r)) return ghDetail(r);
  const ed = r.ed || {}, g = ed.guide || {}, env = ed.env || {}, v = verifyOf(r), vr = ed.verify || {};
  const needs = [...(env.tools || []), ...(r.needs || []).map(n => NEED[n] || n)];
  const uses = r._uses.map(u => ED.uses[u]?.title || u);
  return `<button class="close" type="button" id="dclose" aria-label="닫기">×</button>
  <div class="dmedia">${media(r)}</div>
  <div class="dbody">
    <div class="dhead">
      <div class="meta"><span>@${esc(r.author)}</span><span>${CAT[r.category] || ''}</span><span>수집 ${esc(r.added || '')}</span>${r.likes != null ? `<span title="원본 X 게시물의 좋아요 수 — 이 사이트의 평가가 아닙니다">X ♥ ${fmtLikes(r.likes)}</span>` : ''}</div>
      <h2 tabindex="-1" id="dtitle">${esc(titleOf(r))}</h2>
      ${ed.title_ko && r.title ? `<div class="orig">${esc(r.title)}</div>` : ''}
      <div class="badges" style="margin-top:8px"><span class="b env${levelOf(r)}">${LV[levelOf(r)]}</span>
        <span class="b${r.partial ? ' partial' : ''}">${r.partial ? '프롬프트 일부 공개' : '프롬프트 전체 공개'}</span>
        <span class="b v-${v}">${VERIFY[v].label}</span></div>
    </div>
    <div class="acts" id="acts"></div>
    ${sec('1', '어떤 효과인가', g.what || ed.summary_ko ? `<p>${esc(g.what || ed.summary_ko)}</p>` : `<p>${esc(r.fx.filter(f => f !== 'etc').map(f => FXN[f]).join(' · ') || CAT[r.category] || '')}</p><p class="note">편집 설명이 아직 없는 작품입니다. 원본 프롬프트와 영상으로 판단해 주세요.</p>`)}
    ${sec('2', '어디에 쓰면 좋은가', g.where ? `<p>${esc(g.where)}</p>${ed.featured_reason ? `<p class="note">추천 이유: ${esc(ed.featured_reason)}</p>` : ''}` : (uses.length ? `<p>${esc(uses.join(', '))}${ed.uses ? '' : ' <span class="note">(키워드로 자동 분류)</span>'}</p>` : ''))}
    ${sec('3', '필요한 것', `<ul><li>${esc(LV_LONG[levelOf(r)])}</li>${needs.map(n => `<li>${esc(n)}</li>`).join('')}${env.paid ? `<li>유료: ${esc(env.paid)}</li>` : ''}${env.assets ? `<li>내 자료: ${esc(env.assets)}</li>` : ''}</ul>`)}
    ${sec('4', '실행 순서', g.steps && g.steps.length ? `<ol>${g.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>` : '')}
    ${sec('5', '바꾸면 좋은 변수', g.variables && g.variables.length ? `<div class="vars">${g.variables.map(x => `<div><b>${esc(x.name)}</b><span>${esc(x.hint || '')}</span></div>`).join('')}</div>` : '')}
    ${sec('6', '원본 프롬프트', `${r.partial ? '<p class="warn">원작자가 프롬프트 일부만 공개했습니다. 아래는 전체가 아닙니다.</p>' : ''}<pre class="prompt" id="dprompt">${esc(r.prompt || '(프롬프트 없음)')}</pre>`)}
    <div id="applyslot"></div>
    ${sec('8', '출처와 검증', `<ul>
      <li>원작자 @${esc(r.author)}${r.post_url ? ` · <a href="${esc(r.post_url)}" target="_blank" rel="noopener">원본 게시물</a>` : ''}${r.prompt_url ? ` · <a href="${esc(r.prompt_url)}" target="_blank" rel="noopener">프롬프트 출처</a>` : ''}</li>
      <li>검증: <b>${VERIFY[v].label}</b> — ${esc(vr.note || VERIFY[v].note)}${vr.date ? ` (${esc(vr.date)}${vr.env ? ', ' + esc(vr.env) : ''})` : ''}${vr.evidence ? ` · <a href="${esc(vr.evidence)}" target="_blank" rel="noopener">만들어 본 결과 화면</a>` : ''}</li>
      ${vr.missing ? `<li>부족한 조건: ${esc(vr.missing)}</li>` : ''}
      ${DATA.filter(x => isGH(x) && (x.x_ids || []).includes(r.id)).map(x => `<li>같은 작품의 GitHub 저장소: <a href="?item=${encodeURIComponent(x.id)}">${esc(x.slug)}</a></li>`).join('')}
      <li class="note">영상·프롬프트의 권리는 원작자에게 있습니다. 작품 ID ${esc(r.id)}</li></ul>`)}
  </div>`;
}
/* ---------- 적용용 요청문 (템플릿. 외부 AI 를 부르지 않는다) ---------- */
function applyBlock(r) {
  const uses = r._uses.map(u => ED.uses[u]?.title || u);
  const env = levelOf(r) === 1 ? 'chat' : 'code';
  return sec('7', '적용용 요청문 만들기', `
    <p class="note">${isGH(r) ? '사이트가 만든 요청문입니다(원본 프롬프트가 아님). 저장소 주소와 구현할 효과, 실행 환경을 담습니다. ' : ''}아래 칸을 채우면 내 작업에 맞춘 요청문이 만들어집니다. 틀에 값을 채운 것이라 원본과 같은 결과를 보장하지 않습니다. 입력한 내용은 이 화면 밖으로 보내지 않습니다.</p>
    <div class="apply">
      <label>용도<input id="ap-use" list="ap-uses" placeholder="${esc(uses[0] || '예: 랜딩 페이지 첫 화면')}"><datalist id="ap-uses">${Object.values(ED.uses).map(u => `<option value="${esc(u.title)}">`).join('')}</datalist></label>
      <label>들어갈 문구<input id="ap-text" placeholder="예: 우리 카페 그랜드 오픈"></label>
      <label>색상<input id="ap-color" placeholder="예: 크림 바탕에 진한 주황"></label>
      <label>실행 환경<select id="ap-env">${Object.entries({chat: 'Claude 채팅 (HTML 한 장)', code: 'Claude Code (프로젝트)', video: '영상 파일 (MP4)'}).map(([k, t]) => `<option value="${k}"${k === env ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
    </div>
    <pre class="prompt" id="ap-out" aria-live="polite"></pre>
    <div class="acts"><button type="button" class="btn primary" id="cp-req" data-id="${esc(r.id)}">적용용 요청문 복사</button></div>`);
}
function bindApply(r) {
  const uses = r._uses.map(u => ED.uses[u]?.title || u);
  const upd = () => { $('ap-out').textContent = buildRequest(r, {use: $('ap-use').value.trim(), text: $('ap-text').value.trim(), color: $('ap-color').value.trim(), env: $('ap-env').value}, uses); };
  ['ap-use', 'ap-text', 'ap-color', 'ap-env'].forEach(id => $(id).addEventListener('input', upd));
  upd();
  $('cp-req').onclick = e => copyText($('ap-out').textContent, e.currentTarget, 'copy_request');
}

function flash(btn, text) { const o = btn.textContent; btn.textContent = text; setTimeout(() => btn.textContent = o, 1600); }
function copyText(t, btn, ev) {
  const o = btn.textContent;
  navigator.clipboard.writeText(t).then(() => { btn.textContent = '복사됨'; track(ev, {id: btn.dataset.id}); })
    .catch(() => { btn.textContent = '복사 실패 — 직접 선택해 주세요'; })
    .finally(() => setTimeout(() => btn.textContent = o, 1600));
}
function bindDetail(r) {
  /* GitHub 코드 작품에는 원본 프롬프트가 없으므로 복사 버튼 대신 저장소·데모 링크를 둔다 */
  $('acts').innerHTML = isGH(r)
    ? `<a class="btn primary" href="${esc(r.repo.url)}" target="_blank" rel="noopener">저장소 열기</a>${r.demo_url ? `<a class="btn" href="${esc(r.demo_url)}" target="_blank" rel="noopener">데모 열기</a>` : ''}`
    : `<button type="button" class="btn primary" id="cp-orig" data-id="${esc(r.id)}">${r.partial ? '원본 프롬프트 복사 (일부 공개)' : '원본 프롬프트 복사'}</button>`;
  $('acts').insertAdjacentHTML('beforeend', `<button type="button" class="btn" id="favbtn" aria-pressed="false"></button><button type="button" class="btn" id="share">공유</button>${r.ed && r.ed.guide ? `<a class="btn" href="${itemPath(r.id)}">작품 페이지</a>` : ''}`);
  if ($('cp-orig')) $('cp-orig').onclick = e => copyText(r.prompt || '', e.currentTarget, 'copy_original');
  const paintFav = () => { const on = favs().includes(r.id); $('favbtn').setAttribute('aria-pressed', on); $('favbtn').textContent = on ? '★ 즐겨찾기됨' : '☆ 즐겨찾기'; };
  paintFav();
  $('favbtn').onclick = () => { const on = toggleFav(r.id); paintFav(); track('favorite', {id: r.id, on}); favDirty = true; };
  $('acts').insertAdjacentHTML('afterend', '<p class="note">즐겨찾기는 로그인 없이 이 브라우저에만 저장됩니다. 다른 기기·브라우저에서는 보이지 않습니다.</p>');
  $('share').onclick = async e => { const how = await shareLink({title: titleOf(r), url: shareURL(r)}, e.currentTarget, flash); track('share', {id: r.id, how}); };
  $('applyslot').outerHTML = applyBlock(r);
  bindApply(r);
  const m = $('dlg').querySelector('[data-media]');
  /* 창을 닫으며 내용을 지울 때도 영상이 늦게 error 를 보낸다 — 그때는 대체 문구 칸이 없다. */
  if (m) m.addEventListener('error', () => { const box = m.parentNode; m.remove(); const n = box && box.querySelector('.none'); if (n) n.hidden = false; });
  $('dclose').onclick = () => $('dlg').close();
}
$('dlg').addEventListener('close', () => {
  $('dlg').querySelector('video')?.pause();
  $('dlg').innerHTML = '';
  document.title = BASE_TITLE;
  if (popClosing) popClosing = false;
  else if (itemParam()) {
    if (pushed && history.state && history.state.fxItem === pushed) history.back();
    else history.replaceState(null, '', urlWithItem(null));
  }
  pushed = null;
  if (favDirty) {
    /* 별 표시를 고치려고 다시 그리면 누른 카드가 바뀐다. 같은 작품 카드를 찾아 포커스를 돌려준다. */
    favDirty = false;
    const id = opener && opener.dataset ? opener.dataset.id : null, inFeat = !!(opener && opener.closest && opener.closest('#fgrid'));
    const y = scrollY; buildUses(); buildFeatured(); render(); scrollTo(0, y);
    if (id) opener = document.querySelector(`${inFeat ? '#fgrid' : '#grid'} .card[data-id="${CSS.escape(id)}"]`) || opener;
  }
  if (opener && document.contains(opener)) opener.focus({preventScroll: true});
});
$('dlg').addEventListener('click', e => { if (e.target === $('dlg')) $('dlg').close(); });

load();
