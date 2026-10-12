/* Сводка НХЛ — экраны */
"use strict";

/* ===================== оболочка ===================== */
function isNav(k){return VIEW===k||(k==="more"&&MORE.some(m=>m[0]===VIEW))}
function renderChrome(){
  $("#dock").innerHTML=NAV.map(([k,l])=>`<button data-nav="${k}" ${isNav(k)?'aria-current="page"':""}>${IC[k]}<span>${l}</span></button>`).join("");
  $("#tnav").innerHTML=NAV.map(([k,l])=>`<button data-nav="${k}" ${isNav(k)?'aria-current="page"':""}>${l}</button>`).join("");
  const f=freshness();const u=$("#upd");u.innerHTML=f.txt;u.classList.toggle("old",f.old);
  const s=$("#strip .wrap");const h=stripHtml();if(s.dataset.h!==h){s.innerHTML=h;s.dataset.h=h}}
function go(v){VIEW=v;try{history.replaceState(null,"","#"+v)}catch(e){}render();window.scrollTo(0,0)}
const VIEWS={home:vHome,games:vGames,news:vNews,results:vResults,table:vTable,picks:vPicks,more:vMore,teams:vTeams,lead:vLead,power:vPower,inj:vInj,rus:vRus};
function render(){if(!D)return;renderChrome();const f=VIEWS[VIEW]||vHome;$("#app").innerHTML=f();afterRender()}
function afterRender(){const dc=$(".dch");if(dc){const on=dc.querySelector('[aria-pressed="true"]');on&&on.scrollIntoView({inline:"center",block:"nearest"})}
  const ps=$("#psearch");if(ps)ps.oninput=()=>{const q=ps.value.trim().toLowerCase();const out=$("#psres");if(q.length<2){out.innerHTML="";return}
    const hits=[...(D.skaters||[]),...(D.goalies||[]).map(g=>({...g,pos:"G"}))].filter(s=>s.name.toLowerCase().includes(q)).slice(0,8);
    out.innerHTML=hits.length?`<div class="box">${hits.map((r,i)=>lrow(r,i,r.pos==="G"?(r.sv*100).toFixed(1)+"%":`${r.g}+${r.a}`,EN[r.team])).join("")}</div>`:'<p class="note">Никого не нашёл. Имена латиницей, например «Kaprizov».</p>'}}

/* лента счетов */
function stripHtml(){if(!D)return"";const d=lastDate();const gs=A.games.filter(g=>g.date===d);
  const up=(D.upcoming||[]).filter(m=>!A.games.some(g=>g.away===m.away&&g.home===m.home&&g.date>=nhlDate(m.start)));
  const row=(t,s,lo)=>`<div class="r ${lo?"lo":""}">${logo(t,22)}<span>${t}</span><b>${s}</b></div>`;
  const day=iso=>{const [a,b]=dShort(iso).split(" ");return `<span class="sday"><b>${esc(a)}</b>${esc(b||"")}</span>`};
  let h="";
  if(gs.length)h+=day(d)+gs.map(g=>{const aw=g.as>g.hs;return `<button class="sg" data-res="${g.date}" data-gid="${g.id}" aria-label="${EN[g.away]} ${g.as}, ${EN[g.home]} ${g.hs}"><small>Финал${endTag(g.end)?" · "+endTag(g.end):""}</small>${row(g.away,g.as,!aw)}${row(g.home,g.hs,aw)}</button>`}).join("");
  if(up.length)h+=day(D.upcoming_date||nhlDate(up[0].start))+up.map(m=>{const L=liveOf(m);const p=modelOf(m);
    if(L&&L.state!=="pre"){const aw=L.as>L.hs;return `<button class="sg" data-go="games" data-open="${m.away}-${m.home}"><small class="${L.state==="in"?"live":""}">${L.state==="in"?'<span class="dot"></span>'+esc(L.short):"Финал"+(L.end?" · "+L.end:"")}</small>${row(m.away,L.as,L.state==="post"&&!aw)}${row(m.home,L.hs,L.state==="post"&&aw)}</button>`}
    return `<button class="sg" data-go="games" data-open="${m.away}-${m.home}"><small>${kt(m.start)}</small>${row(m.away,p?pct(pB(p,"away")):"",false)}${row(m.home,p?pct(pB(p,"home")):"",false)}</button>`}).join("");
  return h}

/* ===================== матчи: строка и разбор ===================== */
function tmLine(a,{p,f,sc,lo}){return `<span class="tm ${lo?"lo":""}">${logo(a,28)}<b>${EN[a]}</b><span class="rec">${rec(a)}</span>${sc!=null?`<span class="sc">${sc}</span>`:`${formDots(a)}${p!=null?`<span class="p ${f?"f":""}">${pct(p)}</span>`:""}`}</span>`}
function pcLine(a,p,f){return `<span class="${f?"f":""}" style="--c:${tcol(a)}"><span class="bar2"><i style="--w:${Math.round(p*100)}%"></i></span>${pct(p)}</span>`}
function timeCell(m,L){if(L&&L.state==="in")return `<span class="t">${esc(L.ps||L.per)}<small class="live"><span class="dot"></span>${esc(L.clock||"идёт")}</small></span>`;
  if(L&&L.state==="post")return `<span class="t">Финал<small>${L.end?endLong(L.end):kt(m.start)}</small></span>`;
  const s=state(m.start);return `<span class="t">${kt(m.start)}${s==="pre"&&rel(m.start)?`<small>${rel(m.start)}</small>`:s!=="pre"?"<small>идёт</small>":""}</span>`}
function gRow(m,{mo=false,nav=false}={}){const key=`${m.away}-${m.home}`,open=!nav&&OPEN.has(key);const p=modelOf(m);const L=liveOf(m);
  const pa=pB(p,"away"),ph=pB(p,"home");const fa=pa!=null&&pa>ph;
  const pickT=m.pick_side?sideTeam(m,m.pick_side):(p?fcOf(p,m).t:null);const tp=m.total_pick;const po=oddsOf(m,m.pick_side);const a=altOf(p,m);
  const lv=L&&L.state!=="pre";const aw=lv&&L.as>L.hs;
  const [ca,ch]=[tcol(m.away),tcol(m.home)];
  const btn=nav?`data-go="games" data-open="${key}"`:`data-tog="${key}" aria-expanded="${open}"`;
  return `<div class="mr${mo?" mo":""}${L&&L.flash?" flash":""}" id="g-${key}" style="--ca:${ca};--ch:${ch};--fc:${L&&L.flash?tcol(L.flash)+"55":"transparent"}"><button class="row" ${btn}>${timeCell(m,L)}
    <span class="tms">${tmLine(m.away,{p:pa,f:fa,sc:lv?L.as:null,lo:lv&&L.state==="post"&&!aw})}${tmLine(m.home,{p:ph,f:!fa,sc:lv?L.hs:null,lo:lv&&L.state==="post"&&aw})}</span>
    <span class="pcs">${pa!=null?pcLine(m.away,pa,fa)+pcLine(m.home,ph,!fa):""}</span>
    <span class="pk">${pickT?`<span class="k"><small>Прогноз</small>${EN[pickT]}${po?` · ${f2(po)}`:""}</span>`:""}${tp?`<span class="k"><small>Тотал</small>${tp.side==="over"?"Больше":"Меньше"} ${esc(tp.line)}${tp.odds?` · ${f2(tp.odds)}`:""}</span>`:""}${a&&!lv?`<span class="chip gold">Недооценка: ${EN[a.t]}${a.odds?" · "+f2(a.odds):""}</span>`:""}</span>${IC.chev}
    ${mo&&D.motd&&D.motd.text?`<span class="mo-t"><b>Матч дня.</b> ${esc(D.motd.text)}</span>`:""}</button>${open?gDetail(m,p,L):""}</div>`}
