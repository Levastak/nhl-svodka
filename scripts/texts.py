"""Тексты без ИИ: вечерний финальный прогноз и запасной утренний режим.

final(data, model)        — вечером после сбора pm: финальные прогнозы модели на матчи вечера,
                            поздние кэфы в журнал, пометки «Вечером передумали», data.final.
fallback(data, model, archive, box) — если утренние тексты Claude не вышли: итоги матчей,
                            звёзды и антигерои, превью и прогнозы, уверенные исходы, матч дня,
                            разборы модели и журнал — по шаблонам из данных.
Тексты Claude всегда главнее: fallback ничего не трогает, если утренние тексты уже есть.
"""
import datetime as dt
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

RU = {"ANA": "Анахайм", "BOS": "Бостон", "BUF": "Баффало", "CAR": "Каролина", "CBJ": "Коламбус", "CGY": "Калгари",
      "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Даллас", "DET": "Детройт", "EDM": "Эдмонтон", "FLA": "Флорида",
      "LAK": "Лос-Анджелес", "MIN": "Миннесота", "MTL": "Монреаль", "NJD": "Нью-Джерси", "NSH": "Нэшвилл",
      "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттава", "PHI": "Филадельфия", "PIT": "Питтсбург",
      "SEA": "Сиэтл", "SJS": "Сан-Хосе", "STL": "Сент-Луис", "TBL": "Тампа", "TOR": "Торонто", "UTA": "Юта",
      "VAN": "Ванкувер", "VGK": "Вегас", "WPG": "Виннипег", "WSH": "Вашингтон"}

_NAMES = None


def q(t):
    return f"«{RU.get(t, t)}»"


def names():
    global _NAMES
    if _NAMES is None:
        try:
            _NAMES = json.load(open(os.path.join(SITE, "names_ru.json"), encoding="utf-8"))
        except Exception:
            _NAMES = {}
    return _NAMES


def ru(full):
    """Полное имя латиницей → фамилия по-русски (без латиницы в текстах)."""
    full = str(full or "").split(" (")[0].strip()
    r = names().get(full)
    if r:
        return r.split(" ", 1)[-1]
    for k, v in names().items():          # фамилия из протокола («Tkachuk») — берём, только если однозначно
        if k.split(" ")[-1] == full:
            return v.split(" ", 1)[-1]
    return full


def sg(n):
    return f"+{n}" if n > 0 else (f"−{-n}" if n < 0 else "0")


def pct(x):
    return f"{round(x * 100)}%"


def num(x):
    return str(x).replace(".", ",")


def now():
    return dt.datetime.now(dt.timezone.utc)


def iso():
    return now().strftime("%Y-%m-%dT%H:%M:%SZ")


def started(u):
    return dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) <= now()


def line_s(x):
    return str(int(x)) if float(x) == int(float(x)) else num(x)


def goalie_line(u):
    gs = u.get("goalies") or []
    if len(gs) != 2:
        return None
    out = []
    for g in gs:
        nm = str(g).split(" (")[0]
        st = "подтверждён" if "подтв.)" in str(g) and "не подтв" not in str(g) else "ожидается"
        out.append(f"{ru(nm)} ({st})" if nm and nm != "не объявлен" else "не объявлен")
    return f"Вратари: {out[0]} — {out[1]}."


def side_p(g, side):
    return g["p_home"] if side == "home" else g["p_away"]


def tot_p(g, side):
    return g["p_over"] if side == "over" else g["p_under"]


def mkt_p(g, side):
    k = "mkt_home" if side == "home" else "mkt_away"
    return g.get(k)


# ------------------------------------------------------------------ тексты прогноза одного матча
def lean_text(u, g):
    v = g["verdict"]
    fav, mf = v["fav"], v.get("mkt_fav")
    pick = u[fav]
    s = f"Модель за {q(pick)} ({pct(side_p(g, fav))})"
    if mf and g.get("mkt_home") is not None:
        if v.get("vs_market"):
            return f"Рынок за {q(u[mf])} ({pct(mkt_p(g, mf))}), модель — за {q(pick)} ({pct(side_p(g, fav))}). " + why(u, g, fav)
        return s + f", рынок согласен ({pct(mkt_p(g, fav))}). " + why(u, g, fav)
    return s + ". " + why(u, g, fav)


