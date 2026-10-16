"""Telegram-канал NHL-STATS.RU: посты из готовых текстов сайта. Без Claude, запускается в GitHub (tg.yml).

Режимы:
  auto     — после каждого сбора/публикации: постит то, что появилось и ещё не публиковалось (утро, матчи, колонка, история, вечерние изменения);
  test     — опубликовать утренний набор прямо сейчас (утро, матчи дня, колонка) и отметить его опубликованным;
  discover — найти канал, куда бота добавили админом (getUpdates), и записать tg/config.json.
Токен — только в секрете TELEGRAM_BOT_TOKEN. Что опубликовано — tg/state.json; итог запуска — tg/last.json.
"""
import datetime as dt
import html
import json
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
TG = os.path.join(ROOT, "tg")
URL = "https://levastak.github.io/nhl-svodka/"
KIROV = ZoneInfo("Europe/Kirov")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
LOG = {"t": None, "mode": None, "ok": [], "fail": []}

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
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KIROV)
    return t.strftime("%H:%M")


def pct(p):
    return f"{round(p * 100)}%"


def num(x):
    try:
        x = float(x)
        return (f"{int(x)}" if x == int(x) else f"{x:g}").replace(".", ",")
    except Exception:
        return str(x)


class Names:
    def __init__(self):
        self.d = load(f"{SITE}/names_ru.json", {}) or {}

    def full(self, n):
        return self.d.get(n, n)


# ---------------------------------------------------------------- Bot API
def api(method, **params):
    if not TOKEN:
        raise RuntimeError("нет TELEGRAM_BOT_TOKEN")
    data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:
        j = json.loads(ex.read().decode() or "{}")
    if not j.get("ok"):
        raise RuntimeError(f"{method}: {j.get('error_code')} {j.get('description')}")
    return j["result"]


def send(chat, text, photo=None, preview=False):
    if photo:
        try:
            return api("sendPhoto", chat_id=chat, photo=photo, caption=text[:1024], parse_mode="HTML")
        except Exception as ex:
            LOG["fail"].append(f"фото не ушло, шлю текстом: {ex}"[:200])
    return api("sendMessage", chat_id=chat, text=text[:4096], parse_mode="HTML",
               link_preview_options={"is_disabled": not preview})


def discover():
    cfg = load(f"{TG}/config.json", {}) or {}
    ups = api("getUpdates", allowed_updates=["my_chat_member", "channel_post"])
    found = {}
    for u in ups:
        for k in ("my_chat_member", "channel_post"):
            c = (u.get(k) or {}).get("chat") or {}
            if c.get("type") == "channel":
                found[c["id"]] = dict(chat_id=c["id"], title=c.get("title"), username=c.get("username"))
    if len(found) == 1:
        cfg.update(list(found.values())[0])
        save(f"{TG}/config.json", cfg)
        LOG["ok"].append(f"канал найден: {cfg.get('title')} (@{cfg.get('username')})")
    elif found:
        LOG["fail"].append(f"несколько каналов: {[v['title'] for v in found.values()]} — укажи нужный в tg/config.json")
    elif not cfg.get("chat_id"):
        LOG["fail"].append("канал не найден: удали бота из админов и добавь снова, затем повтори discover")
    return cfg


# ---------------------------------------------------------------- посты
def post_morning(D, A, E, N):
    day = D.get("results_date")
    gs = [g for g in A.get("games", []) if g.get("date") == day and g.get("as") is not None]
    if not gs:
        return None
    L = [f"🏒 <b>Итоги ночи · {ru_date(day)}</b>", ""]
    for g in gs:
        end = {"OT": " ОТ", "SO": " Б"}.get(g.get("end"), "")
        aw, hm = (f"<b>{e(RU.get(g['away']))}</b>", e(RU.get(g["home"]))) if g["as"] > g["hs"] else (e(RU.get(g["away"])), f"<b>{e(RU.get(g['home']))}</b>")
        L.append(f"{aw} — {hm} {g['as']}:{g['hs']}{end}")
    n = D.get("daily") or {}
    if n.get("date") == day:
        if n.get("heroes"):
            L += ["", "⭐ <b>Три звезды</b>"]
            for i, h in enumerate(n["heroes"][:3]):
                L.append(f"{i + 1}. {e(N.full(h['name']))} ({e(RU.get(h['team']))}) — {e(h.get('line'))}")
        if n.get("goalie"):
            gk = n["goalie"]
            L.append(f"🧤 Вратарь дня: {e(N.full(gk['name']))} ({e(RU.get(gk['team']))}) — {e(gk.get('line'))}")
        if n.get("russian"):
            r = n["russian"]
            L.append(f"🇷🇺 Россиянин дня: {e(N.full(r['name']))} ({e(RU.get(r['team']))}) — {e(r.get('line'))}")
        if n.get("sensation") and n["sensation"].get("head"):
            L += ["", f"⚡ <b>Сенсация:</b> {e(n['sensation']['head'])}"]
    num_d = n.get("number") if n.get("date") == day else None
    f = (E or {}).get("findings") or []
    if num_d and num_d.get("text"):
        L += ["", f"🔢 <b>Цифра дня: {e(num_d.get('big'))}{e(num_d.get('unit') or '')}</b> — {e(num_d.get('head'))}", e(num_d["text"])]
    elif f:
        L += ["", f"🔢 <b>Цифра дня:</b> {e(f[0]['line'])}"]
    L += ["", f"<a href=\"{URL}#results\">Все итоги и протоколы →</a>"]
    return "\n".join(L)


