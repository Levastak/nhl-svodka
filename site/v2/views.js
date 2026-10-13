Warning: truncated output (original token count: 24686)
Total output lines: 496

/* NHL-STATS.RU — экраны */
"use strict";

/* ===================== оболочка ===================== */
function isNav(k){return VIEW===k||(k==="more"&&MORE.some(m=>m[0]===VIEW))}
function renderChrome(){
  $("#dock").innerHTML=NAV.map(([k,l])=>`<button data-nav="${k}" ${isNav(k)?'aria-current="page"':""}>${IC[k]}<span>${l}</span></button>`).join("");
  $("#tnav").innerHTML=NAV.map(([k,l])=>`<button data-nav="${k}" ${isNav(k)?'aria-current="page"':""}>${l}</button>`).join("");
  const f=freshness();const u=$("#upd");u.classList.toggle("old",f.old);u.title="Данные сайта "+f.txt.replace(/<[^>]+>/g,"");tick();
  const s=$("#strip .wrap");const h=stripHtml();if(s.dataset.h!==h){s.innerHTML=h;s.dataset.h=h}}
 /* часы с устройства: «13.10.2026, вторник 04:12 (UTC+3)» */
const WD=["воскресенье","понедельник","вторник","среда","четверг","пятница","суббота"];
function tick(){const u=$("#upd");if(!u)return;const d=new Date();const p=n=>String(n).padStart(2,"0");const off=-d.getTimezoneOffset();const oh=off/60;
  const tz="UTC"+(off>=0?"+":"−")+(Number.isInteger(oh)?Math.abs(oh):Math.abs(oh).toFixed(1));
  u.innerHTML=`<span class="ck-d">${p(d.getDate())}.${p(d.getMonth()+1)}.${d.getFullYear()}, ${WD[d.getDay()]}</span><span class="ck-t"><b>${p(d.getHours())}:${p(d.getMinutes())}</b> <span class="ck-z">${tz}</span></span>`}
setInterval(tick,15000);
function go(v){VIEW=v;try{history.replaceState(null,"","#"+v)}catch(e){}render();window.scrollTo(0,0)}
const VIEWS={home:vHome,games:vGames,news:vNews,results:vResults,table:vTable,picks:vPicks,more:vMore,teams:vTeams,lead:vLead,power:vPower,inj:vInj,rus:vRus};
function render(){if(!D)return;renderChrome();const f=VIEWS[VIEW]||vHome;$("#app").innerHTML=f();afterRender()}
function afterRender(){const dc=$(".dch");if(dc){const on=dc.querySelector('[aria-pressed="true"]');on&&on.scrollIntoView({inline:"center",block:"nearest"})}}

/* лента счетов */
function stripHtml(){if(!D)return"";const d=lastDate();const gs=A.games.filter(g=>g.date===d);
  const up=(D.upcoming||[]).filter(m=>!A.games.some(g=>g.away===m.away&&g.home===m.home&&g.date>=nhlDate(m.start)));
  const row=(t,s,lo)=>`<div class="r ${lo?"lo":""}">${badge(t,38)}<span>${AB[t]||t}</span><b>${s}</b></div>`;
  const day=iso=>{const [a,b]=dShort(iso).split(" ");return `<span class="sday"><b>${esc(a)}</b>${esc(b||"")}</span>`};
  let h="";
  if(gs.length)h+=day(d)+gs.map(g=>{const aw=g.as>g.hs;return `<button class="sg" data-res="${g.date}" data-gid="${g.id}" aria-label="${EN[g.away]} ${g.as}, ${EN[g.home]} ${g.hs}"><small>Финал${endTag(g.end)?" · "+endTag(g.end):""}</small>${row(g.away,g.as,!aw)}${row(g.home,g.hs,aw)}</button>`}).join("");
  const upd=D.upcoming_date||(up[0]&&nhlDate(up[0].start));
  if(up.length)h+=(gs.length&&d===upd?"":day(upd))+up.map(m=>{const L=liveOf(m);const p=modelOf(m);
    if(L&&L.state!=="pre"){const aw=L.as>L.hs;return `<button class="sg" data-go="games" data-open="${m.away}-${m.home}"><small class="${L.state==="in"?"live":""}">${L.state==="in"?'<span class="dot"></span>'+esc(L.short):"Финал"+(L.end?" · "+L.end:"")}</small>${row(m.away,L.as,L.state==="post"&&!aw)}${row(m.home,L.hs,L.state==="post"&&aw)}</button>`}
    return `<button class="sg" data-go="games" data-open="${m.away}-${m.home}"><small>${kt(m.start)}</small>${row(m.away,p?pct(pB(p,"away")):"",false)}${row(m.home,p?pct(pB(p,"home")):"",false)}</button>`}).join("");
  /* дальше — матчи следующего игрового дня (и ещё одного, если их мало) */
  const fut=(D.week||[]).filter(w=>w.date>(upd||"")&&state(w.start)==="pre");const days=[...new Set(fut.map(w=>w.date))].sort();let n=0;
  for(const dd of days){if(n>=8)break;const gg=fut.filter(w=>w.date===dd).sort((a,b)=>a.start<b.start?-1:1);n+=gg.length;
    h+=day(dd)+gg.map(m=>{const p=modelOf(m);return `<button class="sg" data-go="games" data-open="${m.away}-${m.home}"><small>${kt(m.start)}</small>${row(m.away,p?pct(pB(p,"away")):"",false)}${row(m.home,p?pct(pB(p,"home")):"",false)}</button>`}).join("")}
  return h}

/* ===================== матчи: строка и разбор ===================== */
function tmLine(a,{p,f,sc,lo}){return `<span class="tm ${lo?"lo":""}">${logo(a,44)}<b>${EN[a]}</b><span class="rec">${rec(a)}</span>${sc!=null?`<span class="sc">${sc}</span>`:`${formDots(a)}${p!=null?`<span class="p ${f?"f":""}">${pct(p)}</span>`:""}`}</span>`}
function pcLine(a,p,f){return `<span class="${f?"f":""}" style="--c:${tcol(a)}" aria-label="${EN[a]}: ${pct(p)}"><i class="pc-team">${AB[a]}</i><span class="bar2"><i style="--w:${Math.round(p*100)}%"></i></span><b class="pc-value">${pct(p)}</b></span>`}
function timeCell(m,L){if(L&&L.state==="in")return `<span class="t lv">${esc(L.ps||L.per)}<small class="live"><span class="dot"></span>${esc(L.clock||"идёт")}</small></span>`;
  if(L&&L.state==="post")return `<span class="t">Финал<small>${L.end?endLong(L.end):kt(m.start)}</small></span>`;
  const s=state(m.start);return `<span class="t">${kt(m.start)}${s==="pre"&&rel(m.start)?`<small>${rel(m.start)}</small>`:s!=="pre"?"<small>идёт</small>":""}</span>`}
function gRow(m,{mo=false,nav=false}={}){const key=`${m.away}-${m.home}`,open=!nav&&OPEN.has(key);const p=modelOf(m);const L=liveOf(m);
  const pa=pB(p,"away"),ph=pB(p,"home");const fa=pa!=null&&pa>ph;
  const pickT=m.pick_side?sideTeam(m,m.pick_side):(p?fcOf(p,m).t:null);const tp=m.total_pick;const po=oddsOf(m,m.pick_side);const vs=vsOf(p,m);
  const lv=L&&L.state!=="pre";const aw=lv&&L.as>L.hs;
  const [ca,ch]=[tcol(m.away),tcol(m.home)];
  const btn=nav?`data-go="games" data-open="${key}"`:`data-tog="${key}" aria-expanded="${open}"`;
  return `<div class="mr${mo?" mo":""}${L&&L.flash?" flash":""}" id="g-${key}" style="--ca:${ca};--ch:${ch};--fc:${L&&L.flash?tcol(L.flash)+"55":"transparent"}"><button class="row" ${btn}>${timeCell(m,L)}
    <span class="tms">${tmLine(m.away,{p:pa,f:fa,sc:lv?L.as:null,lo:lv&&L.state==="post"&&!aw})}${tmLine(m.home,{p:ph,f:!fa,sc:lv?L.hs:null,lo:lv&&L.state==="post"&&aw})}</span>
    <span class="pcs">${pa!=null?pcLine(m.away,pa,fa)+pcLine(m.home,ph,!fa):""}</span>
    <span class="pk">${pickT?`<span class="k"><small>Модель</small>${RU[pickT]}${po?` · ${f2(po)}`:""}</span>`:""}${tp?`<span class="k"><small>Тотал</small>${tp.side==="over"?"Больше":"Меньше"} ${esc(tp.line)}${tp.odds?` · ${f2(tp.odds)}`:""}</span>`:""}${lv?liveChips(m,L):""}${vs&&!lv&&(vs.win||vs.tot)?`<span class="chip gold">Против рынка: ${[vs.win?"исход":"",vs.tot?"тотал":""].filter(Boolean).join(" и ")}</span>`:""}</span>${IC.chev}
    ${mo&&D.motd&&D.motd.text?`<span class="mo-t"><b>Матч дня.</b> ${esc(D.motd.text)}</span>`:""}</button>${open?gDetail(m,p,L):""}</div>`}
function liveChips(m,L){const out=[];const ps=m.pick_side;const tp=m.total_pick;
  const st=(r,fin,lab)=>`<span class="chip ${r==="hit"?"win":r==="miss"?"loss":""}">${lab}: ${r==="hit"?(fin?"угадан":"заходит"):r==="miss"?(fin?"мимо":"не заходит"):"ничья"}</span>`;
  if(ps){const x=legLive(m.away,m.home,ps);if(x)out.push(st(x.r,x.fin,"Прогноз"))}
  if(tp){const x=liveRes({type:"total",away:m.away,home:m.home,side:tp.side,line:tp.line});if(x)out.push(st(x.r,x.fin,"Тотал"))}
  return out.join("")}
