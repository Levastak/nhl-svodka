"""Карточки для Telegram-канала: HTML → PNG через Playwright (Chromium).

Формат — вертикальный 4:5 (1080×1350, рендер ×2 для чёткости): в ленте Telegram такие картинки крупнее горизонтальных.
Виды: scores (итоги ночи), stars (три звезды — коллекционные карточки как на сайте), number (цифра дня),
match (матч ночи), column (колонка / рубрика), player (одна звезда), changes (вечерние изменения).
Логотипы — SVG НХЛ (тёмная версия), фото игроков — assets.nhle.com (вырезанные портреты);
не загрузилось — логотип или кружок с аббревиатурой в цвете клуба. Шрифты лежат рядом (Golos Text, Fira Sans Extra Condensed, OFL).
"""
import base64
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SITE = os.path.join(ROOT, "site")
W, H, SCALE = 1080, 1350, 2

RU = {"ANA": "Анахайм", "BOS": "Бостон", "BUF": "Баффало", "CAR": "Каролина", "CBJ": "Коламбус", "CGY": "Калгари",
      "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Даллас", "DET": "Детройт", "EDM": "Эдмонтон", "FLA": "Флорида",
      "LAK": "Лос-Анджелес", "MIN": "Миннесота", "MTL": "Монреаль", "NJD": "Нью-Джерси", "NSH": "Нэшвилл",
      "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттава", "PHI": "Филадельфия", "PIT": "Питтсбург",
      "SEA": "Сиэтл", "SJS": "Сан-Хосе", "STL": "Сент-Луис", "TBL": "Тампа", "TOR": "Торонто", "UTA": "Юта",
      "VAN": "Ванкувер", "VGK": "Вегас", "WPG": "Виннипег", "WSH": "Вашингтон"}


def _colors():
    try:
        s = open(os.path.join(SITE, "core.js"), encoding="utf-8").read()
        m = re.search(r"const COLORS=(\{.*?\});", s)
        return json.loads(re.sub(r"([A-Z]{3}):", r'"\1":', m.group(1)))
    except Exception:
        return {}


COLORS = _colors()


def e(s):
    return html.escape(str(s if s is not None else ""))


def _lum(c):
    c = c.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def main_c(abbr):
    return (COLORS.get(abbr) or ["#30353E"])[0]


def bright(abbr):
    """Цвет клуба, заметный на тёмном фоне: основной, если он не слишком тёмный, иначе второй, иначе серый."""
    for c in COLORS.get(abbr) or []:
        if _lum(c) > 0.12 and c.upper() != "#FFFFFF":
            return c
    return "#8C929C"


def dark(hexc, k=0.45):
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r * k):02x}{int(g * k):02x}{int(b * k):02x}"


def logo(abbr, logos, size):
    u = (logos.get(abbr) or f"https://assets.nhle.com/logos/nhl/svg/{abbr}_light.svg").replace("_light.svg", "_dark.svg")
    return (f'<span class="lg" style="width:{size}px;height:{size}px;--c:{main_c(abbr)}"><img src="{e(u)}" onerror="this.remove()">'
            f'<i style="font-size:{max(12, int(size * .28))}px">{e(abbr)}</i></span>')


def mug(path):
    return f"https://assets.nhle.com/mugs/nhl/{path}.png" if path else ""


def head(path, abbr, size):
    img = f'<img src="{e(mug(path))}" onerror="this.remove()">' if path else ""
    return f'<span class="hs" style="width:{size}px;height:{size}px;--c:{main_c(abbr)}">{img}</span>'