function altBox(a){return a?`<div class="alt full"><small>Альтернативный взгляд</small><p>Фаворит — <b>${EN[a.fav]}</b>, но модель оценивает шансы <b>${EN[a.t]}</b> выше рынка: ${pct(a.pm)} против ${pct(a.pk)}${a.odds?`. По линии-ориентиру — <b>${f2(a.odds)}</b>, рынок их недооценивает`:""}. Это более рискованный вариант.</p></div>`:""}
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
     <div class="kv"><div><small>Модель без рынка</small><b>${pct(p.p_away)} : ${pct(p.p_home)}</b></div>${p.mkt_home!=null?`<div><small>Рынок</small><b>${pct(p.mkt_away)} : ${pct(p.mkt_home)}</b></div>`:""}<div><small>Ожидаемые голы</small><b>${nz(p.lam_away)} : ${nz(p.lam_home)}</b></div><div><small>Ничья в осн. время</small><b>${pct(p.p_ot)}</b></div></div></div>
    <div class="blk"><h4 style="margin-top:0">Из чего складывается оценка</h4><ul class="ul">${modelWhy(m||p,p).map(x=>`<li>${x}</li>`).join("")}</ul>
     ${h2h.length?`<h4>Личные встречи в сезоне</h4><ul class="ul">${h2h.map(g=>`<li>${esc(dShort(g.date))}: ${EN[g.away]} — ${EN[g.home]} <b>${esc(g.score)}</b>${g.end&&g.end!=="REG"?" "+endTag(g.end):""}</li>`).join("")}</ul>`:""}</div></div></details>`}
function gDetail(m,p,L){const tp=m.total_pick;const pickT=m.pick_side?sideTeam(m,m.pick_side):(p?fcOf(p,m).t:null);const po=oddsOf(m,m.pick_side);
  const ga=m.goalies||[];const injA=injOut(m.away),injH=injOut(m.home);
  const pick=pickT||tp?`<div class="picks full">${pickT?`<div><small>Прогноз на исход</small><b>${EN[pickT]}${po?`<em>${f2(po)}</em>`:""}</b>${m.lean?`<p>${esc(m.lean)}</p>`:""}</div>`:""}${tp?`<div><small>Тотал</small><b>${tp.side==="over"?"Больше":"Меньше"} ${esc(tp.line)}${tp.odds?`<em>${f2(tp.odds)}</em>`:""}</b>${tp.lean?`<p>${esc(tp.lean)}</p>`:""}</div>`:""}</div>`:"";
  const fac=(m.factors||[]).length?`<div class="blk"><h4>Почему так</h4><ul class="ul">${m.factors.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`:"";
  const gl=`<div class="blk"><h4>Вратари</h4><div class="kv">${[0,1].map(i=>{const t=i?m.home:m.away;const gp=p&&(i?p.goalie_home:p.goalie_away);const nm=String(ga[i]||"").split(" (")[0];
      return `<div><small>${EN[t]}</small><span style="display:flex;align-items:center;gap:8px">${nm&&nm!=="не объявлен"?photo(nm,t,32):""}<b style="font-family:var(--f-body);font-size:var(--fs-s)">${esc(ga[i]||"не объявлен")}</b></span>${gp&&gp.sv?`<small>${nz(gp.sv*100)}% отражённых · ${gp.gp} и.</small>`:""}</div>`}).join("")}</div>
    ${(injA.length||injH.length)?`<h4>Без кого играют</h4><ul class="ul">${[[m.away,injA],[m.home,injH]].filter(x=>x[1].length).map(([t,l])=>`<li><b>${EN[t]}:</b> ${l.map(x=>esc(x.name)).join(", ")}</li>`).join("")}</ul>`:""}</div>`;
  const lines=(m.odds||m.books||m.odds_1x)?`<div class="blk full"><h4>Линии</h4>${booksTable(m)}</div>`:"";
  const live=L&&L.state!=="pre"?liveBlock(m,L):"";
  return `<div class="x">${live}${pick}${live?"":altBox(altOf(p,m))}${fac}${gl}${lines}${modelBlk(p,m)}<div class="acts full"><button class="btn" data-team="${m.away}">${logo(m.away,20)}${EN[m.away]}</button><button class="btn" data-team="${m.home}">${logo(m.home,20)}${EN[m.home]}</button></div></div>`}
function wRow({p,m,start}){const key="w"+(p.id||p.away+p.home),open=OPEN.has(key);const pa=pB(p,"away"),ph=pB(p,"home");const fa=pa>ph;
  const b2b=[p.b2b_away&&EN[p.away],p.b2b_home&&EN[p.home]].filter(Boolean);
  return `<div class="mr" id="${key}" style="--ca:${tcol(p.away)};--ch:${tcol(p.home)}"><button class="row" data-tog="${key}" aria-expanded="${open}"><span class="t">${kt(start)}</span>
    <span class="tms">${tmLine(p.away,{p:pa,f:fa})}${tmLine(p.home,{p:ph,f:!fa})}</span><span class="pcs">${pcLine(p.away,pa,fa)}${pcLine(p.home,ph,!fa)}</span>
    <span class="pk"><span class="k"><small>Фаворит</small>${EN[fa?p.away:p.home]}</span>${b2b.length?`<span class="k"><small>Второй матч подряд</small>${b2b.join(", ")}</span>`:""}</span>${IC.chev}</button>${open?`<div class="x">${modelBlk(p,m,true)}</div>`:""}</div>`}
function weekList(){const ids=new Set((D.upcoming||[]).map(x=>x.away+x.home));const all=mGames().filter(g=>(g.p.date||g.m.date)>(D.upcoming_date||"")&&!ids.has(g.p.away+g.p.home));if(!all.length)return"";
  const by={};all.forEach(g=>{const d=g.p.date||g.m.date;(by[d]=by[d]||[]).push(g)});
  return `<section class="sec"><div class="hd"><h2>Дальше на неделе<small>предварительно, по модели без линии</small></h2></div>${Object.entries(by).map(([d,gs],k)=>`<details class="day" ${k?"":"open"}><summary>${esc(dLong(d))}<small>${plural(gs.length,"матч","матча","матчей")}</small></summary><div class="box">${gs.map(wRow).join("")}</div></details>`).join("")}</section>`}
function confLine(){const ex=confLegs();return ex.length?`<p class="txt">Самые уверенные исходы: ${ex.map(x=>`<b>${EN[x.t]}</b> ${pct(x.p)}`).join(", ")}</p>`:""}
function todayGames(){return (D.upcoming||[]).slice().sort((a,b)=>String(a.start).localeCompare(String(b.start)))}
function vGames(){const u=todayGames();const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  if(!u.length)return `<div class="col">${noGames()}${weekList()}</div>`;
  return `<div class="col"><section class="sec"><div class="hd"><h1>Матчи<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h1></div>${confLine()}
    <div class="box">${u.map(m=>gRow(m,{mo:m===mo})).join("")}</div>
    <p class="note">Проценты — итог модели и рынка (60% рынка, 40% модели), кэфы — линия-ориентир. «Недооценка» — модель оценивает аутсайдера заметно выше рынка. Во время матча счёт обновляется сам.</p></section>${weekList()}</div>`}
function noGames(){const nx=(D.week||[]).filter(g=>state(g.start)==="pre").sort((a,b)=>a.start<b.start?-1:1)[0];
  return `<section class="sec"><div class="hd"><h1>Матчи</h1></div><div class="box empty">Сегодня матчей нет.${nx?` Следующий игровой день — ${esc(dLong(nx.date||nhlDate(nx.start)))}, первый матч в ${kt(nx.start)} по Кирову.`:""}</div></section>`}

/* ===================== главная ===================== */
function topScorer(t){return (D.skaters||[]).filter(s=>s.team===t).sort((a,b)=>b.pts-a.pts||b.g-a.g)[0]}
function posterSec(){const mo=D.motd;if(!mo)return"";const m=(D.upcoming||[]).find(x=>x.away===mo.away&&x.home===mo.home);if(!m||state(m.start)==="done")return"";
  const p=modelOf(m);const L=liveOf(m);const [ca,ch]=pair(m.away,m.home);const pa=pB(p,"away"),ph=pB(p,"home");
  const lv=L&&L.state!=="pre";
  const side=(t,cls)=>`<button class="side ${cls}" data-team="${t}"><span class="lgw">${logo(t,64)}</span><span><b>${EN[t]}</b><small>${rec(t)}${TEAMS[t]&&TEAMS[t].gp?" · "+place(t)+"-е место":""}</small></span></button>`;
  const pl=(t,cls)=>{const s=topScorer(t);return s?`<button class="pl ${cls}" data-player="${esc(s.name)}" data-pteam="${t}">${photo(s.name,t,48)}<span><b>${esc(s.name)}</b><small>${s.g}+${s.a} в сезоне · лидер ${EN[t]}</small></span></button>`:""};
  const mid=lv?`<b>${L.as}:${L.hs}</b><small>${L.state==="in"?'<span class="dot"></span> '+esc(L.short):"финал"}</small>`:`<b>${kt(m.start)}</b><small>${esc(rel(m.start)||"")}</small>`;
  return `<section class="poster" style="--a:${ca};--h:${ch}"><div class="bg"></div><div class="rink"></div><div class="in">
    <div class="lab"><span>Матч дня</span><span>${esc(dLong(D.upcoming_date))}</span></div>
    <div class="vs">${side(m.away,"a")}<div class="mid">${mid}</div>${side(m.home,"h")}</div>
    ${pa!=null&&!lv?`<div class="pb"><span>${pct(pa)}</span><span class="two"><i style="width:${pa*100}%;background:rgba(255,255,255,${pa>ph?.95:.45})"></i><i style="width:${ph*100}%;background:rgba(255,255,255,${ph>pa?.95:.45})"></i></span><span>${pct(ph)}</span></div>`:""}
    <div class="stars">${pl(m.away,"a")}${pl(m.home,"h")}</div>
    ${mo.text?`<p>${esc(mo.text)}</p>`:""}
    <button class="go" data-go="games" data-open="${m.away}-${m.home}">Разбор матча</button></div></section>`}
function todaySec(){const u=todayGames();if(!u.length)return noGames();const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  return `<section class="sec"><div class="hd"><h2>Сегодня<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h2><button class="lnk" data-go="games">Все матчи</button></div>
    <div class="box">${u.map(m=>gRow(m,{nav:true,mo:m===mo&&false})).join("")}</div>${confLine()}</section>`}
function nightSec(){const d=lastDate();if(!d)return"";const gs=A.games.filter(g=>g.date===d);
  return `<section class="sec"><div class="hd"><h2>Ночь<small>${esc(dLong(d))}</small></h2><button class="lnk" data-go="results">Итоги и протоколы</button></div>
    <div class="box"><div class="scores">${gs.map(g=>{const aw=g.as>g.hs;return `<button class="sc1" data-res="${g.date}" data-gid="${g.id}"><span class="r ${aw?"":"lo"}">${logo(g.away,30)}${EN[g.away]}<b>${g.as}</b></span><span class="r ${aw?"lo":""}">${logo(g.home,30)}${EN[g.home]}<b>${g.hs}</b></span>${endTag(g.end)?`<small>${endLong(g.end)}</small>`:""}</button>`}).join("")}</div></div></section>`}

/* герои игрового дня */
function sensation(n){if(n.sensation)return n.sensation;const d=n.date;
  const j=(D.journal||[]).filter(x=>x.date===d&&x.result==="miss"&&x.odds&&x.odds<2&&(x.type==="win"||x.type==="total")).sort((a,b)=>(a.type==="win"?0:1)-(b.type==="win"?0:1)||a.odds-b.odds)[0];if(!j)return null;
  const g=A.games.find(x=>x.date===d&&x.away===j.away&&x.home===j.home);if(!g)return null;const p=Math.round(100/j.odds/1.04)/100;
  if(j.type==="win"){const w=g.as>g.hs?g.away:g.home;return {id:g.id,kind:"исход",head:`Победа аутсайдера: ${EN[w]}`,fav:j.pick,p}}
  return {id:g.id,kind:"тотал",head:`Тотал ${g.as+g.hs} при линии ${j.line}`,p,tot:pickLabel(j)}}
function svp(l){const m=/(\d+)\s*из\s*(\d+)/.exec(l||"");return m&&+m[2]?nz(m[1]/m[2]*100)+"% отражённых":""}
function card3(x,i){const n=pnum(x.name,x.pos);return `<article class="card3" style="--c:${tdeep(x.team)}"><div class="top3"><span class="wm">${logo(x.team,120)}</span><span class="rk">${i+1}<i>★</i></span>${n&&headOf(x.name)?`<span class="num3">#${n}</span>`:""}${photo(x.name,x.team,118)}</div>
  <div class="bd"><div class="nm"><span>${plink(x.name,x.team)}<small>${esc(FULL[x.team]||x.team)}</small></span><b class="v">${esc(x.line||"")}</b></div>${x.text?`<p>${esc(x.text)}</p>`:""}</div></article>`}
function feat(x,role,big,sub){return `<div class="feat">${photo(x.name,x.team,72,"ring")}<span class="nm2">${plink(x.name,x.team)}<small>${role} · ${esc(FULL[x.team]||x.team)}</small></span><span class="big">${esc(big||"")}${sub?`<small>${sub}</small>`:""}</span>${x.text?`<p>${esc(x.text)}</p>`:""}</div>`}
function heroPanel(n){const t=HERO_TAB;
  if(t==="stars")return `<div class="cards">${n.heroes.slice(0,3).map(card3).join("")}</div>`;
  if(t==="goalie")return `<div class="box">${feat(n.goalie,"Вратарь дня",n.goalie.line,svp(n.goalie.line))}</div>`;
  if(t==="russian")return `<div class="box">${feat(n.russian,"Россиянин дня",n.russian.line)}</div>`;
  if(t==="sense"){const x=sensation(n);const g=x&&A.games.find(y=>y.id===x.id);if(!g)return"";
    const why=x.kind==="исход"&&x.fav?`Фаворитом был <b>${EN[x.fav]}</b>${x.p?` — линия давала около ${Math.round(x.p*100)}%`:""}.`:x.tot?`Линия ждала: <b>${esc(x.tot)}</b>${x.p?`, около ${Math.round(x.p*100)}%`:""}.`:"";
    return `<div class="box sense"><div class="sc"><span class="${x.fav===g.away?"fav":""}">${logo(g.away,36)}${EN[g.away]}</span><b>${g.as}:${g.hs}</b><span class="${x.fav===g.home?"fav":""}">${EN[g.home]}${logo(g.home,36)}</span></div><h3>${esc(x.head||"")}</h3>${why?`<p class="txt">${why}</p>`:""}${x.text?`<p class="txt">${esc(x.text)}</p>`:""}<button class="lnk" style="align-self:flex-start" data-res="${g.date}" data-gid="${g.id}">Протокол матча</button></div>`}
  if(t==="flop"){const x=(n.antiheroes||[])[0],tm=n.worst_team;
    return `<div class="box">${x?`<div class="flop"><span class="tag">Игрок</span>${photo(x.name,x.team,52)}<span class="nm2">${plink(x.name,x.team)}<small>${esc(FULL[x.team]||x.team)}</small></span><span class="v">${esc(x.line||"")}</span>${x.text?`<p>${esc(x.text)}</p>`:""}</div>`:""}
      ${tm?`<div class="flop"><span class="tag">Команда</span>${logo(tm.abbr,52)}<span class="nm2"><button class="plink" data-team="${tm.abbr}">${esc(FULL[tm.abbr]||tm.abbr)}</button><small>${rec(tm.abbr)}</small></span>${formDots(tm.abbr)}${tm.text?`<p>${esc(tm.text)}</p>`:""}</div>`:""}</div>`}
  return""}
function heroTabs(n){return [["stars","Три звезды",n.heroes&&n.heroes.length],["goalie","Вратарь дня",n.goalie],["russian","Россиянин дня",n.russian],["sense","Сенсация",sensation(n)],["flop","Неудачники",(n.antiheroes||[]).length||n.worst_team]].filter(t=>t[2])}
function heroesBody(){const n=D.daily;const t=heroTabs(n);if(!t.some(x=>x[0]===HERO_TAB))HERO_TAB=t[0][0];
  return `<div class="pills" role="tablist">${t.map(x=>`<button role="tab" data-ht="${x[0]}" aria-selected="${x[0]===HERO_TAB}">${x[1]}</button>`).join("")}</div><div class="appear">${heroPanel(n)}</div>`}
function heroesSec(){const n=D.daily;if(!n||!n.heroes||!n.heroes.length)return"";
  return `<section class="sec"><div class="hd"><h2>Герои игрового дня<small>${esc(dLong(n.date||lastDate()))}</small></h2><button class="lnk" data-go="results">Все итоги</button></div><div id="hb" class="sec">${heroesBody()}</div></section>`}

/* новости */
function leadCard(x,noCover){return `<button class="lead" data-art="${x.k}">${noCover?"":coverHtml(x)}<span class="tx">${metaHtml(x)}<h3>${esc(x.title)}</h3><p>${esc(x.dek||x.body[0]||"")}</p></span></button>`}
function nrow(x){return `<button class="nr" data-art="${x.k}">${metaHtml(x)}<h4>${esc(x.title)}</h4><p>${esc(x.dek||x.body[0]||"")}</p>${coverHtml(x,"th",false)}</button>`}
function newsBlock(limit){const arts=articles();const col=arts.find(x=>x.kind==="column");const news=arts.filter(x=>x.kind!=="column");if(!news.length&&!col)return"";
  const lead=news[0];const rest=limit?news.slice(1,limit+1):news.slice(1);
  return `${lead?`<div class="box">${leadCard(lead)}${rest.map(nrow).join("")}</div>`:""}${col?`<div class="box colm">${leadCard(col,true)}</div>`:""}`}
function newsSec(){const b=newsBlock(5);return b?`<section class="sec"><div class="hd"><h2>Главное</h2><button class="lnk" data-go="news">Все новости</button></div>${b}</section>`:""}
function vNews(){const b=newsBlock(0);return `<div class="col"><section class="sec"><div class="hd"><h1>Новости<small>пересказ по-русски за последние сутки</small></h1></div>${b||'<div class="box empty">Новостей пока нет — они появляются после утреннего обновления.</div>'}</section></div>`}

/* правая колонка */
function accW(){const j=(D.journal||[]).filter(x=>x.result&&x.result!=="void");if(!j.length)return"";const hit=j.filter(x=>x.result==="hit").length;
  return `<section class="box"><div class="wg-h"><h3>Точность модели</h3><button class="lnk" data-go="picks">Журнал</button></div><div class="acc"><b>${Math.round(hit/j.length*100)}%</b><span>${hit} из ${j.length} прогнозов угадано с начала журнала</span></div></section>`}
function standW(){const list=ALL.filter(a=>CONF_OF[a]===RAIL_CONF).map(a=>TEAMS[a]).sort(cmp);
  return `<section class="box"><div class="wg-h"><h3>Таблица</h3><button class="lnk" data-go="table">Полностью</button></div><div class="pills wg-pills">${["Восток","Запад"].map(c=>`<button data-rconf="${c}" aria-pressed="${RAIL_CONF===c}">${c}</button>`).join("")}</div>
   <table class="wtab"><thead><tr><th></th><th>Команда</th><th>И</th><th>О</th></tr></thead><tbody>${list.map((t,i)=>`<tr class="${i===8?"cut":""}" data-team="${t.abbr}" style="cursor:pointer"><td>${i+1}</td><td><span class="tn">${logo(t.abbr,24)}${EN[t.abbr]}</span></td><td>${t.gp}</td><td class="p">${t.pts}</td></tr>`).join("")}</tbody></table></section>`}
const LTABS=[["points","Очки"],["goals","Голы"],["assists","Передачи"],["pm","+/−"],["gk","Вратари"]];
function leaderRows(k,n=10){const S=(D.skaters||[]).filter(s=>s.gp>0);
  if(k==="points")return S.slice().sort((a,b)=>b.pts-a.pts||b.g-a.g||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.pts,sub:`${s.g}+${s.a} · ${s.gp} и`}));
  if(k==="goals")return S.slice().sort((a,b)=>b.g-a.g||b.pts-a.pts||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.g,sub:`${s.gp} и`}));
  if(k==="assists")return S.slice().sort((a,b)=>b.a-a.a||b.pts-a.pts||a.gp-b.gp).slice(0,n).map(s=>({...s,v:s.a,sub:`${s.gp} и`}));
  if(k==="pm")return S.slice().sort((a,b)=>b.pm-a.pm||b.pts-a.pts).slice(0,n).map(s=>({...s,v:(s.pm>0?"+":"")+s.pm,sub:`${s.pts} очк.`}));
  return (D.goalies||[]).filter(g=>g.gp>=3).sort((a,b)=>b.sv-a.sv||a.gaa-b.gaa).slice(0,n).map(g=>({...g,pos:"G",v:nz(g.sv*100)+"%",sub:`${g.w}-${g.l}-${g.otl} · ${nz(g.gaa,2)} КН`}))}
function lrow(r,i,v,sub){return `<div class="lr"><span class="n">${i+1}</span><span class="who">${photo(r.name,r.team,38)}<span class="nm2">${plink(r.name,r.team)}<small>${esc(sub||"")}</small></span></span><span class="v">${v}</span></div>`}
function leadersW(){return `<section class="box"><div class="wg-h"><h3>Лидеры</h3><button class="lnk" data-go="lead">Все</button></div><div class="pills wg-pills">${LTABS.map(([k,l])=>`<button data-rlead="${k}" aria-pressed="${RAIL_LEAD===k}">${l}</button>`).join("")}</div>${leaderRows(RAIL_LEAD,6).map((r,i)=>lrow(r,i,r.v,`${EN[r.team]} · ${r.sub}`)).join("")}</section>`}
function staleBanner(){const f=freshness();return f.old?`<div class="banner">Данные давно не обновлялись — последний сбор ${esc(kdt(D.generated))}. Счёт матчей обновляется сам, остальное подтянется со следующим сбором.</div>`:""}
function vHome(){return `${staleBanner()}<div class="home"><div class="col">${posterSec()}${todaySec()}${nightSec()}${heroesSec()}${newsSec()}</div><aside class="col">${accW()}${standW()}${leadersW()}</aside></div>`}

/* ===================== итоги ===================== */
function goalsBlock(g){if(!g.goals||!g.goals.length)return g.end==="SO"&&g.as+g.hs===1?'<p class="note">Голов в игре не было, победа в серии буллитов.</p>':"";const per={};g.goals.forEach(x=>(per[x[3]]=per[x[3]]||[]).push(x));
  const pn=k=>k==4?"Овертайм":k==5?"Буллиты":`${k}-й период`;const st={pp:"бол.",sh:"мен.",en:"п.в."};
  return `<div class="goals">${Object.keys(per).sort().map(k=>`<div class="per">${pn(+k)}</div>${per[k].map(x=>`<div class="goal"><time>${+k===5?"Б":esc(x[4])}</time>${logo(x[1],20)}<span><b>${esc(x[0])}</b>${st[x[2]]?`<em>${st[x[2]]}</em>`:""}${x[5]?` <span class="as">(${esc(String(x[5]).replace(/,/g,", "))})</span>`:""}</span></div>`).join("")}`).join("")}</div>`}
function sbar(l,v,a,h,parse=x=>x){const x=parse(v[0]),y=parse(v[1]);const tot=(x+y)||1;return `<div class="sbar"><b>${esc(v[0])}</b><div class="mid"><small>${l}</small><div class="two"><i style="width:${x/tot*100}%;background:${x>=y?tcol(a):"var(--soft2)"}"></i><i style="width:${y/tot*100}%;background:${y>=x?tcol(h):"var(--soft2)"}"></i></div></div><b>${esc(v[1])}</b></div>`}
function sbars(g){const s=g.stats;const parse=v=>typeof v==="string"?+v.split("/")[0]:v;
  if(!s)return g.sog?`<div class="sbars">${sbar("Броски в створ",g.sog,g.away,g.home)}</div>`:"";
  const rows=[["Броски в створ",s.sog],["Большинство",s.pp],["Вбрасывания, %",s.fo],["Силовые",s.hits],["Блок-шоты",s.blk],["Штрафные минуты",s.pim]].filter(r=>r[1]);
  return `<div class="sbars">${rows.map(([l,v])=>sbar(l,v,g.away,g.home,parse)).join("")}</div>`}
function resRow(g){const key="r"+g.id,open=OPEN.has(key);const aw=g.as>g.hs;
  return `<div class="mr" id="g${g.id}" style="--ca:${tcol(g.away)};--ch:${tcol(g.home)}"><button class="rr" data-tog="${key}" aria-expanded="${open}"><span class="s ${aw?"":"lo"}">${logo(g.away,40)}<span><b>${EN[g.away]}</b><small>${rec(g.away)}</small></span></span>
   <span class="score">${g.as}:${g.hs}<small>${endTag(g.end)?endLong(g.end):"финал"}</small></span><span class="s h ${aw?"lo":""}">${logo(g.home,40)}<span><b>${EN[g.home]}</b><small>${rec(g.home)}</small></span></span>${IC.chev}</button>
   ${open?`<div class="x">${g.recap?`<p class="txt full">${esc(g.recap)}</p>`:""}<div class="blk">${goalsBlock(g)}</div><div class="blk">${sbars(g)}${g.stars&&g.stars.length?`<h4>Три звезды матча</h4><div class="acts">${g.stars.map((s,i)=>s&&s!=="—"?`<span class="chip gold">${"★".repeat(i+1)} ${esc(s)}</span>`:"").join("")}</div>`:""}</div>
   <div class="acts full">${g.video?`<a class="btn" href="${esc(g.video)}" target="_blank" rel="noopener">${IC.play}Обзор матча</a>`:""}${g.gc?`<a class="btn" href="${esc(g.gc)}" target="_blank" rel="noopener">${IC.ext}Матч на NHL.com</a>`:""}<button class="btn" data-team="${g.away}">${logo(g.away,20)}${EN[g.away]}</button><button class="btn" data-team="${g.home}">${logo(g.home,20)}${EN[g.home]}</button></div></div>`:""}</div>`}
function vResults(){const ds=dates();if(!ds.length)return `<div class="box empty">Архив пока пуст.</div>`;if(!RES_DATE||!ds.includes(RES_DATE))RES_DATE=ds[ds.length-1];const i=ds.indexOf(RES_DATE);
  const gs=A.games.filter(g=>g.date===RES_DATE);
  return `<div class="col"><section class="sec"><div class="hd"><h1>Итоги<small>${esc(dLong(RES_DATE))} · ${plural(gs.length,"матч","матча","матчей")}</small></h1></div>
   <div class="dates"><button class="arr" data-rd="${ds[i-1]||""}" ${i?"":"disabled"} aria-label="Предыдущий день"><svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg></button>
   <div class="dch">${ds.map(d=>`<button data-rd="${d}" aria-pressed="${d===RES_DATE}"><span>${esc(dWd(d))}</span><b>${+d.slice(8)}</b></button>`).join("")}</div>
   <button class="arr" data-rd="${ds[i+1]||""}" ${i<ds.length-1?"":"disabled"} aria-label="Следующий день"><svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg></button></div>
   <div class="box">${gs.map(resRow).join("")}</div>
   <p class="note">Дата — по Северной Америке. бол. — гол в большинстве, мен. — в меньшинстве, п.в. — в пустые ворота. Нажми на матч, чтобы открыть голы и статистику.</p></section></div>`}

/* ===================== таблица ===================== */
function stTable(title,list,opt={}){return `<div class="box stc"><div class="th3"><h3>${esc(title)}</h3>${opt.sub?`<span class="note">${esc(opt.sub)}</span>`:""}</div><table class="st"><thead><tr><th></th><th class="l">Команда</th><th>И</th><th>В</th><th>П</th><th class="c-otl">ПО</th><th>О</th><th class="c-gd">Шайбы</th><th class="l c-form">Форма</th></tr></thead><tbody>
  ${list.map((t,i)=>`<tr class="${opt.cut&&i===opt.cut?"cut":""}" data-team="${t.abbr}"><td class="n">${i+1}</td><td class="l"><span class="tn">${logo(t.abbr,26)}${EN[t.abbr]}</span></td><td>${t.gp}</td><td>${t.w}</td><td>${t.l}</td><td class="c-otl">${t.otl}</td><td class="p">${t.pts}</td><td class="c-gd">${t.gf}–${t.ga}</td><td class="l c-form">${formDots(t.abbr)}</td></tr>`).join("")}</tbody></table></div>`}
function vTable(){const modes=[["div","Дивизионы"],["conf","Конференции"],["league","Лига"],["wc","Уайлд-кард"]];let body="";
  if(TBL_MODE==="div")body=`<div class="tgrid">${DIVS.map(d=>stTable(`${d[1]} дивизион`,d[2].map(a=>TEAMS[a]).sort(cmp),{sub:d[0]})).join("")}</div>`;
  else if(TBL_MODE==="conf")body=`<div class="tgrid">${["Восток","Запад"].map(c=>stTable(c==="Восток"?"Восточная конференция":"Западная конференция",ALL.filter(a=>CONF_OF[a]===c).map(a=>TEAMS[a]).sort(cmp),{cut:8})).join("")}</div>`;
  else if(TBL_MODE==="league")body=stTable("Вся лига",ALL.map(a=>TEAMS[a]).sort(cmp));
  else body=`<div class="tgrid">${["Восток","Запад"].map(c=>{const ds=DIVS.filter(d=>d[0]===c);const tops=ds.map(d=>d[2].map(a=>TEAMS[a]).sort(cmp));const rest=tops.flatMap(t=>t.slice(3)).sort(cmp);
    return `<div class="sec"><div class="hd"><h3>${c==="Восток"?"Восточная конференция":"Западная конференция"}</h3></div>${ds.map((d,i)=>stTable(`${d[1]} · топ-3`,tops[i].slice(0,3))).join("")}${stTable("Уайлд-кард",rest,{cut:2,sub:"две путёвки, черта — граница плей-офф"})}</div>`}).join("")}</div>`;
  return `<div class="col"><section class="sec"><div class="hd"><h1>Таблица<small>${plural(A.games.length,"матч сыгран","матча сыграно","матчей сыграно")}</small></h1></div><div class="pills">${modes.map(([k,l])=>`<button data-tm="${k}" aria-pressed="${TBL_MODE===k}">${l}</button>`).join("")}</div>${body}
   <p class="note">И — игры, В — победы, П — поражения в основное время, ПО — в овертайме или по буллитам, О — очки. При равенстве очков выше команда с лучшим процентом очков, затем с большим числом побед в основное время. Форма: свежие матчи справа. Нажми на команду, чтобы открыть её карточку.</p></section></div>`}

/* ===================== прогнозы ===================== */
function jRow(x){const t=x.type||"win";const TY={win:"Исход",total:"Тотал",express:"Уверенные"};const r=x.result;
  const rs=r==="hit"?'<span class="res hit">Угадан</span>':r==="miss"?'<span class="res miss">Мимо</span>':r==="void"?'<span class="res void">Возврат</span>':'<span class="res wait">ждём</span>';
  const legs=t==="express"?(x.legs||[]):[x];
  return `<div class="jr"><div class="l"><span class="ty"><span class="chip">${TY[t]||t}</span><small>${esc(dShort(x.date))}${x.changed?" · вечером изменён":""}</small></span><b>${pickLabel(x)}${x.odds?` · ${f2(x.odds)}`:""}</b><small>${esc(matchLabel(x))}${x.score?` · <b>${esc(x.score)}</b>`:""}</small></div>${rs}</div>`}
function vPicks(){const all=(D.journal||[]);const list=all.filter(x=>JF==="all"||(x.type||"win")===JF);const done=list.filter(x=>x.result&&x.result!=="void");
  const hit=done.filter(x=>x.result==="hit").length;const withOdds=done.filter(x=>x.odds);const roi=withOdds.length?withOdds.reduce((s,x)=>s+plOf(x.result,x.odds),0)/withOdds.length:null;
  const ch=all.filter(x=>x.changed&&x.result&&x.result!=="void"&&(x.type||"win")!=="express");
  const am=ch.length?`<div class="box pad"><h4 class="sub">Утро против вечера</h4><p class="txt" style="margin-top:6px">Вечером прогноз менялся ${plural(ch.length,"раз","раза","раз")}: вечерний вариант угадан ${ch.filter(x=>x.result==="hit").length}, утренний был бы угадан ${ch.filter(x=>amRes(x)==="hit").length}.</p></div>`:`<p class="note">Прогноз фиксируется утром и уточняется перед матчами — после объявления вратарей, травм и по поздней линии. Когда вечером он изменится, здесь появится счёт «утро против вечера».</p>`;
  return `<div class="col"><section class="sec"><div class="hd"><h1>Прогнозы<small>что прогнозировали и что вышло</small></h1></div>
   <div class="pills">${[["all","Все"],["win","Исходы"],["total","Тоталы"],["express","Уверенные исходы"]].map(([k,l])=>`<button data-jf="${k}" aria-pressed="${JF===k}">${l}</button>`).join("")}</div>
   <div class="box"><div class="sum"><div><b>${done.length?Math.round(hit/done.length*100)+"%":"—"}</b><small>точность</small></div><div><b>${hit}/${done.length}</b><small>угадано</small></div><div><b class="${sgn(roi)}">${roi==null?"—":(roi>0?"+":"")+Math.round(roi*100)+"%"}</b><small>условная доходность</small></div></div></div>
   ${am}
   <div class="box">${list.length?list.slice().reverse().map(jRow).join(""):'<div class="empty">Пока пусто.</div>'}</div>
   <p class="note">Прогноз фиксируется до начала матча и задним числом не меняется. Условная доходность — если бы на каждый прогноз шла одна и та же единица по коэффициенту линии-ориентира. Исход — победа с учётом овертайма и буллитов; тотал — все голы, включая овертайм; «уверенные исходы» засчитываются, только если сыграли все.</p></section></div>`}

/* ===================== ещё ===================== */
const back=()=>`<button class="back" data-go="more">← Ещё</button>`;
function vMore(){return `<div class="col"><section class="sec"><div class="hd"><h1>Ещё</h1></div><div class="menu">${MORE.map(([k,l,s])=>`<button data-go="${k}">${IC[k]}<span><b>${l}</b><small>${s}</small></span></button>`).join("")}</div></section></div>`}
function vTeams(){return `<div class="col">${back()}<section class="sec"><div class="hd"><h1>Команды</h1></div>
  <input class="inp" id="psearch" placeholder="Найти игрока, например Kaprizov" aria-label="Найти игрока"><div id="psres"></div>
  ${DIVS.map(d=>`<div class="sec"><div class="hd"><h3>${d[1]} дивизион</h3></div><div class="teams">${d[2].map(a=>`<button data-team="${a}">${logo(a,36)}<span>${EN[a]}</span></button>`).join("")}</div></div>`).join("")}</section></div>`}
function lastNPoints(n=5){const teamG={};A.games.slice().sort((x,y)=>x.date<y.date?-1:1).forEach(g=>{for(const t of [g.away,g.home])(teamG[t]=teamG[t]||[]).push(g)});
  const pts={};for(const t in teamG)for(const g of teamG[t].slice(-n))for(const x of (g.goals||[])){if(x[1]!==t||x[3]===5)continue;const add=(s,k)=>{s=String(s||"").trim();if(!s)return;const key=t+"|"+s;pts[key]=pts[key]||{g:0,a:0};pts[key][k]++};add(x[0],"g");String(x[5]||"").split(",").forEach(s=>add(s,"a"))}
  return pts}
function hotList(){const L=lastNPoints(5);const rows=(D.skaters||[]).filter(s=>s.gp>=3).map(s=>{const p=L[s.team+"|"+s.name.split(" ").slice(1).join(" ")]||L[s.team+"|"+s.name.split(" ").pop()]||{g:0,a:0};return {...s,l5g:p.g,l5a:p.a,l5:p.g+p.a}});
  return {hot:rows.slice().sort((a,b)=>b.l5-a.l5||b.l5g-a.l5g||b.pts-a.pts).slice(0,10),cold:rows.filter(r=>r.l5===0).sort((a,b)=>b.pts/b.gp-a.pts/a.gp).slice(0,10)}}
function vLead(){const {hot,cold}=hotList();const list=HOT_MODE==="hot"?hot:cold;
  return `<div class="col">${back()}<section class="sec"><div class="hd"><h1>Лидеры<small>текущий сезон</small></h1></div><div class="tgrid">
  ${LTABS.map(([k,l])=>`<section class="box"><div class="wg-h"><h3>${l}${k==="gk"?" · от 3 игр":""}</h3></div>${leaderRows(k,10).map((r,i)=>lrow(r,i,r.v,`${EN[r.team]} · ${r.sub}`)).join("")}</section>`).join("")}
  <section class="box"><div class="wg-h"><h3>Форма игроков</h3></div><div class="pills wg-pills">${[["hot","Горячие"],["cold","Холодные"]].map(([k,l])=>`<button data-hot="${k}" aria-pressed="${HOT_MODE===k}">${l}</button>`).join("")}</div><p class="note" style="padding:0 16px 6px">${HOT_MODE==="hot"?"Больше всех очков за последние 5 матчей команды":"Были среди результативных, но без очков 5 матчей"}</p>
   ${list.map((r,i)=>lrow(r,i,HOT_MODE==="hot"?r.l5:"0",HOT_MODE==="hot"?`${EN[r.team]} · ${r.l5g}+${r.l5a} за 5 · сезон ${r.pts}`:`${EN[r.team]} · сезон ${r.g}+${r.a} за ${r.gp} и`)).join("")}</section></div></section></div>`}
function vPower(){const t=Object.entries(M.teams||{}).sort((a,b)=>b[1].power-a[1].power);const mx=Math.max(...t.map(x=>Math.max(x[1].att,1/x[1].dfn)),1.3);
  return `<div class="col">${back()}<section class="sec"><div class="hd"><h1>Сила команд<small>${M.league?`${M.league.games} матчей, ${nz(M.league.goals_pg,2)} гола на команду за игру`:""}</small></h1></div>
  <div class="box">${t.map(([a,v],i)=>`<div class="pw"><span class="mute" style="font-weight:700">${i+1}</span><div style="display:flex;flex-direction:column;gap:6px;min-width:0"><button class="tm" data-team="${a}">${logo(a,26)}<b>${EN[a]}</b></button><div class="bars"><span class="bar2" style="--c:var(--blue)"><i style="--w:${v.att/mx*100}%"></i></span><span class="bar2" style="--c:var(--win)"><i style="--w:${(1/v.dfn)/mx*100}%"></i></span></div><small class="mute">голы ${v.gf_pg}–${v.ga_pg} · броски ${v.sf_pg}–${v.sa_pg} за игру</small></div><span class="v">${Math.round(v.power*100)}</span></div>`).join("")}</div>
  <p class="note">Индекс 100 — средняя команда лиги. Синяя полоса — атака, зелёная — оборона (длиннее — лучше). Индекс считается по всем матчам сезона: 70% веса — ожидаемые голы (xG MoneyPuck), 30% — реальные голы, с поправкой на соперников и на уровень прошлого сезона, которая слабеет с каждым матчем.</p></section></div>`}
function vInj(){const rows=ALL.map(a=>[a,(((D.teams||{})[a]||{}).injuries||[])]).filter(x=>x[1].length);
  return `<div class="col">${back()}<section class="sec"><div class="hd"><h1>Травмы<small>по данным Daily Faceoff</small></h1></div><div class="tgrid">${rows.map(([a,l])=>`<div class="box pad" style="display:flex;flex-direction:column;gap:10px"><button class="tm" data-team="${a}">${logo(a,32)}<b>${FULL[a]}</b></button><ul class="ul">${l.map(x=>`<li><b>${esc(x.name)}</b> · ${esc(x.status)}</li>`).join("")}</ul></div>`).join("")}</div>
  <p class="note">IR и LTIR — список травмированных, Out — точно не сыграет, DTD — решение принимают перед игрой.</p></section></div>`}
function vRus(){const r=(D.russians||[]).map(x=>({...x,s:skater(x.name),g:goalie(x.name)}));const sk=r.filter(x=>!x.g).sort((a,b)=>((b.s||{}).pts||0)-((a.s||{}).pts||0)),gk=r.filter(x=>x.g);
  return `<div class="col">${back()}<section class="sec"><div class="hd"><h1>Россияне<small>${plural(r.length,"игрок","игрока","игроков")}</small></h1></div><div class="tgrid">
  <section class="box"><div class="wg-h"><h3>Полевые · очки</h3></div>${sk.map((x,i)=>lrow(x,i,x.s?`${x.s.g}+${x.s.a}`:"—",`${EN[x.team]}${x.s?` · ${x.s.gp} и · ${x.s.pm>0?"+":""}${x.s.pm}`:""}`)).join("")}</section>
  <section class="box"><div class="wg-h"><h3>Вратари</h3></div>${gk.map((x,i)=>lrow(x,i,nz(x.g.sv*100)+"%",`${EN[x.team]} · ${x.g.gp} и · ${x.g.w}-${x.g.l}-${x.g.otl}`)).join("")}</section></div></section></div>`}

/* ===================== карточки ===================== */
function openSheet(html){$("#panel").innerHTML=html;$("#sheet").hidden=false;document.body.style.overflow="hidden";$("#panel").scrollTop=0}
function closeSheet(){$("#sheet").hidden=true;document.body.style.overflow=""}
function specTeams(a){const off=(D.team_stats||{})[a];if(!off)return null;const all=Object.values(D.team_stats||{});const rank=k=>all.map(x=>x[k]).filter(x=>x!=null).sort((p,q)=>q-p).indexOf(off[k])+1;
  return {pp:off.pp_pct,pk:off.pk_pct,ppr:rank("pp_pct"),pkr:rank("pk_pct"),fo:off.fo_pct,sf:off.sf_pg,sa:off.sa_pg,gf:off.gf_pg,ga:off.ga_pg}}
function teamSheet(a){const t=TEAMS[a],md=(M.teams||{})[a],r=(D.teams||{})[a]||{};const sp=specTeams(a);
  const nxt=(D.week||[]).filter(g=>(g.away===a||g.home===a)&&state(g.start)==="pre").slice(0,5);const last=(t.games||[]).slice(-8).reverse();
  const ln=(k,arr)=>arr&&arr.length?`<div><span class="k">${k}</span>${arr.map(p=>`<button class="plink" data-player="${esc(p)}" data-pteam="${a}">${esc(p)}</button>`).join(" · ")}</div>`:"";
  const rus=(D.russians||[]).filter(x=>x.team===a);const f=v=>v==null?"—":nz(v)+"%";
  openSheet(`<div class="sh-h" style="--c:${tdeep(a)}"><span class="wm">${logo(a,200)}</span><span class="lgw">${logo(a,58)}</span><div><h2>${esc(FULL[a])}</h2><small>${t.w}-${t.l}-${t.otl} · ${plural(t.pts,"очко","очка","очков")} · ${place(a)}-е место, ${esc(DIV_OF[a])} дивизион</small></div><button class="sh-x" data-close aria-label="Закрыть">×</button></div>
   <div class="sh-b">
    <div class="kv"><div><small>Форма</small><b>${formDots(a,10)||"—"}</b></div><div><small>Серия</small><b>${esc(t.streak||"—")}</b></div><div><small>Дома / в гостях</small><b>${t.hw}-${t.hl}-${t.ho} / ${t.aw}-${t.al}-${t.ao}</b></div>${md?`<div><small>Индекс силы</small><b>${Math.round(md.power*100)}</b></div>`:""}</div>
    ${sp?`<div class="sec"><h4 class="sub">Игра команды</h4><div class="kv"><div><small>Большинство</small><b>${f(sp.pp)}</b><small>${sp.ppr}-е в лиге</small></div><div><small>Меньшинство</small><b>${f(sp.pk)}</b><small>${sp.pkr}-е в лиге</small></div><div><small>Голы за игру</small><b>${nz(sp.gf,2)} – ${nz(sp.ga,2)}</b></div><div><small>Броски за игру</small><b>${nz(sp.sf)} – ${nz(sp.sa)}</b></div><div><small>Вбрасывания</small><b>${f(sp.fo)}</b></div></div></div>`:""}
    ${nxt.length?`<div class="sec"><h4 class="sub">Ближайшие матчи</h4><div class="box">${nxt.map(g=>{const o=g.home===a?g.away:g.home;return `<div class="lr" style="grid-template-columns:minmax(0,1fr) auto"><span class="who">${logo(o,26)}<span>${g.home===a?"дома":"в гостях"} · <b>${EN[o]}</b></span></span><span class="note">${esc(kdt(g.start))}</span></div>`}).join("")}</div></div>`:""}
    ${last.length?`<div class="sec"><h4 class="sub">Последние матчи</h4><div class="box">${last.map(g=>`<button class="lr" style="grid-template-columns:22px minmax(0,1fr) auto;width:100%" data-res="${g.date}" data-gid="${g.id}"><span class="fd"><i class="${g.r}">${g.r==="W"?"В":g.r==="O"?"О":"П"}</i></span><span class="who">${g.home?"дома":"в гостях"} · ${logo(g.opp,24)}<b>${EN[g.opp]}</b></span><span><b>${g.gf}:${g.ga}</b>${g.end!=="REG"?" "+endTag(g.end):""} <span class="note">${esc(dShort(g.date))}</span></span></button>`).join("")}</div></div>`:""}
    ${r.forwards?`<div class="sec"><h4 class="sub">Звенья</h4><div class="lines">${(r.forwards||[]).map((l,i)=>ln(`${i+1}-е`,l)).join("")}${(r.defense||[]).map((l,i)=>ln(`З${i+1}`,l)).join("")}${ln("Вр",r.goalies)}${ln("ПП1",r.pp1)}${ln("ПП2",r.pp2)}</div><p class="note">Звенья по Daily Faceoff${r.updated?`, обновлено ${esc(dShort(r.updated.slice(0,10)))}`:""}.</p></div>`:""}
    ${(r.injuries||[]).length?`<div class="sec"><h4 class="sub">Травмы</h4><ul class="ul">${r.injuries.map(x=>`<li><b>${esc(x.name)}</b> · ${esc(x.status)}</li>`).join("")}</ul></div>`:""}
    ${rus.length?`<div class="sec"><h4 class="sub">Россияне</h4><div class="acts">${rus.map(x=>`<button class="btn" data-player="${esc(x.name)}" data-pteam="${a}">${photo(x.name,a,24)}${esc(x.name)}</button>`).join("")}</div></div>`:""}
   </div>`)}
function playerGames(name,tm){const ln=name.split(" ").slice(1).join(" ")||name;const short=name.split(" ").pop();const out=[];
  for(const g of A.games.slice().sort((x,y)=>x.date<y.date?-1:1)){if(g.away!==tm&&g.home!==tm)continue;let G=0,As=0;for(const x of g.goals||[]){if(x[1]!==tm||x[3]===5)continue;if(x[0]===ln||x[0]===short)G++;if(String(x[5]||"").split(",").map(s=>s.trim()).some(s=>s===ln||s===short))As++}out.push({g,G,As})}return out}
function playerSheet(name,tm){const s=skater(name),gk=goalie(name);tm=tm||(s||gk||{}).team;const pg=gk?[]:playerGames(name,tm);const mx=Math.max(1,...pg.map(x=>x.G+x.As));
  const withPts=pg.filter(x=>x.G||x.As).reverse();const POS={C:"центральный нападающий",L:"левый нападающий",R:"правый нападающий",D:"защитник",G:"вратарь"};
  openSheet(`<div class="sh-h" style="--c:${tdeep(tm)}"><span class="wm">${logo(tm,200)}</span>${photo(name,tm,84)}<div><h2>${esc(name)}</h2><small>${esc(FULL[tm]||tm)}${s&&s.pos?" · "+(POS[s.pos]||s.pos):gk?" · вратарь":""}${pnum(name)?" · #"+pnum(name):""}</small></div><button class="sh-x" data-close aria-label="Закрыть">×</button></div>
   <div class="sh-b">${s?`<div class="kv"><div><small>Игры</small><b>${s.gp}</b></div><div><small>Голы</small><b>${s.g}</b></div><div><small>Передачи</small><b>${s.a}</b></div><div><small>Очки</small><b>${s.pts}</b></div><div><small>+/−</small><b>${s.pm>0?"+":""}${s.pm}</b></div>${s.toi?`<div><small>Время на льду</small><b>${nz(s.toi)}</b></div>`:""}</div>`
     :gk?`<div class="kv"><div><small>Игры</small><b>${gk.gp}</b></div><div><small>В-П-ПО</small><b>${gk.w}-${gk.l}-${gk.otl}</b></div><div><small>% отражённых</small><b>${nz(gk.sv*100)}%</b></div><div><small>Коэф. надёжности</small><b>${nz(gk.gaa,2)}</b></div><div><small>Сухие матчи</small><b>${gk.so||0}</b></div></div>`:'<p class="note">Сезонной статистики по игроку пока нет в сводке.</p>'}
   ${pg.length?`<div class="sec"><h4 class="sub">Очки по матчам команды</h4><div class="spark" style="--c:${tcol(tm)}">${pg.map(x=>`<i class="${x.G+x.As?"":"z"}" style="height:${(x.G+x.As)/mx*100}%" title="${esc(dShort(x.g.date))}: ${x.G}+${x.As}"></i>`).join("")}</div></div>`:""}
   ${gk?"":`<div class="sec"><h4 class="sub">Матчи с очками</h4>${withPts.length?`<div class="box">${withPts.map(({g,G,As})=>{const opp=g.away===tm?g.home:g.away;return `<button class="lr" style="grid-template-columns:minmax(0,1fr) auto;width:100%" data-res="${g.date}" data-gid="${g.id}"><span class="who">${esc(dShort(g.date))} · ${g.away===tm?"в гостях":"дома"} · ${logo(opp,22)}<b>${EN[opp]}</b></span><b>${G}+${As}</b></button>`}).join("")}</div>`:'<p class="note">В архиве матчей пока нет его голов и передач.</p>'}<p class="note">Голы и передачи — по протоколам матчей из архива сводки.</p></div>`}</div>`)}
function playersOf(x){const out=[];const seen=new Set();for(const n of x.players||[]){const s=skater(n)||goalie(n);const t=(s&&s.team)||(x.teams||[])[0];if(!seen.has(n)&&t){seen.add(n);out.push([n,t])}}return out}
function openArticle(k){const x=articles().find(a=>a.k===k);if(!x)return;const all=articles();const relA=all.filter(a=>a.k!==k&&(a.teams||[]).some(t=>(x.teams||[]).includes(t))).slice(0,3);const pls=playersOf(x);
  openSheet(`<article class="reader"><div style="position:relative">${coverHtml(x)}<button class="sh-x" data-close aria-label="Закрыть">×</button></div><div class="rb">
   ${metaHtml(x)}<h1>${esc(x.title)}</h1>${x.dek&&x.body[0]!==x.dek?`<p class="dek">${esc(x.dek)}</p>`:""}
   ${(x.teams||[]).length||pls.length?`<div class="who">${(x.teams||[]).map(t=>`<button data-team="${t}">${logo(t,26)}${EN[t]}</button>`).join("")}${pls.map(([n,t])=>`<button data-player="${esc(n)}" data-pteam="${t}">${photo(n,t,30)}${esc(n)}</button>`).join("")}</div>`:""}
   <div class="body">${x.body.map(p=>`<p>${esc(p)}</p>`).join("")}</div>
   ${x.url?`<div class="acts"><a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">${IC.ext}Оригинал: ${esc(x.source||"источник")}</a></div>`:""}
   ${relA.length?`<div class="sec"><h4 class="sub">По теме</h4>${relA.map(r=>`<button class="plink" data-art="${r.k}" style="font-family:var(--f-disp);font-size:20px;padding:4px 0">${esc(r.title)}</button>`).join("")}</div>`:""}</div></article>`)}

/* ===================== события ===================== */
document.addEventListener("click",e=>{const t=e.target.closest("button,a,tr[data-team]");if(!t)return;const ds=t.dataset;
  if(ds.close!==undefined){closeSheet();return}
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