def game_line(u, M):
    m = next((x for x in M.get("games", []) if x.get("id") == u["id"]), {}) or {}
    v = m.get("verdict") or {}
    side = u.get("pick_side") or v.get("fav")
    pick = u.get("pick") or (u["home"] if side == "home" else u["away"])
    p = m.get(f"p_{side}") if side else None
    t = u.get("total_pick") or {}
    tline = t.get("line", v.get("total", {}).get("line"))
    tside = t.get("side") or (v.get("total") or {}).get("side")
    tp = m.get("p_over" if tside == "over" else "p_under")
    tot = f"{'больше' if tside == 'over' else 'меньше'} {num(tline)}" if tside and tline else None
    s = f"{e(T(pick))}" + (f" — {pct(p)}" if p else "")
    if tot:
        s += f" · {tot}" + (f" — {pct(tp)}" if tp else "")
    vs = v.get("vs_market")
    mk = m.get(f"mkt_{side}") if side else None
    mtxt = (" · рынок против" if vs else " · рынок согласен") if mk else ""
    return s, mtxt, v


def posts_games(D, M):
    ups = [u for u in D.get("upcoming") or [] if u.get("date") == D.get("upcoming_date")]
    if not ups:
        return []
    ups.sort(key=lambda u: u["start"])
    motd = D.get("motd") or {}
    day = D.get("upcoming_date")
    if len(ups) <= 4:
        out = []
        for u in ups:
            s, mtxt, v = game_line(u, M)
            is_motd = motd.get("away") == u["away"] and motd.get("home") == u["home"]
            L = [("🔥 <b>Матч дня</b>\n" if is_motd else "") + f"🏒 <b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b> · {kirov_time(u['start'])} по Кирову"]
            if is_motd and motd.get("text"):
                L += ["", e(motd["text"])]
            fac = (u.get("factors") or [])[:3]
            if fac:
                L += [""] + [f"• {e(x)}" for x in fac]
            L += ["", f"📊 <b>Прогноз модели:</b> {s}{mtxt}"]
            if v.get("sure"):
                L.append("✅ Сигнал «уверенный фаворит»")
            if u.get("lean"):
                L.append(f"<i>{e(u['lean'])}</i>")
            L += ["", f"<a href=\"{URL}#games\">Разбор модели и линия →</a>"]
            out.append("\n".join(L))
        return out
    # больше 4 матчей — кратко, двумя постами
    half = (len(ups) + 1) // 2
    out = []
    for k, part in enumerate((ups[:half], ups[half:])):
        L = [f"🏒 <b>Матчи {ru_date(day)}</b> · часть {k + 1} из 2", ""]
        for u in part:
            s, mtxt, v = game_line(u, M)
            star = "🔥 " if motd.get("away") == u["away"] and motd.get("home") == u["home"] else ""
            L.append(f"{star}<b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b> · {kirov_time(u['start'])}")
            L.append(f"{s}{mtxt}" + (" · ✅ уверенный фаворит" if v.get("sure") else ""))
            if u.get("factors"):
                L.append(f"<i>{e(u['factors'][0])}</i>")
            L.append("")
        L.append(f"<a href=\"{URL}#games\">Все матчи и разборы →</a>")
        out.append("\n".join(L))
    return out


def post_column(D):
    col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), None)
    if not col:
        return None, None
    kick = col.get("kicker") if col.get("kicker") and col.get("kicker") != "Колонка Claude" else "Колонка"
    icon = {"Под микроскопом": "🔬", "Итоги недели": "📅"}.get(kick, "✍️")
    txt = f"{icon} <b>{e(kick)}</b>\n\n<b>{e(col.get('title'))}</b>\n\n{e(col.get('dek'))}\n\n<a href=\"{URL}#a=col\">Читать →</a>"
    return txt, col.get("title")


def post_story(S):
    s = (S or [None])[0]
    if not s:
        return None, None, None
    txt = f"📜 <b>История</b>\n\n<b>{e(s.get('title'))}</b>\n\n{e(s.get('dek'))}\n\n<a href=\"{URL}#a=s{e(s.get('id'))}\">Читать →</a>"
    return txt, (s.get("cover") or {}).get("url"), s.get("id")


