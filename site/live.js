/* NHL-STATS.RU — живой счёт (табло ESPN из браузера) и запуск */
"use strict";
const ESPN="https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/";
const EAB={NJ:"NJD",TB:"TBL",LA:"LAK",SJ:"SJS",UTAH:"UTA",MON:"MTL",WAS:"WSH",VEG:"VGK",CLB:"CBJ",NAS:"NSH",WIN:"WPG",ARI:"UTA"};
const ab=x=>EAB[x]||x;
const LIVE={},LSUM={},LSUMT={};let LIVE_OK=true,LTIMER=null,LAST_POLL=0;
function liveOf(m){const L=LIVE[`${m.away}-${m.home}`];if(L)return L;
  /* табло ESPN уже не отдаёт матч — берём финал из архива сводки */
  if(m&&m.start&&state(m.start)!=="pre"){const d=nhlDate(m.start);const g=(A.games||[]).find(x=>x.away===m.away&&x.home===m.home&&x.date===d);
    if(g)return {state:"post",as:g.as,hs:g.hs,end:g.end&&g.end!=="REG"?g.end:"",fromArchive:true}}
  return null}
function perName(n){return n<=3?`${n}-й период`:n===4?"Овертайм":"Буллиты"}
function perShort(n){return n<=3?`${n}-й`:n===4?"ОТ":"Б"}
function parseEvent(ev){const c=(ev.competitions||[])[0];if(!c)return null;const st=ev.status||c.status||{};const ty=st.type||{};
  const tm={};for(const x of c.competitors||[])tm[x.homeAway]={a:ab(x.team&&x.team.abbreviation),s:+x.score||0,id:x.team&&x.team.id};
  if(!tm.away||!tm.home)return null;const per=st.period||0;const detail=String(ty.detail||ty.shortDetail||"");
  const inter=/end of|intermission/i.test(detail);
  return {id:ev.id,key:`${tm.away.a}-${tm.home.a}`,away:tm.away.a,home:tm.home.a,ida:tm.away.id,idh:tm.home.id,state:ty.state,as:tm.away.s,hs:tm.home.s,
    per:perName(per),ps:per<=3?`${per}-й пер.`:per===4?"ОТ":"Буллиты",clock:inter?"перерыв":(st.displayClock||""),short:inter?`перерыв после ${perShort(per)}`:`${perShort(per)} · ${st.displayClock||""}`,end:ty.state==="post"?(per===4?"ОТ":per>=5?"Б":""):""}}
function needLive(){const u=D&&D.upcoming||[];const now=Date.now();
  return u.some(m=>{const t=new Date(m.start).getTime();const L=liveOf(m);if(L&&L.state==="post")return false;return now>t-10*6e4&&now<t+5*36e5})}
async function poll(force){if(!D||!LIVE_OK)return;if(document.hidden&&!force)return;if(!needLive()&&!force)return;
  const d=(D.upcoming_date||"").replace(/-/g,"");let sb;
  try{const r=await fetch(`${ESPN}scoreboard${d?`?dates=${d}`:""}`,{cache:"no-store"});if(!r.ok)throw 0;sb=await r.json()}catch(e){return}
  LAST_POLL=Date.now();let changed=false;
  for(const ev of sb.events||[]){const L=parseEvent(ev);if(!L)continue;const old=LIVE[L.key];
    if(!(D.upcoming||[]).some(m=>m.away===L.away&&m.home===L.home))continue;
    if(old&&L.state==="in"&&(L.as!==old.as||L.hs!==old.hs))L.flash=L.as>old.as?L.away:L.home;
    if(!old||JSON.stringify({...old,flash:0})!==JSON.stringify({...L,flash:0}))changed=true;
    LIVE[L.key]=L}
  /* подробности для раскрытых идущих матчей */
  for(const k in LIVE){const L=LIVE[k];if(L.state==="pre"||!OPEN.has(k))continue;if(LSUMT[L.id]&&Date.now()-LSUMT[L.id]<20000&&!force)continue;
    try{const r=await fetch(`${ESPN}summary?event=${L.id}`,{cache:"no-store"});if(r.ok){LSUM[L.id]=parseSummary(await r.json(),L);LSUMT[L.id]=Date.now();changed=true}}catch(e){}}
  if(changed&&["home","games","picks"].includes(VIEW)&&$("#sheet").hidden)rerenderKeep();
  else if(changed)renderChrome();
  for(const k in LIVE)delete LIVE[k].flash}
function rerenderKeep(){const y=window.scrollY;render();window.scrollTo(0,y)}
function liveTouch(){poll(true)}
/* расчёт прогнозов по живому счёту: до утреннего сбора результат ставит сайт, утром — скрипт */
function legLive(away,home,side){const L=LIVE[`${away}-${home}`];if(!L||L.state==="pre")return null;const fin=L.state==="post";
  const w=L.as===L.hs?null:(L.as>L.hs?"away":"home");if(!w)return {r:null,fin,txt:"ничья"};return {r:w===side?"hit":"miss",fin}}
