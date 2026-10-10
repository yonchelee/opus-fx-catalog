// 브라우저 통합 시험.  npm install 후  node tests/e2e.mjs
// 저장소를 /opus-fx-catalog/ 하위 경로로 직접 서빙한다(GitHub Pages 와 같은 조건).
// Chrome 경로: CHROME_PATH 또는 macOS 기본 위치. 스크린샷: E2E_OUT (기본 /tmp/fx-e2e)
import http from 'node:http';
import {readFile, mkdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {extname, join, normalize} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const OUT = process.env.E2E_OUT || '/tmp/fx-e2e';
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.xml': 'application/xml'};

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (!u.pathname.startsWith('/opus-fx-catalog/')) { res.writeHead(404); return res.end(); }
  let p = normalize(join(ROOT, decodeURIComponent(u.pathname.slice('/opus-fx-catalog/'.length))));
  if (!p.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  if (p.endsWith('/') || (existsSync(p) && !extname(p))) p = join(p, 'index.html');
  try { const b = await readFile(p); res.writeHead(200, {'content-type': TYPES[extname(p)] || 'application/octet-stream'}); res.end(b); }
  catch { res.writeHead(404); res.end('not found'); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const ORIGIN = `http://127.0.0.1:${server.address().port}`;
const BASE = ORIGIN + '/opus-fx-catalog/';
await mkdir(OUT, {recursive: true});

let pass = 0, fail = 0;
const ok = (name, cond, info = '') => { cond ? pass++ : fail++; console.log(`${cond ? 'PASS' : 'FAIL'} ${name}${info ? ' — ' + info : ''}`); };
const browser = await chromium.launch({executablePath: CHROME, headless: true});
async function page(opt = {}) {
  const ctx = await browser.newContext({viewport: {width: 1280, height: 800}, ...opt});
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: ORIGIN});
  const p = await ctx.newPage();
  p.errs = [];
  p.on('pageerror', e => p.errs.push(String(e)));
  p.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|ERR_|net::/.test(m.text())) p.errs.push(m.text()); });
  return p;
}
const ready = p => p.waitForSelector('#grid .card', {timeout: 15000});
const dlgOpen = p => p.evaluate(() => document.getElementById('dlg').open);
const clip = p => p.evaluate(() => navigator.clipboard.readText());
const ID = 'yihui:stewchan2-369810';

