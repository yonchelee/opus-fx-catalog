import {FX, FXN, CAT, LV, NEED, mergeEditorial, titleOf, fmtLikes as fmtN} from './data.js';
const PAGE=48;
const fmtLikes=n=>n==null?'':'♥ '+fmtN(n);
const $=id=>document.getElementById(id);
/* 테마는 홈과 같은 키(yl-theme)로 기억한다. 도메인이 달라 홈의 선택이 넘어오지는 않는다. */
$('theme').onclick=()=>{const d=document.documentElement,t=d.dataset.theme==='dark'?'light':'dark';d.dataset.theme=t;try{localStorage.setItem('yl-theme',t)}catch(e){}};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const params=new URLSearchParams(location.search);
let DATA=[],rows=[],shown=0,pick=null;
const sel=new Set((params.get('fx')||'').split(',').filter(Boolean));

Promise.all([fetch('catalog.json').then(r=>r.json()),fetch('editorial.json').then(r=>r.ok?r.json():{}).catch(()=>({}))]).then(([j,ed])=>{
  DATA=mergeEditorial(j.items,ed).items.sort((a,b)=>(b.added||'').localeCompare(a.added||'')||a.id.localeCompare(b.id));
  $('synced').textContent=`${DATA.length}개 · ${j.synced} 갱신.`;
  const ids=(params.get('pick')||'').split(',').map(s=>s.trim()).filter(Boolean);
  if(ids.length){
    const by=new Map(DATA.flatMap(r=>[[r.id,r],[r.slug,r]]));
    pick=ids.map(i=>by.get(i)).filter(Boolean);
    $('pickmsg').textContent=`추천 후보 ${pick.length}개`;
    $('pickbar').classList.add('on');document.body.classList.add('picking');
  }
  $('q').value=params.get('q')||'';
  if(params.get('sort')==='new')$('sort').value='new';
  buildIndex();render();
}).catch(()=>{$('grid').innerHTML='<div class="empty">카탈로그를 불러오지 못했습니다. 잠시 뒤 새로고침해 주세요.</div>'});

function buildIndex(){
  const cnt={};DATA.forEach(r=>r.fx.forEach(f=>cnt[f]=(cnt[f]||0)+1));
  $('index').innerHTML=FX.filter(([k])=>cnt[k]).sort((a,b)=>(a[0]==='etc')-(b[0]==='etc')||cnt[b[0]]-cnt[a[0]])
    .map(([k,n])=>`<button class="fx" type="button" data-k="${k}" aria-pressed="${sel.has(k)}">${n}<span>${cnt[k]}</span></button>`).join('');
}
$('index').addEventListener('click',e=>{const b=e.target.closest('.fx');if(!b)return;const k=b.dataset.k;sel.has(k)?sel.delete(k):sel.add(k);b.setAttribute('aria-pressed',sel.has(k));pick=null;$('pickbar').classList.remove('on');render()});
['q','sort','cat','lv','vid'].forEach(id=>$(id).addEventListener('input',()=>{pick=null;$('pickbar').classList.remove('on');render()}));
$('reset').onclick=$('showall').onclick=()=>{sel.clear();pick=null;document.body.classList.remove('picking');$('pickbar').classList.remove('on');['q','cat','lv','vid'].forEach(id=>$(id).value='');$('sort').value='likes';history.replaceState(null,'',location.pathname);buildIndex();render()};
$('more').onclick=()=>draw();