function liveRes(j){if(j.result)return null;const t=j.type||"win";
  if(t==="win"||t==="sure")return legLive(j.away,j.home,j.side);
  if(t==="total"){const L=LIVE[`${j.away}-${j.home}`];if(!L||L.state==="pre")return null;const tot=L.as+L.hs,line=+j.line,fin=L.state==="post";
    if(tot>line)return {r:j.side==="over"?"hit":"miss",fin:true};
    if(fin)return {r:tot===line?"void":(j.side==="under"?"hit":"miss"),fin};
    return {r:j.side==="under"?"hit":"miss",fin:false}}
  if(t==="express"){const rs=(j.legs||[]).map(l=>legLive(l.away,l.home,l.side));if(rs.some(x=>!x))return rs.some(x=>x&&x.fin&&x.r==="miss")?{r:"miss",fin:true}:null;
    if(rs.some(x=>x.fin&&x.r==="miss"))return {r:"miss",fin:true};return {r:rs.every(x=>x.r==="hit")?"hit":"miss",fin:rs.every(x=>x.fin)}}
  return null}
function statOf(t,label){const s=(t.statistics||[]).find(x=>x.label===label||x.name===label);return s?s.displayValue:null}
function parseSummary(s,L){const out={goals:[],teams:{},players:[],goalies:[]};
  const idA={};for(const c of ((s.header||{}).competitions||[{}])[0].competitors||[])idA[c.team&&c.team.id]=ab(c.team&&c.team.abbreviation);
  for(const p of s.plays||[]){if(!p.scoringPlay)continue;const pt=p.participants||[];const nm=x=>(x.athlete||{}).displayName||"";
    const sc=pt.find(x=>x.type==="scorer");const as=pt.filter(x=>x.type==="assister").map(nm).join(", ");const txt=String(p.text||"");const sa=((p.strength||{}).abbreviation)||"";
    out.goals.push({per:(p.period||{}).number||0,clock:(p.clock||{}).displayValue||"",team:idA[(p.team||{}).id]||"",who:sc?nm(sc):txt.split(/ Goal\b/)[0].replace(/^,.*$/,"гол"),as,kind:/empty/i.test(txt)||p.emptyNet?"п.в.":sa==="power-play"?"бол.":sa==="short-handed"?"мен.":""})}
  for(const t of ((s.boxscore||{}).teams||[])){const a=ab(t.team&&t.team.abbreviation);
    out.teams[a]={sog:statOf(t,"Shots"),ppg:statOf(t,"Power Play Goals"),ppo:statOf(t,"Power Play Opportunities"),fo:statOf(t,"Faceoff Win Percent"),hits:statOf(t,"Hits"),blk:statOf(t,"Blocked Shots"),pim:statOf(t,"Penalty Minutes"),give:statOf(t,"Giveaways"),take:statOf(t,"Takeaways")}}
  for(const g of ((s.boxscore||{}).players||[])){const a=ab(g.team&&g.team.abbreviation);
    for(const grp of g.statistics||[]){const lab=grp.labels||[];const ix=k=>lab.indexOf(k);
      const keys=grp.keys||[];const kx=k=>keys.indexOf(k);
      for(const x of grp.athletes||[]){const st=x.stats||[];const v=k=>{const i=kx(k)>=0?kx(k):ix(k);return i<0?null:st[i]};const nm=(x.athlete||{}).displayName||"";
        if(/goal/i.test(grp.name||"")){const SA=+(v("shotsAgainst")??v("SA"))||0;if(SA>0)out.goalies.push({name:nm,team:a,sa:SA,sv:+(v("saves")??v("SV"))||0,pct:v("savePct")??v("SV%")})}
        else{const G=+(v("goals")??v("G"))||0,As=+(v("assists")??v("A"))||0;out.players.push({name:nm,team:a,g:G,a:As,pts:G+As,sog:+(v("shotsTotal")??v("S"))||0,pm:v("plusMinus"),toi:v("timeOnIce")})}}}}
  out.players.sort((x,y)=>y.pts-x.pts||y.g-x.g||y.sog-x.sog);return out}
