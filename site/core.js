/* NHL-STATS.RU — ядро: справочники, данные, утилиты, общие компоненты */
"use strict";
const DATA="./";
/* названия: EN — интерфейс (английский), RU — прогнозы и тексты */
const AB={"ANA": "АНА", "BOS": "БОС", "BUF": "БАФ", "CGY": "КАЛ", "CAR": "КАР", "CHI": "ЧИК", "COL": "КОЛ", "CBJ": "КЛМ", "DAL": "ДАЛ", "DET": "ДЕТ", "EDM": "ЭДМ", "FLA": "ФЛА", "LAK": "ЛАК", "MIN": "МИН", "MTL": "МОН", "NSH": "НЭШ", "NJD": "НДЖ", "NYI": "АЙЛ", "NYR": "РЕЙ", "OTT": "ОТТ", "PHI": "ФИЛ", "PIT": "ПИТ", "SJS": "САН", "SEA": "СИЭ", "STL": "СЕН", "TBL": "ТАМ", "TOR": "ТОР", "UTA": "ЮТА", "VAN": "ВАН", "VGK": "ВЕГ", "WSH": "ВАШ", "WPG": "ВИН"};
const RU={ANA:"Анахайм",BOS:"Бостон",BUF:"Баффало",CGY:"Калгари",CAR:"Каролина",CHI:"Чикаго",COL:"Колорадо",CBJ:"Коламбус",DAL:"Даллас",DET:"Детройт",EDM:"Эдмонтон",FLA:"Флорида",LAK:"Лос-Анджелес",MIN:"Миннесота",MTL:"Монреаль",NSH:"Нэшвилл",NJD:"Нью-Джерси",NYI:"Айлендерс",NYR:"Рейнджерс",OTT:"Оттава",PHI:"Филадельфия",PIT:"Питтсбург",SJS:"Сан-Хосе",SEA:"Сиэтл",STL:"Сент-Луис",TBL:"Тампа",TOR:"Торонто",UTA:"Юта",VAN:"Ванкувер",VGK:"Вегас",WSH:"Вашингтон",WPG:"Виннипег"};
const FULL_LAT={"ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres", "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars", "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montréal Canadiens", "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders", "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken", "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs", "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights", "WSH": "Washington Capitals", "WPG": "Winnipeg Jets"};
/* прежние названия клубов в карьерах игроков */
const OLD_TEAMS={"Montreal Canadiens":"MTL","Arizona Coyotes":"UTA","Utah Hockey Club":"UTA","Utah Mammoth":"UTA","Phoenix Coyotes":"UTA","Atlanta Thrashers":"WPG","Mighty Ducks of Anaheim":"ANA","Hartford Whalers":"CAR"};
const OLD_RU={ARI:"Аризона",PHX:"Финикс",ATL:"Атланта",HFD:"Хартфорд",QUE:"Квебек",MNS:"Миннесота Норт Старз"};
const EN=RU; /* интерфейс по-русски: короткие названия клубов */
const FULL={"ANA": "Анахайм Дакс", "BOS": "Бостон Брюинз", "BUF": "Баффало Сейбрз", "CGY": "Калгари Флэймз", "CAR": "Каролина Харрикейнз", "CHI": "Чикаго Блэкхокс", "COL": "Колорадо Эвеланш", "CBJ": "Коламбус Блю Джекетс", "DAL": "Даллас Старз", "DET": "Детройт Ред Уингз", "EDM": "Эдмонтон Ойлерз", "FLA": "Флорида Пантерз", "LAK": "Лос-Анджелес Кингз", "MIN": "Миннесота Уайлд", "MTL": "Монреаль Канадиенс", "NSH": "Нэшвилл Предаторз", "NJD": "Нью-Джерси Девилз", "NYI": "Нью-Йорк Айлендерс", "NYR": "Нью-Йорк Рейнджерс", "OTT": "Оттава Сенаторз", "PHI": "Филадельфия Флайерз", "PIT": "Питтсбург Пингвинз", "SJS": "Сан-Хосе Шаркс", "SEA": "Сиэтл Кракен", "STL": "Сент-Луис Блюз", "TBL": "Тампа-Бэй Лайтнинг", "TOR": "Торонто Мейпл Лифс", "UTA": "Юта Мамонт", "VAN": "Ванкувер Кэнакс", "VGK": "Вегас Голден Найтс", "WSH": "Вашингтон Кэпиталз", "WPG": "Виннипег Джетс"};
const COLORS={ANA:["#F47A38","#B9975B"],BOS:["#FFB81C","#000000"],BUF:["#003087","#FFB81C"],CGY:["#C8102E","#F1BE48"],CAR:["#CE1126","#000000"],CHI:["#CF0A2C","#000000"],COL:["#6F263D","#236192"],CBJ:["#002654","#CE1126"],DAL:["#006847","#8F8F8C"],DET:["#CE1126","#FFFFFF"],EDM:["#041E42","#FF4C00"],FLA:["#041E42","#C8102E"],LAK:["#111111","#A2AAAD"],MIN:["#154734","#A6192E"],MTL:["#AF1E2D","#192168"],NSH:["#FFB81C","#041E42"],NJD:["#CE1126","#000000"],NYI:["#00539B","#F47D30"],NYR:["#0038A8","#CE1126"],OTT:["#C52032","#C2912C"],PHI:["#F74902","#000000"],PIT:["#000000","#FCB514"],SJS:["#006D75","#EA7200"],SEA:["#001628","#99D9D9"],STL:["#002F87","#FCB514"],TBL:["#002868","#FFFFFF"],TOR:["#00205B","#FFFFFF"],UTA:["#6CACE4","#010101"],VAN:["#00205B","#00843D"],VGK:["#B4975A","#333F42"],WSH:["#C8102E","#041E42"],WPG:["#041E42","#004C97"]};
const DIVS=[["Восток","Атлантический",["BOS","BUF","DET","FLA","MTL","OTT","TBL","TOR"]],["Восток","Столичный",["CAR","CBJ","NJD","NYI","NYR","PHI","PIT","WSH"]],["Запад","Центральный",["CHI","COL","DAL","MIN","NSH","STL","UTA","WPG"]],["Запад","Тихоокеанский",["ANA","CGY","EDM","LAK","SJS","SEA","VAN","VGK"]]];
const ALL=DIVS.flatMap(d=>d[2]);
const DIV_OF={},CONF_OF={};DIVS.forEach(d=>d[2].forEach(a=>{DIV_OF[a]=d[1];CONF_OF[a]=d[0]}));
const IC={
 home:'<svg viewBox="0 0 24 24"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
 games:'<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
 news:'<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/></svg>',
 results:'<svg viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg>',
 table:'<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
 picks:'<svg viewBox="0 0 24 24"><path d="M3 17l5-5 4 4 8-8"/><path d="M15 8h5v5"/></svg>',
 more:'<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/></svg>',
 teams:'<svg viewBox="0 0 24 24"><circle cx="9" cy="9" r="3.2"/><circle cx="17" cy="10" r="2.4"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5M15 15.5c3 0 6 1.5 6 4.5"/></svg>',
 lead:'<svg viewBox="0 0 24 24"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>',
 inj:'<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V4h6v3M12 11v5M9.5 13.5h5"/></svg>',
 rus:'<svg viewBox="0 0 24 24"><path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z"/></svg>',
 power:'<svg viewBox="0 0 24 24"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg>',
 play:'<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
 ext:'<svg viewBox="0 0 24 24"><path d="M14 4h6v6h-2V7.4l-7.3 7.3-1.4-1.4L16.6 6H14zM5 6h6v2H6v10h10v-5h2v7H4V6z"/></svg>',
 chev:'<svg class="chev" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>'
};
const NAV=[["home","Главная"],["games","Матчи"],["news","Новости"],["results","Итоги"],["table","Таблица"],["picks","Прогнозы"],["more","Ещё"]];
const MORE=[["teams","Команды","составы, звенья, календарь"],["lead","Лидеры","очки, голы, вратари, форма"],["power","Сила команд","рейтинг модели"],["inj","Травмы","кто пропускает матчи"],["rus","Россияне","все наши в НХЛ"]];

