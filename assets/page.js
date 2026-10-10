/* 생성 페이지(fx/·use/) 동작: 테마, 미리보기 실패 대체, 원본·요청문 복사, 즐겨찾기, 공유.
   작품 정보는 페이지 안의 <script id="item"> 에 들어 있다 — 카탈로그를 다시 받지 않는다. */
import {ENVS, buildRequest} from './apply.js';
import {favs, toggleFav, shareLink} from './store.js';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

$('theme').onclick = () => {
  const d = document.documentElement, t = d.dataset.theme === 'dark' ? 'light' : 'dark';
  d.dataset.theme = t;
  try { localStorage.setItem('yl-theme', t); } catch (e) {}
};

const m = document.querySelector('[data-media]');
if (m) m.addEventListener('error', () => { m.remove(); document.querySelector('.dmedia .none').hidden = false; });

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

  const env = r.level === 1 ? 'chat' : 'code';
  $('applyslot').outerHTML = `<section class="dsec"><h3><span class="n">7</span>적용용 요청문 만들기</h3>
    <p class="note">아래 칸을 채우면 내 작업에 맞춘 요청문이 만들어집니다. 틀에 값을 채운 것이라 원본과 같은 결과를 보장하지 않습니다. 입력한 내용은 이 화면 밖으로 보내지 않습니다.</p>
    <div class="apply">
      <label>용도<input id="ap-use" placeholder="${esc(r.uses[0] || '예: 랜딩 페이지 첫 화면')}"></label>
      <label>들어갈 문구<input id="ap-text" placeholder="예: 우리 카페 그랜드 오픈"></label>
      <label>색상<input id="ap-color" placeholder="예: 크림 바탕에 진한 주황"></label>
      <label>실행 환경<select id="ap-env">${Object.entries({chat: 'Claude 채팅 (HTML 한 장)', code: 'Claude Code (프로젝트)', video: '영상 파일 (MP4)'}).map(([k, t]) => `<option value="${k}"${k === env ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
    </div>
    <pre class="prompt" id="ap-out" aria-live="polite"></pre>
    <div class="acts"><button type="button" class="btn primary" id="cp-req">적용용 요청문 복사</button></div></section>`;
  const upd = () => { $('ap-out').textContent = buildRequest(r, {use: $('ap-use').value.trim(), text: $('ap-text').value.trim(), color: $('ap-color').value.trim(), env: $('ap-env').value}, r.uses); };
  ['ap-use', 'ap-text', 'ap-color', 'ap-env'].forEach(id => $(id).addEventListener('input', upd));
  upd();
  $('cp-req').onclick = e => copy($('ap-out').textContent, e.currentTarget);
}
void ENVS;
