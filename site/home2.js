/* Главная v2: три понятных блока — «Сегодня», «Ночь», «Главное». Без декоративных обложек и каруселей. */
(function(){
const css=`
.h2w{display:grid;gap:28px;grid-template-columns:minmax(0,1fr)}
@media (min-width:980px){.h2w{grid-template-columns:minmax(0,1fr) 340px;align-items:start;gap:32px}}
.h2main,.h2side{display:flex;flex-direction:column;gap:28px;min-width:0}
.h2sec{display:flex;flex-direction:column;gap:10px}
.h2hd{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.h2hd h2{font-family:var(--display);font-weight:700;font-size:28px;line-height:1.05;letter-spacing:.005em;text-transform:none;margin:0}
.h2hd h2 small{font-family:var(--body,inherit);font-size:15px;font-weight:500;color:var(--mute);margin-left:8px;letter-spacing:0}
.h2hd a,.h2hd button.lnk{font-size:14px;font-weight:600;color:var(--link);background:none;border:0;padding:0;cursor:pointer}
.h2box{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
/* сегодня: строка табло */
.h2g{display:grid;grid-template-columns:78px minmax(0,1fr) auto;gap:10px 14px;align-items:center;padding:12px 14px;border-top:1px solid var(--line);width:100%;background:none;border-left:0;border-right:0;border-bottom:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.h2g:first-child{border-top:0}
.h2g:hover{background:var(--soft)}
.h2g .tm{display:flex;flex-direction:column;font-family:var(--display);font-size:19px;font-weight:700;line-height:1}
.h2g .tm small{display:block;font-family:var(--body,inherit);font-size:11.5px;font-weight:600;color:var(--mute);margin-top:4px;white-space:nowrap}
.h2g.mo{box-shadow:inset 3px 0 0 var(--gold)}
.h2g .teams{display:flex;flex-direction:column;gap:6px;min-width:0}
.h2g .tr{display:flex;align-items:center;gap:8px;min-width:0}
.h2g .tr b{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.h2g .tr .p{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:600;color:var(--mute)}
.h2g .tr .p.fav{color:var(--ink);font-weight:800}
.h2g .bar{grid-column:2/3;height:4px;border-radius:2px;display:flex;overflow:hidden;background:var(--soft2);margin-top:2px}
.h2g .bar i{display:block;height:100%}
.h2g .v{grid-row:1/3;grid-column:3;align-self:center;font-size:12px;font-weight:700;padding:4px 8px;border-radius:999px;white-space:nowrap;background:var(--soft);color:var(--ink2)}
.h2g .v.val{background:var(--valbg);color:var(--win)}.h2g .v.gold{background:var(--goldbg);color:var(--gold)}.h2g .v.no{background:none;color:var(--mute);border:1px dashed var(--line)}
.h2g .h2mo{grid-column:2/-1;font-size:14px;line-height:1.45;color:var(--ink2);margin:2px 0 0;background:none;padding:0}
.h2g .h2mo b{color:var(--gold)}
.h2conf{font-size:14px;color:var(--ink2);padding:0 2px}
.h2conf b{color:var(--ink)}
/* ночь */
.h2scores{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));margin:0 -1px -1px 0}
.h2sc{background:var(--card);padding:10px 12px;border-right:1px solid var(--line)!important;border-bottom:1px solid var(--line)!important;display:flex;flex-direction:column;gap:5px;border-top:0;border-left:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.h2sc:hover{background:var(--soft)}
.h2sc .r{display:flex;align-items:center;gap:7px;font-weight:600}
.h2sc .r .s{margin-left:auto;font-family:var(--display);font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}
.h2sc .r.lo{color:var(--mute)}
.h2sc small{font-size:11.5px;color:var(--mute);font-weight:600}
.h2star{display:grid;grid-template-columns:58px 44px minmax(0,1fr) auto;gap:4px 12px;align-items:center;padding:12px 14px;border-top:1px solid var(--line)}
.h2star:first-child{border-top:0}
.h2star .n{font-family:var(--display);font-size:26px;font-weight:700;color:var(--gold);text-align:center}
.h2star .nm{display:flex;flex-direction:column;min-width:0}
.h2star .nm button{font-weight:700;font-size:15.5px;text-align:left;padding:0;background:none;border:0;color:inherit;cursor:pointer}
.h2star .nm small{color:var(--mute);font-size:12.5px}
.h2star .ln{font-family:var(--display);font-size:22px;font-weight:700;white-space:nowrap}
.h2star p{grid-column:3/5;margin:0;font-size:14px;line-height:1.45;color:var(--ink2)}
.h2star.g .n{color:var(--mute);font-size:12px;font-family:inherit;font-weight:700}
/* главное */
.h2lead{padding:16px 16px 14px;display:flex;flex-direction:column;gap:8px;border:0;background:none;text-align:left;color:inherit;font:inherit;cursor:pointer;width:100%}
.h2lead h3{font-family:var(--display);font-size:27px;line-height:1.08;font-weight:700;margin:0}
.h2lead p{margin:0;font-size:15px;line-height:1.5;color:var(--ink2);max-width:68ch}
.h2meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12.5px;color:var(--mute);font-weight:600}
.h2meta .k{color:var(--acc)}
.h2n{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;padding:12px 16px;border-top:1px solid var(--line);width:100%;background:none;border-left:0;border-right:0;border-bottom:0;text-align:left;color:inherit;font:inherit;cursor:pointer}
.h2n:hover,.h2lead:hover{background:var(--soft)}
.h2n h4{margin:0;font-size:16px;line-height:1.3;font-weight:700}
.h2n .bd{display:flex;gap:4px;align-self:center}
.h2n .h2meta{grid-column:1/2}
.h2col{border-left:3px solid var(--acc)}
.h2acc{display:flex;align-items:baseline;gap:10px;padding:14px 16px}
.h2acc b{font-family:var(--display);font-size:34px;font-weight:700;line-height:1}
@media (max-width:560px){.h2g{grid-template-columns:58px minmax(0,1fr);padding:12px}.h2g .v{grid-row:auto;grid-column:2;justify-self:start}.h2g .h2mo{grid-column:1/-1}.h2hd h2 small{display:block;margin:6px 0 0;font-size:14px}.h2star{grid-template-columns:34px 40px minmax(0,1fr) auto;gap:4px 10px;padding:12px}.h2star .n{font-size:22px}.h2star p{grid-column:2/5}.h2lead h3{font-size:24px}}
.h2acc span{color:var(--ink2);font-size:14px}
.h2side .wg-h h2{text-transform:none;letter-spacing:0}
`;
const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);

const LV={bet:["Выше рынка","val"],lean:["Чуть выше","gold"],pass:["Как рынок",""],noodds:["Без линии","no"]};
const rel2=(iso)=>{const ms=new Date(iso)-Date.now();if(ms<=0)return "";const h=Math.floor(ms/36e5);return h>=24?`через ${Math.floor(h/24)} д`:h?`через ${h} ч`:`через ${Math.max(1,Math.floor(ms/6e4))} мин`};
const ord=(i)=>["1","2","3"][i]||"";

function gameRow2(m,isMotd){const p=modelOf(m);const s=state(m.start);
  const pa=p?(p.p_away_blend??p.p_away):null, ph=p?(p.p_home_blend??p.p_home):null;const fa=pa!=null&&pa>ph;
  const v=p&&p.verdict?LV[p.verdict.level]:null;
  const time=s==="live"?'<span class="chip live">LIVE</span>':s==="done"?"<small>завершён</small>":`${kt(m.start)}${rel2(m.start)?`<small>${rel2(m.start)}</small>`:""}`;
  const bar=p?`<div class="bar"><i style="width:${pa*100}%;background:${fa?tcol(m.away):"var(--line)"}"></i><i style="width:${ph*100}%;background:${fa?"var(--line)":tcol(m.home)}"></i></div>`:"";
  const mo=isMotd&&D.motd&&D.motd.text?`<p class="h2mo"><b>Матч дня.</b> ${esc(D.motd.text)}</p>`:"";
  return `<button class="h2g${isMotd?" mo":""}" data-go="games" data-open="${m.away}-${m.home}"><span class="tm">${time}</span>
   <span class="teams"><span class="tr">${badge(m.away,"xs")}<b>${EN[m.away]}</b><span class="p ${fa?"fav":""}">${pa!=null?pct(pa):""}</span></span><span class="tr">${badge(m.home,"xs")}<b>${EN[m.home]}</b><span class="p ${fa?"":"fav"}">${ph!=null?pct(ph):""}</span></span></span>
   ${v?`<span class="v ${v[1]}">${v[0]}</span>`:""}${bar}${mo}</button>`}

function todaySec(){const u=D.upcoming||[];if(!u.length)return "";
  const mo=D.motd?u.find(x=>x.away===D.motd.away&&x.home===D.motd.home):null;
  const list=[...u].sort((a,b)=>String(a.start).localeCompare(String(b.start)));
  const ex=D.express&&D.express.legs&&D.express.date===(D.upcoming_date||D.express.date)?D.express:null;
  const conf=ex?`<div class="h2conf">Самые уверенные исходы: ${ex.legs.map(l=>{const t=l.side?sideTeam(l,l.side):l.pick;return `<b>${EN[t]||esc(t)}</b>`}).join(" и ")}</div>`:"";
  return `<section class="h2sec"><div class="h2hd"><h2>Сегодня<small>${esc(dLong(D.upcoming_date))}, время по Кирову</small></h2><button class="lnk" data-go="model">Все матчи вперёд</button></div>
   <div class="h2box">${list.map(m=>gameRow2(m,m===mo)).join("")}</div>${conf}</section>`}

function nightSec(){const d=lastDate();if(!d)return "";const gs=A.games.filter(g=>g.date===d);const n=dly();
  const sc=`<div class="h2box"><div class="h2scores">${gs.map(g=>{const aw=g.as>g.hs;return `<button class="h2sc" data-res="${g.date}" data-gid="${g.id}"><span class="r ${aw?"":"lo"}">${badge(g.away,"xs")}${EN[g.away]}<span class="s">${g.as}</span></span><span class="r ${aw?"lo":""}">${badge(g.home,"xs")}${EN[g.home]}<span class="s">${g.hs}</span></span>${endTag(g.end)?`<small>${g.end==="OT"?"овертайм":"буллиты"}</small>`:""}</button>`}).join("")}</div></div>`;
  let stars="";
  if(n&&n.heroes&&n.heroes.length){
    const row=(x,lab,cls,role)=>`<div class="h2star ${cls||""}"><span class="n">${lab}</span>${pk(x.name,x.team,"m",x.pos)}<span class="nm"><button class="plink" data-player="${esc(x.name)}" data-pteam="${x.team}">${esc(x.name)}</button><small>${role?role+" · ":""}${esc(FULL[x.team]||x.team)}</small></span><span class="ln">${esc(x.line||"")}</span>${x.text?`<p>${esc(x.text)}</p>`:""}</div>`;
    stars=`<div class="h2box">${n.heroes.map((x,i)=>row(x,ord(i)+"★")).join("")}${n.goalie&&!n.heroes.some(h=>h.name===n.goalie.name)?row(n.goalie,"","g","Вратарь ночи"):""}${n.russian&&!n.heroes.some(h=>h.name===n.russian.name)?row(n.russian,"","g","Лучший россиянин"):""}</div>`}
  return `<section class="h2sec"><div class="h2hd"><h2>Ночь<small>${esc(dLong(d))}</small></h2><button class="lnk" data-go="results">Итоги и протоколы</button></div>${sc}
   ${stars?`<div class="h2hd" style="margin-top:6px"><h2 style="font-size:22px">Три звезды</h2></div>${stars}`:""}</section>`}

function newsSec(){const arts=freshArts();if(!arts.length)return "";
  const col=arts.find(x=>x.kind==="column");const news=arts.filter(x=>x.kind!=="column");const lead=news[0];const rest=news.slice(1,6);
  const meta=x=>`<span class="h2meta">${x.kind==="column"?'<span class="k">Колонка Claude</span>':""}${x.source&&x.kind!=="column"?`<span>${esc(x.source)}</span>`:""}${x.time?`<span>${String(x.time).length>10?esc(new Date(x.time).toLocaleString("ru-RU",{timeZone:"Europe/Kirov",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).replace(".","")):esc(dShort(String(x.time).slice(0,10)))}</span>`:""}</span>`;
  const bd=x=>`<span class="bd">${(x.teams||[]).slice(0,2).map(t=>badge(t,"xs")).join("")}</span>`;
  return `<section class="h2sec"><div class="h2hd"><h2>Главное</h2><button class="lnk" data-go="news">Все новости</button></div>
   <div class="h2box">${lead?`<button class="h2lead" data-art="${lead.k}">${meta(lead)}<h3>${esc(lead.title)}</h3><p>${esc(lead.dek||lead.body[0])}</p></button>`:""}
   ${rest.map(x=>`<button class="h2n" data-art="${x.k}"><h4>${esc(x.title)}</h4>${bd(x)}${meta(x)}</button>`).join("")}</div>
   ${col?`<div class="h2box h2col"><button class="h2lead" data-art="${col.k}">${meta(col)}<h3 style="font-size:23px">${esc(col.title)}</h3><p>${esc(col.dek||col.body[0])}</p></button></div>`:""}</section>`}

function accSec(){const j=(D.journal||[]).filter(x=>x.result&&x.result!=="void");if(!j.length)return "";
  const hit=j.filter(x=>x.result==="hit").length;
  return `<section class="h2sec"><div class="h2hd"><h2 style="font-size:22px">Точность модели</h2><button class="lnk" data-go="picks">Журнал</button></div>
   <div class="h2box"><div class="h2acc"><b>${Math.round(hit/j.length*100)}%</b><span>${hit} из ${j.length} прогнозов угадано с начала ведения журнала</span></div></div></section>`}

window.vHome=function(){return `<div class="h2w"><div class="h2main">${todaySec()}${nightSec()}${newsSec()}</div>
  <aside class="h2side">${accSec()}${standW()}${leadersW()}</aside></div>`};
try{if(typeof D!=="undefined"&&D&&D.upcoming&&typeof render==="function")render()}catch(e){}
})();