/* ---------- состояние ---------- */
let D=null,A={games:[]},M={games:[],horizon:[],teams:{}},ST=[],RUN={};
let VIEW="home",RES_DATE=null,TBL_MODE="div",JF="all",HERO_TAB="stars",RAIL_CONF="Восток",RAIL_LEAD="points",HOT_MODE="hot";
const OPEN=new Set();
const $=s=>document.querySelector(s);

/* ---------- утилиты ---------- */
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function lum(hex){const n=parseInt(String(hex).slice(1),16),r=(n>>16&255)/255,g=(n>>8&255)/255,b=(n&255)/255;const f=v=>v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4);return .2126*f(r)+.7152*f(g)+.0722*f(b)}
function shade(hex,k){const n=parseInt(hex.slice(1),16);const f=v=>Math.max(0,Math.min(255,Math.round(v*k)));return "#"+[n>>16&255,n>>8&255,n&255].map(v=>f(v).toString(16).padStart(2,"0")).join("")}
function tcol(a){const c=COLORS[a]||["#556070","#8892A0"];const ok=x=>{const l=lum(x);return l>.05&&l<.75};return ok(c[0])?c[0]:ok(c[1])?c[1]:"#8FA6C8"}
function tdeep(a){const c=COLORS[a]||["#2A2E35","#3A3F48"];return lum(c[0])<.5?c[0]:lum(c[1])<.5?c[1]:shade(c[0],.55)}
function cdist(x,y){const p=h=>{const n=parseInt(String(h).slice(1),16);return [n>>16&255,n>>8&255,n&255]};const [a,b]=[p(x),p(y)];return Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2])}
/* цвета двух команд, которые не сливаются: при похожих хозяева берут второй цвет клуба */
function tpair(a,h){const ca=tcol(a);let ch=tcol(h);if(cdist(ca,ch)<90){const alt=(COLORS[h]||[])[1];const ok=alt&&lum(alt)>.05&&lum(alt)<.85&&cdist(ca,alt)>=90;ch=ok?alt:"#9AA3AE"}return [ca,ch]}
function pair(a,b){let x=tdeep(a),y=tdeep(b);if(Math.abs(lum(x)-lum(y))<.012&&x.toLowerCase()===y.toLowerCase())y=shade(y,.6);return [x,y]}
const f2=x=>x==null||isNaN(x)?"—":Number(x).toFixed(2);
const pct=x=>x==null||isNaN(x)?"—":Math.round(x*100)+"%";
const nz=(x,d=1)=>String((+x).toFixed(d)).replace(".",",");
const sgn=v=>v>0?"pos":v<0?"neg":"";
const plural=(n,a,b,c)=>{const m=n%10,k=n%100;return n+" "+(m===1&&k!==11?a:m>=2&&m<=4&&(k<12||k>14)?b:c)};
function dShort(iso){return new Date(iso+"T12:00:00Z").toLocaleDateString("ru-RU",{day:"numeric",month:"short"}).replace(".","")}
function dLong(iso){return new Date(iso+"T12:00:00Z").toLocaleDateString("ru-RU",{weekday:"long",day:"numeric",month:"long"})}
function dWd(iso){return new Date(iso+"T12:00:00Z").toLocaleDateString("ru-RU",{weekday:"short"})}
function kt(iso){return new Date(iso).toLocaleTimeString("ru-RU",{timeZone:"Europe/Kirov",hour:"2-digit",minute:"2-digit"})}
function kdt(iso){return new Date(iso).toLocaleString("ru-RU",{timeZone:"Europe/Kirov",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).replace(".","")}
function rel(iso){const ms=new Date(iso)-Date.now();if(ms<=0)return "";const h=Math.floor(ms/36e5);return h>=24?`через ${Math.floor(h/24)} д`:h?`через ${h} ч`:`через ${Math.max(1,Math.floor(ms/6e4))} мин`}
function state(iso){const ms=Date.now()-new Date(iso);return ms<0?"pre":ms<3.6*36e5?"live":"done"}
function nhlDate(iso){return new Date(new Date(iso)-6*36e5).toISOString().slice(0,10)}
const endTag=e=>e==="OT"?"ОТ":e==="SO"?"Б":"";
const endLong=e=>e==="OT"?"овертайм":e==="SO"?"буллиты":"";
function ls(k,v){try{if(v===undefined)return JSON.parse(localStorage.getItem(k)||"null");localStorage.setItem(k,JSON.stringify(v))}catch(e){return null}}
const sideTeam=(m,s)=>s==="home"?m.home:m.away;

/* ---------- логотипы и фото ---------- */
const LG="https://assets.nhle.com/logos/nhl/svg/",MG="https://assets.nhle.com/mugs/nhl/";
let LOGO={};
function logoUrl(a,dark){let u=LOGO[a]||`${LG}${a}_light.svg`;if(dark)u=u.replace(/_light\.svg$/,"_dark.svg");return u}
function puck(a){const c=COLORS[a]||["#556070","#8892A0"];const fg=lum(c[0])>.45?"#10131A":"#FFFFFF";return `<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="19" fill="${c[0]}"/><circle cx="20" cy="20" r="16" fill="none" stroke="${c[1]}" stroke-width="1.6"/><text x="20" y="24.5" text-anchor="middle" font-family="Arial Narrow,Arial,sans-serif" font-weight="700" font-size="12" fill="${fg}">${esc(AB[a]||a)}</text></svg>`}
window._lgf=function(img){const s=img.closest(".lg");if(s)s.innerHTML=puck(s.dataset.a)};
function logo(a,s=28){if(!COLORS[a])return `<span class="lg" style="--s:${s}px">${puck(a)}</span>`;
  return `<span class="lg" data-a="${a}" style="--s:${typeof s==="number"?s+"px":s}" aria-hidden="true"><picture><source srcset="${logoUrl(a,true)}" media="(prefers-color-scheme: dark)"><img src="${logoUrl(a)}" alt="" loading="lazy" decoding="async" onerror="_lgf(this)"></picture></span>`}
/* логотип для всегда-тёмных зон (лента, матч дня): прозрачный, тёмная версия */
function badge(a,s=36){if(!COLORS[a])return logo(a,s);return `<span class="lg lgd" data-a="${a}" style="--s:${s}px" aria-hidden="true"><img src="${logoUrl(a,true)}" alt="" loading="lazy" decoding="async" onerror="_lgf(this)"></span>`}
function initials(n){return String(n||"").split(/\s+/).map(w=>w[0]||"").join("").slice(0,2).toUpperCase()}
let NUMN=null;const nrm=s=>String(s||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z]/g,"");
function pnum(name,pos){const N=(D&&D.numbers)||{};let n=pos!=null?N[name+"|"+pos]:null;if(n==null)n=N[name];if(n==null){if(!NUMN){NUMN={};for(const k in N)NUMN[nrm(k)]=N[k]}n=NUMN[nrm(name)]}return n!=null?String(n):null}
let HEADN=null;
function headOf(name){const H=(D&&D.heads)||{};if(H[name])return H[name];if(!HEADN){HEADN={};for(const k in H)HEADN[nrm(k)]=H[k]}return HEADN[nrm(name)]||null}
window._phf=function(img){const s=img.closest(".ph");if(s){img.remove()}};
function photo(name,team,s=44,cls=""){const h=headOf(name);const c=tdeep(team);const n=pnum(name);
  return `<span class="ph ${cls}" style="--s:${s}px;--c:${c}" aria-hidden="true" title="${esc(pn(name))}"><span class="ph-t">${n?"#"+n:initials(name)}</span>${h?`<img src="${MG}${h}.png" alt="" loading="lazy" decoding="async" onerror="_phf(this)">`:""}</span>`}
