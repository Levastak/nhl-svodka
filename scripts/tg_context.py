"""Выжимка для задачи Opus «Сводка НХЛ: Telegram» (content/prompts/telegram.md) → tg/context.json.

Opus — самая дорогая модель, поэтому вместо шести больших файлов (data.json ~340 КБ, model, archive, box, edge, словарь)
он читает один файл только с тем, что нужно для подписей: ночь, звёзды, россияне по протоколам, видео, цифра дня,
новости, колонка, матчи вечера с предысторией и моделью, нужные строки таблицы и xG, русские имена всех упомянутых
игроков и вчерашние подписи (чтобы не повторяться). Запускается самой задачей первым шагом, сеть не нужна.
"""
import json
from game_day import day_complete, daily_ready
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
CONF = {"Atlantic": "E", "Metropolitan": "E", "Central": "W", "Pacific": "W"}


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def places(st):
    out = {}
    for c in ("E", "W"):
        rows = sorted([x for x in st if CONF.get(x.get("div")) == c], key=lambda x: (-x.get("pts", 0), x.get("gp", 0), -(x.get("gf", 0) - x.get("ga", 0))))
        for i, x in enumerate(rows):
            out[x["abbr"]] = f"{i + 1}-е на {'Западе' if c == 'W' else 'Востоке'}"
    return out


