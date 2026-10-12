/* v2: разделы «Матчи», «Модель», «Таблица», «Прогнозы» в спокойном построчном стиле главной. */
(function(){
const css=`
.sec-h h2,.thead h3,.wg-h h2{text-transform:none;letter-spacing:0}
.t2{display:flex;flex-direction:column;gap:22px}
.t2hd{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}
.t2hd h2{font-family:var(--display);font-weight:700;font-size:30px;line-height:1.05;margin:0}
.t2hd h2 small{font-family:var(--body,inherit);font-size:15px;font-weight:500;color:var(--mute);margin-left:8px}
.t2hd h3{font-family:var(--display);font-weight:700;font-size:22px;margin:0}
.t2hd h3 small{font-family:var(--body,inherit);font-size:14px;font-weight:500;color:var(--mute);margin-left:8px}
.t2note{font-size:14px;color:var(--ink2);margin:0}
.t2note b{color:var(--ink)}
/* строка матча */
.t2r{border-top:1px solid var(--line)}
.t2r:first-child{border-top:0}
.t2r.mo{box-shadow:inset 3px 0 0 var(--gold)}
.t2row{display:grid;grid-template-columns:70px minmax(0,1fr) 150px 170px 22px;gap:6px 16px;align-items:center;padding:14px 16px;width:100%;background:none;border:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.t2row:hover{background:var(--soft)}
.t2t{font-family:var(--display);font-size:20px;font-weight:700;line-height:1;display:flex;flex-direction:column}
.t2t small{font-family:var(--body,inherit);font-size:11.5px;font-weight:600;color:var(--mute);margin-top:4px;white-space:nowrap}
.t2tm{display:flex;flex-direction:column;gap:7px;min-width:0}
.t2tm>span{display:flex;align-items:center;gap:9px;min-width:0}
.t2tm b{font-weight:600;font-size:15.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.t2tm small{color:var(--mute);font-size:12.5px;font-variant-numeric:tabular-nums}
.t2tm .fd{margin-left:auto}
.t2pc{display:flex;flex-direction:column;gap:7px}
.t2pc span{display:flex;align-items:center;gap:8px;font-variant-numeric:tabular-nums;font-weight:600;color:var(--mute);font-size:15px}
.t2pc span.f{color:var(--ink);font-weight:800}
.t2pc i{display:block;height:5px;border-radius:3px;background:var(--line);flex:1}
.t2pc span.f i{background:var(--c)}
.t2pk{display:flex;flex-direction:column;gap:5px;align-items:flex-start}
.t2chip{font-size:12.5px;font-weight:700;padding:4px 9px;border-radius:999px;background:var(--soft);color:var(--ink2);white-space:nowrap}
.t2chip.val{background:var(--valbg);color:var(--win)}.t2chip.gold{background:var(--goldbg);color:var(--gold)}.t2chip.no{background:none;border:1px dashed var(--line);color:var(--mute)}
.t2pk .pk{font-size:14px;font-weight:600;white-space:nowrap}
.t2pk .pk small{color:var(--mute);font-weight:500;margin-right:4px}
.t2chev{width:20px;height:20px;fill:none;stroke:var(--mute);stroke-width:2;transition:transform .15s}
.t2row[aria-expanded="true"] .t2chev{transform:rotate(180deg)}
.t2mo{grid-column:2/-1;margin:2px 0 0;font-size:14px;line-height:1.45;color:var(--ink2)}
.t2mo b{color:var(--gold)}
/* раскрытый матч */
.t2x{padding:4px 16px 18px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px 28px;border-top:1px dashed var(--line)}
.t2x>.full{grid-column:1/-1}
.t2blk{display:flex;flex-direction:column;gap:8px;min-width:0}
.t2blk h4{margin:14px 0 0;font-size:13px;font-weight:700;color:var(--mute)}
.t2pick{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.t2pick>div{background:var(--soft);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.t2pick small{font-size:12.5px;font-weight:700;color:var(--mute)}
.t2pick b{font-family:var(--display);font-size:22px;line-height:1.1}
.t2pick b em{font-style:normal;font-family:var(--body,inherit);font-size:14px;color:var(--mute);font-weight:600;margin-left:6px}
.t2pick p{margin:2px 0 0;font-size:13.5px;line-height:1.45;color:var(--ink2)}
.t2ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px}
.t2ul li{font-size:14px;line-height:1.5;color:var(--ink2);padding-left:14px;position:relative}
.t2ul li::before{content:"";position:absolute;left:0;top:.62em;width:5px;height:5px;border-radius:50%;background:var(--mute)}
.t2kv{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.t2kv>div{display:flex;flex-direction:column;gap:2px;font-size:14px}
.t2kv small{font-size:12px;color:var(--mute);font-weight:600}
.t2more{grid-column:1/-1;border-top:1px solid var(--line);padding-top:12px}
.t2more summary{cursor:pointer;font-weight:700;font-size:14.5px;color:var(--link);list-style:none}
.t2more summary::-webkit-details-marker{display:none}
.t2more[open] summary{margin-bottom:12px}
.t2more .mtab{width:100%}
.t2acts{grid-column:1/-1;display:flex;gap:8px;flex-wrap:wrap}
/* неделя */
.t2wk{display:grid;grid-template-columns:70px minmax(0,240px) minmax(0,240px);gap:10px 16px;align-items:center;padding:10px 16px;border-top:1px solid var(--line);font-size:15px}
.t2wk:first-child{border-top:0}
.t2wk>span{display:flex;align-items:center;gap:8px;min-width:0;white-space:nowrap;overflow:hidden}
.t2wk time{font-weight:700;font-variant-numeric:tabular-nums}
.t2day{display:flex;flex-direction:column;gap:8px}
.t2day>summary{cursor:pointer;list-style:none;display:flex;align-items:baseline;gap:8px;font-family:var(--display);font-weight:700;font-size:19px}
.t2day>summary::-webkit-details-marker{display:none}
.t2day>summary small{font-family:var(--body,inherit);font-size:13.5px;color:var(--mute);font-weight:500}
.t2day>summary::after{content:"";width:8px;height:8px;border-right:2px solid var(--mute);border-bottom:2px solid var(--mute);transform:rotate(45deg) translateY(-3px);margin-left:4px}
.t2day[open]>summary::after{transform:rotate(225deg)}
/* модель */
.t2seg{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
.t2seg::-webkit-scrollbar{display:none}
.t2seg button{flex:none;font:inherit;font-size:14px;font-weight:600;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink2);cursor:pointer}
.t2seg button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--card)}
.t2ess{display:flex;flex-direction:column;gap:10px}
.t2ess p{margin:0;font-size:15px;line-height:1.6;color:var(--ink2);max-width:72ch}
.t2sum{display:flex;gap:22px;flex-wrap:wrap;padding:14px 16px;border-bottom:1px solid var(--line)}
.t2sum div{display:flex;flex-direction:column}
.t2sum b{font-family:var(--display);font-size:26px;line-height:1}
.t2sum small{font-size:12.5px;color:var(--mute);font-weight:600;margin-top:3px}
.t2box{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.t2pad{padding:16px}
.t2fold>summary{cursor:pointer;list-style:none;padding:14px 16px;font-weight:700;display:flex;justify-content:space-between;gap:10px}
.t2fold>summary::-webkit-details-marker{display:none}
.t2fold>summary span{color:var(--link);font-size:14px}
.t2fold[open]>summary span{display:none}
.t2fold .t2ess{padding:0 16px 16px}
.sum{grid-template-columns:repeat(3,minmax(0,1fr))!important}
.sum .card b{font-size:26px}
/* таблица */
.t2tg{display:grid;gap:16px;grid-template-columns:minmax(0,1fr)}
@media (min-width:1100px){.t2tg{grid-template-columns:repeat(2,minmax(0,1fr))}}
.card:has(table.st){container-type:inline-size}
.card:has(table.st) .tbl-wrap{overflow:visible}
table.st td.l b{white-space:nowrap}
@container (max-width:640px){table.st th:nth-child(9),table.st td:nth-child(9){display:none}}
@container (max-width:480px){table.st th:nth-child(8),table.st td:nth-child(8){display:none}}
@container (max-width:380px){table.st td,table.st th{padding-inline:5px}}
@media (max-width:760px){
 .t2row{grid-template-columns:58px minmax(0,1fr) 22px;padding:12px}
 .t2pc{display:none}
 .t2tm .p{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:600;color:var(--mute)}
 .t2tm .p.f{color:var(--ink);font-weight:800}
 .t2pk{grid-column:2/3;flex-direction:row;flex-wrap:wrap;gap:6px 10px;align-items:center}
 .t2chev{grid-column:3;grid-row:1}
 .t2tm .fd,.t2tm small,.t2pk .favpk{display:none}
 .t2x{grid-template-columns:minmax(0,1fr);padding:4px 12px 16px}
 .t2mo{grid-column:1/-1}
 .t2wk{grid-template-columns:52px minmax(0,1fr);padding:10px 12px}
 .t2wk>span+span{grid-column:2}
 .t2hd h2 small{display:block;margin:6px 0 0}
}
@media (min-width:761px){.t2tm .p{display:none}}
`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);

const LV={bet:["Модель выше рынка","val"],lean:["Чуть выше рынка","gold"],pass:["Согласна с рынком",""],noodds:["Линии пока нет","no"]};
const chev=`<svg class="t2chev" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>`;
const rel2=(iso)=>{const ms=new Date(iso)-Date.now();if(ms<=0)return "";const h=Math.floor(ms/36e5);return h>=24?`через ${Math.floor(h/24)} д`:h?`через ${h} ч`:`через ${Math.max(1,Math.floor(ms/6e4))} мин`};
const plural=(n,a,b,c)=>{const m=n%10,k=n%100;return n+" "+(m===1&&k!==11?a:m>=2&&m<=4&&(k<12||k>14)?b:c)};
const tmLine=(a,p,f)=>`<span>${badge(a,"s")}<b>${EN[a]}</b><small>${rec(a)}</small>${formDots(a)}${p!=null?`<span class="p ${f?"f":""}">${pct(p)}</span>`:""}</span>`;
const pcLine=(a,p,f)=>`<span class="${f?"f":""}" style="--c:${tcol(a)}"><i></i>${pct(p)}</span>`;

/* прогноз матча: одна сторона — та же, что во вкладке «Матчи» */
function fcOf(p,m){const pa=pB(p,"away"),ph=pB(p,"home");const side=(m&&m.pick_side)||(pa>ph?"away":"home");return {side,t:side==="home"?p.home:p.away,p:side==="home"?ph:pa}}
window.confLegs=function(){return (D.upcoming||[]).filter(m=>state(m.start)!=="done").map(m=>{const p=modelOf(m);if(!p)return null;const f=fcOf(p,m);return f.p>=.6?f:null}).filter(Boolean).sort((a,b)=>b.p-a.p).slice(0,3)};
/* ---------------- Матчи ---------------- */
function gDetail(m,p){const tp=m.total_pick;const pickT=m.pick_side?sideTeam(m,m.pick_side):null;
  const po=m.odds?(m.pick_side==="home"?m.odds.home:m.odds.away):null;
  const ga=m.goalies||[];const injA=injOut(m.away),injH=injOut(m.home);const h2h=(p&&p.h2h)||[];
  const pick=pickT||tp?`<div class="t2pick full">${pickT?`<div><small>Исход</small><b>${EN[pickT]}${po?`<em>${f2(po)}</em>`:""}</b>${m.lean?`<p>${esc(m.lean)}</p>`:""}</div>`:""}${tp?`<div><small>Тотал</small><b>${tp.side==="over"?"Больше":"Меньше"} ${esc(tp.line)}${tp.odds?`<em>${f2(tp.odds)}</em>`:""}</b>${tp.lean?`<p>${esc(tp.lean)}</p>`:""}</div>`:""}</div>`:"";
  const fac=(m.factors||[]).length?`<div class="t2blk"><h4>Почему так</h4><ul class="t2ul">${m.factors.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`:"";
  const gl=`<div class="t2blk"><h4>Вратари</h4><div class="t2kv">${[0,1].map(i=>{const t=i?m.home:m.away;const gp=p&&(i?p.goalie_home:p.goalie_away);return `<div><small>${EN[t]}</small><b>${esc(ga[i]||"не объявлен")}</b>${gp&&gp.sv?`<small>${(gp.sv*100).toFixed(1).replace(".",",")}% отражённых · ${gp.gp} и.</small>`:""}</div>`}).join("")}</div>
    ${(injA.length||injH.length)?`<h4>Без кого играют</h4><ul class="t2ul">${[[m.away,injA],[m.home,injH]].filter(x=>x[1].length).map(([t,l])=>`<li><b>${EN[t]}:</b> ${l.map(x=>esc(x.name)).join(", ")}</li>`).join("")}</ul>`:""}</div>`;
  const more=`<details class="t2more"><summary>Линии, модель и личные встречи</summary><div class="t2x" style="padding:0;border:0">
     <div class="t2blk">${oddsRow(m)}${booksTable(m)}${softBlock(p)}${p?`<h4>Модель</h4>${probBar(p,m.away,m.home)}<div class="t2kv"><div><small>Ожидаемые голы</small><b>${p.lam_away.toFixed(1)} : ${p.lam_home.toFixed(1)}</b></div><div><small>Ничья в осн. время</small><b>${pct(p.p_ot)}</b></div></div>`:""}</div>
     <div class="t2blk">${p?`<h4>Из чего складывается оценка</h4><ul class="t2ul">${modelWhy(m,p).map(x=>`<li>${x}</li>`).join("")}</ul>`:""}<h4>Личные встречи в сезоне</h4>${h2h.length?`<ul class="t2ul">${h2h.map(g=>`<li>${esc(dShort(g.date))}: ${EN[g.away]} — ${EN[g.home]} <b>${esc(g.score)}</b>${g.end&&g.end!=="REG"?" "+endTag(g.end):""}</li>`).join("")}</ul>`:'<p class="t2note">В этом сезоне ещё не встречались.</p>'}</div></div></details>`;
  return `<div class="t2x">${pick}${fac}${gl}${more}<div class="t2acts"><button class="btn ghost" data-team="${m.away}">${EN[m.away]}: карточка</button><button class="btn ghost" data-team="${m.home}">${EN[m.home]}: карточка</button></div></div>`}

function gRow(m,isMo){const key=`${m.away}-${m.home}`,open=OPEN.has(key);const p=modelOf(m);const s=state(m.start);
  const pa=p?(p.p_away_blend??p.p_away):null,ph=p?(p.p_home_blend??p.p_home):null;const fa=pa!=null&&pa>ph;
  const v=p&&p.verdict?LV[p.verdict.level]:null;const pickT=m.pick_side?sideTeam(m,m.pick_side):null;const tp=m.total_pick;
  const time=s==="live"?'<span class="chip live">LIVE</span>':s==="done"?`${kt(m.start)}<small>завершён</small>`:`${kt(m.start)}${rel2(m.start)?`<small>${rel2(m.start)}</small>`:""}`;
  return `<div class="t2r${isMo?" mo":""}" id="g-${key}"><button class="t2row" data-tog="${key}" aria-expanded="${open}"><span class="t2t">${time}</span>
    <span class="t2tm">${tmLine(m.away,pa,fa)}${tmLine(m.home,ph,!fa)}</span>
    <span class="t2pc">${pa!=null?pcLine(m.away,pa,fa)+pcLine(m.home,ph,!fa):""}</span>
    <span class="t2pk">${pickT?`<span class="pk"><small>Исход</small>${EN[pickT]}</span>`:""}${tp?`<span class="pk"><small>Тотал</small>${tp.side==="over"?"ТБ":"ТМ"} ${esc(tp.line)}</span>`:""}</span>${chev}
    ${isMo&&D.motd.text?`<p class="t2mo"><b>Матч дня.</b> ${esc(D.motd.text)}</p>`:""}</button>${open?gDetail(m,p):""}</div>`}

function weekList(){const w=(D.week||[]).filter(g=>g.date>(D.upcoming_date||""));if(!w.length)return"";const by={};w.forEach(g=>(by[g.date]=by[g.date]||[]).push(g));
  return `<section class="t2"><div class="t2hd"><h3>Дальше на неделе<small>прогнозы появятся накануне</small></h3></div>${Object.entries(by).map(([d,gs],k)=>`<details class="t2day" ${k?"":"open"}><summary>${esc(dLong(d))}<small>${plural(gs.length,"матч","матча","матчей")}</small></summary><div class="t2box">${gs.slice().sort((a,b)=>String(a.start).localeCompare(String(b.start))).map(g=>`<div class="t2wk"><time>${kt(g.start)}</time><span>${badge(g.away,"s")}${EN[g.away]}</span><span>${badge(g.home,"s")}${EN[g.home]}</span></div>`).join("")}</div></details>`).join("")}</section>`}

window.vGames=function(){const u=(D.upcoming||[]).slice().sort((a,b)=>String(a.start).localeCompare(String(b.start)));
  if(!u.length)return `<div class="t2">${weekList()||'<div class="card empty">Матчей в ближайший игровой день нет.</div>'}</div>`;
  const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  const ex=confLegs();
  return `<div class="t2"><section class="t2"><div class="t2hd"><h2>Матчи<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h2></div>
    ${ex.length?`<p class="t2note">Самые уверенные исходы: ${ex.map(x=>`<b>${EN[x.t]}</b> ${pct(x.p)}`).join(", ")}</p>`:""}
    <div class="t2box">${u.map(m=>gRow(m,m===mo)).join("")}</div>
    <p class="t2note" style="font-size:12.5px;color:var(--mute)">Проценты — итог модели и рынка (60% рынка, 40% модели). Нажми на матч, чтобы открыть разбор.</p></section>${weekList()}</div>`};

/* ---------------- Модель ---------------- */
function mDetail(p,m){const hasOdds=m.odds||m.odds_1x||m.books||m.fonbet;
  return `<div class="t2x">${fBox(p,m)}
    <div class="t2blk full"><div class="t2ess">${essayOf(p).map(x=>`<p>${esc(x)}</p>`).join("")}</div></div>
    <details class="t2more"><summary>Цифры: вероятности, рынок, линии</summary><div class="t2x" style="padding:0;border:0">
      <div class="t2blk">${probBar(p,p.away,p.home)}<div class="t2kv"><div><small>Ожидаемые голы</small><b>${nz(p.lam_away)} : ${nz(p.lam_home)}</b></div><div><small>Ничья в осн. время</small><b>${pct(p.p_ot)}</b></div><div><small>ТБ ${p.line}</small><b>${pct(p.p_over)}</b></div><div><small>ТМ ${p.line}</small><b>${pct(p.p_under)}</b></div></div>${mktTable(p)}</div>
      <div class="t2blk">${hasOdds?booksTable(m)+softBlock(p):'<p class="t2note">Кэфов пока нет: линия открывается примерно за сутки до матча.</p>'}<h4>Из чего складывается оценка</h4><ul class="t2ul">${modelWhy(p,p).map(x=>`<li>${x}</li>`).join("")}</ul></div></div></details>
    <div class="t2acts"><button class="btn ghost" data-team="${p.away}">${EN[p.away]}: карточка</button><button class="btn ghost" data-team="${p.home}">${EN[p.home]}: карточка</button></div></div>`}
function fBox(p,m){const f=fcOf(p,m);const pa=pB(p,"away"),ph=pB(p,"home");const mk=p.mkt_home!=null;
  const ms=f.side==="home"?p.mkt_home:p.mkt_away,mo=f.side==="home"?p.p_home:p.p_away;
  const b=p.verdict&&p.verdict.bet&&p.verdict.bet.kind==="win"&&["bet","lean"].includes(p.verdict.level)?p.verdict.bet.side:null;
  const other=b&&b!==f.side?(b==="home"?p.home:p.away):null;
  const note=mk?`Модель без рынка — ${pct(mo)}, рынок — ${pct(ms)}.${other?` Модель оценивает шансы ${EN[other]} чуть выше рынка (${pct(b==="home"?p.p_home:p.p_away)} против ${pct(b==="home"?p.mkt_home:p.mkt_away)}), но фаворит всё равно ${EN[f.t]}.`:""}`:"Линии пока нет — это чистая оценка модели.";
  const o=p.p_over_blend??p.p_over,u=p.p_under_blend??p.p_under;
  return `<div class="t2pick full"><div><small>Прогноз</small><b>${EN[f.t]}<em>${pct(f.p)}</em></b><p>${note}</p></div>${o!=null?`<div><small>Тотал</small><b>${o>=u?"Больше":"Меньше"} ${p.line}<em>${pct(Math.max(o,u))}</em></b><p>Ожидаемые голы ${nz(p.lam_away)} : ${nz(p.lam_home)}, ничья в основное время — ${pct(p.p_ot)}.</p></div>`:""}</div>`}
function mRow2({p,m,start}){const key="m"+(p.id||p.away+p.home),open=OPEN.has(key);
  const ph=pB(p,"home"),pa=pB(p,"away");const f=fcOf(p,m);const fa=f.side==="away";
  return `<div class="t2r" id="${key}"><button class="t2row" data-tog="${key}" aria-expanded="${open}"><span class="t2t">${kt(start)}${rel2(start)?`<small>${rel2(start)}</small>`:""}</span>
    <span class="t2tm">${tmLine(p.away,pa,fa)}${tmLine(p.home,ph,!fa)}</span><span class="t2pc">${pcLine(p.away,pa,fa)}${pcLine(p.home,ph,!fa)}</span>
    <span class="t2pk favpk"><span class="pk"><small>Прогноз</small>${EN[f.t]}</span></span>${chev}</button>${open?mDetail(p,m):""}</div>`}
window.vModel=function(){const all=mGames();if(!all.length)return `<div class="card empty">Будущих матчей в расписании пока нет — модель посчитает их после ближайшего обновления.</div>`;
  const list=all;
  const by={};list.forEach(g=>(by[g.p.date]=by[g.p.date]||[]).push(g));
  const n=x=>all.filter(g=>(g.p.verdict||{}).level===x).length;const withOdds=all.filter(g=>g.p.mkt_home!=null).length;
  const mt=D.model_tab||{};const ess=Array.isArray(mt.essay)&&mt.essay.length?mt.essay:[];const upd=mt.updated||M.generated;
  const seg="";
  return `<div class="t2"><div class="t2hd"><h2>Модель<small>все матчи вперёд, время по Кирову</small></h2></div>
   <div class="t2box"><div class="t2sum"><div><b>${all.length}</b><small>матчей вперёд</small></div><div><b>${withOdds}</b><small>уже с линией</small></div></div></div>
    ${ess.length?`<details class="t2fold"><summary>${esc(String(ess[0]).split(/(?<=[.!?])\s/)[0])}<span>Читать обзор</span></summary><div class="t2ess">${ess.map(x=>`<p>${esc(x)}</p>`).join("")}${upd?`<p style="font-size:12.5px;color:var(--mute)">Обновлено ${esc(new Date(upd).toLocaleString("ru-RU",{timeZone:"Europe/Kirov",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}))}</p>`:""}</div></details>`:""}</div>
   ${seg}
   ${Object.keys(by).length?Object.entries(by).map(([d,gs],k)=>`<details class="t2day" ${k<2?"open":""}><summary>${esc(dLong(d))}<small>${plural(gs.length,"матч","матча","матчей")}</small></summary><div class="t2box">${gs.map(mRow2).join("")}</div></details>`).join(""):'<div class="card empty">Под этот фильтр матчей нет.</div>'}
   <details class="t2box t2fold"><summary>Как читать оценку<span>Открыть</span></summary><div class="t2ess"><ul class="t2ul">
    <li>Прогноз — сторона, у которой больше шансов. Проценты — итог: 60% рынка и 40% модели, когда линия есть, и чистая модель, когда её нет.</li>
    <li>Линия открывается примерно за сутки до матча. Вечером, после объявления вратарей, прогноз уточняется.</li>
    <li>Самыми уверенными считаем исходы с шансом от 60%. Если таких нет, в этот день их не называем.</li></ul></div></details></div>`};

/* ---------------- Таблица ---------------- */
const _vTable=window.vTable;
window.vTable=function(){return _vTable().replace('class="grid2"','class="t2tg"').replace(/<div class="sec">(?=<div class="card">|<div class="sec">)/,'<div class="sec t2st">')};

/* ---------------- Прогнозы: без графика ---------------- */
window.lineChart=function(){return ""};
const _pc=window.pClaude;window.pClaude=function(){return _pc().replace('<div class="card pad"></div>','')};

try{if(typeof D!=="undefined"&&D&&D.upcoming&&typeof render==="function")render()}catch(e){}
})();