const POS1={C:"C",L:"LW",R:"RW",D:"D",G:"G",LW:"LW",RW:"RW",LD:"LD",RD:"RD"};
function posOf(name,pos){const P=(D&&D.ppos)||{};return P[name]||POS1[pos]||(goalie(name)?"G":(skater(name)&&POS1[skater(name).pos]))||""}
const POSRU={C:"ЦН",LW:"ЛН",RW:"ПН",LD:"ЛЗ",RD:"ПЗ",D:"З",G:"ВР"};
function posRu(name,pos){const p=posOf(name,pos);return POSRU[p]||p||""}
function posTag(name,pos){const p=posRu(name,pos);return p?`<span class="pp">${p}</span>`:""}
function gaHtml(g,a){g=+g||0;a=+a||0;if(!g&&!a)return "0";return `<span class="ga">${[g?`${g}<i>Г</i>`:"",a?`${a}<i>П</i>`:""].filter(Boolean).join(`<em>·</em>`)}</span>`}
function lineHtml(line){const m=/^\s*(\d+)\s*\+\s*(\d+)\s*$/.exec(String(line||""));return m?gaHtml(m[1],m[2]):esc(line||"")}
/* имена по-русски: словарь names_ru.json; pn — полное имя, ps — фамилия; findP — полное латинское имя по фамилии и клубу */
let RUNN=null;
function pn(name){if(!name)return"";if(RUN[name])return RUN[name];if(!RUNN){RUNN={};for(const k in RUN)RUNN[nrm(k)]=RUN[k]}return RUNN[nrm(name)]||name}
function ps(name){const r=pn(name);if(r===name&&!/[А-яЁё]/.test(r))return String(name).split(" ").slice(-1)[0];const p=r.split(" ");return p.length>1?p.slice(1).join(" "):r}
/* id игрока из пути фото (heads: "сезон/КОМ/id") — различает однофамильцев */
let _PID=null;function pidMap(){if(_PID)return _PID;_PID={byId:{},byName:{}};const H=(D&&D.heads)||{};for(const n in H){const id=String(H[n]).split("/").pop();if(id){_PID.byId[id]=n;_PID.byName[n]=id}}return _PID}
function idName(id){return id?pidMap().byId[String(id)]||null:null}
function nameId(n){return pidMap().byName[n]||null}
function findP(s,team){if(!s)return null;s=String(s).trim();const all=[...((D&&D.skaters)||[]),...((D&&D.goalies)||[])];if(all.some(x=>x.name===s))return s;
  const k=nrm(s),last=x=>nrm(String(x.name).split(" ").slice(-1)[0]),full=x=>nrm(x.name);
  let c=all.filter(x=>(!team||x.team===team)&&(full(x)===k||last(x)===k||full(x).endsWith(k)));if(c.length===1)return c[0].name;
  if(!c.length){const ks=Object.keys(RUN).filter(n=>nrm(n)===k||nrm(n.split(" ").slice(-1)[0])===k);if(ks.length===1)return ks[0]}
  return c.length?c[0].name:null}
