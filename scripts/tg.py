"""Telegram-канал NHL-STATS.RU (@nhlstatsru): посты с картинками из готовых текстов сайта. Без Claude, запускается в GitHub (tg.yml).

Режимы:
  auto     — после каждого прогона «Сводка НХЛ»: постит то, что появилось и ещё не публиковалось
             (утро, матчи дня, колонка, история, вечерние изменения);
  test     — опубликовать утренний набор прямо сейчас и отметить его опубликованным;
  preview  — только нарисовать карточки текущего дня в tg/preview/ (ничего не постит);
  discover — найти канал, куда бота добавили админом (getUpdates), и записать tg/config.json.
Подписи «по-человечески» пишет утренняя задача Claude в data.tg (morning, games{id}, column); нет — шаблоны ниже.
Картинки — scripts/cards/render.py (Playwright, ставится сам при первом посте).
Токен — только в секрете TELEGRAM_BOT_TOKEN. Отметки — tg/state.json; итог запуска — tg/last.json.
"""
import datetime as dt
import html
import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
TG = os.path.join(ROOT, "tg")
URL = "https://levastak.github.io/nhl-svodka/"
KIROV = ZoneInfo("Europe/Kirov")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
LOG = {"t": None, "mode": None, "ok": [], "fail": []}
FOOT = f'\n\n<a href="{URL}">NHL-STATS.RU</a> — статистика, прогнозы и аналитика НХЛ по-русски'

RU = {"ANA": "Анахайм", "BOS": "Бостон", "BUF": "Баффало", "CAR": "Каролина", "CBJ": "Коламбус", "CGY": "Калгари",
      "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Даллас", "DET": "Детройт", "EDM": "Эдмонтон", "FLA": "Флорида",
      "LAK": "Лос-Анджелес", "MIN": "Миннесота", "MTL": "Монреаль", "NJD": "Нью-Джерси", "NSH": "Нэшвилл",
      "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттава", "PHI": "Филадельфия", "PIT": "Питтсбург",
      "SEA": "Сиэтл", "SJS": "Сан-Хосе", "STL": "Сент-Луис", "TBL": "Тампа", "TOR": "Торонто", "UTA": "Юта",
      "VAN": "Ванкувер", "VGK": "Вегас", "WPG": "Виннипег", "WSH": "Вашингтон"}
MON = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return d


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def e(s):
    return html.escape(str(s or ""), quote=False)


def T(a):
    return f"«{RU.get(a, a)}»"


def ru_date(d):
    x = dt.date.fromisoformat(d)
    return f"{x.day} {MON[x.month - 1]}"


def kirov_time(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KIROV).strftime("%H:%M")


def pct(p):
    return f"{round(p * 100)}%"


def num(x):
    try:
        x = float(x)
        return (f"{int(x)}" if x == int(x) else f"{x:g}").replace(".", ",")
    except Exception:
        return str(x)


def plural(n, a, b, c):
    n = abs(n) % 100
    return a if n % 10 == 1 and n != 11 else b if 2 <= n % 10 <= 4 and not 12 <= n <= 14 else c


class Names:
    def __init__(self):
        self.d = load(f"{SITE}/names_ru.json", {}) or {}

    def full(self, n):
        return self.d.get(n, n)

    def last(self, n):
        return self.full(n).split(" ", 1)[-1]


# ---------------------------------------------------------------- Bot API
def _call(method, fields, files=None):
    if not TOKEN:
        raise RuntimeError("нет TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    fields = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)) for k, v in fields.items() if v is not None}
    if files:
        bd = uuid.uuid4().hex
        body = b""
        for k, v in fields.items():
            body += f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, path in files.items():
            ct = mimetypes.guess_type(path)[0] or "image/png"
            body += (f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(path)}"\r\n'
                     f'Content-Type: {ct}\r\n\r\n').encode() + open(path, "rb").read() + b"\r\n"
        body += f"--{bd}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={bd}"})
    else:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode())
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:
        j = json.loads(ex.read().decode() or "{}")
    if not j.get("ok"):
        raise RuntimeError(f"{method}: {j.get('error_code')} {j.get('description')}")
    return j["result"]