def prev_tg(cur_date):
    """Подписи прошлого дня: ищем в истории data.json версию, где tg.date другая."""
    try:
        hs = subprocess.run(["git", "log", "-n", "40", "--format=%H", "--", "site/data.json"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        for h in hs:
            r = subprocess.run(["git", "show", f"{h}:site/data.json"], cwd=ROOT, capture_output=True, text=True)
            try:
                tg = (json.loads(r.stdout).get("tg") or {})
            except Exception:
                continue
            if tg.get("date") and tg.get("date") != cur_date:
                return tg
    except Exception:
        pass
    return None


def main():
    D = load(f"{SITE}/data.json", {})
    M = load(f"{SITE}/model.json", {})
    A = load(f"{SITE}/archive.json", {"games": []})
    B = load(f"{SITE}/box.json", {}) or {}
    E = load(f"{SITE}/edge.json", {}) or {}
    NR = load(f"{SITE}/names_ru.json", {}) or {}
    rd, ud = D.get("results_date"), D.get("upcoming_date")
    st = D.get("standings") or []
    pl = places(st)
    srow = {x["abbr"]: dict(pts=x.get("pts"), gp=x.get("gp"), rec=f"{x.get('w')}-{x.get('l')}-{x.get('otl')}", l10=x.get("l10"),
                            streak=x.get("streak"), gf=x.get("gf"), ga=x.get("ga"), place=pl.get(x["abbr"])) for x in st}
    rus = {x.get("name") for x in D.get("russians") or []}

    # ночь: матчи results_date — голы из архива, в протоколах только отличившиеся и вратари
    box = {g.get("id"): g for g in (B.get("games") or [])} if B.get("date") == rd else {}
    night = []
    for g in A.get("games", []):
        if g.get("date") != rd:
            continue
        bx = box.get(g["id"]) or {}
        pls = [dict(name=p["name"], team=p["team"], pos=p.get("pos"), g=p.get("g"), a=p.get("a"), sog=p.get("sog"), toi=p.get("toi"),
                    saves=p.get("saves"), shots=p.get("shots"), russian=p["name"] in rus or None)
               for p in bx.get("players") or [] if (p.get("g") or 0) + (p.get("a") or 0) > 0 or (p.get("pos") == "G" and p.get("shots"))]
        night.append(dict(id=g["id"], home=g["home"], away=g["away"], score_home_away=f"{g['hs']}:{g['as']}", end=g.get("end"), sog_away_home=g.get("sog"),
                          goals=[dict(scorer=x[0], team=x[1], strength=x[2], period=x[3], time=x[4], assists=x[5]) for x in g.get("goals") or []],
                          players=[{k: v for k, v in p.items() if v is not None} for p in pls],
                          standings={t: srow.get(t) for t in (g["home"], g["away"])}))
    # россияне ночи по протоколам (все, включая без очков)
    rus_box = []
    for g in box.values():
        for p in g.get("players") or []:
            if p["name"] in rus:
                opp = g["home"] if p["team"] == g["away"] else g["away"]
                rus_box.append({k: v for k, v in dict(name=p["name"], team=p["team"], opp=opp, pos=p.get("pos"), g=p.get("g"), a=p.get("a"), pm=p.get("pm"),
                                                      sog=p.get("sog"), toi=p.get("toi"), saves=p.get("saves"), shots=p.get("shots")).items() if v is not None})
    # матчи вечера
    mg = {x.get("id"): x for x in M.get("games") or []}
    games = []
    for u in D.get("upcoming") or []:
        m = mg.get(u["id"]) or {}
        games.append(dict(id=u["id"], home=u["home"], away=u["away"], start=u["start"], motd=(D.get("motd") or {}).get("home") == u["home"] or None,
                          factors=u.get("factors"), pick=u.get("pick"), lean=u.get("lean"), total_pick=u.get("total_pick"), goalies=u.get("goalies"),
                          model={k: m.get(k) for k in ("p_home", "p_away", "mkt_home", "mkt_away", "rating_home", "rating_away", "lam_home", "lam_away",
                                                       "b2b_home", "b2b_away", "pacific_home", "new_coach_home", "new_coach_away", "inj_home", "inj_away",
                                                       "goalie_home", "goalie_away", "verdict") if m.get(k) not in (None, False, [])},
                          preview=(D.get("preview") or {}).get(str(u["id"])),
                          standings={t: srow.get(t) for t in (u["home"], u["away"])},
                          team_xg={t: (D.get("team_xg") or {}).get(t) for t in (u["home"], u["away"])},
                          injuries={t: ((D.get("teams") or {}).get(t) or {}).get("injuries") for t in (u["home"], u["away"])}))
    daily = D.get("daily") or {}
    arts = [dict(kind=a.get("kind"), kicker=a.get("kicker"), title=a.get("title"), dek=a.get("dek"), body=(a.get("body") or [])[:3]) for a in (D.get("articles") or [])[:1]]
    ctx = dict(
        note="Выжимка из site/data.json, model.json, archive.json, box.json, edge.json и names_ru.json для подписей канала. Счёт матчей ночи — хозяева первыми.",
        results_date=rd, upcoming_date=ud,
        fresh=dict(daily_date=daily.get("date"), auto_texts=bool(D.get("auto_texts")), tg_date=(D.get("tg") or {}).get("date"),
                   day_complete=day_complete(D, A, rd, B), daily_ready=daily_ready(D, A, B)),
        daily=daily, night=night, russians_box=rus_box, highlights=D.get("highlights"),
        edge=dict(data_date=E.get("data_date"), findings=(E.get("findings") or [])[:6]),
        news=[dict(title=n.get("title"), summary=n.get("summary"), url=n.get("url"), time=n.get("time"), body=(n.get("body") or [])[:2]) for n in D.get("news") or []],
        column=arts[0] if arts else None, motd=D.get("motd"), games=games,
        skater_xg={}, tg_prev=prev_tg(rd))
    # модель против рынка: те же матчи, что попадут в вечерний пост (tg.py vs_market_rows), и счёт сезона в таких спорах
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import tg as _tg
        ups = [u for u in D.get("upcoming") or [] if u.get("date") == ud]
        rows = _tg.vs_market_rows(ups, M)
        if rows:
            ctx["vs_market"] = dict(rows=rows, season_record=_tg.vs_market_record(D),
                                    note="kind: исход — модель и рынок за разные команды; тотал — за разные стороны тотала. Подробности матча — в games по id.")
    except Exception as ex:
        ctx["vs_market_error"] = repr(ex)[:200]
    # по понедельникам (results_date — воскресенье): честный счёт модели за неделю для tg.model_week
    import datetime as _dt
    W = load(f"{SITE}/weekly.json", {}) or {}
    if rd and W.get("to") == rd and _dt.date.fromisoformat(rd).weekday() == 6:
        ag = {g["id"]: g for g in A.get("games", [])}
        byteams = {(g["date"], g["home"], g["away"]): g for g in A.get("games", [])}
        J = [x for x in D.get("journal") or [] if W["from"] <= (x.get("date") or "") <= rd and x.get("type") in ("win", "total") and x.get("result") in ("hit", "miss")]
        miss = []
        for x in J:
            if x["result"] != "miss":
                continue
            g = byteams.get((x["date"], x["home"], x["away"])) or {}
            miss.append(dict(date=x["date"], home=x["home"], away=x["away"], type=x["type"], pick=x.get("pick"), side=x.get("side"), line=x.get("line"),
                             market_agreed=x.get("mkt_side") == x.get("side"), odds=x.get("odds"), score_home_away=f"{g.get('hs')}:{g.get('as')}" if g else None,
                             end=g.get("end"), sog_away_home=g.get("sog"), changed_evening=x.get("changed") or None))
        ctx["model_week"] = dict(window=[W["from"], rd], score=W.get("model"), misses=miss,
                                 note="score.vs_market: n — матчей, где модель спорила с рынком, model — сколько из них права модель")
    # xG и сезонная статистика — только по упомянутым игрокам
    blob = json.dumps(ctx, ensure_ascii=False)
    sk = {s["name"]: s for s in D.get("skaters") or []}
    for n, v in (D.get("skater_xg") or {}).items():
        if n in blob:
            s = sk.get(n) or {}
            ctx["skater_xg"][n] = dict(v, g=s.get("g"), a=s.get("a"), pts=s.get("pts"), season_gp=s.get("gp"))
    # русские имена: все латинские имена из выжимки (полные и фамилии из протоколов голов)
    blob = json.dumps(ctx, ensure_ascii=False)
    names = {}
    for lat, ru in NR.items():
        if lat in blob:
            names[lat] = ru
        else:
            last = lat.split(" ")[-1]
            if len(last) > 3 and re.search(r'"' + re.escape(last) + r'"', blob):
                names[lat] = ru
    ctx["names_ru"] = names
    out = os.path.join(ROOT, "tg", "context.json")
    json.dump(ctx, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"context.json: {os.path.getsize(out) // 1024} КБ, матчей ночи {len(night)}, вечера {len(games)}, россиян {len(rus_box)}, имён {len(names)}")


if __name__ == "__main__":
    main()