/* время на льду: минуты (21.6) → «21:36» */
function mmss(m){if(m==null||m==="")return"—";if(typeof m==="string"&&m.includes(":"))return m;m=+m;let mi=Math.floor(m),s=Math.round((m-mi)*60);if(s===60){mi++;s=0}return `${mi}:${String(s).padStart(2,"0")}`}
function plink(name,team,label){return `<button class="plink" data-player="${esc(name)}" data-pteam="${team}">${esc(label||pn(name))}</button>`}
/* фамилия или имя из протокола → кликабельное русское имя */
function pref(s,team,short){const f=findP(s,team);const lab=f?(short?ps(f):pn(f)):(short?ps(s):pn(s));return f?plink(f,team,lab):esc(lab)}

/* ---------- расчёты по архиву ---------- */
let TEAMS={};
function buildTeams(){
  TEAMS={};ALL.forEach(a=>TEAMS[a]={abbr:a,gp:0,w:0,l:0,otl:0,pts:0,gf:0,ga:0,rw:0,hw:0,hl:0,ho:0,aw:0,al:0,ao:0,games:[]});
  const gs=A.games.slice().sort((x,y)=>x.date<y.date?-1:x.date>y.date?1:x.id-y.id);
  for(const g of gs){for(const [s,o,gf,ga,home] of [[g.away,g.home,g.as,g.hs,false],[g.home,g.away,g.hs,g.as,true]]){
    const t=TEAMS[s];if(!t)continue;t.gp++;t.gf+=gf;t.ga+=ga;
    const r=gf>ga?"W":g.end==="REG"?"L":"O";
    if(r==="W"){t.w++;t.pts+=2;if(g.end==="REG")t.rw++;home?t.hw++:t.aw++}else if(r==="L"){t.l++;home?t.hl++:t.al++}else{t.otl++;t.pts++;home?t.ho++:t.ao++}
    t.games.push({id:g.id,date:g.date,opp:o,home,gf,ga,end:g.end,r})}}
  for(const t of Object.values(TEAMS)){const g=t.games;let k=0;const last=g[g.length-1];if(last){for(let i=g.length-1;i>=0&&g[i].r===last.r;i--)k++;t.streak=(last.r==="W"?"В":last.r==="L"?"П":"ОТ")+k}t.pp=t.gp?t.pts/(2*t.gp):0}
  /* если архив ещё не пришёл — берём таблицу НХЛ */
  if(!A.games.length)for(const s of (D&&D.standings)||[]){const t=TEAMS[s.abbr];if(t)Object.assign(t,{gp:s.gp,w:s.w,l:s.l,otl:s.otl,pts:s.pts,gf:s.gf,ga:s.ga,pp:s.gp?s.pts/(2*s.gp):0})}
}
const cmp=(a,b)=>b.pts-a.pts||b.pp-a.pp||b.rw-a.rw||b.w-a.w||(b.gf-b.ga)-(a.gf-a.ga)||b.gf-a.gf;
function rec(a){const t=TEAMS[a];return t&&t.gp?`${t.w}-${t.l}-${t.otl}`:""}
function formDots(a,n=5){const g=(TEAMS[a]?.games||[]).slice(-n);if(!g.length)return"";return `<span class="fd" aria-label="последние матчи">${g.map(x=>`<i class="${x.r}" title="${esc(dShort(x.date))} ${x.home?"дома":"в гостях"} ${esc(EN[x.opp])} ${x.gf}:${x.ga}${x.end!=="REG"?" "+endTag(x.end):""}">${x.r==="W"?"В":x.r==="O"?"О":"П"}</i>`).join("")}</span>`}
function place(a){const d=DIVS.find(d=>d[2].includes(a));return d[2].map(x=>TEAMS[x]).sort(cmp).findIndex(t=>t.abbr===a)+1}
function lastDate(){return A.games.reduce((m,g)=>g.date>m?g.date:m,"")}
function dates(){return [...new Set(A.games.map(g=>g.date))].sort()}
const skater=n=>(D.skaters||[]).find(s=>s.name===n);
const goalie=n=>(D.goalies||[]).find(s=>s.name===n);
/* Сезонная статистика НХЛ (club-stats) обновляется с опозданием: матчи ночи уже в архиве, а очки игроков — ещё вчерашние.
   Если у клуба в архиве матчей больше, чем игр у его самого играющего игрока, досчитываем последний игровой день из протоколов box.json.
   Как только НХЛ обновит цифры, разрыв исчезнет и досчёт сам выключится. */
