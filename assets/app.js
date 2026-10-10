/* 효과 갤러리 화면. 상태(검색어·용도·필터·정렬)를 하나로 두고, 바뀔 때마다 화면과 주소를 함께 고친다.
   데이터 병합: data.js · 검색: search.js · 생성 페이지: skill/opus-fx-scout/scripts/pages.py */
import {FX, FXN, CAT, LV, LV_LONG, NEED, VERIFY, mergeEditorial, usesOf, verifyOf, titleOf, fmtLikes} from './data.js';
import {synonymIndex, prepare, search} from './search.js';

const PAGE = 48;
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
const S = {q: '', use: '', fx: new Set(), sort: 'likes', cat: '', lv: '', full: '', vid: '', pick: null};

/* ---------- 주소 ↔ 상태 ---------- */
function readURL() {
  const p = new URLSearchParams(location.search);
  S.q = p.get('q') || '';
  S.use = ED.uses[p.get('use')] ? p.get('use') : '';
  S.fx = new Set((p.get('fx') || '').split(',').filter(f => FXN[f]));
  S.sort = p.get('sort') === 'new' ? 'new' : 'likes';
  S.cat = CAT[p.get('cat')] ? p.get('cat') : '';
  S.lv = ['1', '2'].includes(p.get('lv')) ? p.get('lv') : '';
  S.full = p.get('full') === '1' ? '1' : '';
  S.vid = p.get('vid') === '1' ? '1' : '';
  const ids = (p.get('pick') || '').split(',').map(s => s.trim()).filter(Boolean);
  S.pick = ids.length ? ids : null;
}
function stateQuery() {
  const p = new URLSearchParams();
  if (S.pick) p.set('pick', S.pick.join(','));
  if (S.q) p.set('q', S.q);
  if (S.use) p.set('use', S.use);
  if (S.fx.size) p.set('fx', [...S.fx].join(','));
  if (S.sort !== 'likes') p.set('sort', S.sort);
  for (const k of ['cat', 'lv', 'full', 'vid']) if (S[k]) p.set(k, S[k]);
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
    fetch('editorial.json').then(r => r.ok ? r.json() : {}).catch(() => ({}))
  ]).then(([cat, ed]) => {
    ED = {uses: {}, items: {}, ...ed};
    SYN = synonymIndex(ED.synonyms);
    DATA = mergeEditorial(cat.items, ED).items
      .sort((a, b) => (b.added || '').localeCompare(a.added || '') || a.id.localeCompare(b.id));
    DATA.forEach(r => { r._uses = usesOf(r, ED.uses); BYID.set(r.id, r); if (!BYID.has(r.slug)) BYID.set(r.slug, r); });
    PREP = DATA.map(r => prepare(r, ED.uses));
    $('total').textContent = DATA.length;
    status('');
    readURL(); syncControls(); buildUses(); buildIndex(); buildFeatured(); render();
    document.dispatchEvent(new Event('fx:ready'));
  }).catch(() => {
    status('<h3>작품 목록을 불러오지 못했습니다</h3><p>네트워크가 잠시 끊겼거나 파일을 받지 못했습니다.</p><div class="row"><button type="button" id="retry">다시 시도</button></div>');
    $('retry').onclick = load;
  });
}