def why(u, g, fav):
    other = "away" if fav == "home" else "home"
    bits = []
    if g.get(f"b2b_{other}") and not g.get(f"b2b_{fav}"):
        bits.append(f"{q(u[other])} играет второй день подряд")
    ra, rb = g.get(f"rating_{fav}") or {}, g.get(f"rating_{other}") or {}
    if ra and rb and ra.get("att", 1) - rb.get("att", 1) >= 0.05:
        bits.append(f"{q(u[fav])} сильнее в атаке")
    if ra and rb and rb.get("dfn", 1) - ra.get("dfn", 1) >= 0.05:
        bits.append(f"{q(u[other])} слабее в обороне")
    if g.get(f"inj_{other}") and not g.get(f"inj_{fav}"):
        bits.append(f"{q(u[other])} без части ключевых игроков")
    if fav == "home" and not bits:
        bits.append("своя площадка")
    return ("Главное: " + ", ".join(bits[:2]) + ".") if bits else ""


def total_lean(g):
    v = g["verdict"]["total"]
    side, p = v["side"], tot_p(g, v["side"])
    word = "больше" if side == "over" else "меньше"
    exp = num(round(g.get("exp_total", 0), 1))
    if v.get("mkt_side") and v.get("vs_market"):
        mw = "больше" if v["mkt_side"] == "over" else "меньше"
        return f"Рынок ждёт {mw}, модель — {word} ({pct(p)}): по её расчёту в матче около {exp} гола."
    return f"Модель за «{word}» ({pct(p)}), ожидает около {exp} гола" + (", рынок согласен." if v.get("mkt_side") else ".")


def factors(u, g, data, archive):
    f = []
    for side in ("away", "home"):
        t = u[side]
        frm = form(t, archive)
        if frm:
            f.append(f"{q(t)}: {frm}.")
    for side in ("away", "home"):
        if g.get(f"b2b_{side}"):
            f.append(f"{q(u[side])} играет второй день подряд.")
    inj = [ru(i["name"]) for s in ("away", "home") for i in (g.get(f"inj_{s}") or [])]
    inj = [x for x in inj if not re.search(r"[A-Za-z]", x)]
    if inj:
        f.append("Не сыграют: " + ", ".join(inj[:4]) + ".")
    gl = goalie_line(u)
    if gl:
        f.append(gl)
    ts = data.get("team_stats") or {}
    a, h = ts.get(u["away"]) or {}, ts.get(u["home"]) or {}
    if a.get("pp_pct") is not None and h.get("pp_pct") is not None and len(f) < 5:
        f.append(f"Большинство: {q(u['away'])} {num(a['pp_pct'])}%, {q(u['home'])} {num(h['pp_pct'])}%.")
    return f[:5]


def form(t, archive):
    gs = [g for g in archive.get("games", []) if t in (g["away"], g["home"])]
    gs = sorted(gs, key=lambda g: g["date"])[-5:]
    if not gs:
        return ""
    w = sum(1 for g in gs if (g["hs"] > g["as"]) == (g["home"] == t))
    gf = sum(g["hs"] if g["home"] == t else g["as"] for g in gs)
    ga = sum(g["as"] if g["home"] == t else g["hs"] for g in gs)
    return f"побед — {w} из {len(gs)} последних, голы {gf}:{ga}"