function patchFromBox(B){if(!B||!B.date||!(B.games||[]).length||!D)return;const S=D.skaters||(D.skaters=[]),G=D.goalies||(D.goalies=[]);
  const tg={},mx={},ld={};for(const g of A.games)for(const t of [g.away,g.home]){tg[t]=(tg[t]||0)+1;if(!ld[t]||g.date>ld[t])ld[t]=g.date}
  for(const s of S)mx[s.team]=Math.max(mx[s.team]||0,s.gp||0);for(const g of G)mx[g.team]=Math.max(mx[g.team]||0,g.gp||0);
  const sec=t=>{const m=/^(\d+):(\d+)$/.exec(t||"");return m?+m[1]*60+ +m[2]:0};let n=0;
  for(const b of B.games){const g=A.games.find(x=>x.id===b.id);if(!g)continue;
    for(const tm of [g.away,g.home]){if(!mx[tm]||(tg[tm]||0)-mx[tm]<1||g.date!==ld[tm])continue;const won=(tm===g.home?g.hs>g.as:g.as>g.hs);
      for(const p of (b.players||[]).filter(p=>p.team===tm)){
        if(p.pos==="G"){let x=G.find(s=>s.name===p.name&&s.team===tm);if(!x){x={team:tm,name:p.name,gp:0,w:0,l:0,otl:0,sv:0,gaa:0,so:0};G.push(x)}
          const ga0=(x.gaa||0)*x.gp,sa0=x.sv<1?ga0/(1-(x.sv||0)):0,sa=sa0+(p.shots||0),ga=ga0+(p.ga||0);x.gp++;
          if(p.starter!==false){if(won)x.w++;else if(g.end==="REG")x.l++;else x.otl++;if(!p.ga&&won)x.so=(x.so||0)+1}
          x.sv=sa?Math.round((sa-ga)/sa*1000)/1000:x.sv;x.gaa=Math.round(ga/x.gp*100)/100;x.live=1;continue}
        let x=S.find(s=>s.name===p.name&&s.team===tm);if(!x){x={team:tm,name:p.name,pos:p.pos,gp:0,g:0,a:0,pts:0,pm:0,toi:0,toi_s:0};S.push(x)}
        const t=sec(p.toi);x.toi_s=Math.round(((x.toi_s||0)*x.gp+t)/(x.gp+1));x.toi=Math.round(x.toi_s/6)/10;
        x.gp++;x.g+=p.g||0;x.a+=p.a||0;x.pts=x.g+x.a;x.pm+=p.pm||0;x.live=1}
      n++}}
  if(n)D.stats_patched=B.date}