/* ---------- 컨트롤 ---------- */
function syncControls() {
  $('q').value = S.q; $('sort').value = S.sort;
  for (const k of ['cat', 'lv', 'full', 'vid']) $(k).value = S[k];
  document.body.classList.toggle('picking', !!S.pick);
  $('pickbar').classList.toggle('on', !!S.pick);
  if (S.pick) $('pickmsg').textContent = `추천 후보 ${S.pick.length}개`;
}
function buildUses() {
  const n = {};
  DATA.forEach(r => r._uses.forEach(u => n[u] = (n[u] || 0) + 1));
  $('uses').innerHTML = Object.entries(ED.uses).map(([k, u]) =>
    `<button type="button" class="use" data-use="${k}" aria-pressed="${S.use === k}">${esc(u.title)}<small>${n[k] || 0}</small></button>`).join('');
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
function buildFeatured() {
  const f = featured();
  $('featured').hidden = !f.length;
  $('fgrid').innerHTML = f.slice(0, 6).map(r => card(r)).join('');
  $('ft-all').hidden = f.length <= 6;
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
$('uses').addEventListener('click', e => {
  const b = e.target.closest('.use'); if (!b) return;
  S.use = S.use === b.dataset.use ? '' : b.dataset.use;
  [...$('uses').children].forEach(x => x.setAttribute('aria-pressed', x.dataset.use === S.use));
  changed();
});
$('index').addEventListener('click', e => {
  const b = e.target.closest('.fx'); if (!b) return;
  const k = b.dataset.k; S.fx.has(k) ? S.fx.delete(k) : S.fx.add(k);
  b.setAttribute('aria-pressed', S.fx.has(k)); changed();
});
for (const k of ['sort', 'cat', 'lv', 'full', 'vid']) $(k).addEventListener('change', () => { S[k] = $(k).value; changed(); });
$('ftoggle').onclick = () => {
  const open = !$('filters').classList.contains('open');
  $('filters').classList.toggle('open', open); $('ftoggle').setAttribute('aria-expanded', open);
};
$('ft-all').onclick = () => {
  S.pick = featured().map(r => r.id); syncControls(); $('pickmsg').textContent = `추천작 ${S.pick.length}개`;
  changed('pick'); $('all').scrollIntoView({block: 'start'});
};
function clearAll() {
  Object.assign(S, {q: '', use: '', cat: '', lv: '', full: '', vid: '', pick: null});
  S.fx.clear(); syncControls(); buildUses(); buildIndex(); changed();
}
$('showall').onclick = clearAll;

/* ---------- 켜진 필터 ---------- */
const OPT = {cat: v => CAT[v], lv: v => v === '1' ? '채팅에서 바로' : 'Claude Code까지', full: () => '프롬프트 전체 공개', vid: () => '영상 링크 있음'};
function activeChips() {
  const chips = [];
  if (S.q) chips.push(['q', `검색: ${S.q}`]);
  if (S.use) chips.push(['use', `용도: ${ED.uses[S.use]?.title || S.use}`]);
  S.fx.forEach(f => chips.push(['fx:' + f, `효과: ${FXN[f]}`]));
  for (const k of ['cat', 'lv', 'full', 'vid']) if (S[k]) chips.push([k, OPT[k](S[k])]);
  $('active').innerHTML = chips.length ? chips.map(([k, t]) =>
    `<span class="chipx">${esc(t)}<button type="button" data-k="${esc(k)}" aria-label="${esc(t)} 해제">×</button></span>`).join('') +
    (chips.length > 1 ? '<button type="button" class="clearall" id="clearall">전체 해제</button>' : '') : '';
  const n = S.fx.size + ['cat', 'lv', 'full', 'vid'].filter(k => S[k]).length;
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
  const lv = +S.lv;
  let pool = DATA.filter(r => (!S.cat || r.category === S.cat) && (!lv || r.level <= lv) && (!S.full || !r.partial) &&
    (!S.vid || r.mp4) && (!S.use || r._uses.includes(S.use)) && [...S.fx].every(f => r.fx.includes(f)));
  if (S.sort === 'likes') pool = pool.slice().sort((a, b) => (b.likes ?? -1) - (a.likes ?? -1));
  if (!S.q) return pool;
  /* 검색어가 있으면 관련도가 먼저, 같은 관련도 안에서는 고른 정렬 */
  const order = new Map(pool.map((r, i) => [r, i]));
  const prep = PREP.filter(p => order.has(p.r)).sort((a, b) => order.get(a.r) - order.get(b.r));
  return search(prep, S.q, SYN);
}
function render() {
  rows = filtered();
  activeChips();
  $('count').textContent = `${rows.length} / ${DATA.length}`;
  $('grid').innerHTML = '';
  if (!rows.length) {
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
function card(r, num) {
  const ed = r.ed || {}, u = r._uses[0], v = verifyOf(r);
  const useline = u ? (ED.uses[u]?.title || u) : (CAT[r.category] || '');
  return `<button class="card" type="button" data-id="${esc(r.id)}">
    <div class="media">${num ? `<span class="num">${num}</span>` : ''}${ed.featured ? '<span class="pin">추천</span>' : ''}${thumb(r)}${r.mp4 ? '<span class="play">▶ 영상 링크</span>' : ''}</div>
    <div class="body">
      <div class="title">${esc(titleOf(r))}</div>
      ${ed.title_ko && r.title ? `<div class="orig">${esc(r.title)}</div>` : ''}
      <div class="useline">${esc(useline)}</div>
      <div class="badges"><span class="b env${r.level}">${LV[r.level]}</span>
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
let opener = null;
function openItem(r, from) {
  if (!r) return;
  stopHover(); opener = from || document.activeElement;
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
function detail(r) {
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
      <div class="badges" style="margin-top:8px"><span class="b env${r.level}">${LV[r.level]}</span>
        <span class="b${r.partial ? ' partial' : ''}">${r.partial ? '프롬프트 일부 공개' : '프롬프트 전체 공개'}</span>
        <span class="b v-${v}">${VERIFY[v].label}</span></div>
    </div>
    <div class="acts" id="acts"></div>
    ${sec('1', '어떤 효과인가', g.what || ed.summary_ko ? `<p>${esc(g.what || ed.summary_ko)}</p>` : `<p>${esc(r.fx.filter(f => f !== 'etc').map(f => FXN[f]).join(' · ') || CAT[r.category] || '')}</p><p class="note">편집 설명이 아직 없는 작품입니다. 원본 프롬프트와 영상으로 판단해 주세요.</p>`)}
    ${sec('2', '어디에 쓰면 좋은가', g.where ? `<p>${esc(g.where)}</p>` : (uses.length ? `<p>${esc(uses.join(', '))}${ed.uses ? '' : ' <span class="note">(키워드로 자동 분류)</span>'}</p>` : ''))}
    ${sec('3', '필요한 것', `<ul><li>${esc(LV_LONG[r.level])}</li>${needs.map(n => `<li>${esc(n)}</li>`).join('')}${env.paid ? `<li>유료: ${esc(env.paid)}</li>` : ''}${env.assets ? `<li>내 자료: ${esc(env.assets)}</li>` : ''}</ul>`)}
    ${sec('4', '실행 순서', g.steps && g.steps.length ? `<ol>${g.steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol>` : '')}
    ${sec('5', '바꾸면 좋은 변수', g.variables && g.variables.length ? `<div class="vars">${g.variables.map(x => `<div><b>${esc(x.name)}</b><span>${esc(x.hint || '')}</span></div>`).join('')}</div>` : '')}
    ${sec('6', '원본 프롬프트', `${r.partial ? '<p class="warn">원작자가 프롬프트 일부만 공개했습니다. 아래는 전체가 아닙니다.</p>' : ''}<pre class="prompt" id="dprompt">${esc(r.prompt || '(프롬프트 없음)')}</pre>`)}
    <div id="applyslot"></div>
    ${sec('8', '출처와 검증', `<ul>
      <li>원작자 @${esc(r.author)}${r.post_url ? ` · <a href="${esc(r.post_url)}" target="_blank" rel="noopener">원본 게시물</a>` : ''}${r.prompt_url ? ` · <a href="${esc(r.prompt_url)}" target="_blank" rel="noopener">프롬프트 출처</a>` : ''}</li>
      <li>검증: <b>${VERIFY[v].label}</b> — ${esc(vr.note || VERIFY[v].note)}${vr.date ? ` (${esc(vr.date)}${vr.env ? ', ' + esc(vr.env) : ''})` : ''}${vr.evidence ? ` · <a href="${esc(vr.evidence)}" target="_blank" rel="noopener">확인 기록</a>` : ''}</li>
      ${vr.missing ? `<li>부족한 조건: ${esc(vr.missing)}</li>` : ''}
      <li class="note">영상·프롬프트의 권리는 원작자에게 있습니다. 작품 ID ${esc(r.id)}</li></ul>`)}
  </div>`;
}
function copyText(t, btn, ev) {
  const o = btn.textContent;
  navigator.clipboard.writeText(t).then(() => { btn.textContent = '복사됨'; track(ev, {id: btn.dataset.id}); })
    .catch(() => { btn.textContent = '복사 실패 — 직접 선택해 주세요'; })
    .finally(() => setTimeout(() => btn.textContent = o, 1600));
}
function bindDetail(r) {
  $('acts').innerHTML = `<button type="button" class="btn primary" id="cp-orig" data-id="${esc(r.id)}">${r.partial ? '원본 프롬프트 복사 (일부 공개)' : '원본 프롬프트 복사'}</button>`;
  $('cp-orig').onclick = e => copyText(r.prompt || '', e.currentTarget, 'copy_original');
  const m = $('dlg').querySelector('[data-media]');
  if (m) m.addEventListener('error', () => { m.remove(); $('dlg').querySelector('.dmedia .none').hidden = false; });
  $('dclose').onclick = () => $('dlg').close();
}
$('dlg').addEventListener('close', () => {
  $('dlg').querySelector('video')?.pause();
  $('dlg').innerHTML = '';
  if (opener && document.contains(opener)) opener.focus();
});
$('dlg').addEventListener('click', e => { if (e.target === $('dlg')) $('dlg').close(); });

load();