function liveBlock(m,L){const S=LSUM[L.id];const title=L.state==="in"?`<span class="dot"></span> Идёт: ${esc(L.per)}${L.clock?", "+esc(L.clock):""}`:`Финал${L.end?" ("+endLong(L.end)+")":""}`;
  if(!S)return `<div class="blk full"><h4 style="display:flex;align-items:center;gap:8px">${title}</h4><p class="note">Загружаю статистику матча…</p></div>`;
  const ta=S.teams[m.away]||{},th=S.teams[m.home]||{};const pr=(x,y)=>[x,y];
  const rows=[["Броски в створ",pr(ta.sog,th.sog)],["Большинство",pr(ta.ppg!=null?`${ta.ppg}/${ta.ppo}`:null,th.ppg!=null?`${th.ppg}/${th.ppo}`:null)],["Вбрасывания, %",pr(ta.fo,th.fo)],["Силовые",pr(ta.hits,th.hits)],["Блок-шоты",pr(ta.blk,th.blk)],["Штрафные минуты",pr(ta.pim,th.pim)]].filter(r=>r[1][0]!=null&&r[1][1]!=null);
  const parse=v=>typeof v==="string"?parseFloat(v.split("/")[0])||0:+v||0;
  const per={};S.goals.forEach(g=>(per[g.per]=per[g.per]||[]).push(g));
  const top=S.players.filter(p=>p.pts>0).slice(0,3);
  return `<div class="blk"><h4 style="display:flex;align-items:center;gap:8px;margin-top:0">${title}</h4>
     ${S.goals.length?goalList(S.goals.map(g=>({per:g.per,time:g.clock,team:g.team,who:g.who,kind:g.kind,as:g.as})),m.away,m.home):'<p class="note">Голов пока нет.</p>'}</div>
   <div class="blk">${rows.length?`<div class="sbars">${sbHead(m.away,m.home)}${rows.map(([l,v])=>sbar(l,v,m.away,m.home,parse)).join("")}</div>`:""}
     ${S.goalies.length?`<h4>Вратари</h4><ul class="ul">${S.goalies.map(g=>`<li><b>${pref(g.name,g.team)}</b> (${EN[g.team]||g.team}) — ${g.sv} из ${g.sa}${g.pct?`, ${esc(g.pct)}`:""}</li>`).join("")}</ul>`:""}
     ${top.length?`<h4>Лучшие в матче</h4>${top.map(p=>`<div class="lr" style="padding:6px 0;border:0;grid-template-columns:minmax(0,1fr) auto"><span class="who">${photo(findP(p.name,p.team)||p.name,p.team,46)}<span class="nm2"><span>${pref(p.name,p.team)}${posTag(findP(p.name,p.team)||p.name)}</span><small>${EN[p.team]||p.team} · бросков ${p.sog}${p.toi?` · ${esc(p.toi)} на льду`:""}</small></span></span><span class="v">${gaHtml(p.g,p.a)}</span></div>`).join("")}`:""}</div>`}
function liveLoop(){clearInterval(LTIMER);LTIMER=setInterval(()=>poll(false),25000);poll(false)}
document.addEventListener("visibilitychange",()=>{if(!document.hidden&&Date.now()-LAST_POLL>20000)poll(false)});

/* ---------- запуск ---------- */
(async function(){
  const v="?v="+Math.floor(Date.now()/6e4);
  const h=(location.hash||"").slice(1);if(h==="model")VIEW="games";else if(VIEWS[h])VIEW=h;
  try{const [d,m,n]=await Promise.all([fetch(DATA+"data.json"+v).then(r=>r.json()),fetch(DATA+"model.json"+v).then(r=>r.json()).catch(()=>({games:[],teams:{}})),fetch(DATA+"names_ru.json"+v).then(r=>r.json()).catch(()=>({}))]);D=d;M=m;RUN=n||{}}
  catch(e){$("#app").innerHTML='<div class="box empty">Не удалось загрузить данные. Обнови страницу.</div>';return}
  for(const s of D.standings||[])if(s.logo)LOGO[s.abbr]=s.logo;
  buildTeams();render();
  try{A=await fetch(DATA+"archive.json"+v).then(r=>r.json());buildTeams();
    try{BOX=await fetch(DATA+"box.json"+v).then(r=>r.ok?r.json():null);patchFromBox(BOX)}catch(e){}
    rerenderKeep()}catch(e){}
  try{ST=await fetch(DATA+"stories.json"+v).then(r=>r.ok?r.json():[]);ST=(Array.isArray(ST)?ST:ST.stories||[]).slice().sort((a,b)=>String(b.time).localeCompare(String(a.time)));if(ST.length)rerenderKeep()}catch(e){ST=[]}
  try{EDGE=await fetch(DATA+"edge.json"+v).then(r=>r.ok?r.json():null);if(EDGE&&VIEW==="home")rerenderKeep()}catch(e){EDGE=null}
  liveLoop();
  setInterval(()=>{if(["home","games"].includes(VIEW)&&$("#sheet").hidden&&!needLive())rerenderKeep()},60000);
})();
window.addEventListener("hashchange",()=>{const h=(location.hash||"").slice(1);closeSheet();if(VIEWS[h]&&h!==VIEW){VIEW=h;render();window.scrollTo(0,0)}});