CSS = """
@font-face{font-family:G;src:url(fonts/GolosText.ttf);font-weight:100 900}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-SemiBold.ttf);font-weight:600}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-Bold.ttf);font-weight:700}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-ExtraBold.ttf);font-weight:800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:G,sans-serif;color:#EDEFF2;background:#0D0F12;position:relative}
.bg{position:absolute;inset:0;background:radial-gradient(1100px 900px at 0% 0%,var(--c1,#1a1f27),transparent 62%),radial-gradient(1100px 900px at 100% 100%,var(--c2,#1a1f27),transparent 62%),#0D0F12}
.top{position:absolute;left:64px;right:64px;top:60px;display:flex;align-items:baseline;gap:16px}
.kick{font-family:F;font-weight:800;font-size:50px;letter-spacing:.05em;text-transform:uppercase;line-height:1}
.kick b{color:#FF4A55}
.date{margin-left:auto;font-family:F;font-weight:600;font-size:32px;color:#A9AFB8;letter-spacing:.04em;text-transform:uppercase}
.brand{position:absolute;left:64px;bottom:50px;display:flex;align-items:center;gap:14px;font-family:F;font-weight:800;font-size:38px;letter-spacing:.03em}
.brand img{width:56px;height:56px}
.brand em{font-style:normal}.brand span{color:#FF4A55}
.tag{position:absolute;right:64px;bottom:60px;font-size:28px;color:#8C929C}
.lg{position:relative;display:inline-flex;align-items:center;justify-content:center;flex:none}
.lg img{position:relative;z-index:2;width:100%;height:100%;object-fit:contain}
.lg i{position:absolute;inset:6%;border-radius:50%;background:var(--c);display:flex;align-items:center;justify-content:center;font-style:normal;font-family:F;font-weight:800;color:#fff;z-index:1}
.lg img+i{display:none}
.hs{position:relative;display:inline-block;border-radius:50%;overflow:hidden;background:var(--c);flex:none;border:5px solid rgba(255,255,255,.18)}
.hs img{width:100%;height:100%;object-fit:cover;object-position:50% 0}
.body{position:absolute;left:64px;right:64px;top:150px;bottom:146px}
/* итоги ночи */
.list{display:flex;flex-direction:column;gap:10px;height:100%;justify-content:center}
.row{flex:1;display:grid;grid-template-columns:var(--l) 1fr auto 1fr var(--l);align-items:center;gap:16px;background:rgba(255,255,255,.05);border-radius:18px;padding:0 20px;max-height:124px}
.row .n{font-family:F;font-weight:600;font-size:var(--fs);color:#9AA0A9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .n.r{text-align:right}
.row .n.w{color:#fff;font-weight:800}
.row .sc{font-family:F;font-weight:800;font-size:calc(var(--fs)*1.25);min-width:130px;text-align:center;white-space:nowrap}
.row .sc small{font-size:calc(var(--fs)*.62);color:#FF4A55;margin-left:6px}
/* три звезды */
.stars{display:grid;grid-template-columns:repeat(var(--n,3),1fr);gap:22px;height:100%}
.sc3{border-radius:28px;overflow:hidden;background:#16191E;display:flex;flex-direction:column;border:1px solid rgba(255,255,255,.08)}
.sc3 .t3{position:relative;height:560px;background:var(--c);overflow:hidden;display:flex;align-items:flex-end;justify-content:center;flex:none}
.sc3 .t3::before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 70% 25%,rgba(255,255,255,.25),transparent 60%)}
.sc3 .wm3{position:absolute;right:-50px;top:-40px;opacity:.2}
.sc3 .pic{position:relative;z-index:1;width:100%;height:470px;display:flex;align-items:flex-end;justify-content:center}
.sc3 .pic img{height:100%;width:auto;max-width:none;object-fit:contain;object-position:50% 100%}
.sc3 .pic .lg{margin-bottom:70px}
.sc3 .rk{position:absolute;left:24px;top:16px;z-index:2;font-family:F;font-weight:800;font-size:104px;line-height:1;color:#fff;text-shadow:0 3px 14px rgba(0,0,0,.35)}
.sc3 .rk i{font-style:normal;font-size:46px;color:#FFD66B;margin-left:4px;vertical-align:top}
.sc3 .bd{flex:1;padding:28px 26px 30px;display:flex;flex-direction:column;gap:16px}
.sc3 .nm{font-family:F;font-weight:800;font-size:50px;line-height:1}
.sc3 .nm small{display:block;font-weight:600;font-size:32px;color:#C3C7CE;margin-bottom:4px}
.sc3 .tm{display:flex;align-items:center;gap:12px;font-size:28px;color:#A9AFB8}
.sc3 .st{margin-top:auto;font-family:F;font-weight:800;font-size:48px;line-height:1.02;color:#FF4A55}
.sc3 .st small{display:block;font-family:G;font-weight:500;font-size:24px;color:#A9AFB8;margin-top:10px;line-height:1.3}
/* цифра дня */
.num{display:flex;flex-direction:column;height:100%;justify-content:center;gap:24px}
.num .big{font-family:F;font-weight:800;line-height:.82;color:#FF4A55;white-space:nowrap}
.num .big small{font-size:120px;color:#EDEFF2;margin-left:10px}
.num .sub{font-size:40px;color:#A9AFB8;line-height:1.3}
.num h2{font-family:F;font-weight:800;font-size:88px;line-height:1.02;text-wrap:balance;margin-top:40px}
.num .who{display:flex;align-items:center;gap:24px;font-size:40px;color:#C3C7CE;margin-top:16px}
.num .who small{display:block;color:#8C929C;font-size:30px}
/* матч */
.mt{display:flex;flex-direction:column;height:100%;justify-content:space-between}
.teams{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:30px}
.side{display:flex;flex-direction:column;align-items:center;gap:20px;text-align:center}
.side b{font-family:F;font-weight:800;font-size:76px;line-height:1}
.side small{font-size:32px;color:#A9AFB8}
.when{text-align:center}
.when .t{font-family:F;font-weight:800;font-size:170px;line-height:1}
.when .k{font-size:36px;color:#A9AFB8}
.bar .lbl{display:flex;justify-content:space-between;align-items:baseline;font-family:F;font-weight:800;font-size:72px;margin-bottom:16px}
.bar .lbl span{color:#A9AFB8;font-family:G;font-weight:500;font-size:30px}
.bar .tr{display:flex;height:28px;border-radius:14px;overflow:hidden;background:#2A2E35}
.badges{display:flex;gap:12px;justify-content:center}
.badge{font-family:F;font-weight:800;font-size:32px;letter-spacing:.05em;text-transform:uppercase;padding:8px 22px;border-radius:999px;background:#1E8E5A;color:#fff}
/* колонка */
.col{display:flex;flex-direction:column;height:100%;justify-content:center;gap:64px}
.col h1{font-family:F;font-weight:800;line-height:1.02;text-wrap:balance}
.col .lgs{display:flex;gap:32px}
/* изменения */
.chg{display:flex;flex-direction:column;gap:22px;height:100%;justify-content:center}
.chg .it{display:flex;flex-direction:column;gap:14px;background:rgba(255,255,255,.06);border-radius:22px;padding:28px 30px}
.chg .it .tt{display:flex;align-items:center;gap:16px;font-family:F;font-weight:800;font-size:46px}
.chg .it span{color:#FF4A55;font-family:F;font-weight:800;font-size:40px}
"""