def model_paras(u, g):
    v = g["verdict"]
    fav = v["fav"]
    ra, rh = g.get("rating_away") or {}, g.get("rating_home") or {}
    r = lambda x: round(x * 100)
    p1 = (f"Атака гостей, {q(u['away'])}, — {r(ra.get('att', 1))}, хозяев, {q(u['home'])}, — {r(rh.get('att', 1))}; "
          f"оборона — {r(ra.get('dfn', 1))} и {r(rh.get('dfn', 1))} (100 — средний уровень лиги; у атаки больше — лучше, "
          f"у обороны меньше — лучше). Модель ждёт {num(g['lam_away'])} гола гостей и {num(g['lam_home'])} гола хозяев.")
    extra = []
    for s in ("away", "home"):
        if g.get(f"b2b_{s}"):
            extra.append(f"{q(u[s])} играет второй день подряд — модель снимает за это часть сил")
    if g.get("pacific_home"):
        extra.append("хозяевам с тихоокеанского побережья добавлена небольшая прибавка")
    if extra:
        p1 += " " + "; ".join(extra).capitalize() + "."
    lf = "home" if g["lam_home"] > g["lam_away"] else "away"
    if lf != fav and abs(g.get("shares_adj") or 0) >= 0.05:
        p1 += (f" По ожидаемым голам чуть впереди {q(u[lf])}, но поправка на игру в равных составах "
               f"(доли бросков и опасных моментов 5 на 5) переворачивает оценку.")
    p1 += f" Итог — {q(u[fav])}, {pct(side_p(g, fav))}."
    tv = v["total"]
    word = "больше" if tv["side"] == "over" else "меньше"
    if g.get("mkt_home") is not None:
        p2 = f"Рынок даёт фавориту модели, {q(u[fav])}, {pct(mkt_p(g, fav))}: " + \
             ("модель против рынка — фаворит линии другой." if v.get("vs_market") else "модель с рынком согласна.")
        if tv.get("mkt_side"):
            p2 += f" По тоталу {line_s(tv['line'])} модель за «{word}» ({pct(tot_p(g, tv['side']))})" + \
                  (", рынок — за другую сторону." if tv.get("vs_market") else ", рынок тоже.")
    else:
        p2 = f"Линии на матч пока нет. По тоталу модель склоняется к «{word}» ({pct(tot_p(g, tv['side']))})."
    p2 += f" Прогноз модели: {q(u[fav])} и «{word} {line_s(tv['line'])}»."
    return [p1, p2]


def journal_add(data, u, g, date):
    J = data.setdefault("journal", [])
    have = {(j.get("date"), j.get("type"), j.get("away"), j.get("home")) for j in J}
    v, o = g["verdict"], u.get("odds") or {}
    fav, ts = v["fav"], v["total"]["side"]
    if (date, "win", u["away"], u["home"]) not in have:
        j = dict(date=date, type="win", away=u["away"], home=u["home"], pick=u[fav], side=fav, odds=o.get(fav),
                 src="Линия 1", result=None, score=None)
        if v.get("mkt_fav") and o:
            j["mkt_side"] = v["mkt_fav"]
        J.append(j)
    if o.get("total") is not None and (date, "total", u["away"], u["home"]) not in have:
        j = dict(date=date, type="total", away=u["away"], home=u["home"], pick=("ТБ " if ts == "over" else "ТМ ") + str(o["total"]).replace(".0", ""),
                 line=o["total"], side=ts, odds=o.get(ts), src="Линия 1", result=None, score=None)
        if v["total"].get("mkt_side"):
            j["mkt_side"] = v["total"]["mkt_side"]
        J.append(j)