/* полоса вероятностей: подпись · левое % · полоса · правое % */
function pbar(lab,l,r,cl,cr,ll="",rl=""){if(l==null||r==null)return"";return `<div class="pbr"><small>${lab}</small><b class="${l>=r?"on":""}">${ll?`<i>${ll}</i> `:""}${pct(l)}</b><span class="two"><i style="width:${l*100}%;background:${cl};opacity:${l>=r?1:.45}"></i><i style="width:${r*100}%;background:${cr};opacity:${r>l?1:.45}"></i></span><b class="${r>l?"on":""}">${pct(r)}${rl?` <i>${rl}</i>`:""}</b></div>`}
function vsBox(p,m){const vs=vsOf(p,m);if(!vs)return"";const tl=m.total_pick?m.total_pick.line:(m.odds||{}).total;
  const [ca,ch]=tpair(m.away,m.home);const TU="var(--mute)",TO="var(--gold)";
  const msg=vs.win&&vs.tot?"Модель против рынка и в исходе, и в тотале.":vs.win?`Модель против рынка: рынок за «${RU[vs.mk.t]}», модель — за «${RU[vs.f.t]}».`:vs.tot?`В исходе модель с рынком согласна, а в тотале — нет.`:"Модель согласна с рынком.";
  return `<div class="vsb full"><h4>Исход</h4>${pbar("Модель",p.p_away,p.p_home,ca,ch,m.away,m.home)}${pbar("Рынок",p.mkt_away,p.mkt_home,ca,ch,m.away,m.home)}
   ${p.p_over!=null?`<h4>Тотал${tl!=null?" "+esc(tl):""}</h4>${pbar("Модель",p.p_under,p.p_over,TU,TO,"М","Б")}${p.mkt_over!=null?pbar("Рынок",1-p.mkt_over,p.mkt_over,TU,TO,"М","Б"):""}`:""}
   <p class="${vs.win||vs.tot?"df":""}">${msg}</p></div>`}
function booksTable(m){const o=m.odds,x=m.odds_1x,bk=m.books||{};if(!o&&!x&&!Object.keys(bk).length)return"";
  const r=(name,note,a,h,t)=>`<tr><td>${name}<small>${note}</small></td><td>${f2(a)}</td><td>${f2(h)}</td><td>${t&&t.total!=null?`${t.total}: ${f2(t.over)} / ${f2(t.under)}`:"—"}</td></tr>`;
  const BN={marathonbet:"Линия 3",onexbet:"Линия 2"};
  return `<table class="mt"><thead><tr><th>Линия</th><th>${EN[m.away]}</th><th>${EN[m.home]}</th><th>Тотал Б / М</th></tr></thead><tbody>
   ${o?r("Линия 1","ориентир, победа с ОТ",o.away,o.home,o):""}${x&&x.home?r("Линия 2",`основное время, ничья ${f2(x.draw)}`,x.away,x.home,x):""}
   ${Object.entries(bk).filter(([k])=>k!=="onexbet"||!x).map(([k,b])=>r(BN[k]||esc(k),b.draw?`основное время, ничья ${f2(b.draw)}`:"с ОТ",b.away,b.home,b)).join("")}</tbody></table>`}
function injOut(a){return (((D.teams||{})[a]||{}).injuries||[]).filter(x=>/IR|Out|LTIR|DTD/i.test(x.status||""))}
function modelBlk(p,m,openIt){if(!p)return"";const es=essayOf(p);const h2h=p.h2h||[];
  return `<details class="more"${openIt?" open":""}><summary>Как считала модель</summary><div class="in">
    <div class="blk">${es.length?`<div class="ess">${es.map(x=>`<p>${esc(x)}</p>`).join("")}</div>`:""}
     <div class="kv"><div><small>Модель</small><b>${pct(p.p_away)} : ${pct(p.p_home)}</b></div>${p.mkt_home!=null?`<div><small>Рынок</small><b>${pct(p.mkt_away)} : ${pct(p.mkt_home)}</b></div>`:""}<div><small>Ожидаемые голы</small><b>${nz(p.lam_away)} : ${nz(p.lam_home)}</b></div><div><small>Ничья в осн. время</small><b>${pct(p.p_ot)}</b></div></div></div>
    <div class="blk"><h4 style="margin-top:0">Из чего складывается оценка</h4><ul class="ul">${modelWhy(m||p,p).map(x=>`<li>${x}</li>`).join("")}</ul>
     ${h2h.length?`<h4>Личные встречи в сезоне</h4><ul class="ul">${h2h.map(g=>`<li>${esc(dShort(g.date))}: ${EN[g.away]} — ${EN[g.home]} <b>${esc(g.score)}</b>${g.end&&g.end!=="REG"?" "+endTag(g.end):""}</li>`).join("")}</ul>`:""}</div></div></details>`}
function gDetail(m,p,L){const tp=m.total_pick;const pickT=m.pick_side?sideTeam(m,m.pick_side):(p?fcOf(p,m).t:null);const po=oddsOf(m,m.pick_side);
  const ga=m.goalies||[];const injA=injOut(m.away),injH=injOut(m.home);
  const pick=pickT||tp?`<div class="picks full">${pickT?`<div><small>Прогноз модели на исход</small><b>${RU[pickT]}${po?`<em>${f2(po)}</em>`:""}</b>${m.lean?`<p>${esc(m.lean)}</p>`:""}</div>`:""}${tp?`<div><small>Прогноз модели на тотал</small><b>${tp.side==="over"?"Больше":"Меньше"} ${esc(tp.line)}${tp.odds?`<em>${f2(tp.odds)}</em>`:""}</b>${tp.lean?`<p>${esc(tp.lean)}</p>`:""}</div>`:""}</div>`:"";
  const fac=(m.factors||[]).length?`<div class="blk"><h4>Почему так</h4><ul class="ul">${m.factors.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`:"";
  const gl=`<div class="blk"><h4>Вратари</h4><div class="kv">${[0,1].map(i=>{const t=i?m.home:m.away;const gp=p&&(i?p.goalie_home:p.goalie_away);const nm=String(ga[i]||"").split(" (")[0];
      return `<div><small>${EN[t]}</small><span style="display:flex;align-items:center;gap:8px">${nm&&nm!=="не объявлен"?photo(nm,t,44):""}<b style="font-family:var(--f-body);font-size:var(--fs-s)">${esc(ga[i]||"не объявлен")}</b></span>${gp&&gp.sv?`<small>${nz(gp.sv*100)}% отражённых · ${gp.gp} и.</small>`:""}</div>`}).join("")}</div>
    ${(injA.length||injH.length)?`<h4>Без кого играют</h4><ul class="ul">${[[m.away,injA],[m.home,injH]].filter(x=>x[1].length).map(([t,l])=>`<li><b>${EN[t]}:</b> ${l.map(x=>pref(x.name,t)).join(", ")}</li>`).join("")}</ul>`:""}</div>`;
  const lines=(m.odds||m.books||m.odds_1x)?`<div class="blk full"><h4>Линии</h4>${booksTable(m)}</div>`:"";
  const live=L&&L.state!=="pre"?liveBlock(m,L):"";
  return `<div class="x">${live}${pick}${live?"":vsBox(p,m)}${fac}${gl}${lines}${modelBlk(p,m)}<div class="acts full"><button class="btn" data-team="${m.away}">${logo(m.away,24)}${EN[m.away]}</button><button class="btn" data-team="${m.home}">${logo(m.home,24)}${EN[m.home]}</button></div></div>`}
function wRow({p,m,start}){const key="w"+(p.id||p.away+p.home),open=OPEN.has(key);const pa=pB(p,"away"),ph=pB(p,"home");const fa=pa>ph;
  const b2b=[p.b2b_away&&RU[p.away],p.b2b_home&&RU[p.home]].filter(Boolean);
  return `<div class="mr" id="${key}" style="--ca:${tcol(p.away)};--ch:${tcol(p.home)}"><button class="row" data-tog="${key}" aria-expanded="${open}"><span class="t">${kt(start)}</span>
    <span class="tms">${tmLine(p.away,{p:pa,f:fa})}${tmLine(p.home,{p:ph,f:!fa})}</span><span class="pcs">${pcLine(p.away,pa,fa)}${pcLine(p.home,ph,!fa)}</span>
    <span class="pk"><span class="k"><small>Модель</small>${RU[fa?p.away:p.home]}</span>${b2b.length?`<span class="k"><small>Второй матч подряд</small>${b2b.join(", ")}</span>`:""}</span>${IC.chev}</button>${open?`<div class="x">${modelBlk(p,m,true)}</div>`:""}</div>`}
function weekList(){const ids=new Set((D.upcoming||[]).map(x=>x.away+x.home));const all=mGames().filter(g=>(g.p.date||g.m.date)>(D.upcoming_date||"")&&!ids.has(g.p.away+g.p.home));if(!all.length)return"";
  const by={};all.forEach(g=>{const d=g.p.date||g.m.date;(by[d]=by[d]||[]).push(g)});
  return `<section class="sec"><div class="hd"><h2>Дальше на неделе<small>предварительно, по модели без линии</small></h2></div>${Object.entries(by).map(([d,gs],k)=>`<details class="day" ${k?"":"open"}><summary>${esc(dLong(d))}<small>${plural(gs.length,"матч","матча","матчей")}</small></summary><div class="box">${gs.map(wRow).join("")}</div></details>`).join("")}</section>`}