function render(){
  if(pick){rows=pick}else{
    const q=$('q').value.trim().toLowerCase(),c=$('cat').value,lv=+$('lv').value,vid=$('vid').value;
    rows=DATA.filter(r=>(!c||r.category===c)&&(!lv||r.level<=lv)&&(!vid||r.mp4)&&[...sel].every(f=>r.fx.includes(f))
      &&(!q||(r.prompt+' '+(r.title||'')+' '+r.author).toLowerCase().includes(q)));
    /* DATA 는 최신순. 좋아요순은 수가 없는 항목(지워진 게시물·X 밖)을 맨 뒤로, 같으면 최신순. */
    if($('sort').value==='likes')rows=rows.slice().sort((a,b)=>(b.likes??-1)-(a.likes??-1));
  }
  $('count').textContent=`${rows.length} / ${DATA.length}`;
  $('grid').innerHTML=rows.length?'':'<div class="empty">조건에 맞는 작품이 없습니다. 효과 타일을 하나 줄여 보세요.</div>';
  shown=0;draw();
}
function draw(){
  const html=rows.slice(shown,shown+PAGE).map((r,i)=>card(r,shown+i)).join('');
  $('grid').insertAdjacentHTML('beforeend',html);shown+=PAGE;$('more').hidden=shown>=rows.length;
}
function card(r,i){
  const img=r.thumb?`<img src="${esc(r.thumb)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'none',textContent:'미리보기 없음'}))">`:'<div class="none">미리보기 없음</div>';
  return `<button class="card" type="button" data-i="${DATA.indexOf(r)}">
    <div class="media">${pick?`<span class="num">${i+1}</span>`:''}${img}${r.mp4?'<span class="play">▶ 영상</span>':''}</div>
    <div class="body"><div class="title">${esc(titleOf(r))}</div>
    <div class="meta">${r.likes!=null?`<span class="likes">${fmtLikes(r.likes)}</span>`:''}<span>@${esc(r.author)}</span><span>${CAT[r.category]||''}</span><span class="lv${r.level}">${LV[r.level]}</span></div>
    <div class="chips">${r.fx.filter(f=>f!=='etc').slice(0,4).map(f=>`<span class="chip">${FXN[f]}</span>`).join('')}</div></div></button>`;
}
/* hover preview: muted mp4 if we have one, otherwise the animated preview image */
const grid=$('grid');
grid.addEventListener('pointerover',e=>{
  const c=e.target.closest('.card');if(!c||c.dataset.hover||e.pointerType==='touch')return;
  const r=DATA[c.dataset.i],m=c.querySelector('.media');c.dataset.hover=1;
  if(r.mp4){const v=Object.assign(document.createElement('video'),{src:r.mp4,muted:true,loop:true,playsInline:true,autoplay:true});v.setAttribute('referrerpolicy','no-referrer');v.onerror=()=>v.remove();m.appendChild(v)}
  else if(r.preview){const p=new Image();p.referrerPolicy='no-referrer';p.onload=()=>{const im=m.querySelector('img');if(im){im.dataset.src=im.src;im.src=r.preview}};p.src=r.preview}
});
grid.addEventListener('pointerout',e=>{
  const c=e.target.closest('.card');if(!c||c.contains(e.relatedTarget))return;
  delete c.dataset.hover;c.querySelector('video')?.remove();const im=c.querySelector('img[data-src]');if(im){im.src=im.dataset.src;delete im.dataset.src}
});
grid.addEventListener('click',e=>{const c=e.target.closest('.card');if(c)open(DATA[c.dataset.i])});

function open(r){
  const src=r.mp4_hd||r.mp4;
  $('dmedia').innerHTML=src?`<video controls autoplay muted playsinline loop poster="${esc(r.thumb||'')}" src="${esc(src)}"></video>`
    :(r.preview||r.thumb)?`<img src="${esc(r.preview||r.thumb)}" alt="" referrerpolicy="no-referrer" onerror="this.src='${esc(r.thumb||'')}'">`:'';
  $('dmeta').innerHTML=`${r.likes!=null?`<span class="likes">${fmtLikes(r.likes)}</span>`:''}<span>@${esc(r.author)}</span><span>${CAT[r.category]||''}</span><span class="lv${r.level}">${LV[r.level]}</span><span>${esc(r.id)}</span>`;
  $('dtitle').textContent=titleOf(r);
  $('dchips').innerHTML=r.fx.map(f=>`<span class="chip">${FXN[f]}</span>`).join('');
  $('dlinks').innerHTML=[r.post_url&&`<a href="${esc(r.post_url)}" target="_blank" rel="noopener">원본 게시물</a>`,
    r.video_url&&!/twimg/.test(r.video_url)&&`<a href="${esc(r.video_url)}" target="_blank" rel="noopener">영상 페이지</a>`,
    r.prompt_url&&`<a href="${esc(r.prompt_url)}" target="_blank" rel="noopener">프롬프트 원문</a>`,
    `<button type="button" id="copy">프롬프트 복사</button>`,`<button type="button" id="copyid">ID 복사</button>`].filter(Boolean).join('');
  $('dnote').textContent=[r.partial?'프롬프트 일부만 공개된 작품입니다.':'',r.needs?.length?'필요한 것: '+r.needs.map(n=>NEED[n]||n).join(', '):''].filter(Boolean).join(' · ');
  $('dprompt').textContent=r.prompt||'(프롬프트 없음)';
  $('copy').onclick=e=>copy(r.prompt,e.target);$('copyid').onclick=e=>copy(r.id,e.target);
  $('dlg').showModal();
}
async function copy(t,b){const o=b.textContent;try{await navigator.clipboard.writeText(t);b.textContent='복사됨'}catch{b.textContent='복사 실패'}setTimeout(()=>b.textContent=o,1500)}
$('dclose').onclick=()=>$('dlg').close();
$('dlg').addEventListener('close',()=>{$('dmedia').innerHTML=''});
$('dlg').addEventListener('click',e=>{if(e.target===$('dlg'))$('dlg').close()});