def page(body, kicker, date="", c1="#1a1f27", c2="#1a1f27"):
    mk = "data:image/svg+xml;base64," + base64.b64encode(open(os.path.join(SITE, "logo-mark.svg"), "rb").read()).decode()
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body style="--c1:{c1};--c2:{c2}"><div class="bg"></div>'
            f'<div class="top"><span class="kick">{kicker}</span><span class="date">{e(date)}</span></div>'
            f'<div class="body">{body}</div>'
            f'<div class="brand"><img src="{mk}"><em>NHL-STATS<span>.RU</span></em></div><div class="tag">@nhlstatsru</div></body></html>')


def card_scores(spec, logos):
    gs = spec["games"]
    n = len(gs)
    fs = 54 if n <= 6 else 46 if n <= 9 else 40 if n <= 12 else 34
    lsz = 76 if n <= 6 else 64 if n <= 9 else 56 if n <= 12 else 46
    rows = []
    for g in gs:
        aw = g["as"] > g["hs"]
        end = {"OT": "ОТ", "SO": "Б"}.get(g.get("end"), "")
        rows.append(f'<div class="row">{logo(g["away"], logos, lsz)}<span class="n {"w" if aw else ""}">{e(RU.get(g["away"]))}</span>'
                    f'<span class="sc">{g["as"]}:{g["hs"]}{f"<small>{end}</small>" if end else ""}</span>'
                    f'<span class="n r {"" if aw else "w"}">{e(RU.get(g["home"]))}</span>{logo(g["home"], logos, lsz)}</div>')
    return page(f'<div class="list" style="--fs:{fs}px;--l:{lsz}px">{"".join(rows)}</div>', "Итоги <b>ночи</b>", spec.get("date", ""))


def card_stars(spec, logos, kicker="Три <b>звезды</b>"):
    cards = []
    stars = spec["stars"][:3]
    for i, s in enumerate(stars):
        t = s.get("team")
        if s.get("head_path"):
            pic = (f'<img src="{e(mug(s["head_path"]))}" onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
                   f'<span style="display:none">{logo(t, logos, 240)}</span>')
        else:
            pic = logo(t, logos, 240)
        nm = s.get("name") or ""
        first, _, last = nm.partition(" ")
        rank = f'<span class="rk">{s.get("rank", i + 1)}<i>★</i></span>' if len(stars) > 1 or s.get("rank") else ""
        note = f"<small>{e(s['note'])}</small>" if s.get("note") else ""
        cards.append(f'<div class="sc3"><div class="t3" style="--c:{main_c(t)}"><span class="wm3">{logo(t, logos, 320)}</span>'
                     f'{rank}<div class="pic">{pic}</div></div>'
                     f'<div class="bd"><div class="nm">{f"<small>{e(first)}</small>{e(last)}" if last else e(first)}</div>'
                     f'<div class="tm">{logo(t, logos, 46)}<span>{e(RU.get(t, t))}</span></div>'
                     f'<div class="st">{e(s.get("stat") or "")}{note}</div></div></div>')
    return page(f'<div class="stars" style="--n:{len(stars)}">{"".join(cards)}</div>', kicker, spec.get("date", ""))