def send(chat, text, images=None, photo_url=None):
    """Пост: альбом из картинок (подпись у первой), одна картинка, фото по адресу или текст. Возвращает id сообщений."""
    images = [p for p in images or [] if p]
    import re as _re
    vis = len(_re.sub("<[^>]+>", "", html.unescape(text)))
    if vis > 1024 and photo_url and not images:
        # длинный текст: фото крупным превью над текстом (лимит 4096 вместо 1024)
        r = _call("sendMessage", dict(chat_id=chat, text=text[:4096], parse_mode="HTML",
                                      link_preview_options={"url": photo_url, "prefer_large_media": True, "show_above_text": True}))
        return [r["message_id"]]
    try:
        if len(images) > 1:
            media = [dict(type="photo", media=f"attach://f{i}", **({"caption": text[:1024], "parse_mode": "HTML"} if i == 0 else {}))
                     for i, _ in enumerate(images[:10])]
            r = _call("sendMediaGroup", dict(chat_id=chat, media=media), {f"f{i}": p for i, p in enumerate(images[:10])})
            return [m["message_id"] for m in r]
        if images:
            r = _call("sendPhoto", dict(chat_id=chat, caption=text[:1024], parse_mode="HTML"), {"photo": images[0]})
            return [r["message_id"]]
        if photo_url:
            r = _call("sendPhoto", dict(chat_id=chat, photo=photo_url, caption=text[:1024], parse_mode="HTML"))
            return [r["message_id"]]
    except Exception as ex:
        LOG["fail"].append(f"картинка не ушла, шлю текстом: {ex}"[:200])
    r = _call("sendMessage", dict(chat_id=chat, text=text[:4096], parse_mode="HTML", link_preview_options={"is_disabled": True}))
    return [r["message_id"]]


def discover():
    cfg = load(f"{TG}/config.json", {}) or {}
    ups = _call("getUpdates", dict(allowed_updates=["my_chat_member", "channel_post"]))
    found = {}
    for u in ups:
        for k in ("my_chat_member", "channel_post"):
            c = (u.get(k) or {}).get("chat") or {}
            if c.get("type") == "channel":
                found[c["id"]] = dict(chat_id=c["id"], title=c.get("title"), username=c.get("username"))
    if len(found) == 1:
        cfg.update(list(found.values())[0])
        save(f"{TG}/config.json", cfg)
        LOG["ok"].append(f"канал найден: {cfg.get('title')}")
    elif not cfg.get("chat_id"):
        LOG["fail"].append("канал не найден — пропиши @адрес в tg/config.json")
    return cfg


# ---------------------------------------------------------------- картинки
_BROWSER = {"ok": None}


def ensure_browser():
    if _BROWSER["ok"] is None:
        try:
            import playwright  # noqa: F401
            _BROWSER["ok"] = True
        except Exception:
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright==1.48.0"], capture_output=True, text=True)
            _BROWSER["ok"] = r.returncode == 0
        if _BROWSER["ok"] and os.environ.get("GITHUB_ACTIONS"):
            r = subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], capture_output=True, text=True)
            _BROWSER["ok"] = r.returncode == 0
            if not _BROWSER["ok"]:
                LOG["fail"].append(f"chromium: {r.stderr[-200:]}")
    return _BROWSER["ok"]


def cards(specs, D):
    if not specs or not ensure_browser():
        return [None] * len(specs)
    sys.path.insert(0, os.path.join(ROOT, "scripts", "cards"))
    import render
    logos = {s["abbr"]: s.get("logo") for s in D.get("standings") or [] if s.get("logo")}
    try:
        return render.render(specs, os.path.join(ROOT, "tg", "_cards"), logos)
    except Exception as ex:
        LOG["fail"].append(f"карточки: {ex!r}"[:200])
        return [None] * len(specs)


