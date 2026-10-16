"""NHL EDGE (трекинг лиги): сбор и «находки дня» для рубрик «Цифра дня» и «Под микроскопом».

Запускается из fetch.py в режиме am (и отдельно режимом edge). Пишет site/edge.json:
  t, night (дата игрового дня по США), top (топ-10 лиги), teams (по клубам), leaders (лидеры игроков и вратарей),
  findings — отсортированные находки с готовыми цифрами; тексты по ним пишет Claude, запасная строка line — для сайта.
Снимок кладётся в history/<день>_edge.json.gz.
Claude здесь не участвует: все числа считает скрипт.
"""
import datetime as dt
import gzip
import json
import os
import re

B = "https://api-web.nhle.com/v1/edge"
RU = {"ANA": "Анахайм", "BOS": "Бостон", "BUF": "Баффало", "CAR": "Каролина", "CBJ": "Коламбус", "CGY": "Калгари",
      "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Даллас", "DET": "Детройт", "EDM": "Эдмонтон", "FLA": "Флорида",
      "LAK": "Лос-Анджелес", "MIN": "Миннесота", "MTL": "Монреаль", "NJD": "Нью-Джерси", "NSH": "Нэшвилл",
      "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттава", "PHI": "Филадельфия", "PIT": "Питтсбург",
      "SEA": "Сиэтл", "SJS": "Сан-Хосе", "STL": "Сент-Луис", "TBL": "Тампа", "TOR": "Торонто", "UTA": "Юта",
      "VAN": "Ванкувер", "VGK": "Вегас", "WPG": "Виннипег", "WSH": "Вашингтон"}

# топ-10 лиги: ключ → (путь, поле значения, единица)
TOPS = {
    "speed": ("skater-speed-top-10/all/max/now", "maxSpeed", "км/ч"),
    "speed_D": ("skater-speed-top-10/D/max/now", "maxSpeed", "км/ч"),
    "shot": ("skater-shot-speed-top-10/all/max/now", "hardestShot", "км/ч"),
    "shot_F": ("skater-shot-speed-top-10/F/max/now", "hardestShot", "км/ч"),
    "dist": ("skater-distance-top-10/all/all/total/now", "distanceTotal", "км"),
    "ozone": ("skater-zone-time-top-10/all/all/offensive/now", "offensiveZoneTime", "%"),
    "ozone_D": ("skater-zone-time-top-10/D/all/offensive/now", "offensiveZoneTime", "%"),
}
TOP_RU = {"speed": "максимальная скорость", "speed_D": "максимальная скорость среди защитников",
          "shot": "самый сильный бросок", "shot_F": "самый сильный бросок среди нападающих",
          "dist": "пробег за сезон", "dist_game": "пробег за матч",
          "ozone": "доля времени в чужой зоне", "ozone_D": "доля времени в чужой зоне среди защитников"}


def _s(x):
    return x.get("default") if isinstance(x, dict) else x


def _num(v):
    if isinstance(v, dict):
        v = v.get("metric", v.get("value"))
    return v if isinstance(v, (int, float)) else None


def _player(p):
    p = p or {}
    t = p.get("team")
    pid = p.get("id")
    if not pid and p.get("slug"):
        m = re.search(r"(\d{7})$", p["slug"])
        pid = int(m.group(1)) if m else None
    return dict(name=f"{_s(p.get('firstName')) or ''} {_s(p.get('lastName')) or ''}".strip(), id=pid,
                team=(t.get("abbrev") if isinstance(t, dict) else t), pos=p.get("position"))


def _game(ov):
    ov = ov or {}
    a, h = ov.get("awayTeam") or {}, ov.get("homeTeam") or {}
    if not ov.get("gameDate"):
        return {}
    pd = ov.get("periodDescriptor") or {}
    return dict(date=ov.get("gameDate"), away=a.get("abbrev"), home=h.get("abbrev"),
                score=f"{a.get('score')}:{h.get('score')}" if a.get("score") is not None else None,
                period=pd.get("number"), time=ov.get("timeInPeriod"))


def team_ids(get):
    """id клубов НХЛ по аббревиатуре (у переехавших клубов берём самый новый id)."""
    j, _ = get("https://api.nhle.com/stats/rest/en/team", label="edge team ids")
    ids = {}
    for t in (j or {}).get("data", []):
        a = t.get("triCode")
        if a in RU and t.get("id", 0) > ids.get(a, 0):
            ids[a] = t["id"]
    return ids


