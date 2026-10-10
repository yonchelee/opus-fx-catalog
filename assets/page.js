/* 생성 페이지(fx/·use/) 동작: 테마, 미리보기 실패 대체, 원본·요청문 복사, 즐겨찾기, 공유.
   작품 정보는 페이지 안의 <script id="item"> 에 들어 있다 — 카탈로그를 다시 받지 않는다. */
import {buildRequest} from './apply.js';
import {favs, toggleFav, shareLink} from './store.js';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

$('theme').onclick = () => {
  const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark';
  d.dataset.theme = t;
  try { localStorage.setItem('yl-theme', t); } catch (e) {}
};

const m = document.querySelector('[data-media]');
if (m) m.addEventListener('error', () => { const box = m.parentNode; m.remove(); const n = box && box.querySelector('.none'); if (n) n.hidden = false; });

function flash(btn, text) { const o = btn.textContent; btn.textContent = text; setTimeout(() => btn.textContent = o, 1600); }
function copy(t, btn) {
  navigator.clipboard.writeText(t).then(() => flash(btn, '복사됨')).catch(() => flash(btn, '복사 실패 — 직접 선택해 주세요'));
}

const node = $('item');
if (node) {
  const r = JSON.parse(node.textContent);
  $('cp-orig').onclick = e => copy(r.prompt || '', e.currentTarget);

  const fav = $('fav');
  const paint = () => { const on = favs().includes(r.id); fav.setAttribute('aria-pressed', on); fav.textContent = on ? '★ 즐겨찾기됨' : '☆ 즐겨찾기'; };
  fav.onclick = () => { toggleFav(r.id); paint(); };
  paint();

  $('share').onclick = e => shareLink({title: document.title, url: document.querySelector('link[rel=canonical]').href}, e.currentTarget, flash);

  /* 7번 칸은 HTML 에 이미 있다(스크립트가 없어도 기본 요청문이 보인다). 여기서는 입력값만 반영한다. */
  const upd = () => { $('ap-out').textContent = buildRequest(r, {use: $('ap-use').value.trim(), text: $('ap-text').value.trim(), color: $('ap-color').value.trim(), env: $('ap-env').value}, r.uses); };
  ['ap-use', 'ap-text', 'ap-color', 'ap-env'].forEach(id => $(id).addEventListener('input', upd));
  upd();
  $('cp-req').onclick = e => copy($('ap-out').textContent, e.currentTarget);
}