# ---------------------------------------------------------------- посты
# Каждый пост — dict(key, due, expires, text, specs | photo, credit). Одна картинка на пост.
# Расписание (по Москве): итоги 09:15, три звезды 10:30, цифра дня 12:00, главная новость 13:30, колонка 15:00,
# история 16:30, матчи с 19:00 каждые 30 минут (больше 4 — двумя постами), «вечером передумали» — после 23:19.
MSK = ZoneInfo("Europe/Moscow")


def msk(day, hh, mm):
    return dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hh, mm), MSK)


def words(line):
    """«3+0» → «три гола», «1+2» → «гол и две передачи», «36 из 39» → «36 сейвов из 39 бросков»."""
    import re
    m = re.match(r"^\s*(\d+)\s*\+\s*(\d+)", str(line or ""))
    if m:
        g, a = int(m.group(1)), int(m.group(2))
        num_w = {1: "", 2: "два", 3: "три", 4: "четыре", 5: "пять"}
        num_f = {1: "", 2: "две", 3: "три", 4: "четыре", 5: "пять"}
        gs = ("гол" if g == 1 else f"{num_w.get(g, g)} {plural(g, 'гол', 'гола', 'голов')}") if g else ""
        as_ = ("передача" if a == 1 else f"{num_f.get(a, a)} {plural(a, 'передача', 'передачи', 'передач')}") if a else ""
        return " и ".join(x for x in (gs, as_) if x).strip() or str(line)
    m = re.match(r"^\s*(\d+)\s*из\s*(\d+)", str(line or ""))
    if m:
        s, sh = int(m.group(1)), int(m.group(2))
        return f"{s} {plural(s, 'сейв', 'сейва', 'сейвов')} из {sh} {plural(sh, 'броска', 'бросков', 'бросков')}"
    return str(line or "")


def tgv(D, k, day=None):
    t = D.get("tg") or {}
    if day and t.get("date") != day:
        return None
    return t.get(k)


def head_path(D, name):
    return (D.get("heads") or {}).get(name)


