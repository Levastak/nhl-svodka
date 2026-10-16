"""Карточки для Telegram-канала: HTML → PNG 1280×720 через Playwright (Chromium).

Виды: scores (итоги ночи), number (цифра дня), match (матч вечера), column (колонка / рубрика), changes (вечерние изменения).
Логотипы — SVG НХЛ (тёмная версия), фото игроков — assets.nhle.com; не загрузилось — кружок с аббревиатурой в цвете клуба.
Шрифты лежат рядом (Golos Text, Fira Sans Extra Condensed, OFL).
"""
import html
import json
import os
import re
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SITE = os.path.join(ROOT, "site")
W, H = 1280, 720

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


def logo_url(abbr, logos):
    u = logos.get(abbr) or f"https://assets.nhle.com/logos/nhl/svg/{abbr}_light.svg"
    return u.replace("_light.svg", "_dark.svg")


def logo(abbr, logos, size):
    c = (COLORS.get(abbr) or ["#30353E"])[0]
    return (f'<span class="lg" style="width:{size}px;height:{size}px;--c:{c}"><img src="{e(logo_url(abbr, logos))}" '
            f'onerror="this.remove()"><i style="font-size:{max(12, int(size * .28))}px">{e(abbr)}</i></span>')


def head(path, abbr, size):
    c = (COLORS.get(abbr) or ["#30353E"])[0]
    img = f'<img src="https://assets.nhle.com/mugs/nhl/{e(path)}.png" onerror="this.remove()">' if path else ""
    return f'<span class="hs" style="width:{size}px;height:{size}px;--c:{c}">{img}</span>'


CSS = """
@font-face{font-family:G;src:url(fonts/GolosText.ttf);font-weight:100 900}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-SemiBold.ttf);font-weight:600}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-Bold.ttf);font-weight:700}
@font-face{font-family:F;src:url(fonts/FiraSansExtraCondensed-ExtraBold.ttf);font-weight:800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1280px;height:720px;overflow:hidden}
body{font-family:G,sans-serif;color:#EDEFF2;background:#0D0F12;position:relative}
.bg{position:absolute;inset:0;background:radial-gradient(1200px 700px at 0% 0%,var(--c1,#1a1f27),transparent 60%),radial-gradient(1200px 700px at 100% 100%,var(--c2,#1a1f27),transparent 60%),#0D0F12}
.top{position:absolute;left:56px;right:56px;top:40px;display:flex;align-items:center;gap:16px}
.kick{font-family:F;font-weight:800;font-size:30px;letter-spacing:.06em;text-transform:uppercase}
.kick b{color:#FF4A55}
.date{margin-left:auto;font-family:F;font-weight:600;font-size:28px;color:#A9AFB8;letter-spacing:.04em;text-transform:uppercase}
.brand{position:absolute;left:56px;bottom:30px;display:flex;align-items:center;gap:12px;font-family:F;font-weight:800;font-size:26px;letter-spacing:.03em}
.brand img{width:40px;height:40px}
.brand em{font-style:normal}.brand span{color:#FF4A55}
.tag{position:absolute;right:56px;bottom:34px;font-size:20px;color:#8C929C}
.lg{position:relative;display:inline-flex;align-items:center;justify-content:center;flex:none}
.lg img{position:relative;z-index:2;width:100%;height:100%;object-fit:contain}
.lg i{position:absolute;inset:6%;border-radius:50%;background:var(--c);display:flex;align-items:center;justify-content:center;font-style:normal;font-family:F;font-weight:800;color:#fff;z-index:1}
.lg img+i{display:none}
.hs{position:relative;display:inline-block;border-radius:50%;overflow:hidden;background:var(--c);flex:none;border:4px solid rgba(255,255,255,.15)}
.hs img{width:100%;height:100%;object-fit:cover}
/* scores */
.grid{position:absolute;left:56px;right:56px;top:110px;bottom:96px;display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:1fr;column-gap:40px;row-gap:6px;grid-auto-flow:column}
.row{display:grid;grid-template-columns:44px 1fr auto 1fr 44px;align-items:center;gap:12px;background:rgba(255,255,255,.04);border-radius:12px;padding:0 14px}
.row .n{font-family:F;font-weight:600;font-size:26px;color:#A9AFB8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .n.r{text-align:right}
.row .n.w{color:#fff;font-weight:800}
.row .sc{font-family:F;font-weight:800;font-size:32px;min-width:96px;text-align:center}
.row .sc small{font-size:18px;color:#FF4A55;margin-left:4px}
/* number */
.num{position:absolute;left:56px;right:56px;top:120px;bottom:100px;display:grid;grid-template-columns:auto 1fr;gap:56px;align-items:center}
.num .big{font-family:F;font-weight:800;font-size:220px;line-height:.85;color:#FF4A55;white-space:nowrap}
.num .big small{font-size:80px;color:#EDEFF2;margin-left:8px}
.num .sub{font-size:28px;color:#A9AFB8;margin-top:18px;max-width:520px}
.num h2{font-family:F;font-weight:800;font-size:58px;line-height:1.02}
.num .who{display:flex;align-items:center;gap:18px;margin-top:22px;font-size:28px;color:#C3C7CE}
/* match */
.mt{position:absolute;left:56px;right:56px;top:96px;bottom:96px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center}
.side{display:flex;flex-direction:column;align-items:center;gap:14px}
.side b{font-family:F;font-weight:800;font-size:50px}
.side small{font-size:22px;color:#A9AFB8}
.mid{text-align:center;display:flex;flex-direction:column;gap:6px;align-items:center}
.mid .t{font-family:F;font-weight:800;font-size:76px;line-height:1}
.mid .k{font-size:22px;color:#A9AFB8}
.mid .vs{font-family:F;font-weight:700;font-size:30px;color:#FF4A55;letter-spacing:.1em}
.bar{position:absolute;left:56px;right:56px;bottom:112px}
.bar .lbl{display:flex;justify-content:space-between;font-family:F;font-weight:700;font-size:28px;margin-bottom:8px}
.bar .lbl span{color:#A9AFB8;font-weight:600;font-size:22px}
.bar .tr{display:flex;height:16px;border-radius:8px;overflow:hidden;background:#2A2E35}
.badges{position:absolute;top:96px;left:56px;display:flex;gap:10px}
.badge{font-family:F;font-weight:800;font-size:22px;letter-spacing:.05em;text-transform:uppercase;padding:6px 14px;border-radius:999px;background:#FF4A55;color:#fff}
.badge.g{background:#1E8E5A}
/* column */
.col{position:absolute;left:56px;right:330px;top:130px;bottom:110px;display:flex;flex-direction:column;justify-content:center;gap:24px}
.col h1{font-family:F;font-weight:800;font-size:76px;line-height:1.02}
.col p{font-size:28px;color:#C3C7CE;line-height:1.35}
.wm{position:absolute;right:40px;top:150px;display:flex;flex-direction:column;gap:16px;opacity:.95}
/* changes */
.chg{position:absolute;left:56px;right:56px;top:130px;bottom:110px;display:flex;flex-direction:column;gap:18px;justify-content:center}
.chg .it{display:flex;align-items:center;gap:20px;background:rgba(255,255,255,.05);border-radius:16px;padding:18px 22px;font-size:30px}
.chg .it b{font-family:F;font-weight:800;font-size:36px}
.chg .it span{margin-left:auto;color:#FF4A55;font-family:F;font-weight:800}
"""