def collect(get, LOG):
    out = dict(top={}, teams={}, leaders={})
    for key, (path, field, unit) in TOPS.items():
        j, _ = get(f"{B}/{path}", label=f"edge {key}")
        if not isinstance(j, list):
            continue
        rows = []
        for i, x in enumerate(j):
            v = x.get(field)
            r = dict(_player(x.get("player")), rank=i + 1, v=_num(v))
            if isinstance(v, dict) and v.get("overlay"):
                r["game"] = _game(v["overlay"])
            for k in ("burstsOver22", "bursts20To22", "shotAttemptsOver100", "shotAttempts90To100", "distancePer60"):
                if k in x:
                    r[k] = _num(x[k])
            if unit == "%" and r["v"] is not None:
                r["v"] = round(r["v"] * 100, 1)
            rows.append(r)
        out["top"][key] = rows
    for kind in ("skater", "goalie"):
        j, _ = get(f"{B}/{kind}-landing/now", label=f"edge {kind} landing")
        for k, v in ((j or {}).get("leaders") or {}).items():
            r = dict(_player(v.get("player")))
            for f in ("shotSpeed", "skatingSpeed", "distanceSkated", "sog", "zoneTime", "savePctg", "saves", "goalsAgainst", "games"):
                if f in v:
                    r["v"], r["field"] = _num(v[f]), f
            if v.get("overlay"):
                r["game"] = _game(v["overlay"])
            out["leaders"][f"{kind}:{k}"] = r
    ids = team_ids(get)
    for a, tid in sorted(ids.items()):
        d, _ = get(f"{B}/team-detail/{tid}/now", label=f"edge team {a}")
        c, _ = get(f"{B}/team-comparison/{tid}/now", label=f"edge comp {a}")
        if not d and not c:
            continue
        t = dict(id=tid)
        if d:
            tm = d.get("team") or {}
            t.update(gp=tm.get("gamesPlayed"), pts=tm.get("points"))
            ss, sk, ds = d.get("shotSpeed") or {}, d.get("skatingSpeed") or {}, d.get("distanceSkated") or {}
            t["shot_max"] = dict(v=_num(ss.get("topShotSpeed")), rank=(ss.get("topShotSpeed") or {}).get("rank"),
                                 avg=_num((ss.get("topShotSpeed") or {}).get("leagueAvg")))
            t["speed_max"] = dict(v=_num(sk.get("speedMax")), rank=(sk.get("speedMax") or {}).get("rank"),
                                  avg=_num((sk.get("speedMax") or {}).get("leagueAvg")))
            t["bursts22"] = dict(v=_num(sk.get("burstsOver22")), rank=(sk.get("burstsOver22") or {}).get("rank"))
            t["bursts20"] = dict(v=_num(sk.get("burstsOver20")), rank=(sk.get("burstsOver20") or {}).get("rank"),
                                 avg=_num((sk.get("burstsOver20") or {}).get("leagueAvg")))
            t["dist"] = dict(v=_num(ds.get("total")), rank=(ds.get("total") or {}).get("rank"), avg=_num((ds.get("total") or {}).get("leagueAvg")))
            t["sog"] = {x.get("locationCode"): dict(shots=x.get("shots"), shots_rank=x.get("shotsRank"), shots_avg=x.get("shotsLeagueAvg"),
                                                     pct=x.get("shootingPctg"), pct_rank=x.get("shootingPctgRank"), pct_avg=x.get("shootingPctgLeagueAvg"),
                                                     goals=x.get("goals"), goals_rank=x.get("goalsRank"))
                        for x in d.get("sogSummary") or []}
        if c:
            z = c.get("zoneTimeDetails") or {}
            t["zone"] = dict(off=z.get("offensiveZonePctg"), off_avg=z.get("offensiveZoneLeagueAvg"),
                             neu=z.get("neutralZonePctg"), deff=z.get("defensiveZonePctg"))
            t["games"] = [dict(date=g.get("gameDate"), home=g.get("isHomeTeam"),
                               opp=((g.get("awayTeam") if g.get("isHomeTeam") else g.get("homeTeam")) or {}).get("abbrev"),
                               km=round(_num(g.get("distanceSkated")) or 0, 1))
                          for g in c.get("skatingDistanceLast10") or []]
            t["shot_diff"] = (c.get("shotDifferential") or {}).get("shotAttemptDifferential")
        out["teams"][a] = t
    # места клубов по доле времени в чужой зоне считаем сами
    zs = sorted([(v["zone"]["off"], a) for a, v in out["teams"].items() if (v.get("zone") or {}).get("off") is not None], reverse=True)
    for i, (_, a) in enumerate(zs):
        out["teams"][a]["zone"]["off_rank"] = i + 1
    LOG["ok"].append(f"edge: топов {len(out['top'])}, клубов {len(out['teams'])}, лидеров {len(out['leaders'])}")
    return out