def build(D, A, M, E, S, N):
    out = []
    rd, ud = D.get("results_date"), D.get("upcoming_date")
    n = D.get("daily") or {}
    n = n if n.get("date") == rd else {}
    news = D.get("news") or []
    # 1. Итоги ночи — картинка со счетами
    gs = [g for g in A.get("games", []) if g.get("date") == rd and g.get("as") is not None]
    if rd and gs:
        human = tgv(D, "morning", rd)
        if not human:
            parts = []
            if n.get("best", {}).get("text"):
                parts.append(n["best"]["text"])
            if n.get("best_team", {}).get("text"):
                parts.append(n["best_team"]["text"])
            if n.get("worst_team", {}).get("text"):
                parts.append(n["worst_team"]["text"])
            human = " ".join(parts) or f"За ночь — {len(gs)} {plural(len(gs), 'матч', 'матча', 'матчей')}."
        txt = f"<b>Итоги ночи · {ru_date(rd)}</b>\n\n{e(human)}\n\n<a href=\"{URL}#results\">Протоколы всех матчей</a>"
        out.append(dict(key=f"am:{rd}", due=msk(dt.date.fromisoformat(rd).isoformat(), 9, 15) + dt.timedelta(days=1),
                        text=txt + FOOT, specs=[dict(kind="scores", date=ru_date(rd), games=gs)]))
    # 2. Три звезды — фото из матча первой звезды
    hs = (n.get("heroes") or [])[:3]
    if hs:
        st = {x.get("name"): x.get("text") for x in tgv(D, "stars", rd) or [] if isinstance(x, dict)}
        L = [f"<b>Три звезды ночи</b>", ""]
        for i, h in enumerate(hs):
            body = st.get(h["name"]) or f"{words(h.get('line')).capitalize()}. {h.get('text') or ''}".strip()
            L.append(f"<b>{i + 1}. {e(N.full(h['name']))}</b>, {e(T(h['team']))}\n{e(body)}")
            L.append("")
        photo, credit = None, None
        for x in news:
            if hs[0]["name"] in (x.get("players") or []) and x.get("image"):
                photo, credit = x["image"], x.get("image_source") or x.get("source")
                break
        if credit:
            L.append(f"<i>Фото: {e(credit)}</i>")
        L.append(f"<a href=\"{URL}#results\">Все герои и неудачники ночи</a>")
        spec = None if photo else dict(kind="player", kicker="Первая звезда", name=N.full(hs[0]["name"]), team=hs[0]["team"],
                                       head_path=head_path(D, hs[0]["name"]), line=words(hs[0].get("line")), date=ru_date(rd))
        out.append(dict(key=f"stars:{rd}", due=msk(rd, 10, 30) + dt.timedelta(days=1), text="\n".join(L) + FOOT,
                        photo=photo, specs=[spec] if spec else None))
    # 3. Цифра дня — отдельной карточкой
    num_d = n.get("number") or {}
    f = ((E or {}).get("findings") or [None])[0]
    src = num_d if num_d.get("big") else f
    if src and src.get("big") and rd:
        pl = (src.get("players") or [None])[0]
        body = tgv(D, "number", rd) or num_d.get("text") or (f or {}).get("line")
        head_t = num_d.get("head") or src.get("head")
        when = f"По матчам до {ru_date(src['date'])}." if src.get("date") and src.get("date") != rd else ""
        txt = f"<b>Цифра дня — {e(src['big'])}{e(src.get('unit') or '')}. {e(head_t)}</b>\n\n{e(body)}" + (f"\n\n<i>{when} Данные — трекинг НХЛ EDGE.</i>" if when else "\n\n<i>Данные — трекинг НХЛ EDGE.</i>")
        spec = dict(kind="number", big=src["big"], unit=src.get("unit"), sub=src.get("sub"), head=head_t, teams=src.get("teams"),
                    player=N.full(pl) if pl else None, head_path=head_path(D, pl) if pl else None,
                    date=f"по матчам до {ru_date(src['date'])}" if src.get("date") else "")
        out.append(dict(key=f"number:{rd}", due=msk(rd, 12, 0) + dt.timedelta(days=1), text=txt + FOOT, specs=[spec]))
    # 4. Главная новость — фото из статьи (не пересказ матча, если есть; иначе — выбор Claude)
    pick = tgv(D, "news", rd)
    item = None
    if isinstance(pick, dict) and pick.get("url"):
        item = next((x for x in news if x.get("url") == pick["url"]), None)
    if not item:
        item = next((x for x in news if "game-recap" not in str(x.get("url")) and x.get("image")), None)
    if item and item.get("image"):
        body = (pick or {}).get("text") if isinstance(pick, dict) and pick.get("url") == item.get("url") else None
        body = body or item.get("summary")
        txt = (f"<b>{e(item['title'])}</b>\n\n{e(body)}\n\n<i>Фото: {e(item.get('image_source') or item.get('source'))}</i>\n"
               f"<a href=\"{URL}#news\">Все новости дня</a>")
        out.append(dict(key=f"news:{item.get('url')}", due=msk(rd, 13, 30) + dt.timedelta(days=1), text=txt + FOOT, photo=item["image"]))
    # 5. Колонка / «Под микроскопом» / «Итоги недели»
    col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), None)
    if col and col.get("time"):
        kick = col.get("kicker") if col.get("kicker") and col.get("kicker") != "Колонка Claude" else "Колонка"
        body = tgv(D, "column", rd) or col.get("dek")
        txt = f"<b>{e(kick)}. {e(col.get('title'))}</b>\n\n{e(body)}\n\n<a href=\"{URL}#a=col\">Читать полностью</a>"
        cday = dt.datetime.fromisoformat(str(col["time"]).replace("Z", "+00:00")).astimezone(MSK).date().isoformat()
        out.append(dict(key=f"col:{col.get('title')}", due=msk(cday, 15, 0), text=txt + FOOT,
                        specs=[dict(kind="column", kicker=kick, title=col.get("title"), teams=col.get("teams"), date=ru_date(cday))]))
    # 6. История — с обложкой
    s = (S or [None])[0]
    if s and s.get("time"):
        sday = dt.datetime.fromisoformat(str(s["time"]).replace("Z", "+00:00")).astimezone(MSK)
        txt = f"<b>История. {e(s.get('title'))}</b>\n\n{e(s.get('dek'))}\n\n<a href=\"{URL}#a=s{e(s.get('id'))}\">Читать историю</a>"
        cover = (s.get("cover") or {}).get("url")
        credit = (s.get("cover") or {}).get("credit")
        if credit:
            txt = txt.replace("\n\n<a href", f"\n\n<i>Фото: {e(credit)}</i>\n<a href", 1)
        out.append(dict(key=f"story:{s.get('id')}", due=max(sday + dt.timedelta(minutes=30), msk(sday.date().isoformat(), 16, 30)),
                        expires=sday + dt.timedelta(hours=36), text=txt + FOOT, photo=cover,
                        specs=None if cover else [dict(kind="column", kicker="История", title=s.get("title"), teams=s.get("teams"), date="")]))
    # 7. Матчи — с 19:00 по Москве, каждые 30 минут; больше 4 — кратко двумя постами
    ups = sorted([u for u in D.get("upcoming") or [] if u.get("date") == ud], key=lambda u: u["start"])
    if ups:
        motd = D.get("motd") or {}
        is_m = lambda u: motd.get("away") == u["away"] and motd.get("home") == u["home"]
        ups = sorted(ups, key=lambda u: (not is_m(u), u["start"]))
        tgg = tgv(D, "games") or {}
        base = msk(ud, 19, 0)
        night = f"в ночь на {ru_date((dt.date.fromisoformat(ud) + dt.timedelta(days=1)).isoformat())}"

        def spec_for(u, gi):
            return dict(kind="match", away=u["away"], home=u["home"], time=dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")).astimezone(MSK).strftime("%H:%M"),
                        date=night, p_away=gi["m"].get("p_away"), p_home=gi["m"].get("p_home"), motd=is_m(u), sure=bool(gi["v"].get("sure")),
                        rec_a=form5(A, u["away"], ud), rec_h=form5(A, u["home"], ud))

        def tmsk(u):
            return dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")).astimezone(MSK).strftime("%H:%M")

        if len(ups) <= 4:
            for i, u in enumerate(ups):
                gi = game_info(u, M)
                start = dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00"))
                body = tgg.get(str(u["id"]))
                if not body:
                    body = (motd.get("text") if is_m(u) else None) or " ".join((u.get("factors") or [])[:2])
                    if u.get("lean"):
                        body += " " + u["lean"]
                pred = f"Прогноз модели: {T(gi['pick'])}" + (f", {pct(gi['p'])}" if gi["p"] else "")
                if gi["tot"]:
                    pred += f"; тотал — {gi['tot']}"
                pred += ". " + ("Рынок с ней не согласен." if gi["v"].get("vs_market") else "Рынок согласен.") if gi["m"].get("mkt_home") else "."
                if gi["v"].get("sure"):
                    pred += " Это сигнал «уверенный фаворит»: модель заметно увереннее рынка."
                head_t = ("Матч дня. " if is_m(u) else "") + f"{RU.get(u['away'])} — {RU.get(u['home'])}, {tmsk(u)} мск"
                txt = f"<b>{e(head_t)}</b>\n\n{e(body)}\n\n{e(pred)}\n\n<a href=\"{URL}#games\">Как считала модель</a>"
                out.append(dict(key=f"game:{ud}:{u['id']}", due=min(base + dt.timedelta(minutes=30 * i), start - dt.timedelta(minutes=60)),
                                expires=start, text=txt + FOOT, specs=[spec_for(u, gi)]))
        else:
            half = (len(ups) + 1) // 2
            for k, part in enumerate((ups[:half], ups[half:])):
                L = [f"<b>Матчи {night}</b>", ""]
                lead = tgv(D, "games_lead") if k == 0 else None
                if lead:
                    L += [e(lead), ""]
                for u in part:
                    gi = game_info(u, M)
                    L.append(f"<b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>, {tmsk(u)} мск" + (" — матч дня" if is_m(u) else ""))
                    note = tgg.get(str(u["id"]))
                    L.append(e(note) if note else f"Модель за {e(T(gi['pick']))}" + (f" ({pct(gi['p'])})" if gi["p"] else "") + ".")
                    L.append("")
                L.append(f"<a href=\"{URL}#games\">Прогнозы модели и разборы</a>")
                text = "\n".join(L)
                if len(re.sub("<[^>]+>", "", text + FOOT)) > 1024:
                    text = "\n".join(x for x in L if not x or x.startswith("<b>") or x.startswith("<a"))
                first = min(dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in part)
                out.append(dict(key=f"games:{ud}:{k}", due=min(base + dt.timedelta(minutes=45 * k), first - dt.timedelta(minutes=60)),
                                expires=first, text=text + FOOT, specs=[spec_for(part[0], game_info(part[0], M))]))
    # 8. Вечером передумали
    fin = D.get("final") or {}
    pf = p_final(D) if fin.get("t") else None
    if pf and ud:
        ft = dt.datetime.fromisoformat(fin["t"].replace("Z", "+00:00"))
        first = min((dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in ups), default=ft + dt.timedelta(hours=3))
        out.append(dict(key=f"final:{ud}", due=ft, expires=first, text=pf[0], specs=pf[1]))
    return out