def sure_journal(data, model, evening=False):
    """«Уверенный фаворит» (model.py п. 17): запись до матча, ставка — победа с ОТ на команду модели.
    Утром — новые сигналы; вечером (поздняя линия) — новые записываются, у записанных обновляется кэф,
    пропавшие снимаются (result=void, cancelled). Начавшиеся и сыгранные матчи не трогаются."""
    M = {g["id"]: g for g in model.get("games", [])}
    J = data.setdefault("journal", [])
    date = data.get("upcoming_date"); n = 0
    for u in data.get("upcoming", []):
        g = M.get(u["id"])
        if not g or started(u):
            continue
        s = (g.get("verdict") or {}).get("sure"); o = u.get("odds") or {}
        cur = next((j for j in J if j.get("type") == "sure" and j.get("date") == date and j.get("away") == u["away"]
                    and j.get("home") == u["home"]), None)
        if cur and cur.get("result") is not None and not cur.get("cancelled"):
            continue
        if s:
            rec = dict(pick=u[s["side"]], side=s["side"], odds=o.get(s["side"]) or s.get("odds"), p=s["p"], mkt=s["mkt"], edge=s["edge"])
            if not cur:
                J.append(dict(date=date, type="sure", away=u["away"], home=u["home"], src="Линия 1", result=None, score=None, **rec)); n += 1
            else:
                if cur.get("cancelled"):
                    cur.pop("cancelled", None); cur["result"] = None
                if cur.get("side") != s["side"]:
                    cur.update(pick_am=cur.get("pick"), side_am=cur.get("side"), changed=True)
                cur.update(rec); n += 1
                if evening: cur["odds_late"], cur["final"] = rec["odds"], True
        elif cur and evening and cur.get("result") is None:
            cur.update(result="void", cancelled=True, final=True)
    return n


def express(data, M, games):
    legs = []
    for u in games:
        g = M.get(u["id"])
        if not g or not u.get("odds"):
            continue
        s = g["verdict"]["fav"]
        if side_p(g, s) >= 0.60 and u["odds"].get(s):
            legs.append((side_p(g, s), dict(away=u["away"], home=u["home"], pick=u[s], side=s, odds=u["odds"][s])))
    legs = [l for _, l in sorted(legs, key=lambda x: -x[0])[:3]]
    if len(legs) < 2:
        return None
    od = round(math.prod(l["odds"] for l in legs), 2)
    names_ = ", ".join(f"{q(l['pick'])} ({pct(side_p(M[[u['id'] for u in games if u['away']==l['away'] and u['home']==l['home']][0]], l['side']))})" for l in legs)
    return dict(date=data.get("upcoming_date"), legs=legs, odds=od, src="Линия 1",
                lean=f"Самые уверенные оценки модели на сегодня: {names_}.")


