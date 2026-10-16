"""«Итоги недели»: цифры за последние 7 игровых дней для воскресной рубрики. Считает только скрипт.

Запускается из fetch.py в режиме am каждый день (дёшево, без сети). Пишет site/weekly.json:
  from, to — окно (даты игровых дней США), games — сколько матчей;
  teams — по клубам: результаты недели, очки, голы, место в конференции сейчас и неделю назад, сила модели сейчас и неделю назад;
  power — рейтинг силы модели с движением за неделю; players — лучшие по очкам за неделю (по голам и передачам из archive);
  goalies — вратари недели (по протоколам box.json, копятся в history/goalie_lines.json); russians — россияне недели;
  model — счёт прогнозов за неделю (исходы, тоталы, уверенный фаворит, модель против рынка); edge — движение мест по времени в чужой зоне.
"""
import datetime as dt
import glob
import gzip
import json
import os
import subprocess
import sys
import tempfile


def _load(p, d=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return d


def _res(g, t):
    """'W' / 'L' / 'OTL' для клуба t в матче g."""
    mine, other = (g["as"], g["hs"]) if g["away"] == t else (g["hs"], g["as"])
    if mine > other:
        return "W"
    return "OTL" if g.get("end") in ("OT", "SO") else "L"


def conf_ranks(standings):
    """Место в конференции по очкам (как в таблице сайта: очки, затем меньше игр)."""
    conf = {"Atlantic": "E", "Metropolitan": "E", "Central": "W", "Pacific": "W"}
    out = {}
    for c in ("E", "W"):
        rows = [s for s in standings or [] if conf.get(s.get("div")) == c]
        rows.sort(key=lambda s: (-s.get("pts", 0), s.get("gp", 0), -(s.get("gf", 0) - s.get("ga", 0))))
        for i, s in enumerate(rows):
            out[s["abbr"]] = i + 1
    return out


def power_then(ROOT, SITE, day_from, archive):
    """Сила клубов модели «неделю назад»: model.py на архиве до day_from и данных из снимка истории того дня."""
    snaps = sorted(glob.glob(f"{ROOT}/history/*_am.json.gz"))
    snap = None
    for p in snaps:
        d = os.path.basename(p)[:10]
        if d <= day_from:
            snap = p
    data = _load(f"{SITE}/data.json", {})
    approx = True
    if snap:
        try:
            s = json.load(gzip.open(snap, "rt", encoding="utf-8"))
            for k, v in (s.get("data") or {}).items():
                if v is not None:
                    data[k] = v
            approx = os.path.basename(snap)[:10] != day_from
        except Exception:
            pass
    arc = dict(archive, games=[g for g in archive.get("games", []) if g.get("date", "") < day_from])
    if len(arc["games"]) < 32:
        return {}, True, None
    with tempfile.TemporaryDirectory() as td:
        ap, dp = os.path.join(td, "a.json"), os.path.join(td, "d.json")
        json.dump(arc, open(ap, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(data, open(dp, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run([sys.executable, f"{ROOT}/scripts/model.py", ap, dp, f"{ROOT}/scripts/prior.json"],
                           capture_output=True, text=True, timeout=120)
        try:
            m = json.loads(r.stdout)
        except Exception:
            return {}, True, None
    return {a: t.get("power") for a, t in (m.get("teams") or {}).items()}, approx, (os.path.basename(snap)[:10] if snap else None)


def goalie_lines(ROOT, SITE):
    """Копим строки вратарей из протоколов (box.json) за 21 день: в архиве их нет."""
    p = f"{ROOT}/history/goalie_lines.json"
    lines = _load(p, {})
    box = _load(f"{SITE}/box.json", {}) or {}
    day = box.get("date")
    if day:
        rows = []
        for g in box.get("games") or []:
            for x in g.get("players") or []:
                if x.get("pos") == "G" and (x.get("shots") or 0) > 0:
                    rows.append(dict(name=x["name"], team=x["team"], gid=g.get("id"), saves=x.get("saves", 0), shots=x.get("shots", 0),
                                     ga=x.get("ga", 0), toi=x.get("toi")))
        if rows:
            lines[day] = rows
    keep = sorted(lines)[-21:]
    lines = {k: lines[k] for k in keep}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(lines, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return lines


def run(LOG, SITE, ROOT):
    data = _load(f"{SITE}/data.json", {})
    archive = _load(f"{SITE}/archive.json", {"games": []})
    model = _load(f"{SITE}/model.json", {})
    games_all = [g for g in archive.get("games", []) if g.get("as") is not None]
    if not games_all:
        return
    last = data.get("results_date") or max(g["date"] for g in games_all)
    d_to = dt.date.fromisoformat(last)
    d_from = (d_to - dt.timedelta(days=6)).isoformat()
    wk = [g for g in games_all if d_from <= g["date"] <= last]
    out = dict(t=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **{"from": d_from, "to": last}, games=len(wk))

    # клубы: результаты недели
    teams = {}
    for g in wk:
        for t in (g["away"], g["home"]):
            r = teams.setdefault(t, dict(gp=0, w=0, l=0, otl=0, pts=0, gf=0, ga=0, games=[]))
            res = _res(g, t)
            gf, ga = (g["as"], g["hs"]) if g["away"] == t else (g["hs"], g["as"])
            r["gp"] += 1
            r["w" if res == "W" else "l" if res == "L" else "otl"] += 1
            r["pts"] += 2 if res == "W" else 1 if res == "OTL" else 0
            r["gf"] += gf
            r["ga"] += ga
            r["games"].append(dict(date=g["date"], opp=g["home"] if g["away"] == t else g["away"], home=g["home"] == t,
                                   score=f"{gf}:{ga}", res=res, end=g.get("end")))
    rank_now = conf_ranks(data.get("standings"))
    # место неделю назад — по таблице из снимка истории на начало окна
    rank_then, snap_day = {}, None
    for p in sorted(glob.glob(f"{ROOT}/history/*_am.json.gz")):
        if os.path.basename(p)[:10] <= d_from:
            snap_day = p
    if snap_day:
        try:
            rank_then = conf_ranks((json.load(gzip.open(snap_day, "rt", encoding="utf-8")).get("data") or {}).get("standings"))
        except Exception:
            pass
    p_now = {a: t.get("power") for a, t in (model.get("teams") or {}).items()}
    p_then, approx, p_snap = power_then(ROOT, SITE, d_from, archive)
    for a in set(p_now) | set(teams):
        r = teams.setdefault(a, dict(gp=0, w=0, l=0, otl=0, pts=0, gf=0, ga=0, games=[]))
        r.update(rank=rank_now.get(a), rank_then=rank_then.get(a), power=p_now.get(a), power_then=p_then.get(a))
    out["teams"] = teams
    pw = sorted([(v, a) for a, v in p_now.items() if v is not None], reverse=True)
    pw_then = {a: i + 1 for i, (v, a) in enumerate(sorted([(v, a) for a, v in p_then.items() if v is not None], reverse=True))}
    out["power"] = [dict(abbr=a, place=i + 1, index=round(v * 100), place_then=pw_then.get(a),
                         index_then=round(p_then[a] * 100) if p_then.get(a) else None) for i, (v, a) in enumerate(pw)]
    out["power_note"] = dict(then_from_snapshot=p_snap, approx=approx)

    # игроки недели по голам и передачам из протоколов голов архива
    idname = {}
    for n, h in (data.get("heads") or {}).items():
        pid = str(h).split("/")[-1]
        if pid:
            idname[pid] = n
    pl = {}
    for g in wk:
        for x in g.get("goals") or []:
            team = x[1]
            ids = [(str(x[6]) if len(x) > 6 and x[6] else None, "g")]
            if len(x) > 7 and x[7]:
                ids += [(i.strip(), "a") for i in str(x[7]).split(",") if i.strip()]
            for pid, k in ids:
                if not pid:
                    continue
                r = pl.setdefault(pid, dict(id=int(pid), name=idname.get(pid), team=team, g=0, a=0, gp=set()))
                r[k] += 1
                r["gp"].add(g["id"])
    rows = []
    for r in pl.values():
        r["pts"] = r["g"] + r["a"]
        r["gp_pts"] = len(r.pop("gp"))  # матчей с очками
        rows.append(r)
    rows.sort(key=lambda r: (-r["pts"], -r["g"], r["name"] or ""))
    out["players"] = rows[:15]
    rus = {x.get("name") for x in data.get("russians") or []}
    out["russians"] = [r for r in rows if r.get("name") in rus][:10]

    # вратари недели — по протоколам
    gl = goalie_lines(ROOT, SITE)
    gk = {}
    for day, lst in gl.items():
        if not (d_from <= day <= last):
            continue
        for x in lst:
            r = gk.setdefault(x["name"], dict(name=x["name"], team=x["team"], gp=0, saves=0, shots=0, ga=0, so=0))
            r["gp"] += 1
            r["saves"] += x["saves"]
            r["shots"] += x["shots"]
            r["ga"] += x["ga"]
            r["so"] += 1 if x["ga"] == 0 and x["shots"] >= 15 else 0
    gks = [dict(r, sv=round(r["saves"] / r["shots"], 3)) for r in gk.values() if r["shots"] >= 40]
    gks.sort(key=lambda r: (-r["sv"], -r["shots"]))
    out["goalies"] = gks[:8]
    out["goalies_days"] = sorted(d for d in gl if d_from <= d <= last)

    # модель за неделю
    J = [x for x in data.get("journal") or [] if d_from <= (x.get("date") or "") <= last and x.get("result") in ("hit", "miss")]
    sc = {}
    for t in ("win", "total", "sure", "express"):
        jj = [x for x in J if (x.get("type") or "win") == t and not x.get("cancelled")]
        if jj:
            hit = sum(1 for x in jj if x["result"] == "hit")
            odds = [x for x in jj if x.get("odds")]
            roi = sum((x["odds"] - 1) if x["result"] == "hit" else -1 for x in odds) / len(odds) if odds else None
            sc[t] = dict(n=len(jj), hit=hit, roi=round(roi, 3) if roi is not None else None)
    dis = [x for x in J if x.get("mkt_side") and x.get("side") and x["mkt_side"] != x["side"] and (x.get("type") or "win") in ("win", "total")]
    sc["vs_market"] = dict(n=len(dis), model=sum(1 for x in dis if x["result"] == "hit"))
    out["model"] = sc

    # EDGE: движение мест по времени в чужой зоне за неделю (если есть снимок недельной давности)
    e_now = _load(f"{SITE}/edge.json", {}) or {}
    e_then, e_day = None, None
    for p in sorted(glob.glob(f"{ROOT}/history/*_edge.json.gz")):
        if os.path.basename(p)[:10] <= d_from:
            e_day = p
    if e_day:
        try:
            e_then = json.load(gzip.open(e_day, "rt", encoding="utf-8"))
        except Exception:
            e_then = None
    if e_now.get("teams") and e_then and e_then.get("teams"):
        mv = []
        for a, t in e_now["teams"].items():
            r0 = ((e_then["teams"].get(a) or {}).get("zone") or {}).get("off_rank")
            r1 = (t.get("zone") or {}).get("off_rank")
            if r0 and r1 and abs(r0 - r1) >= 5:
                mv.append(dict(abbr=a, off_rank=r1, off_rank_then=r0, off=(t.get("zone") or {}).get("off")))
        out["edge"] = sorted(mv, key=lambda x: -abs(x["off_rank"] - x["off_rank_then"]))[:6]

    with open(f"{SITE}/weekly.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    LOG["ok"].append(f"weekly: {d_from}…{last}, матчей {len(wk)}, сила неделю назад {'по снимку ' + p_snap if p_snap else 'нет'}")