/* ---------- модель ---------- */
function modelOf(m){return (M.games||[]).find(x=>x.away===m.away&&x.home===m.home)||(M.horizon||[]).find(x=>(m.id&&x.id===m.id)||(x.away===m.away&&x.home===m.home&&x.date===m.date))}
/* Модель и рынок разделены: pB — чистая модель, pM — рынок (линия-ориентир без маржи) */
const pB=(p,s)=>p?p["p_"+s]:null;
function fcOf(p,m){const pa=pB(p,"away"),ph=pB(p,"home");const side=(m&&m.pick_side)||(pa>ph?"away":"home");return {side,t:side==="home"?p.home:p.away,p:side==="home"?ph:pa}}
function oddsOf(m,side){const o=m&&m.odds;if(!o)return null;return side==="home"?o.home:side==="away"?o.away:side==="over"?o.over:side==="under"?o.under:null}
function mktOf(p){if(!p||p.mkt_home==null)return null;const side=p.mkt_home>=p.mkt_away?"home":"away";return {side,t:p[side],p:p["mkt_"+side]}}
function mktTot(p){if(!p||p.mkt_over==null)return null;const side=p.mkt_over>=.5?"over":"under";return {side,p:side==="over"?p.mkt_over:1-p.mkt_over}}
function modTot(p){if(!p||p.p_over==null)return null;const side=p.p_over>=.5?"over":"under";return {side,p:side==="over"?p.p_over:p.p_under}}
/* против рынка: исход и/или тотал модели расходятся с рынком */
function vsOf(p,m){const mk=mktOf(p),mt=mktTot(p);if(!mk&&!mt)return null;const f=p?fcOf(p,m):null;const ts=(m&&m.total_pick&&m.total_pick.side)||(modTot(p)||{}).side;
  return {win:!!(mk&&f&&mk.side!==f.side),tot:!!(mt&&ts&&mt.side!==ts),mk,mt,f,ts}}