import re  # noqa: E402


def form5(A, t, before):
    gs = [g for g in A.get("games", []) if t in (g.get("away"), g.get("home")) and g.get("as") is not None and g["date"] < before]
    gs = sorted(gs, key=lambda g: g["date"])[-5:]
    w = sum(1 for g in gs if (g["as"] > g["hs"]) == (g["away"] == t))
    return f"{w}-{len(gs) - w} в последних {len(gs)}" if gs else ""


def game_info(u, M):
    m = next((x for x in M.get("games", []) if x.get("id") == u["id"]), {}) or {}
    v = m.get("verdict") or {}
    side = u.get("pick_side") or v.get("fav")
    pick = u.get("pick") or (u["home"] if side == "home" else u["away"])
    t = u.get("total_pick") or {}
    tline = t.get("line", (v.get("total") or {}).get("line"))
    tside = t.get("side") or (v.get("total") or {}).get("side")
    tot = f"{'больше' if tside == 'over' else 'меньше'} {num(tline)}" if tside and tline else ""
    return dict(m=m, v=v, side=side, pick=pick, p=m.get(f"p_{side}") if side else None, tot=tot)


def p_final(D):
    f = D.get("final") or {}
    ups = {u["id"]: u for u in D.get("upcoming") or []}
    items, rows = [], []
    for c in f.get("changed") or []:
        u = ups.get(c.get("id"))
        if not u or c.get("what") not in ("исход", "тотал"):
            continue
        if c["what"] == "исход":
            to = u["home"] if c.get("to") == "home" else u["away"] if c.get("to") == "away" else c.get("to")
            new, short = f"теперь за {T(to)}", f"за {RU.get(to, to)}"
        else:
            t = u.get("total_pick") or {}
            new = f"тотал теперь {'больше' if c.get('to') == 'over' else 'меньше'} {num(t.get('line', ''))}"
            short = f"тотал {'больше' if c.get('to') == 'over' else 'меньше'} {num(t.get('line', ''))}"
        rows.append(f"<b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>: {e(new)}. Причина — {e(c.get('why') or 'вратари и поздняя линия')}.")
        items.append(dict(away=u["away"], home=u["home"], new=short))
    if not rows:
        return None
    txt = ("<b>Вечером модель передумала</b>\n\nОбъявили стартовых вратарей, сдвинулась линия — и прогноз пересчитан:\n\n" + "\n".join(rows)
           + f'\n\n<a href="{URL}#games">Финальные прогнозы на ночь</a>')
    return txt + FOOT, [dict(kind="changes", items=items, date=ru_date(D.get("upcoming_date")))]