# ------------------------------------------------------------------ вечер
def final(data, model):
    M = {g["id"]: g for g in model.get("games", [])}
    date = data.get("upcoming_date")
    pending = [u for u in data.get("upcoming", []) if not started(u) and u["id"] in M]
    changed = []
    tab = data.setdefault("model_tab", {}).setdefault("games", {})
    for u in pending:
        g = M[u["id"]]
        v = g["verdict"]
        fav, ts = v["fav"], v["total"]["side"]
        o = u.get("odds") or {}
        note = []
        if u.get("goalie_changed"):
            note.append("сменился вратарь")
        if not u.get("pick_side"):                        # утренних текстов не было
            u["pick"], u["pick_side"], u["lean"] = u[fav], fav, lean_text(u, g)
        elif u["pick_side"] != fav:
            u["pick_am"], u["pick_side_am"] = u["pick"], u["pick_side"]
            if u.get("total_pick"):
                u["total_pick_am"] = dict(u["total_pick"])
            why_ = ", ".join(note) or "поздние составы, вратари и линия сдвинули оценку"
            u["pick"], u["pick_side"], u["pick_changed"] = u[fav], fav, True
            u["lean"] = f"Вечером передумали: {why_}. Теперь модель за {q(u[fav])} ({pct(side_p(g, fav))})" + \
                        (f", рынок — за {q(u[v['mkt_fav']])}." if v.get("vs_market") else ", рынок согласен.")
            changed.append(dict(id=u["id"], what="исход", **{"from": u["pick_am"], "to": u[fav], "why": why_}))
        tp = u.get("total_pick")
        if o.get("total") is not None:
            if not tp:
                u["total_pick"] = dict(side=ts, line=o["total"], odds=o.get(ts), lean=total_lean(g))
            elif tp.get("side") != ts:
                u.setdefault("total_pick_am", dict(tp))
                u["total_pick"] = dict(side=ts, line=o["total"], odds=o.get(ts), lean="Вечером передумали. " + total_lean(g))
                changed.append(dict(id=u["id"], what="тотал", **{"from": tp.get("side"), "to": ts, "why": "поздняя линия и составы"}))
            else:
                tp["line"], tp["odds"] = o["total"], o.get(ts)
        fs = [x for x in (u.get("factors") or []) if not str(x).startswith("Вратари:")]
        gl = goalie_line(u)
        u["factors"] = (fs + [gl])[:6] if gl else fs
        if changed and changed[-1]["id"] == u["id"]:
            tab.setdefault(str(u["id"]), model_paras(u, g)).append(
                f"Вечером: {', '.join(note) or 'обновились составы и линия'}. Модель теперь за {q(u[fav])} ({pct(side_p(g, fav))}).")
        elif str(u["id"]) not in tab:
            tab[str(u["id"])] = model_paras(u, g)
        # журнал
        journal_add(data, u, g, date)
        for j in data.get("journal", []):
            if j.get("date") != date or j.get("result") is not None or j.get("away") != u["away"] or j.get("home") != u["home"]:
                continue
            if j["type"] == "win":
                if j.get("side") != fav:
                    j.update(pick_am=j["pick"], side_am=j["side"], odds_am=j.get("odds"), pick=u[fav], side=fav, odds=o.get(fav), changed=True)
                else:
                    j["odds_am"], j["odds"] = j.get("odds_am", j.get("odds")), o.get(fav)
                j["odds_late"] = o.get(fav)
                if v.get("mkt_fav"):
                    if j.get("mkt_side") and j["mkt_side"] != v["mkt_fav"]:
                        j["mkt_side_am"] = j["mkt_side"]
                    j["mkt_side"] = v["mkt_fav"]
                j["final"] = True
            elif j["type"] == "total" and o.get("total") is not None:
                if j.get("side") != ts or float(j.get("line")) != float(o["total"]):
                    j.update(pick_am=j["pick"], side_am=j["side"], line_am=j.get("line"), odds_am=j.get("odds"),
                             pick=("ТБ " if ts == "over" else "ТМ ") + str(o["total"]).replace(".0", ""), side=ts, line=o["total"],
                             odds=o.get(ts), changed=True)
                else:
                    j["odds_am"], j["odds"] = j.get("odds_am", j.get("odds")), o.get(ts)
                j["odds_late"] = o.get(ts)
                if v["total"].get("mkt_side"):
                    if j.get("mkt_side") and j["mkt_side"] != v["total"]["mkt_side"]:
                        j["mkt_side_am"] = j["mkt_side"]
                    j["mkt_side"] = v["total"]["mkt_side"]
                j["final"] = True
    # уверенные исходы — пересобрать, если все матчи ещё впереди
    ex = data.get("express")
    ids = {(u["away"], u["home"]) for u in pending}
    if not ex or all((l["away"], l["home"]) in ids for l in ex.get("legs", [])):
        new = express(data, M, pending)
        old_p = sorted(l["pick"] for l in (ex or {}).get("legs", []))
        new_p = sorted(l["pick"] for l in (new or {}).get("legs", []))
        if old_p != new_p:
            if ex:
                data["express_am"] = ex
            data["express"] = new
            changed.append(dict(id=None, what="уверенные", **{"from": " + ".join(old_p), "to": " + ".join(new_p), "why": "поздние данные"}))
            for j in data.get("journal", []):
                if j.get("date") == date and j.get("type") == "express" and j.get("result") is None:
                    if new:
                        j.update(legs_am=j.get("legs"), pick_am=j.get("pick"), odds_am=j.get("odds"), legs=new["legs"],
                                 pick=" + ".join(l["pick"] for l in new["legs"]), odds=new["odds"], changed=True)
            if new and not any(j.get("date") == date and j.get("type") == "express" for j in data.get("journal", [])):
                data["journal"].append(dict(date=date, type="express", away=None, home=None, pick=" + ".join(l["pick"] for l in new["legs"]),
                                            legs=new["legs"], odds=new["odds"], src="Линия 1", result=None, score=None))
    sure_journal(data, model, evening=True)
    data["final"] = dict(t=iso(), changed=changed, auto=True)
    return len(pending), len(changed)