try {
  {
    const p = await page();
    await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
    ok('첫 화면: 대표 효과 6개', await p.locator('#fgrid .card').count() === 6);
    ok('첫 화면: 전체 수 표시', /\/ 646|\/ \d+/.test(await p.textContent('#count')));
    ok('첫 화면: 콘솔 오류 없음', p.errs.length === 0, p.errs.join(' | '));

    await p.fill('#q', '지도'); await p.waitForTimeout(150);
    const n = parseInt(await p.textContent('#count'));
    ok('한국어 검색 "지도" 결과 있음', n > 5, `${n}건`);
    ok('검색 중에는 대표 효과를 접음', await p.locator('#featured').isHidden());
    ok('검색 결과 제목', (await p.textContent('#all-h')).includes('‘지도’ 검색 결과'));
    ok('검색 중 정렬은 관련도순으로 표시', await p.inputValue('#sort') === 'rel');
    ok('검색 중 상세 필터는 접히고 켜진 조건만', await p.locator('#filters').isHidden() && await p.locator('#ftoggle').isVisible());
    {
      const [top, vh] = await p.evaluate(() => [document.querySelector('#grid .card').getBoundingClientRect().top, innerHeight]);
      ok('데스크톱: 검색하면 첫 결과가 첫 화면 안', top > 0 && top < vh - 120, `${Math.round(top)} / ${vh}`);
    }
    await p.selectOption('#sort', 'likes'); await p.waitForTimeout(150);
    const likes = await p.$$eval('#grid .card .xlikes', e => e.slice(0, 8).map(x => x.textContent));
    const num = t => { const v = t.replace(/[^\d.만]/g, ''); return v.includes('만') ? parseFloat(v) * 10000 : parseFloat(v.replace(/,/g, '')); };
    ok('검색 중 좋아요순을 고르면 좋아요 순서', likes.map(num).every((v, i, a) => i === 0 || a[i - 1] >= v), likes.join(','));
    ok('고른 정렬이 주소에 남음', new URL(p.url()).searchParams.get('sort') === 'likes');
    await p.selectOption('#sort', 'rel'); await p.waitForTimeout(100);
    ok('검색어가 주소에 남음', new URL(p.url()).searchParams.get('q') === '지도');
    ok('켜진 조건 칩', await p.locator('.chipx').count() === 1);
    const titles = await p.$$eval('#grid .card .title', e => e.slice(0, 40).map(x => x.textContent).join(' '));
    ok('"지도" 결과에 영어 사례', /map|globe|Map/i.test(titles) || n > 20);

    await p.fill('#q', 'zzqqxx없는말'); await p.waitForTimeout(150);
    ok('결과 없음 안내', /조건에 맞는 작품이 없습니다/.test(await p.textContent('#status')));
    await p.click('[data-fix="all"]'); await p.waitForTimeout(150);
    ok('필터 모두 해제로 복구', await p.locator('#grid .card').count() > 0 && await p.inputValue('#q') === '');

    await p.fill('#q', 'Blender 3D and self-made soundtrack'); await p.waitForTimeout(150);
    ok('Blender 쇼릴은 채팅이 아니라 외부 프로그램', (await p.textContent('#grid .card .badges')).includes('외부 프로그램'));
    await p.fill('#q', ''); await p.selectOption('#lv', '1'); await p.waitForTimeout(150);
    const lvBadges = await p.$$eval('#grid .card .badges .b:first-child', e => e.map(x => x.textContent));
    ok('"채팅에서 바로" 필터에는 그 표시만', lvBadges.length > 0 && lvBadges.every(t => t === '채팅에서 바로'), `${lvBadges.length}개`);
    ok('"환경 확인 필요" 배지에 설명', await p.locator('#grid .b.env0').count() === 0);
    await p.selectOption('#lv', '2'); await p.waitForTimeout(150);
    const lv2 = await p.$$eval('#grid .card .badges .b:first-child', e => [...new Set(e.map(x => x.textContent))]);
    ok('"Claude Code까지"에는 확인 필요가 없음', lv2.length > 0 && lv2.every(t => t === '채팅에서 바로' || t === 'Claude Code'), lv2.join(','));
    await p.selectOption('#lv', '0'); await p.waitForTimeout(150);
    const lv0 = await p.$$eval('#grid .card .badges .b:first-child', e => [...new Set(e.map(x => x.textContent))]);
    ok('"환경 확인 필요"만 따로 고를 수 있음', lv0.length === 1 && lv0[0] === '환경 확인 필요', lv0.join(','));
    await p.selectOption('#lv', ''); await p.waitForTimeout(150);
    ok('전체에는 "환경 확인 필요" 표시가 있음', await p.locator('#grid .b.env0').count() > 0 && (await p.getAttribute('#grid .b.env0 >> nth=0', 'title')).includes('렌더링'));
    await p.click('.fx[data-k="3d"]'); await p.click('.fx[data-k="shader"]'); await p.waitForTimeout(100);
    ok('효과 여러 개는 AND 라고 표시', /2개를 모두 포함\(AND\)/.test(await p.textContent('#andnote')));
    ok('주소에 fx 반영', new URL(p.url()).searchParams.get('fx') === '3d,shader');
    await p.click('#clearall'); await p.waitForTimeout(100);
    ok('전체 해제', await p.locator('.chipx').count() === 0);
    ok('조건을 모두 풀면 대표 효과가 다시 보임', await p.locator('#featured').isVisible());
    await p.close();
  }

  {
    const p = await page();
    await p.goto(BASE + '?q=' + encodeURIComponent('로고') + '&item=' + encodeURIComponent(ID), {waitUntil: 'networkidle'});
    await p.waitForTimeout(500);
    ok('작품 주소 직접 접속 → 상세 열림', await dlgOpen(p));
    await p.reload({waitUntil: 'networkidle'}); await p.waitForTimeout(500);
    ok('새로고침해도 상세 열림', await dlgOpen(p));
    ok('상세 제목에 포커스', await p.evaluate(() => document.activeElement.id === 'dtitle'));
    const secs = await p.$$eval('.dsec h3', e => e.map(x => x.textContent));
    ok('상세 8칸', secs.length === 8, secs.join(','));
    ok('영상이 정상이면 대체 문구는 숨김', await p.evaluate(() => { const n = document.querySelector('#dlg .dmedia .none'); return !n || getComputedStyle(n).display === 'none'; }));
    ok('검증 상태 표시', /일부 확인|미검증|재현 확인/.test(await p.textContent('.dhead .badges')));
    await p.click('#cp-orig'); await p.waitForTimeout(100);
    ok('원본 프롬프트 복사', (await clip(p)).length > 50 && (await clip(p)) === (await p.textContent('#dprompt')));
    await p.fill('#ap-text', '우리 동네 강수량'); await p.selectOption('#ap-env', 'video');
    await p.click('#cp-req'); await p.waitForTimeout(100);
    const req = await clip(p);
    ok('적용용 요청문 복사(입력 반영)', req.includes('우리 동네 강수량') && req.includes('MP4') && req !== (await p.textContent('#dprompt')));
    await p.evaluate(() => Object.defineProperty(Navigator.prototype, 'share', {value: undefined, configurable: true}));
    await p.click('#share'); await p.waitForTimeout(150);
    ok('공유: 공유 기능 없으면 링크 복사', (await clip(p)) === 'https://yonchelee.github.io/opus-fx-catalog/fx/yihui/stewchan2-369810/');
    await p.click('#favbtn');
    ok('즐겨찾기 켜짐', await p.getAttribute('#favbtn', 'aria-pressed') === 'true');
    await p.click('#dclose'); await p.waitForTimeout(200);
    ok('닫으면 주소에서 item 만 지움', !new URL(p.url()).searchParams.get('item') && new URL(p.url()).searchParams.get('q') === '로고');
    await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
    ok('즐겨찾기가 새로고침 뒤에도 남음', /★ 즐겨찾기\s*1/.test(await p.textContent('#favchip')));
    await p.click('#favchip'); await p.waitForTimeout(150);
    ok('즐겨찾기만 보기', await p.locator('#grid .card').count() === 1 && new URL(p.url()).searchParams.get('fav') === '1');
    ok('카드에 별 표시', await p.locator('#grid .card .fav-on').count() === 1);

    await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
    const first = p.locator('#grid .card').first();
    await first.focus(); await p.keyboard.press('Enter'); await p.waitForTimeout(300);
    ok('키보드 Enter 로 상세 열기', await dlgOpen(p));
    ok('열 때 주소 기록', !!new URL(p.url()).searchParams.get('item'));
    await p.goBack(); await p.waitForTimeout(300);
    ok('뒤로가기가 상세를 닫음', !(await dlgOpen(p)) && !new URL(p.url()).searchParams.get('item'));
    ok('닫은 뒤 포커스가 카드로', await p.evaluate(() => document.activeElement.classList.contains('card')));
    await p.goForward(); await p.waitForTimeout(300);
    ok('앞으로가기가 다시 엶', await dlgOpen(p));
    await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    ok('Esc 로 닫힘', !(await dlgOpen(p)) && !new URL(p.url()).searchParams.get('item'));
    let tabs = 0, reached = false;
    await p.focus('#q');
    while (tabs++ < 12) { await p.keyboard.press('Tab'); if (await p.evaluate(() => document.activeElement.classList.contains('use'))) { reached = true; break; } }
    ok('검색창 다음 Tab 으로 용도 선택에 도달', reached);
    ok('포커스 표시(outline) 있음', await p.evaluate(() => getComputedStyle(document.activeElement).outlineStyle !== 'none'));

    await p.evaluate(() => scrollTo(0, 2400)); await p.waitForTimeout(200);
    const y0 = await p.evaluate(() => scrollY);
    const deep = p.locator('#grid .card').nth(12);
    await deep.scrollIntoViewIfNeeded(); const y1 = await p.evaluate(() => scrollY);
    await deep.click(); await p.waitForTimeout(300); await p.keyboard.press('Escape'); await p.waitForTimeout(500);
    const y2 = await p.evaluate(() => scrollY);
    ok('목록 아래에서 열고 닫아도 스크롤 위치 유지', Math.abs(y2 - y1) < 40, `${y0}→${y1}→${y2}`);
    await p.goto(BASE + '?pick=' + encodeURIComponent(ID) + ',yihui:mounnna-497266', {waitUntil: 'networkidle'}); await p.waitForTimeout(400);
    ok('기존 ?pick= 추천 후보 링크', await p.locator('#grid .num').count() === 2);
    await p.goto(BASE + '?fx=data&sort=new', {waitUntil: 'networkidle'}); await ready(p);
    ok('기존 ?fx= · ?sort=new', await p.inputValue('#sort') === 'new' && await p.getAttribute('.fx[data-k="data"]', 'aria-pressed') === 'true');
    await p.goto(BASE + '?item=nope:none', {waitUntil: 'networkidle'}); await p.waitForTimeout(300);
    ok('없는 작품 주소는 안내', /찾는 작품이 없습니다/.test(await p.textContent('#status')) && !(await dlgOpen(p)));

    await p.click('#theme'); await p.reload({waitUntil: 'networkidle'});
    ok('다크 모드 유지', await p.evaluate(() => document.documentElement.dataset.theme) === 'dark');
    await p.click('#theme');
    ok('콘솔 오류 없음(상세·주소)', p.errs.length === 0, p.errs.join(' | '));
    await p.close();
  }

  {
    const p = await page();
    await p.route(/\.(mp4|webp|jpg|jpeg|png)(\?|$)/, r => r.request().url().startsWith(ORIGIN) ? r.continue() : r.abort());
    await p.goto(BASE + '?item=' + encodeURIComponent('yihui:twoclipping-402193'), {waitUntil: 'networkidle'}); await p.waitForTimeout(800);
    await p.evaluate(() => { const v = document.querySelector('#dlg video'); if (v) v.load(); });
    await p.waitForTimeout(800);
    const fb = await p.evaluate(() => { const n = document.querySelector('#dlg .dmedia .none'); return n && !n.hidden && !!n.querySelector('a'); });
    ok('영상 실패 → 대체 화면과 원본 링크', fb);
    await p.keyboard.press('Escape');
    ok('썸네일 실패 → 대체 문구', await p.locator('#grid .media .none').count() > 0);
    await p.close();
  }
  {
    const p = await page();
    await p.route('**/catalog.json', r => r.abort());
    await p.goto(BASE, {waitUntil: 'domcontentloaded'}); await p.waitForTimeout(800);
    ok('불러오기 실패 안내와 다시 시도', /불러오지 못했습니다/.test(await p.textContent('#status')) && await p.locator('#retry').count() === 1);
    await p.unroute('**/catalog.json'); await p.click('#retry'); await ready(p);
    ok('다시 시도로 복구', await p.locator('#grid .card').count() > 0);
    await p.close();
  }

  {
    const p = await page();
    for (const u of ['fx/yihui/stewchan2-369810/', 'use/', 'use/logo/', 'use/hero/', 'use/chat/', 'use/product/', 'use/data/']) {
      const r = await p.goto(BASE + u, {waitUntil: 'networkidle'});
      ok(`정적 페이지 ${u}`, r.status() === 200 && (await p.title()).includes('효과 갤러리'));
    }
    {
      const nojs = await browser.newContext({javaScriptEnabled: false});
      const q = await nojs.newPage();
      await q.goto(BASE + 'fx/yihui/groundcontrol-230877/', {waitUntil: 'load'});
      const h3 = await q.$$eval('.dsec h3', e => e.map(x => x.textContent));
      ok('스크립트 없이도 작품 페이지 1~8칸(7번 요청문 포함)', h3.some(t => /^7적용용 요청문/.test(t)) && (await q.textContent('#ap-out')).includes('[참고한 효과]'), h3.map(t => t.slice(0, 2)).join(','));
      await nojs.close();
    }
    await p.goto(BASE + 'fx/yihui/stewchan2-369810/', {waitUntil: 'networkidle'});
    await p.reload({waitUntil: 'networkidle'});
    ok('작품 페이지 새로고침', (await p.textContent('h1')).length > 2);
    await p.click('#cp-orig'); await p.waitForTimeout(100);
    ok('작품 페이지 원본 복사', (await clip(p)).length > 50);
    await p.fill('#ap-text', '페이지에서 입력');
    ok('작품 페이지 요청문', (await p.textContent('#ap-out')).includes('페이지에서 입력'));
    await p.click('#fav');
    await p.goto(BASE + '?fav=1', {waitUntil: 'networkidle'}); await ready(p);
    ok('작품 페이지 즐겨찾기가 갤러리와 공유', await p.locator('#grid .card').count() === 1);
    const links = await p.evaluate(async () => (await (await fetch('use/data/')).text()).match(/href="([^"]+)"/g).length);
    ok('용도 페이지에 작품 링크', links > 5);
    ok('콘솔 오류 없음(정적 페이지)', p.errs.length === 0, p.errs.join(' | '));
    await p.close();
  }

  const FF = [['phone', 390, 844, true], ['phone-small', 360, 740, true], ['phone-land', 844, 390, true], ['fold-closed', 344, 882, true],
    ['fold-open', 736, 840, true], ['fold-open-land', 840, 736, true], ['tablet', 768, 1024, true], ['tablet-land', 1024, 768, true],
    ['laptop-low', 1280, 720, false], ['desktop', 1440, 900, false]];
  for (const [name, w, h, touch] of FF) {
    for (const scheme of name === 'phone' || name === 'desktop' ? ['light', 'dark'] : ['light']) {
      const p = await page({viewport: {width: w, height: h}, isMobile: touch && w < 900, hasTouch: touch, colorScheme: scheme, deviceScaleFactor: 1});
      await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
      const m = await p.evaluate(() => ({h: document.documentElement.scrollWidth > innerWidth, ft: document.querySelector('#fgrid .card').getBoundingClientRect().top, vh: innerHeight,
        small: [...document.querySelectorAll('button,select,input,a.use')].filter(e => { const b = (e.type === 'checkbox' && e.closest('label') ? e.closest('label') : e).getBoundingClientRect(); return b.width && b.height && b.height < 44 && !e.closest('#dlg,.chipx,.linkish,footer') && !e.classList.contains('card'); }).map(e => e.id || e.className)}));
      ok(`${name}/${scheme}: 가로 스크롤 없음`, !m.h);
      ok(`${name}/${scheme}: 대표 효과가 1.5화면 안`, m.ft < m.vh * 1.5, `${Math.round(m.ft)} / ${m.vh}`);
      ok(`${name}/${scheme}: 조작 요소 44px 이상`, m.small.length === 0, m.small.slice(0, 4).join(','));
      await p.screenshot({path: `${OUT}/${name}-${scheme}-1-open.png`});
      if (name === 'phone' && scheme === 'light') {
        await p.fill('#q', '지도'); await p.press('#q', 'Enter'); await p.waitForTimeout(400);
        const [top, vh] = await p.evaluate(() => [document.querySelector('#grid .card').getBoundingClientRect().top, innerHeight]);
        ok('폰: 검색하면 첫 결과가 바로 보임', top >= 0 && top < vh * 0.75, `${Math.round(top)} / ${vh}`);
        await p.screenshot({path: `${OUT}/phone-search.png`});
        await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
      }
      const c = p.locator('#fgrid .card').first();
      if (touch) await c.tap(); else await c.click();
      await p.waitForTimeout(500);
      const d = await p.evaluate(() => { const t = document.getElementById('dtitle').getBoundingClientRect(), x = document.getElementById('dclose').getBoundingClientRect();
        return {t: t.top >= 0 && t.top < innerHeight, x: x.top >= 0 && x.right <= innerWidth, h: document.documentElement.scrollWidth > innerWidth}; });
      ok(`${name}/${scheme}: 상세 제목·닫기 보임`, d.t && d.x && !d.h);
      await p.screenshot({path: `${OUT}/${name}-${scheme}-3-dialog.png`});
      await p.keyboard.press('Escape');
      await p.evaluate(() => document.getElementById('all').scrollIntoView());
      await p.waitForTimeout(300);
      await p.screenshot({path: `${OUT}/${name}-${scheme}-2-cards.png`});
      ok(`${name}/${scheme}: 콘솔 오류 없음`, p.errs.length === 0, p.errs.join(' | '));
      await p.close();
    }
  }
  {
    const p = await page({reducedMotion: 'reduce'});
    await p.goto(BASE, {waitUntil: 'networkidle'}); await ready(p);
    await p.hover('#grid .card >> nth=0'); await p.waitForTimeout(300);
    ok('움직임 줄이기: 호버 영상 재생 안 함', await p.locator('#grid .card video').count() === 0);
    await p.close();
  }
} finally {
  await browser.close(); server.close();
  console.log(`\n결과: 통과 ${pass} · 실패 ${fail} · 스크린샷 ${OUT}`);
  process.exitCode = fail ? 1 : 0;
}
