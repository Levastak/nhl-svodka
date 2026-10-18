"""Telegram-канал NHL-STATS.RU (@nhlstatsru): посты с картинками из готовых текстов сайта. Без Claude, запускается в GitHub (tg.yml).

Режимы:
  auto     — после каждого прогона «Сводка НХЛ»: постит то, что появилось и ещё не публиковалось
             (утро, матчи дня, колонка, история, вечерние изменения);
  test     — опубликовать утренний набор прямо сейчас и отметить его опубликованным;
  preview  — только нарисовать карточки текущего дня в tg/preview/ (ничего не постит);
  recard   — перерисовать картинки (и подписи) уже выложенных постов; третьей строкой trigger/tg — префиксы ключей;
  admin    — запомнить личный чат Льва с ботом для оповещений о сбоях (сначала написать боту /start);
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

from game_day import day_complete, daily_ready

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
TG = os.path.join(ROOT, "tg")
URL = "https://levastak.github.io/nhl-svodka/"
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
    if vis > 1024 and images:
        url = host(images[0])
        if url:
            photo_url, images = url, []
    if vis > 1024 and photo_url and not images:
        # длинный текст: фото крупным превью над текстом (лимит 4096 вместо 1024)
        r = _call("sendMessage", dict(chat_id=chat, text=text, parse_mode="HTML",
                                      link_preview_options={"url": photo_url, "prefer_large_media": True, "show_above_text": True}))
        return [r["message_id"]]
    try:
        if len(images) > 1:
            media = [dict(type="photo", media=f"attach://f{i}", **({"caption": text, "parse_mode": "HTML"} if i == 0 else {}))
                     for i, _ in enumerate(images[:10])]
            r = _call("sendMediaGroup", dict(chat_id=chat, media=media), {f"f{i}": p for i, p in enumerate(images[:10])})
            return [m["message_id"] for m in r]
        if images:
            r = _call("sendPhoto", dict(chat_id=chat, caption=text, parse_mode="HTML"), {"photo": images[0]})
            return [r["message_id"]]
        if photo_url:
            r = _call("sendPhoto", dict(chat_id=chat, photo=photo_url, caption=text, parse_mode="HTML"))
            return [r["message_id"]]
    except Exception as ex:
        LOG["fail"].append(f"картинка не ушла, шлю текстом: {ex}"[:200])
    r = _call("sendMessage", dict(chat_id=chat, text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}))
    return [r["message_id"]]


def host(path):
    """Картинку — в отдельную ветку tg-img (одна свежая картинка, без истории) → прямая ссылка raw.githubusercontent."""
    import time
    name = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S_") + os.path.basename(path)
    env = dict(os.environ, GIT_AUTHOR_NAME="svodka-bot", GIT_AUTHOR_EMAIL="svodka-bot@users.noreply.github.com",
               GIT_COMMITTER_NAME="svodka-bot", GIT_COMMITTER_EMAIL="svodka-bot@users.noreply.github.com")
    run = lambda args, inp=None: subprocess.run(["git", "-C", ROOT, *args], input=inp, capture_output=True, text=True, env=env)
    try:
        blob = run(["hash-object", "-w", path]).stdout.strip()
        tree = run(["mktree"], f"100644 blob {blob}\t{name}\n").stdout.strip()
        commit = run(["commit-tree", tree, "-m", "tg image"]).stdout.strip()
        r = run(["push", "-f", "origin", f"{commit}:refs/heads/tg-img"])
        if r.returncode:
            LOG["fail"].append(f"tg-img: {r.stderr[-160:]}")
            return None
        url = f"https://raw.githubusercontent.com/Levastak/nhl-svodka/tg-img/{name}"
        for _ in range(10):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15) as resp:
                    if resp.status == 200:
                        return url
            except Exception:
                pass
            time.sleep(3)
        return url
    except Exception as ex:
        LOG["fail"].append(f"tg-img: {ex!r}"[:160])
        return None


def send_video(chat, text, c):
    """Скачать клипы (склеить, если несколько) и отправить видео с подписью."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import media
    if not media.tools(LOG):
        raise RuntimeError("нет yt-dlp/ffmpeg")
    wd = os.path.join(TG, "_video")
    os.makedirs(wd, exist_ok=True)
    files = [f for f in (media.clip(k["id"], wd) for k in c["clips"]) if f]
    if not files:
        raise RuntimeError("клипы не скачались")
    path = files[0] if len(files) == 1 else media.concat(files, os.path.join(wd, f"cut_{c['clips'][0]['id']}.mp4"))
    if not path:
        raise RuntimeError("склейка не удалась")
    if os.path.getsize(path) > 49 * 1024 * 1024:
        raise RuntimeError(f"видео {os.path.getsize(path) // 1048576} МБ — больше лимита 50 МБ")
    w, h, d = media.probe(path)
    th = media.thumb(path, path + ".jpg")
    files_up = {"video": path}
    if th:
        files_up["thumbnail"] = th
    r = _call("sendVideo", dict(chat_id=chat, caption=text, parse_mode="HTML", supports_streaming="true", width=w, height=h, duration=d), files_up)
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
# Расписание (по Москве): итоги 09:45, три звезды 10:45, цифра дня 12:00, главная новость 13:30, колонка 15:00,
# история 16:30, матчи с 19:00 каждые 30 минут (больше 4 — двумя постами), «вечером передумали» — после 23:19.
MSK = ZoneInfo("Europe/Moscow")


def msk(day, hh, mm):
    return dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hh, mm), MSK)


GOALS = {1: "Гол", 2: "Дубль", 3: "Хет-трик", 4: "Покер"}
NUM_F = {1: "", 2: "две", 3: "три", 4: "четыре", 5: "пять"}


def stat_parts(line):
    """«3+1» → («Хет-трик», «+ передача»), «0+3» → («Три передачи», ""), «36 из 39» → («36 сейвов», «из 39 бросков»)."""
    m = re.match(r"^\s*(\d+)\s*\+\s*(\d+)", str(line or ""))
    if m:
        g, a = int(m.group(1)), int(m.group(2))
        if g:
            main = GOALS.get(g, f"{g} голов")
            extra = ("+ передача" if a == 1 else f"+ {a} {plural(a, 'передача', 'передачи', 'передач')}") if a else ""
            return main, extra
        return (f"{NUM_F.get(a, a)} {plural(a, 'передача', 'передачи', 'передач')}".strip().capitalize() if a > 1 else "Передача"), ""
    m = re.match(r"^\s*(\d+)\s*из\s*(\d+)", str(line or ""))
    if m:
        sv, sh = int(m.group(1)), int(m.group(2))
        return f"{sv} {plural(sv, 'сейв', 'сейва', 'сейвов')}", f"из {sh} {plural(sh, 'броска', 'бросков', 'бросков')}"
    return str(line or ""), ""


def words(line):
    """Строка статистики для текста: «хет-трик и передача», «дубль», «36 сейвов из 39 бросков»."""
    a, b = stat_parts(line)
    if b.startswith("+ "):
        b = "и " + b[2:]
    return (a + (" " + b if b else "")).strip()