function confLine(){const ex=confLegs();return ex.length?`<p class="txt">Самые уверенные исходы: ${ex.map(x=>`<b>${RU[x.t]}</b> ${pct(x.p)}`).join(", ")}</p>`:""}
function todayGames(){return (D.upcoming||[]).slice().sort((a,b)=>String(a.start).localeCompare(String(b.start)))}
function vGames(){const u=todayGames();const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  if(!u.length)return `<div class="col">${noGames()}${weekList()}</div>`;
  return `<div class="col"><section class="sec"><div class="hd"><h1>Матчи<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h1></div>${confLine()}
    <div class="box">${u.map(m=>gRow(m,{mo:m===mo})).join("")}</div>
    <p class="note">Проценты и прогнозы — собственная оценка модели, без подмешивания рынка; кэфы — линия-ориентир. «Против рынка» — модель выбрала не ту сторону, что фаворит линии: это самые интересные прогнозы, их счёт ведётся отдельно в «Прогнозах». Во время матча счёт обновляется сам.</p></section>${weekList()}</div>`}
function noGames(){const nx=(D.week||[]).filter(g=>state(g.start)==="pre").sort((a,b)=>a.start<b.start?-1:1)[0];
  return `<section class="sec"><div class="hd"><h1>Матчи</h1></div><div class="box empty">Сегодня матчей нет.${nx?` Следующий игровой день — ${esc(dLong(nx.date||nhlDate(nx.start)))}, первый матч в ${kt(nx.start)} по Кирову.`:""}</div></section>`}

/* ===================== главная ===================== */
function topScorer(t){return (D.skaters||[]).filter(s=>s.team===t).sort((a,b)=>b.pts-a.pts||b.g-a.g)[0]}
function posterSec(){const mo=D.motd;if(!mo)return"";const m=(D.upcoming||[]).find(x=>x.away===mo.away&&x.home===mo.home);if(!m||state(m.start)==="done")return"";
  const p=modelOf(m);const L=liveOf(m);const [ca,ch]=pair(m.away,m.home);const pa=pB(p,"away"),ph=pB(p,"home");
  const lv=L&&L.state!=="pre";
  const side=(t,cls)=>`<button class="side ${cls}" data-team="${t}">${badge(t,42)}<span><b>${EN[t]}</b><small>${rec(t)}${TEAMS[t]&&TEAMS[t].gp?" · "+place(t)+"-е место":""}</small></span></button>`;
  const mid=lv?`<b>${L.as}:${L.hs}</b><small>${L.state==="in"?'<span class="dot"></span> '+esc(L.short):"финал"}</small>`:`<b>${kt(m.start)}</b><small>${esc(rel(m.start)||"")}</small>`;
  return `<section class="poster motd-compact" style="--a:${ca};--h:${ch};--ta:${tpair(m.away,m.home)[0]};--th:${tpair(m.away,m.home)[1]}"><div class="bg"><span class="wm a">${logo(m.away,420)}</span><span class="wm h">${logo(m.home,420)}</span></div><div class="in">
    <div class="lab"><span>Матч дня</span><span>${esc(dLong(D.upcoming_date))}</span><button class="go" data-go="games" data-open="${m.away}-${m.home}">Разбор матча →</button></div>
    <div class="vs">${side(m.away,"a")}<div class="mid">${mid}</div>${side(m.home,"h")}</div>
    ${pa!=null&&!lv?`<div class="pbs">${pbar("Модель",pa,ph,"var(--ta)","var(--th)")}${p.mkt_home!=null?pbar("Рынок",p.mkt_away,p.mkt_home,"var(--ta)","var(--th)"):""}${(()=>{const mt=modTot(p),kt2=mktTot(p);const tl=(m.total_pick||{}).line??(m.odds||{}).total;if(!mt||tl==null)return"";const S=s=>s==="over"?"больше":"меньше";
      return `<div class="ptot">Тотал ${esc(tl)}: модель за ${S(mt.side)} (${pct(mt.p)})${kt2?`, рынок ${kt2.side===mt.side?"тоже":"за "+S(kt2.side)} (${pct(kt2.p)})`:""}</div>`})()}</div>`:""}
    </div></section>`}
function todaySec(){const u=todayGames();if(!u.length)return noGames();const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  return `<section class="sec"><div class="hd"><h2>Сегодня<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h2><button class="lnk" data-go="games">Все матчи</button></div>
    <div class="box">${u.map(m=>gRow(m,{nav:true,mo:m===mo&&false})).join("")}</div>${confLine()}</section>`}
function nightSec(){const d=lastDate();if(!d)return"";/* пока идёт игровой день, его финалы уже видны в «Сегодня» — блок «Ночь» не дублируем */if(D.upcoming_date&&d>=D.upcoming_date)return"";const gs=A.games.filter(g=>g.date===d);
  return `<section class="sec"><div class="hd"><h2>Ночь<small>${esc(dLong(d))}</small></h2><button class="lnk" data-go="results">Итоги и протоколы</button></div>
    <div class="box"><div class="scores">${gs.map(g=>{const aw=g.as>g.hs;return `<button class="sc1" data-res="${g.date}" data-gid="${g.id}"><span class="r ${aw?"":"lo"}">${logo(g.away,40)}${EN[g.away]}<b>${g.as}</b></span><span class="r ${aw?"lo":""}">${logo(g.home,40)}${EN[g.home]}<b>${g.hs}</b></span>${endTag(g.end)?`<small>${endLong(g.end)}</small>`:""}</button>`}).join("")}</div></div></section>`}

/* герои игрового дня */
function sensation(n){if(n.sensation)return n.sensation;const d=n.date;
  const j=(D.journal||[]).filter(x=>x.date===d&&x.result==="miss"&&x.odds&&x.odds<2&&(x.type==="win"||x.type==="total")).sort((a,b)=>(a.type==="win"?0:1)-(b.type==="win"?0:1)||a.odds-b.odds)[0];if(!j)return null;
  const g=A.games.find(x=>x.date===d&&x.away===j.away&&x.home===j.home);if(!g)return null;const p=Math.round(100/j.odds/1.04)/100;
  if(j.type==="win"){const w=g.as>g.hs?g.away:g.home;return {id:g.id,kind:"исход",head:`Победа аутсайдера: ${EN[w]}`,fav:j.pick,p}}
  return {id:g.id,kind:"тотал",head:`Тотал ${g.as+g.hs} при линии ${j.line}`,p,tot:pickLabel(j)}}