def card_number(spec, logos):
    t = (spec.get("teams") or [None])[0]
    big = str(spec["big"])
    fs = 330 if len(big) <= 4 else 270 if len(big) <= 5 else 220
    who = ""
    if spec.get("player"):
        who = f'<div class="who">{head(spec.get("head_path"), t, 140)}<span>{e(spec["player"])}<small>{e(RU.get(t, ""))}</small></span></div>'
    elif t:
        who = f'<div class="who">{logo(t, logos, 140)}<span>«{e(RU.get(t, t))}»</span></div>'
    return page(f'<div class="num"><div class="big" style="font-size:{fs}px">{e(big)}<small>{e(spec.get("unit") or "")}</small></div>'
                f'<div class="sub">{e(spec.get("sub") or "")}</div><h2>{e(spec.get("head") or "")}</h2>{who}</div>',
                "Цифра <b>дня</b>", spec.get("date", ""), c1=dark(main_c(t), .6) if t else "#1a1f27")


def card_match(spec, logos):
    a, h = spec["away"], spec["home"]
    ca, ch = bright(a), bright(h)
    pa, ph = spec.get("p_away"), spec.get("p_home")
    bar = ""
    if pa is not None and ph is not None:
        bar = (f'<div class="bar"><div class="lbl"><b>{round(pa * 100)}%</b><span>шансы по оценке модели</span><b>{round(ph * 100)}%</b></div>'
               f'<div class="tr"><i style="width:{pa * 100}%;background:{ca}"></i><i style="flex:1;background:{ch}"></i></div></div>')
    badges = '<div class="badges"><span class="badge">Уверенный фаворит</span></div>' if spec.get("sure") else ""
    body = (f'<div class="mt"><div class="teams"><div class="side">{logo(a, logos, 350)}<b>{e(RU.get(a))}</b><small>{e(spec.get("rec_a") or "в гостях")}</small></div>'
            f'<div class="side">{logo(h, logos, 350)}<b>{e(RU.get(h))}</b><small>{e(spec.get("rec_h") or "дома")}</small></div></div>'
            f'<div class="when"><div class="t">{e(spec["time"])}</div><div class="k">по Москве · {e(spec.get("date", ""))}</div></div>'
            f'{badges}{bar}</div>')
    kick = "Матч <b>дня</b>" if spec.get("motd") else "Матч <b>ночи</b>"
    return page(body, kick, "", c1=dark(main_c(a)), c2=dark(main_c(h)))


def card_column(spec, logos):
    ts = spec.get("teams") or []
    c1 = dark(main_c(ts[0])) if ts else "#1a1f27"
    c2 = dark(main_c(ts[1])) if len(ts) > 1 else c1
    title = spec["title"]
    fs = 112 if len(title) <= 50 else 96 if len(title) <= 80 else 80
    lgs = "".join(logo(t, logos, 210) for t in ts[:2])
    return page(f'<div class="col"><h1 style="font-size:{fs}px">{e(title)}</h1><div class="lgs">{lgs}</div></div>',
                e(spec.get("kicker", "Колонка")), spec.get("date", ""), c1=c1, c2=c2)


def card_player(spec, logos):
    return card_stars(dict(stars=[dict(spec)], date=spec.get("date", "")), logos, kicker=e(spec.get("kicker", "Звезда ночи")))


def card_changes(spec, logos):
    items = "".join(f'<div class="it"><div class="tt">{logo(x["away"], logos, 72)}{logo(x["home"], logos, 72)}{e(RU.get(x["away"]))} — {e(RU.get(x["home"]))}</div><span>{e(x["new"])}</span></div>'
                    for x in spec["items"][:5])
    return page(f'<div class="chg">{items}</div>', "Вечером <b>передумали</b>", spec.get("date", ""))


KINDS = {"scores": card_scores, "stars": card_stars, "number": card_number, "match": card_match,
         "column": card_column, "player": card_player, "changes": card_changes}


def render(specs, outdir, logos=None):
    """specs: [dict(kind=…, …)] → список путей PNG (None, где не вышло)."""
    from playwright.sync_api import sync_playwright
    logos = logos or {}
    os.makedirs(outdir, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        for i, s in enumerate(specs):
            try:
                doc = KINDS[s["kind"]](s, logos)
                fn = os.path.join(HERE, f"_card{i}.html")
                with open(fn, "w", encoding="utf-8") as fh:
                    fh.write(doc)
                pg.goto("file://" + fn, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(400)
                png = os.path.join(outdir, f"card{i}_{s['kind']}.png")
                pg.screenshot(path=png)
                os.remove(fn)
                out.append(png)
            except Exception as ex:
                print("card fail", s.get("kind"), repr(ex)[:200])
                out.append(None)
        b.close()
    return out