RU_GEN = {"ANA": "Анахаймом", "BOS": "Бостоном", "BUF": "Баффало", "CAR": "Каролиной", "CBJ": "Коламбусом", "CGY": "Калгари",
          "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Далласом", "DET": "Детройтом", "EDM": "Эдмонтоном", "FLA": "Флоридой",
          "LAK": "Лос-Анджелесом", "MIN": "Миннесотой", "MTL": "Монреалем", "NJD": "Нью-Джерси", "NSH": "Нэшвиллом",
          "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттавой", "PHI": "Филадельфией", "PIT": "Питтсбургом",
          "SEA": "Сиэтлом", "SJS": "Сан-Хосе", "STL": "Сент-Луисом", "TBL": "Тампой", "TOR": "Торонто", "UTA": "Ютой",
          "VAN": "Ванкувером", "VGK": "Вегасом", "WPG": "Виннипегом", "WSH": "Вашингтоном"}


def match_note(gs, t):
    """«победа над «Ванкувером» 3:2 ОТ» / «поражение от …» — для карточки звезды."""
    g = next((g for g in gs if t in (g.get("away"), g.get("home"))), None)
    if not g:
        return ""
    mine, other = (g["as"], g["hs"]) if g["away"] == t else (g["hs"], g["as"])
    opp = g["home"] if g["away"] == t else g["away"]
    end = {"OT": " ОТ", "SO": " Б"}.get(g.get("end"), "")
    return (f"победа над «{RU_GEN.get(opp, opp)}» {mine}:{other}{end}" if mine > other
            else f"матч с «{RU_GEN.get(opp, opp)}», {mine}:{other}{end}")


def col_photo(col, news):
    """Фото к колонке: из статьи NHL.com о матче одного из героев колонки (по players, затем по клубам)."""
    pl = col.get("players") or []
    for name in pl:
        for x in news:
            if name in (x.get("players") or []) and x.get("image"):
                return dict(photo=x["image"], photo_big=x["image"].replace("-size50/", "-size100/"), credit=x.get("image_source") or x.get("source") or "NHL.com")
    for x in news:
        if set(col.get("teams") or []) & set(x.get("teams") or []) and x.get("image"):
            return dict(photo=x["image"], photo_big=x["image"].replace("-size50/", "-size100/"), credit=x.get("image_source") or x.get("source") or "NHL.com")
    return {}


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tgv(D, k, day=None):
    t = D.get("tg") or {}
    if day and t.get("date") != day:
        return None
    return t.get(k)


def edge_fresh(finding, day):
    try:
        ref = max(dt.date.fromisoformat(day), dt.datetime.now(MSK).date() - dt.timedelta(days=1))
        age = (ref - dt.date.fromisoformat(finding.get("date") or "")).days
        return 0 <= age <= 4
    except (TypeError, ValueError):
        return False


def head_path(D, name):
    return (D.get("heads") or {}).get(name)