# ------------------------------------------------------------------ запасное утро
def needs_fallback(data):
    d = data.get("daily") or {}
    up = data.get("upcoming") or []
    return d.get("date") != data.get("results_date") or any(not u.get("pick_side") for u in up)


def recap(g, box, idm):
    a, h = g["away"], g["home"]
    win, los = (h, a) if g["hs"] > g["as"] else (a, h)
    ws, ls = max(g["hs"], g["as"]), min(g["hs"], g["as"])
    end = {"OT": " в овертайме", "SO": " по буллитам"}.get(g.get("end"), "")
    sc = [x for x in g.get("goals", []) if x[1] == win and x[3] != 5]
    names_ = []
    for x in sc:
        n = ru(idm.get(str(x[6])) if len(x) > 6 and x[6] else x[0])
        if n not in names_:
            names_.append(n)
    s = f"{q(a)} — {q(h)} {g['as']}:{g['hs']}{end}, победитель — {q(win)}."
    if names_:
        s += " Голы победителей: " + ", ".join(names_[:4]) + "."
    gk = [p for b in box.get("games", []) if b["id"] == g["id"] for p in b["players"] if p.get("pos") == "G" and p.get("shots")]
    if gk:
        best = max(gk, key=lambda p: p["saves"])
        s += f" Больше всех сейвов — {ru(best['name'])}: {best['saves']} из {best['shots']}."
    return s