function confLegs(){return (D.upcoming||[]).filter(m=>state(m.start)==="pre").map(m=>{const p=modelOf(m);if(!p)return null;const f=fcOf(p,m);return f.p>=.6?{...f,m}:null}).filter(Boolean).sort((a,b)=>b.p-a.p).slice(0,3)}
function srcOf(p){return (D.upcoming||[]).find(x=>x.away===p.away&&x.home===p.home)||(D.week||[]).find(x=>(p.id&&x.id===p.id)||(x.away===p.away&&x.home===p.home&&x.date===p.date))||{away:p.away,home:p.home,start:p.start,date:p.date}}
function mGames(){const seen=new Set();return [...(M.games||[]),...(M.horizon||[])].map(p=>{const m=srcOf(p);return {p,m,start:p.start||m.start}}).filter(({p,start})=>{const k=p.id||p.away+p.home+p.date;if(seen.has(k)||!start)return false;seen.add(k);return state(start)==="pre"}).sort((a,b)=>a.start<b.start?-1:a.start>b.start?1:0)}
function essayOf(p){const g=((D.model_tab||{}).games||{})[p.id];if(g)return Array.isArray(g)?g:String(g).split(/\n\n+/);return []}
function modelWhy(m,p){const out=[];const ra=p.rating_away,rh=p.rating_home;const nm=x=>String(x||"").split("(")[0].trim();
  if(ra&&rh)out.push(`Сила по матчам сезона с поправкой на прошлый: ${RU[m.away]} — атака ${Math.round(ra.att*100)}, оборона ${Math.round(100/ra.dfn)}; ${RU[m.home]} — атака ${Math.round(rh.att*100)}, оборона ${Math.round(100/rh.dfn)}. 100 — средний уровень лиги.`);
  if(M.league&&M.league.home_adv!=null)out.push(`Своя площадка: в этом сезоне хозяева забивают в среднем на ${Math.round(M.league.home_adv*100)}% больше гостей.`);
  for(const [t,g,o] of [[m.away,p.goalie_away,m.home],[m.home,p.goalie_home,m.away]])if(g&&g.name&&g.factor&&Math.abs(g.factor-1)>=.02)out.push(`${nm(g.name)} (${RU[t]}) по сейвам сверх ожидаемого ${g.factor>1?"ниже":"выше"} среднего вратаря лиги: ожидаемые голы ${RU[o]} ${g.factor>1?"+":"−"}${Math.round(Math.abs(1-g.factor)*100)}%.`);
  for(const [t,l,adj,def] of [[m.away,p.inj_away,p.inj_adj_away,p.inj_def_away],[m.home,p.inj_home,p.inj_adj_home,p.inj_def_home]])if(l&&l.length)out.push(`Без ${l.map(x=>x.name).join(", ")}: атака ${RU[t]} −${Math.round((adj||0)*100)}%${def?`, соперник забивает +${Math.round(def*100)}%`:""}.`);
  if(p.b2b_away||p.b2b_home)out.push(`Второй матч за два дня: ${[p.b2b_away&&RU[m.away],p.b2b_home&&RU[m.home]].filter(Boolean).join(" и ")}. Самый надёжный фактор на истории: модель снимает уставшей команде 5% голов.`);
  for(const [t,f] of [[m.away,p.new_coach_away],[m.home,p.new_coach_home]])if(f)out.push(`У ${RU[t]} новый главный тренер: первые 10 матчей после смены обычно лучше ожиданий, модель добавляет 5%.`);
  if(p.p_ot_home!=null&&p.p_ot>=.2)out.push(`Шанс ничьей в основное время ${pct(p.p_ot)}. После ничьей модель даёт ${RU[m.home]} ${pct(p.p_ot_home)}.`);
  return out.map(esc)}