def post_final(D):
    f = D.get("final") or {}
    ch = [c for c in f.get("changed") or [] if c.get("what") in ("исход", "тотал")]
    ups = {u["id"]: u for u in D.get("upcoming") or []}
    rows = []
    for c in ch:
        u = ups.get(c.get("id"))
        if not u:
            continue
        if c["what"] == "исход":
            to = u["home"] if c.get("to") == "home" else u["away"] if c.get("to") == "away" else c.get("to")
            new = f"теперь победа {T(to)}"
        else:
            t = u.get("total_pick") or {}
            new = f"теперь {'больше' if c.get('to') == 'over' else 'меньше'} {num(t.get('line', ''))}"
        rows.append(f"• <b>{e(RU.get(u['away']))} — {e(RU.get(u['home']))}</b>: {e(new)} ({e(c.get('why') or 'вратари и поздняя линия')})")
    if not rows:
        return None
    return "🔄 <b>Вечером передумали</b>\n\nПосле объявления вратарей и поздней линии модель изменила прогноз:\n" + "\n".join(rows) + f"\n\n<a href=\"{URL}#games\">Финальные прогнозы →</a>"


# ---------------------------------------------------------------- запуск
def main(mode):
    now = dt.datetime.now(dt.timezone.utc)
    LOG["t"], LOG["mode"] = now.strftime("%Y-%m-%dT%H:%M:%SZ"), mode
    state = load(f"{TG}/state.json", {"posted": {}}) or {"posted": {}}
    P = state.setdefault("posted", {})
    cfg = load(f"{TG}/config.json", {}) or {}
    if mode == "discover" or not cfg.get("chat_id"):
        cfg = discover()
        if mode == "discover" or not cfg.get("chat_id"):
            return
    chat = cfg["chat_id"]
    D = load(f"{SITE}/data.json", {}) or {}
    A = load(f"{SITE}/archive.json", {"games": []}) or {"games": []}
    M = load(f"{SITE}/model.json", {}) or {}
    E = load(f"{SITE}/edge.json", {}) or {}
    S = load(f"{SITE}/stories.json", []) or []
    S = S if isinstance(S, list) else S.get("stories", [])
    S = sorted(S, key=lambda x: str(x.get("time")), reverse=True)
    N = Names()

    def mark(k):
        P[k] = LOG["t"]

    def do(k, fn):
        try:
            fn()
            mark(k)
            LOG["ok"].append(k)
        except Exception as ex:
            LOG["fail"].append(f"{k}: {ex}"[:300])

    rd, ud = D.get("results_date"), D.get("upcoming_date")
    k_now = now.astimezone(KIROV)
    # утренние тексты готовы: тексты Claude за этот игровой день, или запасные после 10:15 по Кирову
    claude_ready = (D.get("daily") or {}).get("date") == rd and not D.get("auto_texts")
    fallback_ok = bool(D.get("auto_texts")) and k_now.hour * 60 + k_now.minute >= 10 * 60 + 15
    fresh_results = rd and (k_now.date() - dt.date.fromisoformat(rd)).days <= 1
    morning_ok = mode == "test" or (fresh_results and (claude_ready or fallback_ok) and 8 <= k_now.hour < 18)

    if morning_ok and rd and f"am:{rd}" not in P:
        t = post_morning(D, A, E, N)
        if t:
            do(f"am:{rd}", lambda: send(chat, t))
    if (mode == "test" or (morning_ok and ud and k_now.date().isoformat() <= ud)) and ud and f"games:{ud}" not in P:
        ps = posts_games(D, M)
        if ps:
            do(f"games:{ud}", lambda: [send(chat, x) for x in ps])
    ct, ctitle = post_column(D)
    if ct and morning_ok and f"col:{ctitle}" not in P:
        col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), {})
        ctime = col.get("time") or ""
        if mode == "test" or ctime[:10] >= (now - dt.timedelta(hours=20)).strftime("%Y-%m-%d"):
            do(f"col:{ctitle}", lambda: send(chat, ct))
    st, cover, sid = post_story(S)
    if st and mode == "auto" and f"story:{sid}" not in P:
        stime = str(S[0].get("time") or "")
        if stime and (now - dt.datetime.fromisoformat(stime.replace("Z", "+00:00"))).total_seconds() < 36 * 3600:
            do(f"story:{sid}", lambda: send(chat, st, photo=cover))
        else:
            mark(f"story:{sid}")  # старую статью не постим
    f = D.get("final") or {}
    if mode == "auto" and ud and f.get("t", "")[:10] == now.strftime("%Y-%m-%d") and f"final:{ud}" not in P:
        ft = post_final(D)
        if ft:
            do(f"final:{ud}", lambda: send(chat, ft))
        else:
            mark(f"final:{ud}")
    if mode == "test" and st and f"story:{sid}" not in P:
        mark(f"story:{sid}")
    # храним отметки за 30 дней
    cut = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    state["posted"] = {k: v for k, v in P.items() if v[:10] >= cut}
    save(f"{TG}/state.json", state)


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        main(m)
    except Exception as ex:
        LOG["fail"].append(f"{ex!r}"[:300])
    save(f"{TG}/last.json", LOG)
    print(json.dumps(LOG, ensure_ascii=False))