function svp(l){const m=/(\d+)\s*из\s*(\d+)/.exec(l||"");return m&&+m[2]?nz(m[1]/m[2]*100)+"% отражённых":""}
function card3(x,i){const n=pnum(x.name,x.pos);return `<article class="card3" style="--c:${tdeep(x.team)}"><div class="top3"><span class="wm">${logo(x.team,120)}</span><span class="rk">${i+1}<i>★</i></span>${n&&headOf(x.name)?`<span class="num3">#${n}</span>`:""}${photo(x.name,x.team,118)}</div>
  <div class="bd"><div class="nm"><span>${plink(x.name,x.team)}${posTag(x.name,x.pos)}<small>${esc(FULL[x.team]||x.team)}</small></span><b class="v">${lineHtml(x.line)}</b></div>${x.text?`<p>${esc(x.text)}</p>`:""}</div></article>`}
function feat(x,role,big,sub){return `<div class="feat">${photo(x.name,x.team,92,"ring")}<span class="nm2"><span>${plink(x.name,x.team)}${posTag(x.name,x.pos)}</span><small>${role} · ${esc(FULL[x.team]||x.team)}</small></span><span class="big">${lineHtml(big)}${sub?`<small>${sub}</small>`:""}</span>${x.text?`<p>${esc(x.text)}</p>`:""}</div>`}
function heroPanel(n){const t=HERO_TAB;
  if(t==="stars")return `<div class="cards">${n.heroes.slice(0,3).map(card3).join("")}</div>`;
  if(t==="goalie")return `<div class="box">${feat(n.goalie,"Вратарь дня",n.goalie.line,svp(n.goalie.line))}</div>`;
  if(t==="russian")return `<div class="box">${feat(n.russian,"Россиянин дня",n.russian.line)}</div>`;
  if(t==="sense"){const x=sensation(n);const g=x&&A.games.find(y=>y.id===x.id);if(!g)return"";
    const why=x.kind==="исход"&&x.fav?`Фаворитом был <b>${EN[x.fav]}</b>${x.p?` — линия давала около ${Math.round(x.p*100)}%`:""}.`:x.tot?`Линия ждала: <b>${esc(x.tot)}</b>${x.p?`, около ${Math.round(x.p*100)}%`:""}.`:"";
    return `<div class="box sense"><div class="sc"><span class="${x.fav===g.away?"fav":""}">${logo(g.away,46)}${EN[g.away]}</span><b>${g.as}:${g.hs}</b><span class="${x.fav===g.home?"fav":""}">${EN[g.home]}${logo(g.home,46)}</span></div><h3>${esc(x.head||"")}</h3>${why?`<p class="txt">${why}</p>`:""}${x.text?`<p class="txt">${esc(x.text)}</p>`:""}<button class="lnk" style="align-self:flex-start" data-res="${g.date}" data-gid="${g.id}">Протокол матча</button></div>`}
  if(t==="flop"){const x=(n.antiheroes||[])[0],tm=n.worst_team;
    return `<div class="box">${x?`<div class="flop"><span class="tag">Игрок</span>${photo(x.name,x.team,64)}<span class="nm2"><span>${plink(x.name,x.team)}${posTag(x.name,x.pos)}</span><small>${esc(FULL[x.team]||x.team)}</small></span><span class="v">${lineHtml(x.line)}</span>${x.text?`<p>${esc(x.text)}</p>`:""}</div>`:""}
      ${tm?`<div class="flop"><span class="tag">Команда</span>${logo(tm.abbr,60)}<span class="nm2"><button class="plink" data-team="${tm.abbr}">${esc(FULL[tm.abbr]||tm.abbr)}</button><small>${rec(tm.abbr)}</small></span>${formDots(tm.abbr)}${tm.text?`<p>${esc(tm.text)}</p>`:""}</div>`:""}</div>`}
  return""}
function heroTabs(n){return [["stars","Три звезды",n.heroes&&n.heroes.length],["goalie","Вратарь дня",n.goalie],["russian","Россиянин дня",n.russian],["sense","Сенсация",sensation(n)],["flop","Неудачники",(n.antiheroes||[]).length||n.worst_team]].filter(t=>t[2])}
function heroesBody(){const n=D.daily;const t=heroTabs(n);if(!t.some(x=>x[0]===HERO_TAB))HERO_TAB=t[0][0];
  return `<div class="pills" role="tablist">${t.map(x=>`<button role="tab" data-ht="${x[0]}" aria-selected="${x[0]===HERO_TAB}">${x[1]}</button>`).join("")}</div><div class="appear">${heroPanel(n)}</div>`}
function heroesSec(){const n=D.daily;if(!n||!n.heroes||!n.heroes.length)return"";
  return `<section class="sec"><div class="hd"><h2>Герои игрового дня<small>${esc(dLong(n.date||lastDate()))}</small></h2><button class="lnk" data-go="results">Все итоги</button></div><div id="hb" class="sec">${heroesBody()}</div></section>`}

/* новости */
function leadCard(x,noCover){return `<button class="lead" data-art="${x.k}">${noCover?"":coverHtml(x)}<span class="tx">${metaHtml(x)}<h3>${esc(x.title)}</h3><p>${esc(x.dek||(typeof x.body[0]==="string"?x.body[0]:"")||"")}</p></span></button>`}
function nrow(x){return `<button class="nr" data-art="${x.k}">${metaHtml(x)}<h4>${esc(x.title)}</h4><p>${esc(x.dek||(typeof x.body[0]==="string"?x.body[0]:"")||"")}</p>${coverHtml(x,"th",false)}</button>`}
function newsBlock(limit){const arts=articles();const col=arts.find(x=>x.kind==="column");const sty=arts.find(x=>x.kind==="story");const news=arts.filter(x=>x.kind==="news");if(!news.length&&!col)return"";
  const lead=news[0];const rest=limit?news.slice(1,limit+1):news.slice(1);
  return `${lead?`<div class="box">${leadCard(lead)}${rest.map(nrow).join("")}</div>`:""}${sty?`<div class="box stm">${leadCard(sty)}</div>`:""}${col?`<div class="box colm">${leadCard(col,true)}</div>`:""}`}
function homeStoryRow(x){return `<button class="home-story-row" data-art="${x.k}"><span class="home-story-copy">${metaHtml(x)}<b>${esc(x.title)}</b>${x.dek?`<small>${esc(x.dek)}</small>`:""}</span>${coverHtml(x,"home-thumb",false)}</button>`}
function homeHeadline(x){return `<button class="home-headline" data-art="${x.k}"><span class="square" aria-hidden="true">▪</span><span>${esc(x.title)}<small>${x.source?esc(x.source)+" · ":""}${x.time?esc(dShort(String(x.time).slice(0,10))):""}</small></span></button>`}
function homeNewsGrid(){const arts=articles(),news=arts.filter(x=>x.kind==="news");if(!news.length)return"";
  const lead=news.find(x=>x.image)||news[0],rest=news.filter(x=>x!==lead),middle=rest.slice(0,3),heads=rest.slice(3,7),story=arts.find(x=>x.kind==="story"),col=arts.find(x=>x.kind==="column");
  return `<section class="sec home-edition"><div class="home-edition-head"><h1>NHL</h1><span>Истории, результаты и цифры</span><button class="lnk" data-go="news">Все материалы →</button></div>
    <div class="editorial-grid"><div class="ed-feature">${leadCard(lead)}</div>
      <div class="ed-secondary"><h2>Свежие материалы</h2>${middle.map(homeStoryRow).join("")}${story?homeStoryRow(story):""}</div>
      <aside class="ed-headlines"><div class="ed-headline-title"><h2>Заголовки</h2><button class="lnk" data-go="news">Все</button></div>${heads.map(homeHeadline).join("")}${col?`<button class="home-claude" data-art="${col.k}"><small>Колонка Claude</small><b>${esc(col.title)}</b><span>${esc(col.dek||"")}</span></button>`:""}</aside>
    </div></section>`}
function newsSec(){return homeNewsGrid()}
function storiesList(){const s=articles().filter(x=>x.kind==="story");if(s.length<2)return"";return `<section class="sec"><div class="hd"><h2>История<small>все материалы рубрики</small></h2></div><div class="box">${s.slice(1).map(nrow).join("")}</div></section>`}
function vNews(){const b=newsBlock(0);return `<div class="col"><section class="sec"><div class="hd"><h1>Новости<small>пересказ по-русски за последние сутки</small></h1></div>${b||'<div class="box empty">Новостей пока нет — они появляются после утреннего обновления.</div>'}</section>${storiesList()}</div>`}

/* правая колонка */
function jAll(){return (D.journal||[]).map(x=>{const lv=typeof liveRes==="function"?liveRes(x):null;return lv&&lv.fin&&!x.result?{...x,result:lv.r}:x})}
function accW(){const j=jAll().filter(x=>x.result&&x.result!=="void");if(!j.length)return"";const hit=j.filter(x=>x.result==="hit").length;
  return `<section class="box"><div class="wg-h"><h3>Точность модели</h3><button class="lnk" data-go="picks">Журнал</button></div><div class="acc"><b>${Math.round(hit/j.length*100)}%</b><span>${hit} из ${j.length} прогнозов угадано с начала журнала</span></div></section>`}
function standW(){const list=ALL.filter(a=>CONF_OF[a]===RAIL_CONF).map(a=>TEAMS[a]).sort(cmp);
  return `<section class="box"><div class="wg-h"><h3>Таблица</h3><button class="lnk" data-go="table">Полностью</button></div><div class="pills wg-pills">${["Восток","Запад"].map(c=>`<button data-rconf="${c}" aria-pressed="${RAIL_CONF===c}">${c}</button>`).join("")}</div>
   <table class="wtab"><thead><tr><th></th><th>Команда</th><th>И</th><th>О</th></tr></thead><tbody>${list.map((t,i)=>`<tr class="${i===8?"cut":""}" data-team="${t.abbr}" style="cursor:pointer"><td>${i+1}</td><td><span class="tn">${logo(t.abbr,32)}${EN[t.abbr]}</span></td><td>${t.gp}</td><td class="p">${t.pts}</td></tr>`).join("")}</tbody></table></section>`}
const LTABS=[["points","Очки"],["goals","Голы"],["assists","Передачи"],["pm","+/−"],["gk","Вратари"]];
function leaderRows(k,n=10){const S=(D.skaters||[]).filter(s=>s.gp>0);
  if(k==="points")return S.slice().sort((a,b)=>b.pts-a.pts||b.g-a.g||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.pts,sub:`${s.g} Г · ${s.a} П · ${s.gp} И`}));
  if(k==="goals")return S.slice().sort((a,b)=>b.g-a.g||b.pts-a.pts||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.g,sub:`${s.gp} И`}));
  if(k==="assists")return S.slice().sort((a,b)=>b.a-a.a||b.pts-a.pts||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.a,sub:`${s.gp} И`}));
  if(k==="pm")return S.slice().sort((a,b)=>b.pm-a.pm||b.pts-a.pts).slice(0,n).map(s=>({...s,v:(s.pm>0?"+":"")+s.pm,sub:`${s.pts} очк.`}));
  return (D.goalies||[]).filter(g=>g.gp>=3).sort((a,b)=>b.sv-a.sv||a.gaa-b.gaa).slice(0,n).map(g=>({...g,pos:"G",v:nz(g.sv*100)+"%",sub:`${g.w}-${g.l}-${g.otl} · ${nz(g.gaa,2)} КН`}))}
function lrow(r,i,v,sub){return `<div class="lr"><span class="n">${i+1}</span><span class="who">${photo(r.name,r.team,40)}<span class="nm2"><span>${plink(r.name,r.team)}${posTag(r.name,r.pos)}</span><small title="${esc(sub||"")}">${esc(sub||"")}</small></span></span><span class="v">${v}</span></div>`}
function railLeaderSub(r){if(RAIL_LEAD==="points")return `${AB[r.team]} · ${r.g} Г · ${r.a} П · ${r.gp} И`;if(RAIL_LEAD==="goals"||RAIL_LEAD==="assists")return `${AB[r.team]} · ${r.gp} И`;if(RAIL_LEAD==="pm")return `${AB[r.team]} · ${r.pts} О`;return `${AB[r.team]} · ${r.w}-${r.l}-${r.otl} · ${nz(r.gaa,2)} КН`}
function leadersW(){return `<section class="box"><div class="wg-h"><h3>Лидеры</h3><button class="lnk" data-go="lead">Все</button></div><div class="pills wg-pills">${LTABS.map(([k,l])=>`<button data-rlead="${k}" aria-pressed="${RAIL_LEAD===k}">${l}</button>`).join("")}</div>${leaderRows(RAIL_LEAD,6).map((r,i)=>lrow(r,i,r.v,railLeaderSub(r))).join("")}</section>`}
function staleBanner(){const f=freshness();return f.old?`<div class="banner">Данные давно не обновлялись — последний сбор ${esc(kdt(D.generated))}. Счёт матчей обновляется сам, остальное подтянется со следующим сбором.</div>`:""}
function vHome(){return `${staleBanner()}<div class="home-stack">${posterSec()}${newsSec()}<div class="home-lower"><div class="col">${todaySec()}${nightSec()}${heroesSec()}</div><aside class="col">${accW()}${standW()}${leadersW()}</aside></div></div>`}

/* ===================== итоги ===================== */
/* гол…8686 tokens truncated…неаполис","St. Louis":"Сент-Луис","Dallas":"Даллас","Denver":"Денвер","Los Angeles":"Лос-Анджелес","New York":"Нью-Йорк","Ufa":"Уфа","Kazan":"Казань","Yaroslavl":"Ярославль","Chelyabinsk":"Челябинск","Magnitogorsk":"Магнитогорск","Omsk":"Омск","Novosibirsk":"Новосибирск","Nizhny Novgorod":"Нижний Новгород","Yekaterinburg":"Екатеринбург","Tolyatti":"Тольятти","Togliatti":"Тольятти","Khabarovsk":"Хабаровск","Cherepovets":"Череповец","Novokuznetsk":"Новокузнецк","Perm":"Пермь","Kurgan":"Курган","Tyumen":"Тюмень","Penza":"Пенза","Saratov":"Саратов","Voskresensk":"Воскресенск","Elektrostal":"Электросталь","Podolsk":"Подольск","Mytishchi":"Мытищи","Balashikha":"Балашиха","Krasnoyarsk":"Красноярск","Sochi":"Сочи","Vladivostok":"Владивосток","Almaty":"Алматы","Astana":"Астана"};
const CLUB={"CSKA Moskva":"ЦСКА","CSKA Moscow":"ЦСКА","SKA St. Petersburg":"СКА","SKA Saint Petersburg":"СКА","Dynamo Moskva":"«Динамо» Москва","Dynamo Moscow":"«Динамо» Москва","Spartak Moskva":"«Спартак»","Spartak Moscow":"«Спартак»","Lokomotiv Yaroslavl":"«Локомотив»","Ak Bars Kazan":"«Ак Барс»","Salavat Yulaev Ufa":"«Салават Юлаев»","Metallurg Magnitogorsk":"«Металлург» Мг","Metallurg Novokuznetsk":"«Металлург» Нк","Novokuznetsk":"«Металлург» Нк","Avangard Omsk":"«Авангард»","Traktor Chelyabinsk":"«Трактор»","Torpedo Nizhny Novgorod":"«Торпедо»","Severstal Cherepovets":"«Северсталь»","Avtomobilist Yekaterinburg":"«Автомобилист»","Sibir Novosibirsk":"«Сибирь»","Amur Khabarovsk":"«Амур»","Neftekhimik Nizhnekamsk":"«Нефтехимик»","Lada Togliatti":"«Лада»","Vityaz Podolsk":"«Витязь»","Admiral Vladivostok":"«Адмирал»","HC Sochi":"«Сочи»","Barys Astana":"«Барыс»","Dinamo Minsk":"«Динамо» Минск","Kunlun Red Star":"«Куньлунь»","Jokerit Helsinki":"«Йокерит»","Dinamo Riga":"«Динамо» Рига"};
const LEAGUE={NHL:"НХЛ",KHL:"КХЛ",AHL:"АХЛ",ECHL:"ECHL",MHL:"МХЛ",VHL:"ВХЛ",SHL:"Швеция",Liiga:"Финляндия","SM-liiga":"Финляндия",NL:"Швейцария",DEL:"Германия",ELH:"Чехия",Extraliga:"Чехия",OHL:"OHL",WHL:"WHL",QMJHL:"QMJHL",USHL:"USHL",NCAA:"NCAA","Russia-Jr.":"юниоры","H-East":"NCAA","Hockey East":"NCAA","Big Ten":"NCAA","NCHC":"NCAA","WCHA":"NCAA","ECAC":"NCAA","CCHA":"NCAA","NTDP":"США U18","USDP":"США U18","USNTDP":"США U18","J20 SuperElit":"Швеция, мол.","J20 Nationell":"Швеция, мол.","U20 SM-liiga":"Финляндия, мол.","Fin-Jr.":"Финляндия, мол.","HockeyAllsvenskan":"Швеция-2","Sweden":"Швеция","Finland":"Финляндия","Sweden-2":"Швеция-2","Russia2":"ВХЛ","Russia3":"ВХЛ"};
/* путь по клубам — только профессиональные и основные юниорские лиги; турниры сборных — отдельным блоком */
const CLUB_LG=new Set(["NHL","AHL","ECHL","KHL","VHL","MHL","Russia","Russia-Jr.","SHL","Sweden","HockeyAllsvenskan","Sweden-2","J20 SuperElit","J20 Nationell","Liiga","Finland","Mestis","U20 SM-liiga","Fin-Jr.","NL","Swiss","DEL","Germany","ELH","Czech","Czechia","Extraliga","Slovakia","OHL","WHL","QMJHL","USHL","NCAA","H-East","Big Ten","NCHC","WCHA","ECAC","CCHA","Hockey East","NTDP","USDP","USNTDP","Austria","ICEHL","Norway","Denmark","Latvia","Belarus","BCHL","AJHL"]);
const NAT={"OG":["ОИ",9],"Olympics":["ОИ",9],"4 Nations":["Турнир четырёх наций",8],"WCup":["Кубок мира",8],"WC":["ЧМ",7],"WC-A":["ЧМ",7],"WJC-20":["МЧМ",5],"WJC-A":["МЧМ",5],"WJC-18":["ЮЧМ U18",4],"WJ18-A":["ЮЧМ U18",4]};
const NATC={"Canada":"Канада","USA":"США","United States":"США","Russia":"Россия","Sweden":"Швеция","Finland":"Финляндия","Czechia":"Чехия","Czech Republic":"Чехия","Slovakia":"Словакия","Germany":"Германия","Switzerland":"Швейцария","Latvia":"Латвия","Denmark":"Дания","Norway":"Норвегия","Austria":"Австрия","Belarus":"Беларусь","France":"Франция","Slovenia":"Словения","Kazakhstan":"Казахстан","Team Europe":"Сборная Европы","Team North America":"Северная Америка","Team Canada":"Канада","Team USA":"США"};
const INTL={test:lg=>!CLUB_LG.has(lg)};
function trl(s){if(!s)return"";if(TRX[s])return TRX[s];if(CLUB[s])return CLUB[s];if(/[А-яЁё]/.test(s))return s;
  let t=" "+String(s)+" ";const R=[["shch","щ"],["sch","ш"],["sh","ш"],["ch","ч"],["zh","ж"],["kh","х"],["ts","ц"],["tz","ц"],["ya","я"],["yu","ю"],["yo","ё"],["ye","е"],["ee","и"],["oo","у"],["ou","у"],["th","т"],["ph","ф"],["ck","к"],["qu","кв"],["x","кс"],["w","в"],["j","дж"],["ä","я"],["ö","ё"],["ü","ю"],["å","о"],["é","е"],["è","е"],["ç","с"]];
  t=t.toLowerCase();for(const [a,b] of R)t=t.split(a).join(b);
  t=t.replace(/c(?=[eiy])/g,"с").replace(/c/g,"к").replace(/(?<=[aeiouаеёиоуыэюя])y/g,"й").replace(/y/g,"и");
  const M={a:"а",b:"б",d:"д",e:"е",f:"ф",g:"г",h:"х",i:"и",k:"к",l:"л",m:"м",n:"н",o:"о",p:"п",r:"р",s:"с",t:"т",u:"у",v:"в",z:"з"};t=t.replace(/[a-z]/g,ch=>M[ch]||ch).trim();
  return t.replace(/(^|[\s\-.])([а-яё])/g,(m,p,c)=>p+c.toUpperCase())}
const CLUB2={"USNTDP":"Программа сборной США","USNTDP Juniors":"Программа сборной США","USA U-18":"Программа сборной США","U.S. National U18 Team":"Сборная США U18","U.S. National U17 Team":"Сборная США U17","USAHNTDP":"Программа сборной США","USNTDP U18":"Сборная США U18","USNTDP U17":"Сборная США U17","Boston University":"Бостонский университет","Boston College":"Бостонский колледж"};
function clubRu(team,lg){const ab=team_ab(team);if(ab)return EN[ab];if(CLUB2[team])return CLUB2[team];if(CLUB[team])return CLUB[team];
  let m=/^(.*?)\s+(Jr\.|J20|U20|J18|U18)$/.exec(team||"");if(m)return clubRu(m[1],lg)+" (мол.)";
  m=/^Univ\.? of (.+)$/i.exec(team||"")||/^University of (.+)$/i.exec(team||"");if(m)return "Университет "+trl(m[1]);
  m=/^(.+?) (State )?Univ(\.|ersity)?$/i.exec(team||"");if(m)return "Университет "+trl(m[1])+(m[2]?" (штат)":"");
  return trl(team)}
function team_ab(name){if(!name)return null;if(OLD_TEAMS[name])return OLD_TEAMS[name];const k=nrm(name);for(const a in FULL_LAT){if(nrm(FULL_LAT[a])===k)return a}return null}
const TROPHY={"Hart Memorial Trophy":"Харт Трофи — самый ценный игрок","Art Ross Trophy":"Арт Росс Трофи — лучший бомбардир","Maurice \"Rocket\" Richard Trophy":"Морис Ришар Трофи — лучший снайпер","Maurice Richard Trophy":"Морис Ришар Трофи — лучший снайпер","Ted Lindsay Award":"Тед Линдсей Эворд — лучший по версии игроков","Vezina Trophy":"Везина Трофи — лучший вратарь","James Norris Memorial Trophy":"Джеймс Норрис Трофи — лучший защитник","Calder Memorial Trophy":"Колдер Трофи — лучший новичок","Conn Smythe Trophy":"Конн Смайт Трофи — MVP плей-офф","Frank J. Selke Trophy":"Фрэнк Дж. Селки Трофи — лучший оборонительный нападающий","William M. Jennings Trophy":"Уильям Дженнингс Трофи — меньше всех пропустили","Lady Byng Memorial Trophy":"Леди Бинг Трофи — за благородство","Bill Masterton Memorial Trophy":"Билл Мастертон Трофи — за преданность хоккею","King Clancy Memorial Trophy":"Кинг Клэнси Трофи — за лидерство и благотворительность","Mark Messier Leadership Award":"Марк Мессье Эворд — за лидерство","Jack Adams Award":"Джек Адамс Эворд","NHL Foundation Player Award":"Премия фонда НХЛ","Willie O'Ree Community Hero Award":"Премия Вилли О'Ри","Stanley Cup":"Кубок Стэнли"};
const TRK=[["richard","Морис Ришар Трофи — лучший снайпер"],["messier","Марк Мессье Эворд — за лидерство"],["hart","Харт Трофи — самый ценный игрок"],["art ross","Арт Росс Трофи — лучший бомбардир"],["lindsay","Тед Линдсей Эворд — лучший по версии игроков"],["pearson","Лестер Пирсон Эворд — лучший по версии игроков"],["vezina","Везина Трофи — лучший вратарь"],["norris","Джеймс Норрис Трофи — лучший защитник"],["calder","Колдер Трофи — лучший новичок"],["conn smythe","Конн Смайт Трофи — MVP плей-офф"],["selke","Фрэнк Селки Трофи — лучший оборонительный нападающий"],["jennings","Уильям Дженнингс Трофи — меньше всех пропустили"],["lady byng","Леди Бинг Трофи — за благородство"],["masterton","Билл Мастертон Трофи — за преданность хоккею"],["clancy","Кинг Клэнси Трофи — за лидерство и благотворительность"],["jack adams","Джек Адамс Эворд — лучший тренер"],["o'ree","Премия Вилли О'Ри"],["foundation","Премия фонда НХЛ"],["plus-minus","Лучший показатель плюс-минус"],["all-star","Матч всех звёзд — MVP"]];
const tro=t=>{if(TROPHY[t])return TROPHY[t];const k=String(t||"").toLowerCase().replace(/[“”"]/g,"");const m=TRK.find(([w])=>k.includes(w));return m?m[1]:t};
const MON=["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
function dateRu(d){if(!d)return"";const [y,m,dd]=String(d).split("-");return `${+dd} ${MON[+m-1]} ${y}`}
function draftRu(dr){if(!dr)return"Не выбирался на драфте НХЛ — пришёл в лигу свободным агентом.";const t=dr.teamAbbrev;return `Драфт ${dr.year}: ${dr.round}-й раунд, ${dr.overallPick}-й номер, выбран «${RU[t]||OLD_RU[t]||t}».`}
function careerBio(c,tm){if(!c)return"";const cr=(c.career||{}).regularSeason,cp=(c.career||{}).playoffs;const nhl=(c.seasons||[]).filter(x=>x.lg==="NHL"&&x.gt===2);
  const first=nhl.length?seasonLab(nhl[0].s):null;const cc=CTRY[c.country];const city=c.city?trl(c.city):"";
  const isG=c.pos==="G";const parts=[];
  parts.push(`Родился ${dateRu(c.born)}${city?` — ${city}`:""}${cc?`, ${({RU:"Россия",CA:"Канада",US:"США",SE:"Швеция",FI:"Финляндия",CZ:"Чехия",SK:"Словакия",DE:"Германия",CH:"Швейцария",AT:"Австрия",DK:"Дания",NO:"Норвегия",LV:"Латвия",BY:"Беларусь",FR:"Франция"})[cc[0]]||cc[1]}`:""}.`);
  parts.push(draftRu(c.draft));
  if(first&&cr)parts.push(isG?`В НХЛ с сезона ${first}: ${cr.gamesPlayed} ${plural(cr.gamesPlayed,"матч","матча","матчей").split(" ").slice(1).join(" ")}, ${cr.wins||0} ${plural(cr.wins||0,"победа","победы","побед").split(" ").slice(1).join(" ")}, ${cr.shutouts||0} «на ноль».`:`В НХЛ с сезона ${first}: ${cr.gamesPlayed} ${plural(cr.gamesPlayed,"матч","матча","матчей").split(" ").slice(1).join(" ")}, ${cr.points} ${plural(cr.points,"очко","очка","очков").split(" ").slice(1).join(" ")} (${cr.goals} Г, ${cr.assists} П).`);
  if(cp&&cp.gamesPlayed)parts.push(isG?`В плей-офф — ${cp.gamesPlayed} ${plural(cp.gamesPlayed,"матч","матча","матчей").split(" ").slice(1).join(" ")}.`:`В плей-офф — ${cp.gamesPlayed} ${plural(cp.gamesPlayed,"матч","матча","матчей").split(" ").slice(1).join(" ")} и ${cp.points} ${plural(cp.points,"очко","очка","очков").split(" ").slice(1).join(" ")}.`);
  if((c.cups||[]).length)parts.push(`Обладатель Кубка Стэнли: ${c.cups.map(x=>cupYear(x.s)).join(", ")}.`);
  return parts.map(p=>`<p>${esc(p)}</p>`).join("")}
function seasonsTable(c){const isG=c.pos==="G";const nhl=(c.seasons||[]).filter(x=>x.lg==="NHL"&&x.gt===2);
  const by={};nhl.forEach(x=>{const k=x.s;(by[k]=by[k]||[]).push(x)});const keys=Object.keys(by).sort().slice(-5).reverse();if(!keys.length)return"";
  const row=k=>{const xs=by[k];const sum=f=>xs.reduce((s,x)=>s+(+x[f]||0),0);const tms=xs.map(x=>team_ab(x.team)).filter(Boolean);
    const tl=tms.length?tms.map(t=>`<button data-team="${t}" class="tmi" title="${esc(EN[t])}" aria-label="${esc(EN[t])}">${logo(t,18)}<span>${AB[t]}</span></button>`).join(""):"—";
    return isG?`<tr><td>${seasonLab(k)}</td><td>${tl}</td><td>${sum("gp")}</td><td>${sum("w")}</td><td>${xs.length===1&&xs[0].gaa!=null?nz(xs[0].gaa,2):"—"}</td><td>${xs.length===1&&xs[0].sv!=null?nz(xs[0].sv*100,1)+"%":"—"}</td><td>${sum("so")}</td></tr>`
      :`<tr><td>${seasonLab(k)}</td><td>${tl}</td><td>${sum("gp")}</td><td>${sum("g")}</td><td>${sum("a")}</td><td><b>${sum("pts")}</b></td><td>${(v=>v>0?"+"+v:v)(sum("pm"))}</td></tr>`};
  return `<div class="sec"><h4 class="sub">Последние сезоны в НХЛ</h4><div class="tw season-scroll" role="region" aria-label="Статистика игрока по сезонам" tabindex="0"><table class="mt st5 season-table"><thead><tr><th>Сезон</th><th>Клуб</th>${isG?"<th>И</th><th>В</th><th>КН</th><th>%ОБ</th><th>«0»</th>":"<th>И</th><th>Г</th><th>П</th><th>О</th><th>+/−</th>"}</tr></thead><tbody>${keys.map(row).join("")}</tbody></table></div><p class="note season-note"><span class="season-note-full">Показана регулярка; при смене клуба значения за сезон суммированы.</span><span class="season-note-mobile">Прокрутите таблицу вправо, чтобы увидеть все показатели.</span></p></div>`}
function milestones(c){const it=[];const Y=s=>String(s).slice(4);
  (c.cups||[]).forEach(x=>{const t=team_ab(x.team);it.push({k:x.s,y:Y(x.s),t:"🏆 Кубок Стэнли",x:t?`с «${RU[t]}»`:""})});
  (c.awards||[]).filter(a=>a.t!=="Stanley Cup").forEach(a=>(a.s||[]).forEach(s=>it.push({k:s,y:Y(s),t:`🏅 ${tro(a.t)}`,x:""})));
  if(c.draft&&c.draft.overallPick===1)it.push({k:+(c.draft.year+"0000"),y:String(c.draft.year),t:"🎯 Первый номер драфта",x:""});
  const cr=(c.career||{}).regularSeason,ex=[];
  if(cr&&c.pos!=="G"){if(cr.points>=1000)ex.push(["1000+","очков в НХЛ"]);else if(cr.points>=500)ex.push(["500+","очков в НХЛ"]);if(cr.goals>=500)ex.push(["500+","голов в НХЛ"]);}
  if(cr&&c.pos==="G"&&cr.wins>=300)ex.push([cr.wins>=500?"500+":"300+","побед в НХЛ"]);
  if(cr&&cr.gamesPlayed>=1000)ex.push(["1000+","матчей в НХЛ"]);
  if(c.hof)ex.unshift(["★","Член Зала хоккейной славы"]);if(c.top100)ex.unshift(["★","В списке 100 величайших игроков НХЛ"]);
  if(!it.length&&!ex.length)return"";it.sort((a,b)=>b.k-a.k);
  return `<div class="sec"><h4 class="sub">Вехи и трофеи</h4><ul class="mls">${it.map(m=>`<li><span class="y">${esc(m.y)}</span><span>${esc(m.t)}${m.x?` <small>${esc(m.x)}</small>`:""}</span></li>`).join("")}${ex.map(([n,t])=>`<li class="ex"><span class="y">${esc(n)}</span><span>${esc(t)}</span></li>`).join("")}</ul></div>`}
function transfers(c){const rows=(c.seasons||[]).filter(x=>x.gt===2&&!INTL.test(x.lg||""));const segs=[];
  rows.sort((a,b)=>a.s-b.s).forEach(x=>{const last=segs[segs.length-1];if(last&&last.team===x.team&&last.lg===x.lg){last.to=x.s;last.gp+=x.gp||0;last.pts+=x.pts||0}else segs.push({team:x.team,lg:x.lg,from:x.s,to:x.s,gp:x.gp||0,pts:x.pts||0})});
  if(!segs.length)return"";const isG=c.pos==="G";const yr=(a,b)=>a===b?seasonLab(a):`${String(a).slice(0,4)}–${String(b).slice(6)}`;
  return `<div class="sec"><h4 class="sub">Путь по клубам</h4><ol class="path">${segs.reverse().map(s=>{const ab=s.lg==="NHL"?team_ab(s.team):null;return `<li${ab?` data-team="${ab}" class="nhl"`:""}><span class="y">${yr(s.from,s.to)}</span><span class="c">${ab?logo(ab,22):""}<b>${esc(ab?RU[ab]:clubRu(s.team))}</b> <small>${esc(LEAGUE[s.lg]||s.lg)}</small></span><span class="n">${s.gp} И${isG?"":` · ${s.pts} О`}</span></li>`}).join("")}</ol></div>`}
function nationalBlock(c){const rows=(c.seasons||[]).filter(x=>NAT[x.lg]);if(!rows.length)return"";const by={};
  rows.forEach(x=>{const [t,w]=NAT[x.lg];const y=String(x.s).slice(4);const k=t+y;const ctry=NATC[String(x.team||"").replace(/\s*U\d+$/,"").replace(/\s*\(.*\)$/,"")]||trl(String(x.team||"").replace(/\s*U\d+$/,""));if(!by[k]||(x.gp||0)>(by[k].gp||0))by[k]={t,w,y,gp:x.gp||0,g:x.g||0,a:x.a||0,pts:x.pts||0,ctry}});
  const it=Object.values(by).sort((a,b)=>b.y-a.y||b.w-a.w);const isG=c.pos==="G";const ctry=it.find(x=>x.w>=7)?.ctry||it[0].ctry;
  return `<div class="sec"><h4 class="sub">Сборная · ${esc(ctry)}</h4><div class="nat">${it.map(x=>`<div class="${x.w>=7?"sen":""}"><b>${esc(x.t)} ${x.y}</b><small>${x.gp} И${isG?"":` · ${x.g} Г · ${x.a} П`}</small></div>`).join("")}</div><p class="note">МЧМ — молодёжный чемпионат мира, ЮЧМ — юниорский. Медали в данных НХЛ не указаны.</p></div>`}
async function fillCareer(name,tm){const h=headOf(name);const id=h?String(h).split("/").pop():null;const box=$("#career");if(!box||!id)return;const c=await loadPC(id);
  if(!c){box.innerHTML="";return}box.innerHTML=`<div class="sec"><h4 class="sub">Биография</h4><div class="bio-copy">${careerBio(c,tm)}</div></div>${seasonsTable(c)}${milestones(c)}${transfers(c)}${nationalBlock(c)}`}
function playerSheet(name,tm){const s=skater(name),gk=goalie(name);tm=tm||(s||gk||{}).team;const pg=gk?[]:playerGames(name,tm);const mx=Math.max(1,...pg.map(x=>x.G+x.As));
  const withPts=pg.filter(x=>x.G||x.As).reverse();
  openSheet(`${playerHero(name,tm,s)}
   <div class="sh-b">${s?`<div class="kv"><div><small>Игры</small><b>${s.gp}</b></div><div><small>Голы</small><b>${s.g}</b></div><div><small>Передачи</small><b>${s.a}</b></div><div><small>Очки</small><b>${s.pts}</b></div><div><small>+/−</small><b>${s.pm>0?"+":""}${s.pm}</b></div>${s.toi?`<div><small>Время на льду</small><b>${mmss(s.toi_s?s.toi_s/60:s.toi)}</b><small>в среднем за матч</small></div>`:""}</div>`
     :gk?`<div class="kv"><div><small>Игры</small><b>${gk.gp}</b></div><div><small>В-П-ПО</small><b>${gk.w}-${gk.l}-${gk.otl}</b></div><div><small>% отражённых</small><b>${nz(gk.sv*100)}%</b></div><div><small>Коэф. надёжности</small><b>${nz(gk.gaa,2)}</b></div><div><small>Сухие матчи</small><b>${gk.so||0}</b></div></div>`:'<p class="note">Сезонной статистики по игроку пока нет в сводке.</p>'}
   ${pg.length?`<div class="sec"><h4 class="sub">Очки по матчам${pg.length>12?" · последние 12":""}</h4><div class="spk" style="--c:${tcol(tm)}">${pg.slice(-12).map(x=>{const p=x.G+x.As,op=x.g.home===tm?x.g.away:x.g.home;return `<div class="c" title="${esc(dShort(x.g.date))} · ${x.g.home===tm?"дома":"в гостях"} · ${EN[op]||op}: ${x.G} Г, ${x.As} П"><b>${p||""}</b><span class="bar"><i class="${p?"":"z"}" style="height:${p?p/mx*100:0}%"></i></span>${logo(op,24)}<small>${x.g.home===tm?"":"@"}</small></div>`}).join("")}</div></div>`:""}
   ${gk?"":`<div class="sec"><h4 class="sub">Матчи с очками</h4>${withPts.length?`<div class="box">${withPts.map(({g,G,As})=>{const opp=g.away===tm?g.home:g.away;return `<button class="lr" style="grid-template-columns:minmax(0,1fr) auto;width:100%" data-res="${g.date}" data-gid="${g.id}"><span class="who">${logo(opp,30)}<b>${EN[opp]}</b><small class="mute">${esc(dShort(g.date))} · ${g.away===tm?"в гостях":"дома"}</small></span><b>${gaHtml(G,As)}</b></button>`}).join("")}</div>`:'<p class="note">В архиве матчей пока нет его голов и передач.</p>'}<p class="note">Голы и передачи — по протоколам матчей из архива сводки.</p></div>`}<div id="career"><p class="note">Загружаю карьеру…</p></div></div>`);fillCareer(name,tm)}
function playersOf(x){const out=[];const seen=new Set();for(const n of x.players||[]){const s=skater(n)||goalie(n);const t=(s&&s.team)||(x.teams||[])[0];if(!seen.has(n)&&t){seen.add(n);out.push([n,t])}}return out}
/* элементы лонгрида: «## подзаголовок», «> выноска», {img,credit,link,cap} — фото внутри текста */
function bodyItem(p){if(p&&typeof p==="object"){if(p.img)return `<figure class="bimg"><img src="${esc(p.img)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.remove()">${p.cap||p.credit?`<figcaption>${p.cap?esc(p.cap):""}${p.credit?` <span>Фото: ${p.link?`<a href="${esc(p.link)}" target="_blank" rel="noopener">${esc(p.credit)}</a>`:esc(p.credit)}</span>`:""}</figcaption>`:""}</figure>`;return""}
  const s=String(p);if(s.startsWith("## "))return `<h3>${esc(s.slice(3))}</h3>`;if(s.startsWith("> "))return `<blockquote>${esc(s.slice(2))}</blockquote>`;return `<p>${esc(s)}</p>`}
function readMin(x){const w=(x.body||[]).filter(p=>typeof p==="string").join(" ").split(/\s+/).length;return Math.max(1,Math.round(w/180))}
function storyChart(ch){const it=ch.items||[];if(!it.length)return"";const mx=Math.max(...it.map(x=>+x.value||0))||1;const cs=ch.color?` style="--hc:${ch.color}"`:"";
  return `<figure class="hch${ch.color?" tc":""}"${cs}><figcaption>${esc(ch.title||"")}</figcaption><div class="cols">${it.map(x=>`<div class="c${x.hl?" hl":""}"><b>${esc(x.value)}</b><span class="bar"><i style="height:${(+x.value||0)/mx*100}%"></i></span><small>${esc(x.label)}</small></div>`).join("")}</div>${ch.note?`<p class="note">${esc(ch.note)}</p>`:""}</figure>`}
function openArticle(k){const x=articles().find(a=>a.k===k);if(!x)return;const all=articles();const relA=all.filter(a=>a.k!==k&&(a.teams||[]).some(t=>(x.teams||[]).includes(t))).slice(0,3);const pls=playersOf(x);
  openSheet(`<article class="reader${x.kind==="column"?" reader-column":""}"><div class="reader-art" style="position:relative">${coverHtml(x)}<button class="sh-x" data-close aria-label="Закрыть">×</button></div><div class="rb">
   ${metaHtml(x)}${x.kind==="story"?`<span class="rt">${readMin(x)} мин чтения</span>`:""}<h1>${esc(x.title)}</h1>${x.dek&&x.body[0]!==x.dek?`<p class="dek">${esc(x.dek)}</p>`:""}
   ${(x.teams||[]).length||pls.length?`<div class="who">${(x.teams||[]).map(t=>`<button data-team="${t}">${logo(t,32)}${EN[t]}</button>`).join("")}${pls.map(([n,t])=>`<button data-player="${esc(n)}" data-pteam="${t}">${photo(n,t,38)}${esc(pn(n))}</button>`).join("")}</div>`:""}
   ${x.facts&&x.facts.length?`<div class="facts">${x.facts.map(f=>`<div><b>${esc(f.v)}</b><small>${esc(f.l)}</small></div>`).join("")}</div>`:""}
   <div class="body">${x.body.map((p,i)=>bodyItem(p)+(x.chart&&i===(x.chart.after??1)?storyChart(x.chart):"")+((x.charts||[]).filter(c=>c.after===i).map(storyChart).join(""))).join("")}</div>
   ${x.image_link?`<p class="note">Фото: <a href="${esc(x.image_link)}" target="_blank" rel="noopener">${esc(x.image_src||"источник")}</a></p>`:""}
   ${x.sources&&x.sources.length?`<p class="note">Данные: ${x.sources.map(s=>esc(s)).join(", ")}</p>`:""}
   ${x.url?`<div class="acts"><a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">${IC.ext}Оригинал: ${esc(x.source||"источник")}</a></div>`:""}
   ${relA.length?`<div class="sec"><h4 class="sub">По теме</h4>${relA.map(r=>`<button class="plink" data-art="${r.k}" style="font-family:var(--f-disp);font-size:20px;padding:4px 0">${esc(r.title)}</button>`).join("")}</div>`:""}</div></article>`)}

/* ===================== события ===================== */
document.addEventListener("click",e=>{const t=e.target.closest("button,a,[data-team],[data-player]");if(!t)return;const ds=t.dataset;
  if(ds.close!==undefined){closeSheet();return}
  if(ds.search!==undefined){openSearch();return}
  if(ds.ht){HERO_TAB=ds.ht;const w=$("#hb");if(w)w.innerHTML=heroesBody();return}
  if(ds.art){openArticle(ds.art);return}
  if(ds.nav){closeSheet();go(ds.nav);return}
  if(ds.go){closeSheet();if(ds.open)OPEN.add(ds.open);go(ds.go);if(ds.open)setTimeout(()=>{const el=document.getElementById("g-"+ds.open);el&&el.scrollIntoView({behavior:"smooth",block:"start"})},80);return}
  if(ds.res){closeSheet();RES_DATE=ds.res;if(ds.gid)OPEN.add("r"+ds.gid);go("results");if(ds.gid)setTimeout(()=>{const el=document.getElementById("g"+ds.gid);el&&el.scrollIntoView({behavior:"smooth",block:"start"})},80);return}
  if(ds.rd!==undefined){if(ds.rd){RES_DATE=ds.rd;render()}return}
  if(ds.tog){OPEN.has(ds.tog)?OPEN.delete(ds.tog):OPEN.add(ds.tog);render();if(OPEN.has(ds.tog))liveTouch&&liveTouch();return}
  if(ds.tm){TBL_MODE=ds.tm;render();return}
  if(ds.jf){JF=ds.jf;render();return}
  if(ds.rconf){RAIL_CONF=ds.rconf;render();return}
  if(ds.rlead){RAIL_LEAD=ds.rlead;render();return}
  if(ds.hot){HOT_MODE=ds.hot;render();return}
  if(ds.team){teamSheet(ds.team);return}
  if(ds.player){playerSheet(ds.player,ds.pteam);return}
});
$("#sheet").addEventListener("click",e=>{if(e.target.id==="sheet")closeSheet()});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeSheet()});

/* ===================== умный поиск: игроки и команды ===================== */
const TEAM_ALIAS={WSH:"кэпиталз столичные капиталс",PIT:"пингвинз пингвины",SJS:"шаркс акулы",EDM:"ойлерз нефтяники",FLA:"пантерз пантеры",TBL:"лайтнинг молния тампа-бэй",CAR:"харрикейнз ураганы",MIN:"уайлд дикие",NJD:"девилз дьяволы",DET:"ред уингз красные крылья",CHI:"блэкхокс чёрные ястребы",BOS:"брюинз медведи",TOR:"мейпл лифс кленовые листья",MTL:"канадиенс хабс монреаль",VGK:"голден найтс золотые рыцари",COL:"эвеланш лавина",DAL:"старз звёзды",NYR:"рейнджерс нью-йорк",NYI:"айлендерс островитяне",UTA:"мамонт юта хоккей клаб аризона",SEA:"кракен",LAK:"кингз короли",ANA:"дакс утки",STL:"блюз",NSH:"предаторз хищники",WPG:"джетс",VAN:"кэнакс",CGY:"флэймз",OTT:"сенаторз",BUF:"сейбрз",PHI:"флайерз",CBJ:"блю джекетс"};
let SIDX=null;
const snorm=s=>String(s||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/ё/g,"е").replace(/[^a-zа-я0-9 ]/g," ").replace(/\s+/g," ").trim();
function buildSIdx(){const H=(D&&D.heads)||{};const names=new Set([...Object.keys(H),...Object.keys(RUN),...((D.skaters||[]).map(x=>x.name)),...((D.goalies||[]).map(x=>x.name))]);const pl=[];
  names.forEach(n=>{const s=skater(n),g=goalie(n);const team=(H[n]?String(H[n]).split("/")[1]:null)||(s&&s.team)||(g&&g.team);if(!team)return;const ru=pn(n);
    pl.push({n,team,ru,key:" "+snorm(n)+" "+snorm(ru)+" ",tkey:" "+snorm([team,AB[team],RU[team],FULL[team],FULL_LAT[team],TEAM_ALIAS[team]||""].join(" "))+" ",pts:(s&&s.pts)||(g&&g.gp)||0})});
  const tm=Object.keys(FULL).map(a=>({a,key:" "+snorm([a,AB[a],RU[a],FULL[a],FULL_LAT[a],TEAM_ALIAS[a]||""].join(" "))+" "}));SIDX={pl,tm}}
function searchAll(q){if(!SIDX)buildSIdx();q=snorm(q);if(q.length<2)return {tm:[],pl:[]};const words=q.split(" ");
  const score=k=>{let s=0;for(const w of words){const i=k.indexOf(" "+w);if(i>=0)s+=10;else if(k.includes(w))s+=3;else return -1}return s};
  const tm=SIDX.tm.map(t=>({t,s:score(t.key)})).filter(x=>x.s>=0).sort((a,b)=>b.s-a.s).slice(0,4).map(x=>x.t.a);
  const score2=p=>{let s=0;for(const w of words){const i=p.key.indexOf(" "+w);if(i>=0)s+=10;else if(p.key.includes(w))s+=3;else if(p.tkey.indexOf(" "+w)>=0)s+=1;else return -1}return s};
  const pl=SIDX.pl.map(p=>({p,s:score2(p)})).filter(x=>x.s>=0).sort((a,b)=>b.s-a.s||b.p.pts-a.p.pts).slice(0,tm.length&&words.length===1?8:10).map(x=>x.p);
  return {tm,pl}}
function srchRender(){const q=$("#sq").value;const out=$("#sr");if(snorm(q).length<2){out.innerHTML=`<div class="empty">Начни вводить фамилию игрока или название клуба — по-русски или латиницей.</div>`;return}
  const {tm,pl}=searchAll(q);if(!tm.length&&!pl.length){out.innerHTML=`<div class="empty">Ничего не нашёл. Попробуй иначе: «Овечкин», «Ovechkin», «Вашингтон», «WSH».</div>`;return}
  out.innerHTML=`${tm.length?`<h5>Команды</h5>${tm.map(a=>{const t=TEAMS[a]||{};return `<button class="it" data-team="${a}">${logo(a,36)}<span><b>${esc(FULL[a])}</b><small>${t.gp!=null?`${t.w}-${t.l}-${t.otl} · ${plural(t.pts,"очко","очка","очков")} · ${place(a)}-е место`:""}</small></span></button>`}).join("")}`:""}
   ${pl.length?`<h5>Игроки</h5>${pl.map(p=>{const s=skater(p.n),g=goalie(p.n);const st=g?`${g.gp} И · ${nz(g.sv*100,1)}%`:s?`${s.gp} И · ${s.g} Г · ${s.a} П`:"";return `<button class="it" data-player="${esc(p.n)}" data-pteam="${p.team}">${photo(p.n,p.team,40)}<span><b>${esc(p.ru)} ${posTag(p.n)}</b><small>${esc(RU[p.team]||p.team)}${st?" · "+st:""}</small></span></button>`}).join("")}`:""}`;
  const f=out.querySelector(".it");f&&f.classList.add("on")}
function openSearch(){const s=$("#srch");s.hidden=false;const i=$("#sq");i.value="";srchRender();setTimeout(()=>i.focus(),30)}
function closeSearch(){$("#srch").hidden=true}
document.addEventListener("DOMContentLoaded",()=>{});
(function initSearch(){const b=$("#sbtn");if(!b)return;b.onclick=openSearch;$("#sx").onclick=closeSearch;
  $("#srch").addEventListener("click",e=>{if(e.target.id==="srch")closeSearch();const it=e.target.closest(".it");if(it)closeSearch()});
  $("#sq").addEventListener("input",srchRender);
  $("#sq").addEventListener("keydown",e=>{const its=[...document.querySelectorAll("#sr .it")];let i=its.findIndex(x=>x.classList.contains("on"));
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){e.preventDefault();if(!its.length)return;its[i]&&its[i].classList.remove("on");i=(i+(e.key==="ArrowDown"?1:-1)+its.length)%its.length;its[i].classList.add("on");its[i].scrollIntoView({block:"nearest"})}
    if(e.key==="Enter"&&its[i]){its[i].click()}if(e.key==="Escape")closeSearch()});
  document.addEventListener("keydown",e=>{if(e.key==="/"&&!/input|textarea/i.test((document.activeElement||{}).tagName||"")){e.preventDefault();openSearch()}})})();
