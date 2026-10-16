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
FOOT = f'\n\n🏒 <a href="{URL}">NHL-STATS.RU</a> — статистика, прогнозы и аналитика НХЛ по-русски'

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


# ---------------------------------------------------------------- посты: (подпись, [карточки])
def form5(A, t, before):
    gs = [g for g in A.get("games", []) if t in (g.get("away"), g.get("home")) and g.get("as") is not None and g["date"] < before]
    gs = sorted(gs, key=lambda g: g["date"])[-5:]
    w = sum(1 for g in gs if (g["as"] > g["hs"]) == (g["away"] == t))
    return f"{w}-{len(gs) - w} в последних {len(gs)}" if gs else ""


def p_morning(D, A, E, N):
    day = D.get("results_date")
    gs = [g for g in A.get("games", []) if g.get("date") == day and g.get("as") is not None]
    if not gs:
        return None
    n = D.get("daily") or {}
    n = n if n.get("date") == day else {}
    human = (D.get("tg") or {}).get("morning") if (D.get("tg") or {}).get("date") == day else None
    L = []
    if human:
        L.append(e(human))
    else:
        ot = sum(1 for g in gs if g.get("end") in ("OT", "SO"))
        lead = f"Доброе утро! За ночь — {len(gs)} {plural(len(gs), 'матч', 'матча', 'матчей')}"
        lead += f", {ot} из них дошли до овертайма или буллитов." if ot else "."
        h = (n.get("heroes") or [None])[0]
        if h and h.get("text"):
            t = h["text"].strip()
            lead += f" Главный герой — {e(N.full(h['name']))}: {e(t[:1].lower() + t[1:])}"
        L.append(lead)
    if n.get("heroes"):
        L += ["", "⭐ " + " · ".join(f"{e(N.last(h['name']))} {e(h.get('line'))}" for h in n["heroes"][:3])]
    if n.get("russian"):
        r = n["russian"]
        L.append(f"🇷🇺 {e(N.full(r['name']))} — {e(r.get('line'))}")
    if n.get("sensation") and n["sensation"].get("head"):
        L.append(f"⚡ {e(n['sensation']['head'])}")
    L.append(f'\n👉 <a href="{URL}#results">Все итоги, протоколы и герои дня</a>')
    specs = [dict(kind="scores", date=ru_date(day), games=gs)]
    # цифра дня — второй картинкой
    num_d = n.get("number")
    f = ((E or {}).get("findings") or [None])[0]
    src = num_d if num_d and num_d.get("big") else f
    if src and src.get("big"):
        pl = (src.get("players") or [None])[0]
        hp = (D.get("heads") or {}).get(pl) if pl else None
        specs.append(dict(kind="number", big=src["big"], unit=src.get("unit"), sub=src.get("sub"),
                          head=(num_d or {}).get("head") or src.get("head"), teams=src.get("teams"),
                          player=N.full(pl) if pl else None, head_path=hp,
                          date=f"по матчам до {ru_date(src['date'])}" if src.get("date") else ""))
        txt = (num_d or {}).get("text") or (f or {}).get("line")
        if txt:
            L.insert(-1, f"\n🔢 <b>Цифра дня.</b> {e(txt)}")
    return "\n".join(L) + FOOT, specs


def game_info(u, M):
    m = next((x for x in M.get("games", []) if x.get("id") == u["id"]), {}) or {}
    v = m.get("verdict") or {}
    side = u.get("pick_side") or v.get("fav")
    pick = u.get("pick") or (u["home"] if side == "home" else u["away"])
    t = u.get("total_pick") or {}
    tline = t.get("line", (v.get("total") or {}).get("line"))
    tside = t.get("side") or (v.get("total") or {}).get("side")
    tp = m.get("p_over" if tside == "over" else "p_under")
    tot = f"{'больше' if tside == 'over' else 'меньше'} {num(tline)}" if tside and tline else ""
    return dict(m=m, v=v, side=side, pick=pick, p=m.get(f"p_{side}") if side else None, tot=tot, tp=tp)