/* ---------- журнал ---------- */
function pickLabel(j){const t=j.type||"win";
  if(t==="win"||t==="sure")return j.side?RU[sideTeam(j,j.side)]:esc(j.pick);
  if(t==="total")return `${(j.side==="over")?"Больше":"Меньше"} ${j.line}`;
  if(t==="express")return (j.legs||[]).map(l=>l.side?RU[sideTeam(l,l.side)]:l.pick).join(" + ");
  return esc(j.pick||"")}
function matchLabel(j){if((j.type)==="express")return (j.legs||[]).map(l=>`${RU[l.away]} — ${RU[l.home]}`).join(" · ");return j.away?`${RU[j.away]} — ${RU[j.home]}`:""}
const plOf=(res,odds)=>res==="hit"?odds-1:res==="miss"?-1:res==="void"?0:null;
function amRes(x){if(!x.changed||!x.result||x.result==="void")return x.result;const t=x.type||"win";
  if(t==="win")return (x.side_am||x.side)===x.side?x.result:(x.result==="hit"?"miss":"hit");
  if(t==="total"){const m=String(x.score||"").match(/(\d+):(\d+)/);if(!m)return null;const tot=+m[1]+ +m[2];const L=+(x.line_am??x.line),sd=x.side_am||x.side;return tot===L?"void":((tot>L)===(sd==="over")?"hit":"miss")}
  return null}

/* ---------- статьи и новости ---------- */
function newsTime(x){const t=String(x.time||"");if(!t)return 0;if(t.length<=10)return Date.parse(t+"T12:00:00Z");return Date.parse(t)||0}
function articles(){const out=[];const now=D.generated?Date.parse(D.generated):Date.now();
  (D.articles||[]).forEach((x,i)=>out.push({k:"a"+i,...x,kind:x.kind||"column",body:x.body||[]}));
  (ST||[]).forEach((x,i)=>out.push({k:"s"+(x.id||i),...x,kind:"story",body:x.body||[],image:x.cover&&x.cover.url,image_src:x.cover&&x.cover.credit,image_link:x.cover&&x.cover.link}));
  (D.news||[]).forEach((x,i)=>out.push({k:"n"+i,kind:"news",title:x.title,dek:x.summary||x.dek,body:x.body||[x.summary],teams:x.teams||[],players:x.players||[],source:x.source,url:x.url,time:x.time,image:x.image,image_src:x.image_source}));
  return out.filter(x=>x.kind!=="news"||!x.time||now-newsTime(x)<=3*864e5).sort((a,b)=>newsTime(b)-newsTime(a))}
function coverHtml(x,cls="cover",withCap=true){const ts=(x.teams||[]).filter(t=>COLORS[t]).slice(0,2);
  if(x.image)return `<div class="${cls}"><img src="${esc(x.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add('art');this.remove()">${withCap?`<span class="cap">Фото: ${esc(x.image_src||x.source||"источник")}</span>`:""}</div>`;
  const [c1,c2]=ts.length===2?pair(ts[0],ts[1]):ts.length?[tdeep(ts[0]),shade(tdeep(ts[0]),.6)]:["#20242B","#30353E"];
  return `<div class="${cls} art" style="--c1:${c1};--c2:${c2}">${ts.map(t=>`<span class="lgw">${logo(t,"72%")}</span>`).join("")}</div>`}
function metaHtml(x){return `<span class="meta">${x.kind==="column"?'<span class="k">Колонка Claude</span>':x.kind==="story"?'<span class="k st">История</span>':""}${(x.teams||[]).slice(0,2).map(t=>logo(t,24)).join("")}${x.source&&x.kind!=="column"&&x.kind!=="story"?`<span>${esc(x.source)}</span>`:""}${x.time?`<span>${String(x.time).length>10?esc(kdt(x.time)):esc(dShort(String(x.time).slice(0,10)))}</span>`:""}</span>`}

/* ---------- обновление данных ---------- */
function freshness(){if(!D||!D.generated)return {txt:"",old:false};const g=new Date(D.generated);const h=(Date.now()-g)/36e5;
  const today=new Date().toLocaleDateString("ru-RU",{timeZone:"Europe/Kirov"})===g.toLocaleDateString("ru-RU",{timeZone:"Europe/Kirov"});
  return {txt:`обновлено <b>${today?"в "+kt(D.generated):kdt(D.generated)}</b>`,old:h>30}}