def _pct(x, n=1):
    return f"{x * 100:.{n}f}".replace(".", ",")


MON = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def ru_date(d):
    try:
        x = dt.date.fromisoformat(d)
        return f"{x.day} {MON[x.month - 1]}"
    except Exception:
        return d or ""


def _f(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


def findings(e, prev, night, russians, standings, names_ru, archive_games):
    """Находки: каждая — dict(kind, score 0–100, head, line, facts{…}, teams, players). Цифры — только отсюда."""
    out = []
    ru_name = lambda n: names_ru.get(n, n)
    rus = {r.get("name") for r in russians or []}
    st = {s["abbr"]: s for s in standings or []}
    played = {}  # клуб → даты матчей по архиву (для бэк-ту-бэков)
    for g in archive_games or []:
        for t in (g.get("away"), g.get("home")):
            played.setdefault(t, set()).add(g.get("date"))
    prev_top = {k: {r.get("id") for r in v} for k, v in ((prev or {}).get("top") or {}).items()}

    # 1. рекорды ночи: в топ-10 лиги попал момент вчерашнего матча
    for key, rows in (e.get("top") or {}).items():
        if key.startswith("dist") or key.startswith("ozone"):
            continue
        for r in rows:
            g = r.get("game") or {}
            if g.get("date") != night or r.get("v") is None:
                continue
            what = TOP_RU[key]
            sc = (92 if r["rank"] == 1 else 74 - r["rank"] * 2) - (6 if key.endswith(("_D", "_F")) else 0)
            line = (f"{_f(r['v'])} км/ч — {what}: {ru_name(r['name'])} («{RU.get(r['team'], r['team'])}»), {ru_date(night)}, "
                    + ("лучший результат сезона в лиге" if r["rank"] == 1 else f"{r['rank']}-е место в лиге за сезон")
                    + f", {g.get('period')}-й период, {g.get('time')}.")
            out.append(dict(kind="record_night", score=sc, head="Рекорд сезона" if r["rank"] == 1 else "В топ-10 сезона", line=line,
                            facts=dict(list=key, what=what, value=r["v"], unit="км/ч", rank=r["rank"], game=g,
                                       new_in_top=r.get("id") not in prev_top.get(key, set())),
                            teams=[r["team"]], players=[r["name"]]))

    # 2. пробег команд в матчах ночи против их нормы
    for a, t in (e.get("teams") or {}).items():
        gs = [g for g in t.get("games") or [] if g.get("km")]
        cur = [g for g in gs if g.get("date") == night]
        rest = [g["km"] for g in gs if g.get("date") != night]
        if not cur or len(rest) < 3:
            continue
        avg = sum(rest) / len(rest)
        dev = cur[0]["km"] / avg - 1
        if abs(dev) < 0.07:
            continue
        prevday = (dt.date.fromisoformat(night) - dt.timedelta(days=1)).isoformat()
        b2b = prevday in played.get(a, set())
        more = dev > 0
        line = (f"«{RU[a]}»: {_f(cur[0]['km'])} км пробега на всю команду в матче с «{RU.get(cur[0]['opp'], cur[0]['opp'])}» {ru_date(night)} — "
                f"на {_f(abs(dev) * 100, 0)}% {'больше' if more else 'меньше'} своей нормы ({_f(avg)} км)" + (", и это второй матч за два дня." if b2b else "."))
        out.append(dict(kind="team_distance", score=min(70, 40 + abs(dev) * 250) + (8 if b2b and not more else 0),
                        head="Пробег команды", line=line,
                        facts=dict(km=cur[0]["km"], norm=round(avg, 1), dev_pct=round(dev * 100, 1), opp=cur[0]["opp"], home=cur[0]["home"], b2b=b2b, games_in_norm=len(rest)),
                        teams=[a, cur[0]["opp"]], players=[]))

    # 3. давление без голов и голы без давления (время в чужой зоне против голов и реализации)
    teams = e.get("teams") or {}
    for a, t in teams.items():
        z, s = (t.get("zone") or {}), ((t.get("sog") or {}).get("all") or {})
        if not z.get("off_rank") or not s.get("pct_rank") or (t.get("gp") or 0) < 5:
            continue
        if z["off_rank"] <= 8 and s["pct_rank"] >= 24:
            out.append(dict(kind="pressure_no_goals", score=55 + (24 - z["off_rank"]),
                            head="Давят, но не забивают",
                            line=f"«{RU[a]}»: {z['off_rank']}-е место в лиге по времени в чужой зоне ({_pct(z['off'])}%), но по реализации бросков ({_pct(s['pct'])}%) — {s['pct_rank']}-е (в среднем по лиге {_pct(s['pct_avg'])}%).",
                            facts=dict(off=z["off"], off_rank=z["off_rank"], pct=s["pct"], pct_rank=s["pct_rank"], pct_avg=s["pct_avg"], gp=t.get("gp")),
                            teams=[a], players=[]))
        if s["pct_rank"] <= 3 and (s.get("shots_rank") or 0) >= 22:
            out.append(dict(kind="goals_no_shots", score=62 - s["pct_rank"],
                            head="Забивают без бросков",
                            line=f"«{RU[a]}»: реализация бросков {_pct(s['pct'])}% — {s['pct_rank']}-е место в лиге (в среднем {_pct(s['pct_avg'])}%), а по числу бросков — только {s['shots_rank']}-е.",
                            facts=dict(pct=s["pct"], pct_rank=s["pct_rank"], pct_avg=s["pct_avg"], shots=s.get("shots"), shots_rank=s.get("shots_rank"),
                                       long_pct=((t.get("sog") or {}).get("long") or {}).get("pct"), long_pct_avg=((t.get("sog") or {}).get("long") or {}).get("pct_avg"),
                                       pts=(st.get(a) or {}).get("pts"), gp=t.get("gp")),
                            teams=[a], players=[]))

    # 4. россияне в топ-10 лиги
    for key, rows in (e.get("top") or {}).items():
        for r in rows:
            if r["name"] not in rus or r.get("v") is None:
                continue
            new = r.get("id") not in prev_top.get(key, set())
            unit = TOPS[key][2]
            val = f"{_f(r['v'])}{'%' if unit == '%' else ' ' + unit}"
            out.append(dict(kind="russian_top", score=(48 if new else 30) + (11 - r["rank"]) * 2,
                            head="Россиянин в топе лиги",
                            line=f"{ru_name(r['name'])} («{RU.get(r['team'], r['team'])}») — {r['rank']}-й в лиге: {TOP_RU[key]}, {val}.",
                            facts=dict(list=key, what=TOP_RU[key], value=r["v"], unit=unit, rank=r["rank"], new_in_top=new, game=r.get("game")),
                            teams=[r["team"]], players=[r["name"]]))

    # 5. скорость: «вспышки» быстрее 22 миль/ч (35,4 км/ч) — у кого их больше всех
    sp = [r for r in (e.get("top") or {}).get("speed", []) if r.get("burstsOver22") is not None]
    if sp:
        r = max(sp, key=lambda x: x["burstsOver22"])
        out.append(dict(kind="bursts", score=34, head="Самый быстрый на дистанции",
                        line=f"{ru_name(r['name'])} («{RU.get(r['team'], r['team'])}») разгонялся быстрее 35 км/ч уже {r['burstsOver22']} раз — больше всех среди самых быстрых игроков лиги.",
                        facts=dict(bursts_over_35=r["burstsOver22"], max_speed=r["v"]), teams=[r["team"]], players=[r["name"]]))

    # 6. лидеры вратарей с опасных позиций (новый лидер — интереснее)
    for k in ("goalie:highDangerSavePctg", "goalie:highDangerSaves"):
        r = (e.get("leaders") or {}).get(k)
        if not r or r.get("v") is None:
            continue
        old = ((prev or {}).get("leaders") or {}).get(k) or {}
        new = old.get("id") != r.get("id")
        val = f"{_pct(r['v'])}%" if k.endswith("Pctg") else f"{r['v']}"
        what = "процент сейвов с опасных позиций" if k.endswith("Pctg") else "сейвов с опасных позиций"
        out.append(dict(kind="goalie_hd", score=40 if new else 22, head="Вратарь под обстрелом",
                        line=f"{ru_name(r['name'])} («{RU.get(r['team'], r['team'])}») — лучший в лиге: {what} — {val}.",
                        facts=dict(what=what, value=r["v"], new_leader=new), teams=[r["team"]], players=[r["name"]]))

    for x in out:
        f, k = x["facts"], x["kind"]
        if k in ("record_night", "russian_top"):
            u = f.get("unit")
            x["big"], x["unit"] = (_f(f["value"]), "%" if u == "%" else u)
            x["sub"] = f.get("what")
        elif k == "team_distance":
            x["big"], x["unit"], x["sub"] = _f(f["km"]), "км", f"пробег команды, норма {_f(f['norm'])} км"
        elif k == "pressure_no_goals":
            x["big"], x["unit"], x["sub"] = _pct(f["off"]), "%", "времени в чужой зоне"
        elif k == "goals_no_shots":
            x["big"], x["unit"], x["sub"] = _pct(f["pct"]), "%", "реализация бросков"
        elif k == "bursts":
            x["big"], x["unit"], x["sub"] = str(f["bursts_over_35"]), "", "разгонов быстрее 35 км/ч"
        elif k == "goalie_hd":
            pc = "процент" in f["what"]
            x["big"], x["unit"], x["sub"] = (_pct(f["value"]) if pc else str(f["value"])), ("%" if pc else ""), f["what"]
    out.sort(key=lambda x: -x["score"])
    # разнообразие: не больше двух находок одного вида и одна на игрока
    res, kinds, seen = [], {}, set()
    for x in out:
        pl = tuple(x.get("players") or [])
        if kinds.get(x["kind"], 0) >= 2 or (pl and pl in seen):
            continue
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
        if pl:
            seen.add(pl)
        x["score"] = round(x["score"])
        x["date"] = night
        res.append(x)
    return res[:10]


def run(get, LOG, SITE, ROOT, night):
    data = json.load(open(f"{SITE}/data.json", encoding="utf-8"))
    prev = {}
    try:
        prev = json.load(open(f"{SITE}/edge.json", encoding="utf-8"))
    except Exception:
        pass
    e = collect(get, LOG)
    if not e["top"] and not e["teams"]:
        LOG["fail"].append("edge: пусто")
        return
    try:
        names_ru = json.load(open(f"{SITE}/names_ru.json", encoding="utf-8"))
    except Exception:
        names_ru = {}
    try:
        games = json.load(open(f"{SITE}/archive.json", encoding="utf-8")).get("games", [])
    except Exception:
        games = []
    # EDGE отстаёт от результатов на 1–2 дня: «свежий» день — последний матч, который уже есть в трекинге
    dd = max([g.get("date") or "" for t in e["teams"].values() for g in t.get("games") or []] or [""]) or night
    # находки сравниваем со снимком, где трекинг был на прошлом дне, а не с повторным запуском на тех же данных
    base = prev.get("prev") if prev.get("data_date") == dd else prev
    e["findings"] = findings(e, base, dd, data.get("russians"), data.get("standings"), names_ru, games)
    e["t"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    e["night"], e["data_date"] = night, dd
    e["prev"] = {k: (base or {}).get(k) for k in ("top", "leaders", "data_date")} if base else None
    with open(f"{SITE}/edge.json", "w", encoding="utf-8") as fh:
        json.dump(e, fh, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(f"{ROOT}/history", exist_ok=True)
    snap = {k: v for k, v in e.items() if k != "prev"}
    with gzip.open(f"{ROOT}/history/{night}_edge.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, separators=(",", ":"))
    LOG["ok"].append(f"edge: находок {len(e['findings'])}")