# ---------------------------------------------------------------- запуск
def main(mode, arg=None):
    now = dt.datetime.now(dt.timezone.utc)
    LOG["t"], LOG["mode"] = now.strftime("%Y-%m-%dT%H:%M:%SZ"), mode
    state = load(f"{TG}/state.json", {"posted": {}}) or {"posted": {}}
    P = state.setdefault("posted", {})
    MSG = state.setdefault("messages", {})
    D = load(f"{SITE}/data.json", {}) or {}
    A = load(f"{SITE}/archive.json", {"games": []}) or {"games": []}
    M = load(f"{SITE}/model.json", {}) or {}
    E = load(f"{SITE}/edge.json", {}) or {}
    S = load(f"{SITE}/stories.json", []) or []
    S = sorted(S if isinstance(S, list) else S.get("stories", []), key=lambda x: str(x.get("time")), reverse=True)
    N = Names()
    items = build(D, A, M, E, S, N)
    LOG["plan"] = [dict(key=x["key"], due=x["due"].astimezone(MSK).strftime("%d.%m %H:%M"), done=x["key"] in P) for x in items]

    if mode == "preview":
        specs = [s for x in items for s in (x.get("specs") or []) if s]
        out = cards(specs, D)
        import shutil
        os.makedirs(f"{TG}/preview", exist_ok=True)
        for p in out:
            if p:
                shutil.copy(p, f"{TG}/preview/{os.path.basename(p)}")
        save(f"{TG}/preview/texts.json", [dict(key=x["key"], text=x["text"], photo=x.get("photo")) for x in items])
        LOG["ok"].append(f"превью: {sum(1 for p in out if p)} карточек, {len(items)} постов")
        return

    cfg = load(f"{TG}/config.json", {}) or {}
    if mode == "discover" or not cfg.get("chat_id"):
        cfg = discover()
        if mode == "discover" or not cfg.get("chat_id"):
            return
    chat = cfg["chat_id"]

    def post(x):
        try:
            imgs = cards([s for s in x.get("specs") or [] if s], D) if x.get("specs") else []
            ids = send(chat, x["text"], images=imgs[:1], photo_url=None if imgs and imgs[0] else x.get("photo"))
            P[x["key"]] = LOG["t"]
            MSG[x["key"]] = ids
            state["last_post"] = dt.datetime.now(dt.timezone.utc).isoformat()
            LOG["ok"].append(x["key"])
        except Exception as ex:
            LOG["fail"].append(f"{x['key']}: {ex}"[:300])

    if mode == "cleanup":
        for mid in [int(v) for v in str(arg or "").split(",") if v.strip().isdigit()]:
            try:
                _call("deleteMessage", dict(chat_id=chat, message_id=mid))
                LOG["ok"].append(f"удалено {mid}")
            except Exception as ex:
                LOG["fail"].append(f"{mid}: {ex}"[:120])
    elif mode == "test":
        # удаляем прошлые версии тех же постов и публикуем весь набор сразу
        for x in items:
            for mid in MSG.get(x["key"], []):
                try:
                    _call("deleteMessage", dict(chat_id=chat, message_id=mid))
                except Exception:
                    pass
            P.pop(x["key"], None)
        for x in items:
            if x.get("expires") and now > x["expires"]:
                continue
            post(x)
    else:
        last = state.get("last_post")
        gap = (now - dt.datetime.fromisoformat(last)).total_seconds() / 60 if last else 999
        due = [x for x in items if x["key"] not in P and x["due"] <= now and (not x.get("expires") or now < x["expires"])]
        # дневные посты, у которых прошло больше 8 часов от срока, не догоняем
        due = [x for x in due if x.get("expires") or (now - x["due"]).total_seconds() < 8 * 3600]
        due.sort(key=lambda x: x["due"])
        if due:
            x = due[0]
            if x["key"].startswith("final:") or gap >= 20:
                post(x)
    cut = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    state["posted"] = {k: v for k, v in P.items() if v[:10] >= cut}
    state["messages"] = {k: v for k, v in MSG.items() if k in state["posted"]}
    save(f"{TG}/state.json", state)


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        main(m, sys.argv[2] if len(sys.argv) > 2 else None)
    except Exception as ex:
        import traceback
        LOG["fail"].append(traceback.format_exc()[-400:])
    save(f"{TG}/last.json", LOG)
    print(json.dumps(LOG, ensure_ascii=False))