def fallback(data, model, archive, box):
    if not needs_fallback(data):
        return False
    M = {g["id"]: g for g in model.get("games", [])}
    rd, date = data.get("results_date"), data.get("upcoming_date")
    games = [g for g in archive.get("games", []) if g["date"] == rd]
    idm = {str(v).rsplit("/", 1)[-1]: k for k, v in (data.get("heads") or {}).items()}
    for g in games:
        if not g.get("recap"):
            g["recap"] = recap(g, box, idm)
    pl = [dict(p, gid=b["id"]) for b in box.get("games", []) for p in b.get("players", [])] if box.get("date") == rd else []
    sk = [p for p in pl if p.get("pos") != "G"]
    gk = [p for p in pl if p.get("pos") == "G" and (p.get("shots") or 0) >= 15]
    russ = {r["name"] for r in data.get("russians") or []}
    if sk:
        top = sorted(sk, key=lambda p: (-(p["g"] + p["a"]), -p["g"], -p.get("pm", 0)))[:3]
        heroes = [dict(name=p["name"], team=p["team"], pos=p["pos"], line=f"{p['g']}+{p['a']}",
                       text=f"Очки: {p['g']}+{p['a']}, полезность {sg(p.get('pm', 0))}, бросков в створ: {p.get('sog', 0)}.")
                  for p in top]
        bad, per = [], {}
        for p in sorted(sk, key=lambda p: (p.get("pm", 0), -p.get("pim", 0), -p.get("give", 0))):
            if p["g"] + p["a"] == 0 and per.get(p["team"], 0) < 2:
                bad.append(p); per[p["team"]] = per.get(p["team"], 0) + 1
        bad = bad[:3]
        anti = [dict(name=p["name"], team=p["team"], pos=p["pos"], line=sg(p.get('pm', 0)),
                     text=f"Полезность {sg(p.get('pm', 0))}, без очков, потерь: {p.get('give', 0)}, штраф: {p.get('pim', 0)} мин.")
                for p in bad]
        daily = dict(date=rd, heroes=heroes, antiheroes=anti, auto=True)
        if gk:
            b = max(gk, key=lambda p: (p["saves"] / max(1, p["shots"]), p["saves"]))
            daily["goalie"] = dict(name=b["name"], team=b["team"], pos="G", line=f"{b['saves']} из {b['shots']}",
                                   text=f"Отразил {b['saves']} бросков из {b['shots']}.")
        rp = [p for p in sk if p["name"] in russ and p["g"] + p["a"] > 0]
        if rp:
            p = max(rp, key=lambda p: (p["g"] + p["a"], p["g"]))
            daily["russian"] = dict(name=p["name"], team=p["team"], pos=p["pos"], line=f"{p['g']}+{p['a']}",
                                    text=f"Очки: {p['g']}+{p['a']}, полезность {sg(p.get('pm', 0))}.")
        if games:
            m = max(games, key=lambda g: abs(g["hs"] - g["as"]))
            w = m["home"] if m["hs"] > m["as"] else m["away"]
            l = m["away"] if w == m["home"] else m["home"]
            if abs(m["hs"] - m["as"]) >= 2:
                daily["best_team"] = dict(abbr=w, text=f"Самая крупная победа ночи: {q(w)} — {q(l)} {max(m['hs'], m['as'])}:{min(m['hs'], m['as'])}.")
                daily["worst_team"] = dict(abbr=l, text=f"{q(l)} — {q(w)} {min(m['hs'], m['as'])}:{max(m['hs'], m['as'])}: самое крупное поражение ночи.")
            b = max(games, key=lambda g: g["hs"] + g["as"])
            daily["best"] = dict(id=b["id"], text=f"Самый результативный матч ночи: {b['as'] + b['hs']} голов.")
        data["daily"] = daily
    up = data.get("upcoming") or []
    tab = {}
    for u in up:
        g = M.get(u["id"])
        if not g:
            continue
        v, o = g["verdict"], u.get("odds") or {}
        if not u.get("pick_side"):
            u["pick"], u["pick_side"], u["lean"] = u[v["fav"]], v["fav"], lean_text(u, g)
            u["factors"] = factors(u, g, data, archive)
            if o.get("total") is not None:
                ts = v["total"]["side"]
                u["total_pick"] = dict(side=ts, line=o["total"], odds=o.get(ts), lean=total_lean(g))
        tab[str(u["id"])] = model_paras(u, g)
        if o:
            journal_add(data, u, g, date)
    ex = express(data, M, up)
    data["express"] = ex
    if ex and not any(j.get("date") == date and j.get("type") == "express" for j in data.get("journal", [])):
        data["journal"].append(dict(date=date, type="express", away=None, home=None, pick=" + ".join(l["pick"] for l in ex["legs"]),
                                    legs=ex["legs"], odds=ex["odds"], src="Линия 1", result=None, score=None))
    if up:
        cand = [u for u in up if u["id"] in M]
        vs = [u for u in cand if M[u["id"]]["verdict"].get("vs_market")]
        m = (vs or sorted(cand, key=lambda u: abs(M[u["id"]]["p_home"] - 0.5)))[0] if cand else None
        if m:
            g = M[m["id"]]
            data["motd"] = dict(away=m["away"], home=m["home"],
                                text=(f"Главный спор вечера. {lean_text(m, g)}" if g["verdict"].get("vs_market")
                                      else f"Самый равный матч вечера по оценке модели. {lean_text(m, g)}"))
    n_lines = sum(1 for u in up if u.get("odds"))
    vs_n = sum(1 for u in up if u["id"] in M and M[u["id"]]["verdict"].get("vs_market"))
    data["model_tab"] = dict(updated=iso(), auto=True, games=tab, essay=[
        f"Сегодня {len(up)} матчей, линия есть на {n_lines}. Модель против рынка в исходе — в {vs_n}.",
        "Это короткий автоматический разбор: подробные тексты сегодня не вышли, поэтому здесь только цифры модели."])
    data["auto_texts"] = dict(t=iso(), date=date)
    return True
