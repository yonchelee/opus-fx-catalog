/* 즐겨찾기(이 브라우저의 localStorage)와 공유. 로그인·서버 없음. */
const KEY = 'fx-favs';

export function favs() {
  try { const v = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(v) ? v.filter(x => typeof x === 'string') : []; }
  catch (e) { return []; }
}
export function toggleFav(id) {
  const f = favs(), i = f.indexOf(id);
  if (i >= 0) f.splice(i, 1); else f.unshift(id);
  try { localStorage.setItem(KEY, JSON.stringify(f)); } catch (e) {}
  return i < 0;
}

/* 브라우저 공유 기능이 있으면 쓰고, 없거나 취소되면 링크를 복사한다. */
export async function shareLink({title, url}, btn, flash) {
  if (navigator.share) {
    try { await navigator.share({title, url}); return 'shared'; }
    catch (e) { if (e && e.name === 'AbortError') return 'cancelled'; }
  }
  try { await navigator.clipboard.writeText(url); flash && flash(btn, '링크 복사됨'); return 'copied'; }
  catch (e) { flash && flash(btn, '복사 실패'); return 'failed'; }
}