def build(D, A, M, E, S, N):
    out = []
    rd, ud = D.get("results_date"), D.get("upcoming_date")
    n = D.get("daily") or {}
    n = n if daily_ready(D, A, load(f"{SITE}/box.json", {}) or {}) else {}
    news = D.get("news") or []
    # 1. Итоги ночи — картинка со счетами
    gs = [g for g in A.get("games", []) if g.get("date") == rd and g.get("as") is not None]
    if rd and gs:
        lead = tgv(D, "morning", rd)
        night = {str(x.get("id")): x.get("text") for x in tgv(D, "night", rd) or [] if isinstance(x, dict)}
        order = [str(x.get("id")) for x in tgv(D, "night", rd) or [] if isinstance(x, dict)]
        gs_sorted = sorted(gs, key=lambda g: order.index(str(g["id"])) if str(g["id"]) in order else 99)
        L = [f"<b>Итоги ночи · {ru_date(rd)}</b>"]
        if lead:
            L += ["", e(lead)]
        for g in gs_sorted:
            end = {"OT": " ОТ", "SO": " Б"}.get(g.get("end"), "")
            rev = night.get(str(g["id"])) or g.get("recap") or ""
            L += ["", f"<b>{e(RU.get(g['home']))} — {e(RU.get(g['away']))} {g['hs']}:{g['as']}{end}</b>"]
            if rev:
                L.append(e(rev))
        L += ["", f"<a href=\"{URL}#results\">Протоколы всех матчей</a>"]
        txt = "\n".join(L)
        if len(re.sub("<[^>]+>", "", txt + FOOT)) > 4000:  # длинно (запасные разборы) — по одному предложению на матч
            L2 = []
            for x in L:
                if x and not x.startswith("<") and x != e(lead or ""):
                    x = re.split(r"(?<=[.!?…])\s+", x)[0]
                L2.append(x)
            txt = "\n".join(L2)
        out.append(dict(key=f"am:{rd}", due=msk(rd, 9, 45) + dt.timedelta(days=1),
                        text=txt + FOOT, specs=[dict(kind="scores", date=ru_date(rd), games=gs_sorted)], needs_tg=True))
    # 2. Три звезды — фото из матча первой звезды
    hs = (n.get("heroes") or [])[:3]
    if hs:
        st = {x.get("name"): x.get("text") for x in tgv(D, "stars", rd) or [] if isinstance(x, dict)}
        bodies = [st.get(h["name"]) or h.get("text") or f"{words(h.get('line')).capitalize()}." for h in hs]
        # подпись под картинкой — до 1024 знаков: если длинно, оставляем у каждой звезды меньше предложений
        for keep in (9, 3, 2, 1):
            cut = [" ".join(re.split(r"(?<=[.!?…])\s+", b)[:keep]) for b in bodies]
            L = ["<b>Три звезды ночи</b>", ""]
            for i, h in enumerate(hs):
                L.append(f"<b>{i + 1}. {e(N.full(h['name']))}</b>, {e(T(h['team']))}\n{e(cut[i])}")
                L.append("")
            if len(re.sub("<[^>]+>", "", "\n".join(L) + FOOT)) < 960:
                break
        L.append(f"👉 <b><a href=\"{URL}#results\">Все герои и неудачники ночи</a></b>")
        spec = dict(kind="stars", date=ru_date(rd),
                    stars=[dict(name=N.full(h["name"]), team=h["team"], head_path=head_path(D, h["name"]),
                                stat=stat_parts(h.get("line"))[0], stat2=stat_parts(h.get("line"))[1], note=match_note(gs, h["team"])) for h in hs])
        out.append(dict(key=f"stars:{rd}", due=msk(rd, 10, 45) + dt.timedelta(days=1), text="\n".join(L) + FOOT, specs=[spec], needs_tg=True))
    # 2б. Наши в НХЛ (россияне ночи) — все наши игроки по протоколам (box.json), текст — Opus (tg.russians)
    box = load(f"{SITE}/box.json", {}) or {}
    rus = {x.get("name") for x in D.get("russians") or []}
    if rd and box.get("date") == rd and rus:
        rows, rest = [], []
        for g in box.get("games") or []:
            for p in g.get("players") or []:
                if p.get("name") not in rus:
                    continue
                opp = g["home"] if p.get("team") == g["away"] else g["away"]
                vs = f"с «{RU_GEN.get(opp, opp)}»"
                if p.get("pos") == "G":
                    if not p.get("shots"):
                        continue
                    a_, b_ = stat_parts(f"{p.get('saves', 0)} из {p.get('shots', 0)}")
                    rows.append(dict(k=5 + (p["saves"] / p["shots"] if p["shots"] else 0), name=N.full(p["name"]), team=p["team"],
                                     head_path=head_path(D, p["name"]), stat=a_, stat2=b_, vs=vs, raw=p, pos="G", saves=p.get("saves"), shots=p.get("shots"),
                                     tag="Сухарь" if p.get("saves") == p.get("shots") and p["shots"] >= 15 else ""))
                    continue
                pts = (p.get("g") or 0) + (p.get("a") or 0)
                if pts:
                    a_, b_ = stat_parts(f"{p.get('g', 0)}+{p.get('a', 0)}")
                    gg = p.get("g") or 0
                    rows.append(dict(k=pts * 10 + gg, name=N.full(p["name"]), team=p["team"], head_path=head_path(D, p["name"]),
                                     stat=a_, stat2=b_, vs=vs, raw=p, g=gg, a=p.get("a") or 0,
                                     tag={2: "Дубль", 3: "Хет-трик", 4: "Покер"}.get(gg, "Пять голов" if gg >= 5 else "")))
                else:
                    rest.append(N.last(p["name"]))
        rows.sort(key=lambda r: -r["k"])
        if rows:
            extra = rows[9:]
            parts = []
            ep = [N.last(r["raw"]["name"]) for r in extra if r["raw"].get("pos") != "G"]
            eg = [f"{N.last(r['raw']['name'])} {r['raw'].get('saves')} из {r['raw'].get('shots')}" for r in extra if r["raw"].get("pos") == "G"]
            if ep:
                parts.append("ещё с очками: " + ", ".join(ep))
            if eg:
                parts.append("вратари: " + ", ".join(eg))
            if rest:
                parts.append(f"без очков — {len(rest)} {plural(len(rest), 'игрок', 'игрока', 'игроков')}")
            rest_txt = "; ".join(parts)
            rest_txt = rest_txt[:1].upper() + rest_txt[1:]
            body = tgv(D, "russians", rd)
            if not body:
                body = "; ".join(f"{r['name'].split(' ', 1)[-1]} ({T(r['team'])}) — {words(str(r['raw'].get('g', 0)) + '+' + str(r['raw'].get('a', 0)) if r['raw'].get('pos') != 'G' else str(r['raw'].get('saves')) + ' из ' + str(r['raw'].get('shots'))).lower()}" for r in rows[:6]) + "."
            txt = f"<b>Наши в НХЛ · {ru_date(rd)}</b>\n\n{e(body)}" + (f"\n\n<i>{e(rest_txt)}.</i>" if rest_txt else "") + f"\n\n👉 <b><a href=\"{URL}#rus\">Все россияне в НХЛ</a></b>"
            out.append(dict(key=f"rus:{rd}", due=msk(rd, 11, 30) + dt.timedelta(days=1), text=txt + FOOT, needs_tg=True,
                            specs=[dict(kind="russians", date=ru_date(rd), rows=rows, rest=rest_txt)]))
    # 2в. По понедельникам — честный счёт модели за неделю (решение Льва 16.10): итог и самые обидные промахи, текст — Opus (tg.model_week)
    wk = load(f"{SITE}/weekly.json", {}) or {}
    if rd and wk.get("to") == rd and dt.date.fromisoformat(rd).weekday() == 6:
        mod = wk.get("model") or {}
        J = [x for x in D.get("journal") or [] if wk["from"] <= (x.get("date") or "") <= rd and x.get("type") in ("win", "total")]
        misses = sorted([x for x in J if x.get("result") == "miss"], key=lambda x: (x.get("type") != "win", x.get("odds") or 9))
        mrows = []
        for x in misses[:4]:
            as_, hs = (str(x.get("score") or ":").split(":") + [""])[:2]  # в журнале счёт «гости:хозяева»
            pick = (f"Модель: победа «{RU.get(x['pick'], x['pick'])}»" if x["type"] == "win" else
                    f"Модель: тотал {'больше' if x.get('side') == 'over' else 'меньше'} {num(x.get('line'))}")
            pick += ", рынок тоже" if x.get("mkt_side") == x.get("side") else ", рынок был против"
            mrows.append(dict(home=x["home"], away=x["away"], pick=pick, score=f"{hs}:{as_}"))
        vs = mod.get("vs_market") or {}
        if (mod.get("win") or {}).get("n"):
            body = tgv(D, "model_week")
            if not body:
                w_, t_ = mod.get("win") or {}, mod.get("total") or {}
                body = (f"За неделю модель угадала {w_.get('hit', 0)} {plural(w_.get('hit', 0), 'исход', 'исхода', 'исходов')} из {w_.get('n', 0)} "
                        f"и {t_.get('hit', 0)} {plural(t_.get('hit', 0), 'тотал', 'тотала', 'тоталов')} из {t_.get('n', 0)}."
                        + (f" В матчах, где она спорила с рынком, права оказалась в {vs.get('model', 0)} из {vs.get('n', 0)}." if vs.get("n") else ""))
            txt = (f"<b>Счёт модели за неделю · {ru_date(wk['from'])} — {ru_date(rd)}</b>\n\n{e(body)}"
                   f"\n\n👉 <b><a href=\"{URL}#picks\">Журнал всех прогнозов</a></b>")
            out.append(dict(key=f"modelweek:{rd}", due=msk(rd, 16, 30) + dt.timedelta(days=1), text=txt + FOOT, needs_tg=True,
                            specs=[dict(kind="modelweek", date=f"{ru_date(wk['from'])} — {ru_date(rd)}", win=mod.get("win"), total=mod.get("total"),
                                        vs=dict(n=vs.get("n"), hit=vs.get("model")) if vs.get("n") else None, misses=mrows)]))
    # 3. Цифра дня — отдельной карточкой
    num_d = n.get("number") or {}
    if not edge_fresh(num_d, rd):
        num_d = {}
    # не повторять цифру, уже выходившую в канале (тот же вид находки и тот же клуб/игрок) — решение Льва 17.10
    hist = [tuple(h) for h in (load(f"{TG}/state.json", {}) or {}).get("num_hist", [])]
    sig = lambda x: (x.get("kind"), ",".join(x.get("teams") or []) or ",".join(x.get("players") or []))
    if num_d.get("big") and sig(num_d) in hist:
        num_d = {}
    last_kind = hist[-1][0] if hist else None
    fs = [x for x in (E or {}).get("findings") or [] if sig(x) not in hist and edge_fresh(x, rd)]
    f = next((x for x in fs if x.get("kind") != last_kind), fs[0] if fs else None)
    src = num_d if num_d.get("big") and sig(num_d) not in hist else f
    if src and src.get("big") and rd:
        pl = (src.get("players") or [None])[0]
        body = ((tgv(D, "number", rd) or num_d.get("text")) if src is num_d else None) or (f or {}).get("line")
        head_t = num_d.get("head") or src.get("head")
        when = f"По матчам до {ru_date(src['date'])}." if src.get("date") and src.get("date") != rd else ""
        txt = f"<b>Цифра дня — {e(src['big'])}{e(src.get('unit') or '')}. {e(head_t)}</b>\n\n{e(body)}" + (f"\n\n<i>{when} Данные — трекинг НХЛ EDGE.</i>" if when else "\n\n<i>Данные — трекинг НХЛ EDGE.</i>")
        spec = dict(kind="number", big=src["big"], unit=src.get("unit"), sub=src.get("sub"), head=head_t, teams=src.get("teams"),
                    player=N.full(pl) if pl else None, head_path=head_path(D, pl) if pl else None,
                    date=f"по матчам до {ru_date(src['date'])}" if src.get("date") else "")
        out.append(dict(key=f"number:{rd}", due=msk(rd, 12, 0) + dt.timedelta(days=1), text=txt + FOOT, specs=[spec], needs_tg=True,
                        num_sig=list(sig(src))))
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
        out.append(dict(key=f"news:{item.get('url')}", due=msk(rd, 13, 30) + dt.timedelta(days=1), text=txt + FOOT, photo=item["image"], needs_tg=True))
    # 5. Колонка / «Под микроскопом» / «Итоги недели»
    col = next((a for a in D.get("articles") or [] if (a.get("kind") or "column") == "column"), None)
    if col and col.get("time"):
        kick = col.get("kicker") if col.get("kicker") and col.get("kicker") != "Колонка Claude" else "Колонка"
        body = tgv(D, "column", rd) or col.get("dek")
        txt = f"<b>{e(kick)}. {e(col.get('title'))}</b>\n\n{e(body)}\n\n📖 <b><a href=\"{URL}#a=col\">Читать колонку целиком</a></b>"
        cday = dt.datetime.fromisoformat(str(col["time"]).replace("Z", "+00:00")).astimezone(MSK).date().isoformat()
        out.append(dict(key=f"col:{col.get('title')}", due=msk(cday, 15, 0), text=txt + FOOT, needs_tg=True,
                        specs=[dict(kind="column", kicker=kick, title=col.get("title"), teams=col.get("teams"), date=ru_date(cday), **col_photo(col, news))]))
    # 6. История — с обложкой
    s = (S or [None])[0]
    if s and s.get("time"):
        sday = dt.datetime.fromisoformat(str(s["time"]).replace("Z", "+00:00")).astimezone(MSK)
        txt = f"<b>История. {e(s.get('title'))}</b>\n\n{e(s.get('dek'))}\n\n📖 <b><a href=\"{URL}#a=s{e(s.get('id'))}\">Читать историю целиком</a></b>"
        cover = (s.get("cover") or {}).get("url")
        credit = (s.get("cover") or {}).get("credit")
        if credit:
            txt += f"\n\n<i>Фото: {e(credit)}</i>"
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
        # превью — в 19:00, но не позже чем за 3 часа до первого матча (в выходные дневные игры), не раньше 12:00 (решение Льва 17.10)
        first_all = min(dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in ups)
        base = max(msk(ud, 12, 0), min(msk(ud, 19, 0), first_all - dt.timedelta(hours=3)))
        prev_end = base + dt.timedelta(minutes=30 * ((len(ups) - 1) if len(ups) <= 4 else (len(ups) + 3) // 5))
        night = f"в ночь на {ru_date((dt.date.fromisoformat(ud) + dt.timedelta(days=1)).isoformat())}"

        def spec_for(u, gi):
            return dict(kind="match", away=u["away"], home=u["home"], time=dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")).astimezone(MSK).strftime("%H:%M"),
                        date=night, p_away=gi["m"].get("p_away"), p_home=gi["m"].get("p_home"), motd=is_m(u), sure=bool(gi["v"].get("sure")),
                        mkt_home=gi["m"].get("mkt_home"), mkt_away=gi["m"].get("mkt_away"),
                        rec_h=season_rec(D, u["home"]), rec_a=season_rec(D, u["away"]), place_h=conf_place(D, u["home"]), place_a=conf_place(D, u["away"]),
                        leaders=leaders5(D, u, N))

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
                head_t = f"{RU.get(u['home'])} — {RU.get(u['away'])}, {tmsk(u)} мск"
                txt = f"<b>{e(head_t)}</b>\n\n{e(body)}\n\n{e(pred)}\n\n👉 <b><a href=\"{URL}#games\">Как считала модель</a></b>"
                out.append(dict(key=f"game:{ud}:{u['id']}", due=min(base + dt.timedelta(minutes=30 * i), start - dt.timedelta(minutes=60)),
                                expires=start, text=txt + FOOT, specs=[spec_for(u, gi)]))
        else:
            # много матчей (решение Льва 17.10): матч дня — отдельной карточкой, остальные — по времени, по 5 в пост, у каждого короткая строка
            short = tgv(D, "games_short") or {}
            m_ups = [u for u in ups if is_m(u)][:1]
            rest = sorted([u for u in ups if u not in m_ups], key=lambda u: u["start"])
            for u in m_ups:
                gi = game_info(u, M)
                body = tgg.get(str(u["id"])) or (motd.get("text") or "")
                pred = f"Прогноз модели: {T(gi['pick'])}" + (f", {pct(gi['p'])}" if gi["p"] else "")
                if gi["tot"]:
                    pred += f"; тотал — {gi['tot']}"
                pred += ". " + ("Рынок с ней не согласен." if gi["v"].get("vs_market") else "Рынок согласен.") if gi["m"].get("mkt_home") else "."
                head_t = f"Матч дня: {RU.get(u['home'])} — {RU.get(u['away'])}, {tmsk(u)} мск"
                txt = f"<b>{e(head_t)}</b>\n\n{e(body)}\n\n{e(pred)}\n\n👉 <b><a href=\"{URL}#games\">Как считала модель</a></b>"
                start = dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00"))
                out.append(dict(key=f"game:{ud}:{u['id']}", due=min(base, start - dt.timedelta(minutes=60)), expires=start, text=txt + FOOT,
                                specs=[spec_for(u, gi)]))
            chunks = [rest[i:i + 5] for i in range(0, len(rest), 5)]
            for k, part in enumerate(chunks):
                t0, t1 = tmsk(part[0]), tmsk(part[-1])
                L = [f"<b>Матчи {night}" + (f" · {t0}–{t1}" if t0 != t1 else f" · {t0}") + " мск</b>", ""]
                lead = tgv(D, "games_lead") if k == 0 else None
                if lead:
                    L += [e(lead), ""]
                for u in part:
                    gi = game_info(u, M)
                    L.append(f"<b>{e(RU.get(u['home']))} — {e(RU.get(u['away']))}</b>, {tmsk(u)}")
                    note = short.get(str(u["id"]))
                    mline = f"Модель за {T(gi['pick'])}" + (f", {pct(gi['p'])}" if gi["p"] else "") + "."
                    L.append(e(note) if note else e(mline))
                    L.append("")
                L.append(f"👉 <b><a href=\"{URL}#games\">Прогнозы модели и разборы</a></b>")
                first = min(dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in part)
                out.append(dict(key=f"gl:{ud}:{k}", due=min(base + dt.timedelta(minutes=30 * (k + (1 if m_ups else 0))), first - dt.timedelta(minutes=60)),
                                expires=first, text="\n".join(L) + FOOT, specs=[spec_for(part[0], game_info(part[0], M))]))
    # 7а. Модель против рынка — через 30 минут после превью (решение Льва 17.10; раньше было 18:30 до превью), только если в матчах вечера модель спорит с рынком (решение Льва 16.10)
    if ups:
        vsm = vs_market_rows(ups, M)
        if vsm and tgv(D, "vs_market"):  # без разбора Opus пост не выходит — голые проценты без «почему» не нужны
            first = min(dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in ups)
            rec = vs_market_record(D)
            body = tgv(D, "vs_market")
            head_t = "Модель против рынка" + (f" · в спорах сезона права в {rec[0]} из {rec[1]}" if rec and rec[1] else "")
            txt = f"<b>{e(head_t)}</b>\n\n{e(body)}\n\n👉 <b><a href=\"{URL}#games\">Как считала модель</a></b>"
            out.append(dict(key=f"vsm:{ud}", due=min(prev_end + dt.timedelta(minutes=30), first - dt.timedelta(minutes=20)), expires=first, text=txt + FOOT,
                            specs=[dict(kind="vsmarket", date=night, rows=vsm, rec=rec)]))
    # 7б. Видео ночи — официальные клипы НХЛ (склейка хет-трика, голы в ОТ и в концовке): 11:00, 14:30, 17:30
    hl = D.get("highlights") or {}
    if hl.get("date") == rd and rd:
        vt = tgv(D, "videos", rd) or {}
        slots = [(11, 0), (14, 30), (17, 30)]
        for i, c in enumerate((hl.get("items") or [])[:3]):
            who = N.full(c["player"])
            g = next((g for g in A.get("games", []) if g.get("id") == c.get("game")), {})
            opp = (g.get("away") if g.get("home") == c.get("team") else g.get("home")) if g else None
            head_t = {"hattrick": f"Хет-трик: {who}", "ot_winner": f"Гол в овертайме: {who}",
                      "late_equalizer": f"Спасение в концовке: {who}", "russian_goal": f"Гол: {who}"}.get(c["kind"], who)
            body = vt.get(c["key"]) or {"hattrick": f"Все шайбы {N.last(c['player'])} в одном ролике — матч с «{RU_GEN.get(opp, opp)}».",
                                        "ot_winner": f"Победный гол в овертайме в матче с «{RU_GEN.get(opp, opp)}».",
                                        "late_equalizer": f"Сравнял счёт на {c['clips'][0].get('time')} третьего периода в матче с «{RU_GEN.get(opp, opp)}».",
                                        "russian_goal": f"Гол в матче с «{RU_GEN.get(opp, opp)}»."}.get(c["kind"], "")
            txt = f"<b>{e(head_t)}</b>\n\n{e(body)}\n\n<i>Видео: NHL</i>"
            hh, mm = slots[i]
            out.append(dict(key=c["key"], due=msk(rd, hh, mm) + dt.timedelta(days=1), expires=msk(rd, 23, 59) + dt.timedelta(days=1),
                            text=txt + FOOT, video=c, needs_tg=True))
    # 7в. Новости дня из ленты — очередь, которую пишет задача Claude (tg/news_queue.json)
    for q in (load(f"{TG}/news_queue.json", {}) or {}).get("items", []):
        if not q.get("id") or not q.get("text") or q.get("tg") is False:  # tg = false — только для сайта
            continue
        ready = dt.datetime.fromisoformat(str(q.get("ready") or q.get("time") or now_iso()).replace("Z", "+00:00"))
        # тихие часы ленты: с 23:00 до 08:00 по Москве новости ждут утра
        rm = ready.astimezone(MSK)
        if rm.hour >= 23:
            ready = msk((rm.date() + dt.timedelta(days=1)).isoformat(), 8, 0)
        elif rm.hour < 8:
            ready = msk(rm.date().isoformat(), 8, 0)
        txt = (f"<b>{e(q.get('title'))}</b>\n\n{e(q['text'])}\n\n<i>Фото: {e(q.get('source') or '')}</i>\n"
               f"<a href=\"{e(q.get('url'))}\">Источник: {e(q.get('source') or 'статья')}</a>")
        out.append(dict(key=f"feed:{q['id']}", due=ready, expires=ready + dt.timedelta(hours=10), text=txt + FOOT, photo=q.get("image"),
                        hot=bool(q.get("hot"))))
    # 8. Вечером передумали
    fin = D.get("final") or {}
    pf = p_final(D) if fin.get("t") else None
    if pf and ud:
        ft = dt.datetime.fromisoformat(fin["t"].replace("Z", "+00:00"))
        first = min((dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) for u in ups), default=ft + dt.timedelta(hours=3))
        out.append(dict(key=f"final:{ud}", due=ft, expires=first, text=pf[0], specs=pf[1]))
    if not day_complete(D, A, rd, box):
        out = [x for x in out if not x["key"].startswith(("am:", "stars:", "rus:", "modelweek:"))]
    return out


import re  # noqa: E402

FEED_CAP = 5  # новостей из ленты в день всего, включая горячие (решение Льва 17.10)
FEED_GAP = 75  # минут между новостями ленты


CONF = {"Atlantic": "E", "Metropolitan": "E", "Central": "W", "Pacific": "W"}


def season_rec(D, t):
    s = next((x for x in D.get("standings") or [] if x.get("abbr") == t), None)
    return f"{s['w']}-{s['l']}-{s['otl']}" if s else ""


def conf_place(D, t):
    """«5-е на Западе» — место в конференции по очкам, как в таблице сайта."""
    st = D.get("standings") or []
    me = next((x for x in st if x.get("abbr") == t), None)
    if not me or not me.get("gp"):
        return ""
    c = CONF.get(me.get("div"))
    rows = sorted([x for x in st if CONF.get(x.get("div")) == c], key=lambda x: (-x.get("pts", 0), x.get("gp", 0), -(x.get("gf", 0) - x.get("ga", 0))))
    i = next(k for k, x in enumerate(rows) if x["abbr"] == t) + 1
    return f"{i}-е на {'Западе' if c == 'W' else 'Востоке'}"


def leaders5(D, u, N):
    """Лучшие по очкам за последние 5 матчей у хозяев и гостей (gamecenter, data.preview)."""
    lp = (((D.get("preview") or {}).get(str(u["id"])) or {}).get("leaders_last5") or {}).get("points") or {}
    out = {}
    for s, k in (("home", "h"), ("away", "a")):
        x = lp.get(s) or {}
        if x.get("name") and x.get("value"):
            out[k] = dict(name=N.full(x["name"]), head_path=head_path(D, x["name"]), value=x["value"])
    return out if len(out) == 2 else {}




def vs_market_rows(ups, M):
    """Матчи, где модель спорит с рынком: другая сторона в исходе или в тотале (решение Льва 16.10 — только настоящий спор)."""
    mg = {x.get("id"): x for x in M.get("games") or []}
    rows = []
    for u in ups:
        m = mg.get(u["id"]) or {}
        v = m.get("verdict") or {}
        if m.get("mkt_home") is None:
            continue
        fav, mf = v.get("fav"), v.get("mkt_fav")
        pm, pk = m.get(f"p_{fav}"), m.get(f"mkt_{fav}")
        tm, tk = v.get("total") or {}, None
        kind, line = None, ""
        T = lambda side: RU.get(u[side])
        if fav and mf and fav != mf:
            kind = "исход"
            line = f"модель за «{T(fav)}» ({round(pm * 100)}%), рынок — за «{T(mf)}» ({round(m.get(f'mkt_{mf}') * 100)}%)"
        elif tm.get("side") and tm.get("mkt_side") and tm["side"] != tm["mkt_side"]:
            kind = "тотал"
            S = lambda x: "больше" if x == "over" else "меньше"
            line = f"тотал {num(tm.get('line'))}: модель за «{S(tm['side'])}» ({round((tm.get('p') or 0) * 100)}%), рынок — за «{S(tm['mkt_side'])}»"
        if kind:
            rows.append(dict(id=u["id"], home=u["home"], away=u["away"], kind=kind, line=line, p_home=m.get("p_home"), p_away=m.get("p_away"),
                             mkt_home=m.get("mkt_home"), mkt_away=m.get("mkt_away"), total=dict(tm, mkt_p=m.get("mkt_over") if tm.get("mkt_side") == "over" else (1 - m["mkt_over"]) if m.get("mkt_over") else None) if kind == "тотал" else None))
    order = {"исход": 0, "тотал": 1}
    return sorted(rows, key=lambda r: order[r["kind"]])[:3]


def vs_market_record(D):
    """Счёт сезона в спорах с рынком по журналу: (права модель, всего)."""
    J = [x for x in D.get("journal") or [] if x.get("type") in ("win", "total") and x.get("mkt_side") and x.get("side")
         and x["mkt_side"] != x["side"] and x.get("result") in ("hit", "miss")]
    return (sum(1 for x in J if x["result"] == "hit"), len(J)) if J else None


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
        rows.append(f"<b>{e(RU.get(u['home']))} — {e(RU.get(u['away']))}</b>: {e(new)}. Причина — {e(c.get('why') or 'вратари и поздняя линия')}.")
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
    if mode in ("auto", "feed"):
        fd = load(f"{TG}/feed.json", {}) or {}
        age = (now - dt.datetime.fromisoformat(fd["t"].replace("Z", "+00:00"))).total_seconds() / 60 if fd.get("t") else 999
        if mode == "feed" or age >= 110:  # лента круглосуточно: ночью её освежает пульс (режим feed) для новостей сайта
            sys.path.insert(0, os.path.join(ROOT, "scripts"))
            import media
            media.feed(LOG)
        if mode == "feed":
            return
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

    if mode == "texts":
        # для задачи правок: тексты всех постов текущего дня в HTML (ничего не постит, сеть не нужна)
        save(f"{TG}/post_texts.json", [dict(key=x["key"], message_id=(MSG.get(x["key"]) or [None])[0], text=x["text"]) for x in items])
        return

    cfg = load(f"{TG}/config.json", {}) or {}
    if mode == "discover" or not cfg.get("chat_id"):
        cfg = discover()
        if mode == "discover" or not cfg.get("chat_id"):
            return
    chat = cfg["chat_id"]

    def post(x):
        try:
            if x.get("video"):
                ids = send_video(chat, x["text"], x["video"])
            else:
                imgs = cards([s for s in x.get("specs") or [] if s], D) if x.get("specs") else []
                ids = send(chat, x["text"], images=imgs[:1], photo_url=None if imgs and imgs[0] else x.get("photo"))
            P[x["key"]] = LOG["t"]
            MSG[x["key"]] = ids
            if x.get("num_sig"):
                state["num_hist"] = (state.get("num_hist") or [])[-6:] + [x["num_sig"]]
            state["last_post"] = dt.datetime.now(dt.timezone.utc).isoformat()
            LOG["ok"].append(x["key"])
        except Exception as ex:
            LOG["fail"].append(f"{x['key']}: {ex}"[:300])

    if mode == "pin":
        # закреп: картинка tg/pin.png с подписью tg/pin.html, затем попытка закрепить
        try:
            txt = open(f"{TG}/pin.html", encoding="utf-8").read().strip()
            r = _call("sendPhoto", dict(chat_id=chat, caption=txt, parse_mode="HTML"), {"photo": f"{TG}/pin.png"})
            MSG["pin"] = [r["message_id"]]
            P["pin"] = LOG["t"]
            LOG["ok"].append(f"закреп отправлен: {r['message_id']}")
            try:
                _call("pinChatMessage", dict(chat_id=chat, message_id=r["message_id"], disable_notification="true"))
                LOG["ok"].append("закреплено")
            except Exception as ex:
                LOG["fail"].append(f"закрепить не вышло: {ex}"[:200])
        except Exception as ex:
            LOG["fail"].append(f"закреп: {ex}"[:300])
    elif mode == "recard":
        # перерисовать картинку и подпись у уже выложенных постов (editMessageMedia), arg — префиксы ключей через запятую
        pre = tuple(x for x in str(arg or "").split(",") if x)
        for x in items:
            if not pre or not x["key"].startswith(pre) or not MSG.get(x["key"]):
                continue
            if not x.get("specs"):
                # пост без нашей картинки (новость с фото из статьи) — правим только подпись
                try:
                    _call("editMessageCaption", dict(chat_id=chat, message_id=MSG[x["key"]][0], caption=x["text"], parse_mode="HTML"))
                    LOG["ok"].append(f"подпись обновлена {x['key']}")
                except Exception as ex:
                    try:
                        _call("editMessageText", dict(chat_id=chat, message_id=MSG[x["key"]][0], text=x["text"], parse_mode="HTML",
                                                      link_preview_options={"url": x.get("photo"), "prefer_large_media": True, "show_above_text": True} if x.get("photo") else {"is_disabled": True}))
                        LOG["ok"].append(f"текст обновлён {x['key']}")
                    except Exception as ex2:
                        LOG["fail"].append(f"{x['key']}: {ex} / {ex2}"[:300])
                continue
            try:
                img = cards(x["specs"][:1], D)[0]
                if not img:
                    raise RuntimeError("карточка не нарисовалась")
                vis = len(re.sub("<[^>]+>", "", html.unescape(x["text"])))
                media = dict(type="photo", media="attach://photo", **({"caption": x["text"], "parse_mode": "HTML"} if vis <= 1024 else {}))
                _call("editMessageMedia", dict(chat_id=chat, message_id=MSG[x["key"]][0], media=media), {"photo": img})
                LOG["ok"].append(f"обновлено {x['key']} ({MSG[x['key']][0]})")
            except Exception as ex:
                LOG["fail"].append(f"{x['key']}: {ex}"[:300])
    elif mode == "cleanup":
        for mid in [int(v) for v in str(arg or "").split(",") if v.strip().isdigit()]:
            try:
                _call("deleteMessage", dict(chat_id=chat, message_id=mid))
                LOG["ok"].append(f"удалено {mid}")
            except Exception as ex:
                LOG["fail"].append(f"{mid}: {ex}"[:120])
    elif mode == "test" and str(arg or "").startswith("only:"):
        # перевыложить только посты, чей ключ начинается с указанного префикса
        pref = str(arg)[5:]
        for x in [x for x in items if x["key"].startswith(pref)]:
            for mid in MSG.get(x["key"], []):
                try:
                    _call("deleteMessage", dict(chat_id=chat, message_id=mid))
                except Exception:
                    pass
            P.pop(x["key"], None)
            post(x)
    elif mode == "test":
        # удаляем прошлые версии тех же постов (и сообщения из arg: «2,3,4») и публикуем весь набор сразу
        for mid in [int(v) for v in str(arg or "").split(",") if v.strip().isdigit()]:
            try:
                _call("deleteMessage", dict(chat_id=chat, message_id=mid))
                LOG["ok"].append(f"удалено {mid}")
            except Exception as ex:
                LOG["fail"].append(f"удалить {mid}: {ex}"[:120])
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
        inbox(cfg, state, MSG)
        apply_edits(chat, MSG, cfg)
        if state.get("paused"):
            LOG["ok"].append("канал на паузе (/pause) — посты не выходят")
        last = state.get("last_post")
        gap = (now - dt.datetime.fromisoformat(last)).total_seconds() / 60 if last else 999
        tg_ready = (D.get("tg") or {}).get("date") == D.get("results_date")
        late = now.astimezone(MSK).hour * 60 + now.astimezone(MSK).minute >= 11 * 60 + 30
        due = [x for x in items if x["key"] not in P and x["due"] <= now and (not x.get("expires") or now < x["expires"])
               and (not x.get("needs_tg") or tg_ready or late)]
        # дневные посты, у которых прошло больше 8 часов от срока, не догоняем
        due = [x for x in due if x.get("expires") or (now - x["due"]).total_seconds() < 8 * 3600]
        # лента новостей (решение Льва 17.10): не больше FEED_CAP в день ВСЕГО, включая горячие; hot — только первыми в очереди;
        # между новостями ленты — не меньше FEED_GAP минут, чтобы утром после тихих часов не было залпа
        today = now.astimezone(MSK).date()
        feed_t = [dt.datetime.fromisoformat(v.replace("Z", "+00:00")) for k, v in P.items() if k.startswith("feed:")]
        fed = sum(1 for t in feed_t if t.astimezone(MSK).date() == today)
        feed_gap = min(((now - t).total_seconds() / 60 for t in feed_t), default=999)
        # Проверяем время отправки, а не только ready: дневная очередь могла задержаться до ночи.
        quiet = not 8 <= now.astimezone(MSK).hour < 23
        if quiet or fed >= FEED_CAP or feed_gap < FEED_GAP:
            due = [x for x in due if not x["key"].startswith("feed:")]
        due.sort(key=lambda x: (not x.get("hot"), x["due"]))
        if due and not state.get("paused"):
            x = due[0]
            if gap >= 20:
                post(x)
    cut = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    state["posted"] = {k: v for k, v in P.items() if v[:10] >= cut}
    state["messages"] = {k: v for k, v in MSG.items() if k in state["posted"]}
    save(f"{TG}/state.json", state)


# ---------------------------------------------------------------- пульт Льва в личке бота (решение 16.10)
def _admin_send(cfg, text):
    if cfg.get("admin_chat_id"):
        try:
            _call("sendMessage", dict(chat_id=cfg["admin_chat_id"], text=text, parse_mode="HTML", link_preview_options={"is_disabled": True}))
        except Exception as ex:
            LOG["fail"].append(f"ответ Льву: {ex}"[:150])


def inbox(cfg, state, MSG):
    """Личка бота: Лев пересылает кривой пост из канала с комментарием «что поправить» — заявка уходит в tg/edit_requests.json,
    её через час подхватывает задача Claude «Сводка НХЛ: правки канала». Команды: /pause, /resume, /status, /delete (ответом на пересланный пост)."""
    admin = cfg.get("admin_chat_id")
    if not admin:
        return
    try:
        ups = _call("getUpdates", dict(offset=state.get("upd_offset", 0), allowed_updates=["message"], timeout=0))
    except Exception as ex:
        LOG["fail"].append(f"личка бота: {ex}"[:150])
        return
    if not ups:
        return
    state["upd_offset"] = ups[-1]["update_id"] + 1
    msgs = [u["message"] for u in ups if (u.get("message") or {}).get("chat", {}).get("id") == admin]
    key_of = {v[0]: k for k, v in MSG.items() if v}
    req_p = f"{TG}/edit_requests.json"
    reqs = load(req_p, {"items": []}) or {"items": []}
    pending_fwd = None
    for i, m in enumerate(msgs):
        txt = (m.get("text") or m.get("caption") or "").strip()
        fo = m.get("forward_origin") or {}
        if fo.get("type") == "channel":
            mid = fo.get("message_id")
            # комментарий Telegram присылает отдельным сообщением рядом с пересланным
            note = ""
            for j in (i - 1, i + 1):
                if 0 <= j < len(msgs) and not msgs[j].get("forward_origin") and abs(msgs[j]["date"] - m["date"]) <= 120:
                    note = (msgs[j].get("text") or "").strip()
            pending_fwd = mid
            if note.lower().startswith(("/delete", "удали")):
                try:
                    _call("deleteMessage", dict(chat_id=cfg["chat_id"], message_id=mid))
                    _admin_send(cfg, f"Удалил пост {mid}.")
                except Exception as ex:
                    _admin_send(cfg, f"Не смог удалить {mid}: {html.escape(str(ex))[:200]}")
                continue
            reqs["items"].append(dict(message_id=mid, key=key_of.get(mid), note=note, text=txt[:4000],
                                      time=dt.datetime.fromtimestamp(m["date"], dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), status="new"))
            _admin_send(cfg, "Принял: " + (f"«{html.escape(note[:200])}»" if note else "без комментария — поправлю очевидное") +
                        ". Задача правок подхватит в течение часа и отредактирует пост на месте.")
        elif txt.startswith("/pause"):
            state["paused"] = True
            _admin_send(cfg, "Канал на паузе: новые посты не выходят. /resume — продолжить.")
        elif txt.startswith("/resume"):
            state["paused"] = False
            _admin_send(cfg, "Продолжаю публикации.")
        elif txt.startswith("/status"):
            today = dt.datetime.now(MSK).date()
            done = [k for k, v in (state.get("posted") or {}).items()
                    if dt.datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(MSK).date() == today]
            _admin_send(cfg, f"Сегодня вышло постов: {len(done)}" + (" · канал на паузе" if state.get("paused") else "") +
                        f"\nЗаявок на правку в работе: {sum(1 for r in reqs['items'] if r.get('status') == 'new')}")
        elif txt.startswith("/delete") and pending_fwd:
            try:
                _call("deleteMessage", dict(chat_id=cfg["chat_id"], message_id=pending_fwd))
                _admin_send(cfg, f"Удалил пост {pending_fwd}.")
            except Exception as ex:
                _admin_send(cfg, f"Не смог удалить: {html.escape(str(ex))[:200]}")
        elif txt and not any(x.get("forward_origin") and abs(m["date"] - x["date"]) <= 120 for x in msgs):
            _admin_send(cfg, "Чтобы поправить пост — перешли его сюда из канала и одним сообщением напиши, что не так. "
                             "Команды: /status, /pause, /resume; «удали» с пересланным постом — удалить.")
    reqs["items"] = reqs["items"][-50:]
    save(req_p, reqs)


def apply_edits(chat, MSG, cfg=None):
    """Готовые правки от задачи Claude (tg/edits.json: message_id, text — HTML поста целиком, status ready) — правим пост на месте."""
    p = f"{TG}/edits.json"
    ed = load(p, {"items": []}) or {"items": []}
    changed = False
    for x in ed.get("items", []):
        if x.get("status") != "ready":
            continue
        mid, text = x.get("message_id"), x.get("text") or ""
        try:
            try:
                _call("editMessageCaption", dict(chat_id=chat, message_id=mid, caption=text, parse_mode="HTML"))
            except Exception as ex:
                if "no caption" in str(ex).lower() or "there is no" in str(ex).lower():
                    _call("editMessageText", dict(chat_id=chat, message_id=mid, text=text, parse_mode="HTML"))
                elif "not modified" not in str(ex).lower():
                    raise
            x["status"] = "done"
            LOG["ok"].append(f"пост {mid} поправлен")
            if cfg:
                _admin_send(cfg, f"Поправил пост {mid}" + (f": {html.escape(x.get('summary', ''))[:300]}" if x.get("summary") else "."))
        except Exception as ex:
            x["status"] = "error"
            x["error"] = str(ex)[:200]
            LOG["fail"].append(f"правка {mid}: {ex}"[:200])
        changed = True
    if changed:
        ed["items"] = ed["items"][-50:]
        save(p, ed)


# ---------------------------------------------------------------- оповещения Льву о сбоях (решение 16.10)
def health(mode):
    """Проверки после каждого запуска канала; при сбое — сообщение в личку Льву (tg/config.json → admin_chat_id).
    Каждая проблема сообщается один раз в день (tg/state.json → alerts)."""
    cfg = load(f"{TG}/config.json", {}) or {}
    admin = cfg.get("admin_chat_id")
    if not admin or not TOKEN:
        return
    now = dt.datetime.now(dt.timezone.utc)
    m = now.astimezone(MSK)
    mins = m.hour * 60 + m.minute
    day = m.date().isoformat()
    D = load(f"{SITE}/data.json", {}) or {}
    state = load(f"{TG}/state.json", {}) or {}
    P = state.get("posted") or {}
    probs = []
    rd = D.get("results_date")
    complete = day_complete(D, load(f"{SITE}/archive.json", {}) or {}, rd, load(f"{SITE}/box.json", {}) or {})
    gen = str(D.get("generated") or "")
    # 1. Сбой workflow «Сводка НХЛ» (сбор данных, публикация сайта)
    try:
        ev = json.load(open(os.environ.get("GITHUB_EVENT_PATH", "")))
        wr = ev.get("workflow_run") or {}
        if wr.get("conclusion") in ("failure", "timed_out", "startup_failure"):
            probs.append((f"wf:{wr.get('id')}", f"Упал запуск «{wr.get('name')}» ({wr.get('display_title') or ''})", wr.get("html_url")))
    except Exception:
        pass
    # 2. Утренний сбор: к 09:40 мск данные сайта должны быть свежими
    if mins >= 9 * 60 + 40 and gen[:10] < (now - dt.timedelta(hours=6)).strftime("%Y-%m-%d"):
        probs.append(("am_fetch", f"Утренний сбор данных не прошёл: данные сайта от {gen[:16].replace('T', ' ')} UTC", None))
    f = D.get("fetch") or {}
    if f.get("fail") and str(f.get("t") or "")[:10] == now.strftime("%Y-%m-%d"):
        probs.append((f"fetch_fail:{f.get('t')}", "Сбор данных с ошибками: " + "; ".join(map(str, f["fail"]))[:500], None))
    # 3. Утренние тексты Sonnet: к 10:15 мск
    daily = D.get("daily") or {}
    if mins >= 10 * 60 + 15 and rd and complete and (daily.get("date") != rd or D.get("auto_texts")):
        probs.append(("am_texts", "Утренние тексты Claude (Sonnet) не вышли — на сайте запасные шаблоны", None))
    # 4. Подписи Opus для канала: к 10:45 мск
    if mins >= 10 * 60 + 45 and rd and complete and (D.get("tg") or {}).get("date") != rd:
        probs.append(("tg_texts", "Подписи Opus для канала не вышли — посты идут с запасными текстами", None))
    # 5. Утренний пост: к 10:30 мск должен выйти
    if mins >= 10 * 60 + 30 and rd and complete and any(g.get("date") == rd for g in (load(f"{SITE}/archive.json", {}) or {}).get("games", [])[-40:]) and f"am:{rd}" not in P:
        probs.append(("am_post", "Утренний пост «Итоги ночи» не вышел в канал", None))
    # 6. Ошибки самого канала в этом запуске
    for x in dict.fromkeys(LOG.get("fail") or []):  # без повторов
        if "картинка не ушла" in x or x.startswith(("лента ", "feed ")):
            continue
        probs.append((f"tg_fail:{hash(x[:120]) & 0xffffffff}", f"Канал ({mode}): {x}"[:600], None))
    seen = state.setdefault("alerts", {})
    new = [(k, t, u) for k, t, u in probs if seen.get(k) != day]
    if not new:
        return
    txt = "⚠️ <b>NHL-STATS: что-то пошло не так</b>\n\n" + "\n\n".join(f"• {html.escape(t)}" + (f"\n<a href=\"{u}\">подробнее</a>" if u else "") for k, t, u in new)
    try:
        _call("sendMessage", dict(chat_id=admin, text=txt, parse_mode="HTML", link_preview_options={"is_disabled": True}))
        for k, _, _ in new:
            seen[k] = day
        state["alerts"] = {k: v for k, v in seen.items() if v >= (m.date() - dt.timedelta(days=3)).isoformat()}
        save(f"{TG}/state.json", state)
        LOG["ok"].append(f"оповещение Льву: {len(new)}")
    except Exception as ex:
        LOG["fail"].append(f"оповещение: {ex}"[:200])


def admin_setup():
    """Режим admin: найти личный чат Льва с ботом (он пишет боту /start) и сохранить admin_chat_id."""
    cfg = load(f"{TG}/config.json", {}) or {}
    me = _call("getMe", {})
    LOG["ok"].append(f"бот: @{me.get('username')}")
    ups = _call("getUpdates", dict(allowed_updates=["message"]))
    priv = [u["message"]["chat"] for u in ups if (u.get("message") or {}).get("chat", {}).get("type") == "private"]
    if not priv:
        LOG["fail"].append(f"личных сообщений боту нет — напиши @{me.get('username')} /start и запусти режим admin снова")
        return
    c = priv[-1]
    cfg["admin_chat_id"] = c["id"]
    save(f"{TG}/config.json", cfg)
    _call("sendMessage", dict(chat_id=c["id"], text="Готово: сюда будут приходить оповещения NHL-STATS.RU, если что-то сломается."))
    LOG["ok"].append(f"оповещения: личный чат {c.get('first_name') or ''} сохранён")


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "auto"
    try:
        if m == "admin":
            admin_setup()
        else:
            main(m, sys.argv[2] if len(sys.argv) > 2 else None)
    except Exception as ex:
        import traceback
        LOG["fail"].append(traceback.format_exc()[-400:])
    try:
        if m in ("auto", "feed"):
            health(m)
    except Exception as ex:
        LOG["fail"].append(f"health: {ex!r}"[:200])
    save(f"{TG}/last.json", LOG)
    print(json.dumps(LOG, ensure_ascii=False))