def page(body, c1="#1a1f27", c2="#1a1f27"):
    mark = open(os.path.join(SITE, "logo-mark.svg"), encoding="utf-8").read()
    import base64
    mk = "data:image/svg+xml;base64," + base64.b64encode(mark.encode()).decode()
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body style="--c1:{c1};--c2:{c2}"><div class="bg"></div>{body}'
            f'<div class="brand"><img src="{mk}"><em>NHL-STATS<span>.RU</span></em></div><div class="tag">@nhlstatsru</div></body></html>')


def dark(hexc, k=0.45):
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r * k):02x}{int(g * k):02x}{int(b * k):02x}"


def card_scores(spec, logos):
    rows = []
    for g in spec["games"]:
        aw = g["as"] > g["hs"]
        end = {"OT": "ОТ", "SO": "Б"}.get(g.get("end"), "")
        rows.append(f'<div class="row">{logo(g["away"], logos, 44)}<span class="n {"w" if aw else ""}">{e(RU.get(g["away"]))}</span>'
                    f'<span class="sc">{g["as"]}:{g["hs"]}{f"<small>{end}</small>" if end else ""}</span>'
                    f'<span class="n r {"" if aw else "w"}">{e(RU.get(g["home"]))}</span>{logo(g["home"], logos, 44)}</div>')
    n = len(rows)
    per = max(4, (n + 1) // 2)
    style = f'grid-template-rows:repeat({per},1fr)'
    return page(f'<div class="top"><span class="kick">Итоги <b>ночи</b></span><span class="date">{e(spec["date"])}</span></div>'
                f'<div class="grid" style="{style}">{"".join(rows)}</div>')


def card_number(spec, logos):
    t = (spec.get("teams") or [None])[0]
    c = (COLORS.get(t) or ["#30353E"])[0]
    who = ""
    if spec.get("player"):
        who = f'<div class="who">{head(spec.get("head_path"), t, 96)}<span>{e(spec["player"])}<br><small style="color:#8C929C">{e(RU.get(t, ""))}</small></span></div>'
    elif t:
        who = f'<div class="who">{logo(t, logos, 96)}<span>«{e(RU.get(t, t))}»</span></div>'
    return page(f'<div class="top"><span class="kick">Цифра <b>дня</b></span><span class="date">{e(spec.get("date", ""))}</span></div>'
                f'<div class="num"><div><div class="big">{e(spec["big"])}<small>{e(spec.get("unit") or "")}</small></div><div class="sub">{e(spec.get("sub") or "")}</div></div>'
                f'<div><h2>{e(spec.get("head") or "")}</h2>{who}</div></div>', c1=dark(c, .55))


def card_match(spec, logos):
    a, h = spec["away"], spec["home"]
    ca, ch = (COLORS.get(a) or ["#30353E"])[0], (COLORS.get(h) or ["#30353E"])[0]
    pa, ph = spec.get("p_away"), spec.get("p_home")
    badges = "".join([f'<span class="badge">Матч дня</span>' if spec.get("motd") else "",
                      f'<span class="badge g">Уверенный фаворит</span>' if spec.get("sure") else ""])
    bar = ""
    if pa is not None and ph is not None:
        bar = (f'<div class="bar"><div class="lbl"><b>{round(pa * 100)}%</b><span>оценка модели · {e(spec.get("total") or "")}</span><b>{round(ph * 100)}%</b></div>'
               f'<div class="tr"><i style="width:{pa * 100}%;background:{ca}"></i><i style="flex:1;background:{ch}"></i></div></div>')
    return page(f'<div class="top"><span class="kick">Матч <b>вечера</b></span><span class="date">{e(spec.get("date", ""))}</span></div>'
                f'<div class="badges">{badges}</div>'
                f'<div class="mt"><div class="side">{logo(a, logos, 220)}<b>{e(RU.get(a))}</b><small>{e(spec.get("rec_a") or "в гостях")}</small></div>'
                f'<div class="mid"><span class="vs">VS</span><span class="t">{e(spec["time"])}</span><span class="k">по Кирову</span></div>'
                f'<div class="side">{logo(h, logos, 220)}<b>{e(RU.get(h))}</b><small>{e(spec.get("rec_h") or "дома")}</small></div></div>{bar}',
                c1=dark(ca), c2=dark(ch))


def card_column(spec, logos):
    ts = spec.get("teams") or []
    c1 = dark((COLORS.get(ts[0]) or ["#30353E"])[0]) if ts else "#1a1f27"
    c2 = dark((COLORS.get(ts[1]) or ["#30353E"])[0]) if len(ts) > 1 else c1
    title = spec["title"]
    fs = 76 if len(title) <= 60 else 64 if len(title) <= 90 else 54
    wm = "".join(logo(t, logos, 220 if len(ts) == 1 else 190) for t in ts[:2])
    return page(f'<div class="top"><span class="kick">{e(spec.get("kicker", "Колонка"))}</span><span class="date">{e(spec.get("date", ""))}</span></div>'
                f'<div class="col"><h1 style="font-size:{fs}px">{e(title)}</h1></div><div class="wm">{wm}</div>', c1=c1, c2=c2)


def card_changes(spec, logos):
    items = "".join(f'<div class="it">{logo(x["away"], logos, 56)}{logo(x["home"], logos, 56)}<b>{e(RU.get(x["away"]))} — {e(RU.get(x["home"]))}</b><span>{e(x["new"])}</span></div>'
                    for x in spec["items"][:5])
    return page(f'<div class="top"><span class="kick">Вечером <b>передумали</b></span><span class="date">{e(spec.get("date", ""))}</span></div><div class="chg">{items}</div>')


KINDS = {"scores": card_scores, "number": card_number, "match": card_match, "column": card_column, "changes": card_changes}


def render(specs, outdir, logos=None):
    """specs: [dict(kind=…, …)] → список путей PNG (None, где не вышло)."""
    from playwright.sync_api import sync_playwright
    logos = logos or {}
    os.makedirs(outdir, exist_ok=True)
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, s in enumerate(specs):
            try:
                doc = KINDS[s["kind"]](s, logos)
                fn = os.path.join(HERE, f"_card{i}.html")
                with open(fn, "w", encoding="utf-8") as fh:
                    fh.write(doc)
                pg.goto("file://" + fn, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(300)
                png = os.path.join(outdir, f"card{i}_{s['kind']}.png")
                pg.screenshot(path=png)
                os.remove(fn)
                out.append(png)
            except Exception as ex:
                print("card fail", s.get("kind"), repr(ex)[:200])
                out.append(None)
        b.close()
    return out