def p_games(D, M, A):
    ups = sorted([u for u in D.get("upcoming") or [] if u.get("date") == D.get("upcoming_date")], key=lambda u: u["start"])
    if not ups:
        return []
    motd = D.get("motd") or {}
    day = D.get("upcoming_date")
    tgt = (D.get("tg") or {}).get("games") or {}
    night = f"в ночь на {ru_date((dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat())}"
    out = []
    if len(ups) <= 4:
        for u in ups:
            gi = game_info(u, M)
            is_motd = motd.get("away") == u["away"] and motd.get("home") == u["home"]
            L = [f"{'🔥 <b>Матч дня.</b> ' if is_motd else '🏒 '}<b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>, {kirov_time(u['start'])} по Кирову", ""]
            human = tgt.get(str(u["id"]))
            if human:
                L.append(e(human))
            elif is_motd and motd.get("text"):
                L.append(e(motd["text"]))
            else:
                L.append(e((u.get("factors") or [""])[0]))
            if not human:
                for x in (u.get("factors") or [])[1:3]:
                    L.append(f"• {e(x)}")
            s = f"\n📊 Модель за {e(T(gi['pick']))}" + (f" — {pct(gi['p'])}" if gi["p"] else "")
            if gi["tot"]:
                s += f", тотал {gi['tot']}" + (f" — {pct(gi['tp'])}" if gi["tp"] else "")
            s += ". " + ("Рынок думает иначе." if gi["v"].get("vs_market") else "Рынок с ней согласен.") if gi["m"].get("mkt_home") else "."
            L.append(s)
            if gi["v"].get("sure"):
                L.append("✅ Сигнал «уверенный фаворит»: модель заметно увереннее рынка.")
            L.append(f'\n👉 <a href="{URL}#games">Как считала модель и линия</a>')
            text = "\n".join(L)
            if len(text) + len(FOOT) > 1024:  # подпись к картинке — до 1024 знаков
                text = "\n".join(x for x in L if not x.startswith("• "))
            spec = dict(kind="match", away=u["away"], home=u["home"], time=kirov_time(u["start"]), date=night,
                        p_away=gi["m"].get("p_away"), p_home=gi["m"].get("p_home"),
                        total=f"тотал {gi['tot']} — {pct(gi['tp'])}" if gi["tot"] and gi["tp"] else "",
                        motd=is_motd, sure=bool(gi["v"].get("sure")),
                        rec_a=form5(A, u["away"], day), rec_h=form5(A, u["home"], day))
            out.append((text + FOOT, [spec]))
        return out
    # больше 4 матчей — кратко, двумя постами, картинка — матч дня (или первый матч части)
    half = (len(ups) + 1) // 2
    for k, part in enumerate((ups[:half], ups[half:])):
        L = [f"🏒 <b>Матчи {night}</b> · {k + 1}/2", ""]
        if k == 0 and (D.get("tg") or {}).get("games_lead"):
            L += [e(D["tg"]["games_lead"]), ""]
        pic = None
        for u in part:
            gi = game_info(u, M)
            is_motd = motd.get("away") == u["away"] and motd.get("home") == u["home"]
            L.append(f"{'🔥 ' if is_motd else ''}<b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>, {kirov_time(u['start'])}")
            L.append(f"Модель: {e(T(gi['pick']))}" + (f" {pct(gi['p'])}" if gi["p"] else "") + (f", {gi['tot']}" if gi["tot"] else "")
                     + (" ✅" if gi["v"].get("sure") else ""))
            if is_motd or pic is None:
                pic = dict(kind="match", away=u["away"], home=u["home"], time=kirov_time(u["start"]), date=night,
                           p_away=gi["m"].get("p_away"), p_home=gi["m"].get("p_home"),
                           total=f"тотал {gi['tot']} — {pct(gi['tp'])}" if gi["tot"] and gi["tp"] else "",
                           motd=is_motd, sure=bool(gi["v"].get("sure")), rec_a=form5(A, u["away"], day), rec_h=form5(A, u["home"], day))
        L.append(f'\n👉 <a href="{URL}#games">Все матчи и разборы модели</a>')
        out.append(("\n".join(L) + FOOT, [pic]))
    return out


def p_column(D):
    col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), None)
    if not col:
        return None, None
    kick = col.get("kicker") if col.get("kicker") and col.get("kicker") != "Колонка Claude" else "Колонка"
    icon = {"Под микроскопом": "🔬", "Итоги недели": "📅"}.get(kick, "✍️")
    human = (D.get("tg") or {}).get("column")
    txt = f"{icon} <b>{e(col.get('title'))}</b>\n\n{e(human or col.get('dek'))}\n\n👉 <a href=\"{URL}#a=col\">Читать полностью</a>"
    spec = dict(kind="column", kicker=kick, title=col.get("title"), teams=col.get("teams"),
                date=ru_date(str(col.get("time") or dt.date.today().isoformat())[:10]))
    return (txt + FOOT, [spec]), col.get("title")


def p_story(S):
    s = (S or [None])[0]
    if not s:
        return None, None
    txt = f"📜 <b>История.</b> {e(s.get('title'))}\n\n{e(s.get('dek'))}\n\n👉 <a href=\"{URL}#a=s{e(s.get('id'))}\">Читать историю</a>"
    cover = (s.get("cover") or {}).get("url")
    spec = None if cover else dict(kind="column", kicker="История", title=s.get("title"), teams=s.get("teams"), date="")
    return (txt + FOOT, cover, spec), s.get("id")


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
        rows.append(f"• <b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>: {e(new)} ({e(c.get('why') or 'вратари и поздняя линия')})")
        items.append(dict(away=u["away"], home=u["home"], new=short))
    if not rows:
        return None
    txt = ("🔄 <b>Вечером передумали</b>\n\nОбъявили вратарей, сдвинулась линия — и модель пересчитала прогноз:\n" + "\n".join(rows)
           + f'\n\n👉 <a href="{URL}#games">Финальные прогнозы на ночь</a>')
    return txt + FOOT, [dict(kind="changes", items=items, date=ru_date(D.get("upcoming_date")))]


# ---------------------------------------------------------------- запуск
def main(mode):
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

    if mode == "preview":
        specs = []
        pm = p_morning(D, A, E, N)
        if pm:
            specs += pm[1]
        for _, sp in p_games(D, M, A):
            specs += sp
        pc, _ = p_column(D)
        if pc:
            specs += pc[1]
        out = cards(specs, D)
        import shutil
        os.makedirs(f"{TG}/preview", exist_ok=True)
        for p in out:
            if p:
                shutil.copy(p, f"{TG}/preview/{os.path.basename(p)}")
        LOG["ok"].append(f"превью: {sum(1 for p in out if p)} из {len(out)}")
        return

    cfg = load(f"{TG}/config.json", {}) or {}
    if mode == "discover" or not cfg.get("chat_id"):
        cfg = discover()
        if mode == "discover" or not cfg.get("chat_id"):
            return
    chat = cfg["chat_id"]

    def mark(k, ids=None):
        P[k] = LOG["t"]
        if ids:
            MSG[k] = ids

    def post(k, text, specs=None, photo_url=None):
        try:
            imgs = cards([s for s in specs or [] if s], D) if specs else []
            ids = send(chat, text, images=imgs, photo_url=photo_url)
            mark(k, ids)
            LOG["ok"].append(k)
        except Exception as ex:
            LOG["fail"].append(f"{k}: {ex}"[:300])

    rd, ud = D.get("results_date"), D.get("upcoming_date")
    k_now = now.astimezone(KIROV)
    claude_ready = (D.get("daily") or {}).get("date") == rd and not D.get("auto_texts")
    fallback_ok = bool(D.get("auto_texts")) and k_now.hour * 60 + k_now.minute >= 10 * 60 + 15
    fresh = rd and (k_now.date() - dt.date.fromisoformat(rd)).days <= 1
    morning_ok = mode == "test" or (fresh and (claude_ready or fallback_ok) and 8 <= k_now.hour < 18)

    if morning_ok and rd and f"am:{rd}" not in P:
        pm = p_morning(D, A, E, N)
        if pm:
            post(f"am:{rd}", pm[0], pm[1])
    if morning_ok and ud and f"games:{ud}" not in P and (mode == "test" or k_now.date().isoformat() <= ud):
        ps = p_games(D, M, A)
        for i, (t, sp) in enumerate(ps):
            post(f"games:{ud}:{i}", t, sp)
        if ps:
            mark(f"games:{ud}")
    pc, ctitle = p_column(D)
    if pc and morning_ok and f"col:{ctitle}" not in P:
        col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), {})
        if mode == "test" or str(col.get("time") or "")[:10] >= (now - dt.timedelta(hours=20)).strftime("%Y-%m-%d"):
            post(f"col:{ctitle}", pc[0], pc[1])
    ps_, sid = p_story(S)
    if ps_ and f"story:{sid}" not in P:
        stime = str(S[0].get("time") or "")
        if mode == "auto" and stime and (now - dt.datetime.fromisoformat(stime.replace("Z", "+00:00"))).total_seconds() < 36 * 3600:
            post(f"story:{sid}", ps_[0], [ps_[2]] if ps_[2] else None, photo_url=ps_[1])
        else:
            mark(f"story:{sid}")  # старую статью не постим
    f = D.get("final") or {}
    if mode == "auto" and ud and f.get("t", "")[:10] == now.strftime("%Y-%m-%d") and f"final:{ud}" not in P:
        pf = p_final(D)
        if pf:
            post(f"final:{ud}", pf[0], pf[1])
        else:
            mark(f"final:{ud}")
    cut = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    state["posted"] = {k: v for k, v in P.items() if v[:10] >= cut}
    state["messages"] = {k: v for k, v in MSG.items() if k in state["posted"]}
    save(f"{TG}/state.json", state)


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        main(m)
    except Exception as ex:
        LOG["fail"].append(f"{ex!r}"[:300])
    save(f"{TG}/last.json", LOG)
    print(json.dumps(LOG, ensure_ascii=False))
