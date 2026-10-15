#!/usr/bin/env python3
"""Воспроизводимый бэктест модели «Сводки НХЛ».

Запуск:
  python3 scripts/backtest.py --data bt-data --seasons 2021-2025 \\
      --model v4.2=scripts/model.py --model v4.3=backtest/candidates/model_v43.py --out backtest/results/latest

Как это устроено:
  • Данные — пакет scripts/backtest_data.py (результаты НХЛ + поматчевые данные MoneyPuck).
  • На каждый игровой день сезона заново собираются archive.json, data.json и prior.json ровно в том виде,
    в каком их получает модель на сайте, но только из того, что было известно ДО этого дня.
  • Модель запускается как есть (main() из указанного файла, ничего не переписано), версий может быть несколько —
    все на одних и тех же входах.
  • Пишутся построчные прогнозы (preds_<версия>.csv.gz) и сводка (summary.json, report.md).

Чего в восстановленных данных нет или что приближённо (то же для всех версий, на сравнение версий не влияет):
  • кэфов нет — рыночные поля (mkt_*, «выгодные» ставки) в бэктесте пустые, тотал модели — на линии 5,5 и 6,5;
  • вратарь — тот, кто провёл в воротах больше всего времени (как будто старт подтверждён);
  • травмы — игроки команды, сыгравшие за неё хотя бы раз за последние 15 матчей и пропускающие этот матч
    (в том числе по решению тренера), статус Out; давно выбывшие с прошлого сезона не видны;
  • смены тренеров не заданы (coach_changes пустой);
  • prior.json сезона строится из прошлого сезона по тем же правилам, что описаны в prior.json сайта.
"""
import argparse, contextlib, csv, datetime as dt, glob, gzip, importlib.util, io, json, math, multiprocessing as mp, os, sys, tempfile, time
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = {}   # данные воркера


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def load_pack(data, s):
    p = os.path.join(data, f"season_{s}.json.gz")
    return json.load(gzip.open(p, "rt", encoding="utf-8")) if os.path.exists(p) else None


def load_model(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def gdict(g):
    return dict(id=g[0], date=g[1], away=g[2], home=g[3], **{"as": g[4]}, hs=g[5], end=g[6])


# ------------------------------------------------------------------ prior.json сезона из прошлых
def build_prior(packs, s, fit):
    prev, cur = packs.get(s - 1), packs[s]
    if not prev or not prev["games"]:
        raise SystemExit(f"для сезона {s} нужен пакет {s - 1}")
    cur_teams = sorted({g[2] for g in cur["games"]} | {g[3] for g in cur["games"]})
    tm = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
    for g in prev["games"]:
        _, _, a, h, as_, hs, end = g
        if end == "SO":   # гол «за буллиты» в забитые не идёт
            as_, hs = (as_ - 1, hs) if as_ > hs else (as_, hs - 1)
        for t, gf, ga, won in ((a, as_, hs, g[4] > g[5]), (h, hs, as_, g[5] > g[4])):
            r = tm[t]; r[0] += 1; r[5] += gf; r[6] += ga
            if won: r[1] += 1; r[4] += 2
            elif end in ("OT", "SO"): r[3] += 1; r[4] += 1
            else: r[2] += 1
    prev_teams = sorted(tm)
    # рейтинги прошлого сезона: та же регрессия, что в модели, цель 0,7·xG + 0,3·голы, без притяжения
    txg = defaultdict(lambda: dict(gp=0, xgf=0.0, xga=0.0)); sh = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    for r in prev["team"]:
        d, t, xgf, xga, ldf, lda, cf, ca = r
        if xgf is not None and xga is not None:
            x = txg[t]; x["gp"] += 1; x["xgf"] += xgf; x["xga"] += xga
        if None not in (ldf, lda, cf, ca):
            y = sh[t]; y[0] += ldf; y[1] += lda; y[2] += cf; y[3] += ca
    games = [gdict(g) for g in prev["games"]]
    end_day = dt.date.fromisoformat(prev["games"][-1][1]) + dt.timedelta(days=1)
    att, dfn, _, _ = fit(games, {t: tm[t] for t in prev_teams}, end_day, {t: [0.0, 0.0] for t in prev_teams}, dict(txg))
    lg = [sum(v[i] for v in tm.values()) / len(tm) for i in range(7)]

    def src(t):   # откуда брать прошлое для команды этого сезона
        if t in tm: return t
        if t == "UTA" and "ARI" in tm: return "ARI"
        return None
    P = dict(season=f"{s - 1}-{s % 100:02d}", note="бэктест: построено scripts/backtest.py из прошлого сезона",
             teams={}, teams_xg={}, team_shares={}, goalies={}, goalies_gsax={}, players_ixg={})
    for t in cur_teams:
        o = src(t)
        P["teams"][t] = list(tm[o]) if o else [round(v, 1) for v in lg]
        P["teams_xg"][t] = [round(att[o], 4), round(dfn[o], 4)] if o else [0.0, 0.0]
        y = sh.get(o) if o else None
        P["team_shares"][t] = [round(y[0] / (y[0] + y[1]), 4), round(y[2] / (y[2] + y[3]), 4)] if y and y[0] + y[1] > 0 and y[2] + y[3] > 0 else [0.5, 0.5]
    gl = defaultdict(lambda: [0, 0.0, 0.0])
    for r in prev["goalie"]:
        _, _, pid, nm, ice, xga, ga, sog = r
        if sog is None or ga is None: continue
        x = gl[nm]; x[0] += 1; x[1] += sog; x[2] += ga
    P["goalies"] = {n: [v[0], int(v[1]), round(1 - v[2] / v[1], 4)] for n, v in gl.items() if v[1] > 0}
    gs = defaultdict(lambda: [0.0, 0.0])
    for k in range(1, 6):
        pk = packs.get(s - k)
        if not pk: continue
        w = 0.8 ** (k - 1)
        for r in pk["goalie"]:
            if r[5] is None or r[6] is None: continue
            x = gs[r[3]]; x[0] += w * (r[5] - r[6]); x[1] += w * r[5]
    P["goalies_gsax"] = {n: [round(v[0], 2), round(v[1], 1)] for n, v in gs.items()}
    pi = defaultdict(lambda: [0.0, 0.0])
    for k, w in ((1, 1.0), (2, 0.5)):
        pk = packs.get(s - k)
        if not pk: continue
        for r in pk["skater"]:
            x = pi[r[3]]; x[0] += w; x[1] += w * r[6]
    P["players_ixg"] = {n: [round(v[0], 1), round(v[1], 2)] for n, v in pi.items()}
    return P


# ------------------------------------------------------------------ data.json на день
def build_day(pk, day, gmode="actual"):
    games = pk["games"]
    before = [g for g in games if g[1] < day]; today = [g for g in games if g[1] == day]
    A = dict(games=[gdict(g) for g in before])
    # командный xG с начала сезона
    tx = {}
    for d, t, xgf, xga, ldf, lda, cf, ca in pk["team"]:
        if d >= day or xgf is None or xga is None: continue
        x = tx.setdefault(t, dict(gp=0, xgf=0.0, xga=0.0, ld_xgf=0.0, ld_xga=0.0, cf_5v5=0, ca_5v5=0, _ld=0, _cf=0))
        x["gp"] += 1; x["xgf"] += xgf; x["xga"] += xga
        if ldf is not None and lda is not None: x["ld_xgf"] += ldf; x["ld_xga"] += lda; x["_ld"] += 1
        if cf is not None and ca is not None: x["cf_5v5"] += cf; x["ca_5v5"] += ca; x["_cf"] += 1
    team_xg = {}
    for t, x in tx.items():
        y = dict(gp=x["gp"], xgf=round(x["xgf"], 2), xga=round(x["xga"], 2))
        if x["_ld"]: y.update(ld_xgf=round(x["ld_xgf"], 2), ld_xga=round(x["ld_xga"], 2))
        if x["_cf"]: y.update(cf_5v5=int(x["cf_5v5"]), ca_5v5=int(x["ca_5v5"]))
        team_xg[t] = y
    # вратари с начала сезона
    gx = {}
    for d, t, pid, nm, ice, xga, ga, sog in pk["goalie"]:
        if d >= day: continue
        x = gx.setdefault(nm, dict(team=t, gp=0, xga=0.0, ga=0, sog=0)); x["team"] = t; x["gp"] += 1
        x["xga"] += xga or 0; x["ga"] += int(ga or 0); x["sog"] += int(sog or 0)
    goalie_xg = {n: dict(team=v["team"], gp=v["gp"], xga=round(v["xga"], 2), ga=v["ga"]) for n, v in gx.items()}
    goalies = [dict(team=v["team"], name=n, gp=v["gp"], sv=round(1 - v["ga"] / v["sog"], 3) if v["sog"] else None) for n, v in gx.items()]
    # полевые с начала сезона
    sx = {}; team_dates = defaultdict(list)
    for g in before:
        team_dates[g[2]].append(g[1]); team_dates[g[3]].append(g[1])
    for d, t, pid, nm, pos, ice, ixg, pts in pk["skater"]:
        if d >= day: continue
        x = sx.setdefault(pid, dict(name=nm, team=t, pos=pos, gp=0, pts=0, ice=0, ixg=0.0, last=d))
        x["team"] = t; x["last"] = d; x["gp"] += 1; x["pts"] += pts; x["ice"] += ice; x["ixg"] += ixg
    skaters = [dict(name=v["name"], team=v["team"], pos="D" if v["pos"] == "D" else v["pos"], gp=v["gp"], pts=v["pts"],
                    toi=round(v["ice"] / v["gp"] / 60, 1)) for v in sx.values()]
    skater_xg = {v["name"]: dict(team=v["team"], gp=v["gp"], ixg=round(v["ixg"], 2)) for v in sx.values()}
    # сегодняшние составы и вратари (кто провёл больше времени в воротах — «стартовый»)
    play_today = set(); start = {}
    for d, t, pid, nm, pos, ice, ixg, pts in pk["skater"]:
        if d == day: play_today.add(pid)
    starts = defaultdict(dict)   # (команда, дата) → стартовый (больше всех времени в воротах)
    for d, t, pid, nm, ice, xga, ga, sog in pk["goalie"]:
        if d > day: continue
        cur = starts[t].get(d)
        if cur is None or ice > cur[1]: starts[t][d] = (nm, ice)
    for t, by in starts.items():
        if day in by: start[t] = by[day]
    def projected(t):
        """Ожидаемый стартовый: чаще всех начинал последние 10 матчей команды (как прогнозы составов утром)."""
        last = [by for d, by in sorted(starts[t].items()) if d < day][-10:]
        if not last: return None
        cnt = defaultdict(int); recent = {}
        for i, (nm, _) in enumerate(last): cnt[nm] += 1; recent[nm] = i
        return max(cnt, key=lambda n: (cnt[n], recent[n]))   # при равенстве — кто стартовал позже
    teams = {}
    for g in today:
        for t in (g[2], g[3]):
            recent = set(sorted(team_dates[t])[-15:])
            inj = [dict(name=v["name"], status="Out") for pid, v in sx.items()
                   if v["team"] == t and pid not in play_today and v["last"] in recent]
            teams[t] = dict(injuries=inj)
    st = defaultdict(lambda: dict(gp=0, pts=0))
    for g in before:
        for t, won in ((g[2], g[4] > g[5]), (g[3], g[5] > g[4])):
            st[t]["gp"] += 1; st[t]["pts"] += 2 if won else (1 if g[6] in ("OT", "SO") else 0)
    D = dict(upcoming_date=day, week=[], coach_changes=[], standings=[dict(abbr=t, **v) for t, v in st.items()],
             skaters=skaters, goalies=goalies, teams=teams, team_xg=team_xg, goalie_xg=goalie_xg, skater_xg=skater_xg,
             upcoming=[])
    miss = {}
    for g in today:
        act = [(start.get(g[2]) or (None,))[0], (start.get(g[3]) or (None,))[0]]
        if gmode == "projected":
            pr = [projected(g[2]), projected(g[3])]
            miss[g[0]] = int(any(p and p != a for p, a in zip(pr, act)))
            gl = [f"{p} (не подтв.)" if p else None for p in pr]
        else:
            gl = act
        D["upcoming"].append(dict(id=g[0], date=day, away=g[2], home=g[3], goalies=gl))
    return A, D, today, miss


# ------------------------------------------------------------------ воркер
def init(data, seasons, models, prior_dir):
    G["packs"] = {s: load_pack(data, s) for s in seasons}
    G["models"] = []
    for i, (lab, p, opt) in enumerate(models):
        m = load_model(p, f"bt_model_{i}")
        for k, v in opt.items():
            if k == "goalies": continue
            if not hasattr(m, k): raise SystemExit(f"{lab}: в модели нет параметра {k}")
            setattr(m, k, type(getattr(m, k))(float(v)) if isinstance(getattr(m, k), (int, float)) and not isinstance(getattr(m, k), bool) else v)
        G["models"].append((lab, m, opt))
    G["prior_dir"] = prior_dir
    G["tmp"] = tempfile.mkdtemp(prefix="bt_")


def run_day(task):
    s, day = task
    pp = os.path.join(G["prior_dir"], f"prior_{s}.json"); out = []; built = {}
    for lab, mod, opt in G["models"]:
        gm = opt.get("goalies", "actual")
        if gm not in built:
            A, D, today, miss = build_day(G["packs"][s], day, gm)
            ap, dp = os.path.join(G["tmp"], f"a_{gm}.json"), os.path.join(G["tmp"], f"d_{gm}.json")
            json.dump(A, open(ap, "w")); json.dump(D, open(dp, "w"))
            built[gm] = (ap, dp, {g[0]: g for g in today}, miss)
        ap, dp, res, miss = built[gm]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.main(ap, dp, pp)
        js = json.loads(buf.getvalue())
        for r in js["games"]:
            g = res.get(r["id"])
            if not g: continue
            row = dict(model=lab, season=s, date=day, id=r["id"], away=r["away"], home=r["home"],
                       a_goals=g[4], h_goals=g[5], end=g[6], goalies_mode=gm)
            if r["id"] in miss: row["proj_miss"] = miss[r["id"]]
            for k in ("p_home", "p_away", "p_home_reg", "p_away_reg", "p_ot", "p_ot_home", "lam_home", "lam_away",
                      "exp_total", "p_over", "line", "shares_adj", "b2b_home", "b2b_away", "inj_adj_home", "inj_adj_away",
                      "p_home_reg_raw", "p_ot_home_raw", "incomplete"):
                if k in r: row[k] = r[k]
            if "missing" in r: row["missing"] = "|".join(r["missing"])
            row["goalie_away"] = (r.get("goalie_away") or {}).get("name"); row["goalie_home"] = (r.get("goalie_home") or {}).get("name")
            out.append(row)
    return out


# ------------------------------------------------------------------ метрики
def pois(k, l):
    return math.exp(-l) * l ** k / math.factorial(k)


def p_over(lh, la, line):
    """Так же, как модель: ничья в основное время = +1 гол в ОТ/буллитах."""
    P = [[pois(i, lh) * pois(j, la) for j in range(13)] for i in range(13)]
    return sum(P[i][j] for i in range(13) for j in range(13) if i + j + (1 if i == j else 0) > line)


def metrics(rows):
    n = len(rows)
    if not n: return {}
    ll = br = acc = 0.0; ll3 = br3 = 0.0; ot = []; tot = {5.5: [0.0, 0.0, 0.0, 0], 6.5: [0.0, 0.0, 0.0, 0]}
    bins = defaultdict(lambda: [0, 0.0, 0])
    for r in rows:
        hw = r["h_goals"] > r["a_goals"]; ph = r["p_home"]
        ll -= math.log(max(1e-9, ph if hw else 1 - ph)); br += (ph - hw) ** 2; acc += (ph >= 0.5) == hw
        k = 1 if r["end"] in ("OT", "SO") else (0 if hw else 2)
        q = (r["p_home_reg"], r["p_ot"], r["p_away_reg"])
        ll3 -= math.log(max(1e-9, q[k])); br3 += sum((q[i] - (i == k)) ** 2 for i in range(3))
        if k == 1: ot.append((r["p_ot_home"], hw))
        pf = max(ph, 1 - ph); b = min(19, int(pf * 20)); bins[b][0] += 1; bins[b][1] += pf; bins[b][2] += (ph >= 0.5) == hw
        tg = r["h_goals"] + r["a_goals"]
        for L in tot:
            po = p_over(r["lam_home"], r["lam_away"], L); o = tg > L
            tot[L][0] -= math.log(max(1e-9, po if o else 1 - po)); tot[L][1] += (po >= 0.5) == o; tot[L][2] += po; tot[L][3] += o
    res = dict(games=n, accuracy=round(acc / n, 4), logloss=round(ll / n, 4), brier=round(br / n, 4),
               reg3_logloss=round(ll3 / n, 4), reg3_brier=round(br3 / n, 4),
               ot_share=dict(actual=round(sum(r["end"] in ("OT", "SO") for r in rows) / n, 4), predicted=round(sum(r["p_ot"] for r in rows) / n, 4)),
               ot_home=dict(games=len(ot), actual=round(sum(h for _, h in ot) / max(1, len(ot)), 4), predicted=round(sum(p for p, _ in ot) / max(1, len(ot)), 4),
                            logloss=round(-sum(math.log(max(1e-9, p if h else 1 - p)) for p, h in ot) / max(1, len(ot)), 4)),
               totals={str(L): dict(logloss=round(v[0] / n, 4), accuracy=round(v[1] / n, 4), over_predicted=round(v[2] / n, 4), over_actual=round(v[3] / n, 4)) for L, v in tot.items()},
               goals=dict(predicted=round(sum(float(r["exp_total"]) for r in rows) / n, 3), actual=round(sum(r["h_goals"] + r["a_goals"] for r in rows) / n, 3)),
               calibration=[dict(range=f"{b * 5}-{b * 5 + 5}%", games=v[0], predicted=round(v[1] / v[0], 3), actual=round(v[2] / v[0], 3))
                            for b, v in sorted(bins.items())])
    if "incomplete" in rows[0]: res["incomplete_share"] = round(sum(bool(r.get("incomplete")) for r in rows) / n, 4)
    return res


def paired(rows_a, rows_b, key):
    """Разница лог-лосса b − a по одним и тем же матчам ± стандартная ошибка."""
    ia = {r["id"]: r for r in rows_a}; d = []
    for r in rows_b:
        a = ia.get(r["id"])
        if a: d.append(key(r) - key(a))
    if len(d) < 2: return None
    m = sum(d) / len(d); se = (sum((x - m) ** 2 for x in d) / (len(d) - 1) / len(d)) ** 0.5
    return dict(diff=round(m, 5), se=round(se, 5), games=len(d))


def ll_win(r):
    return -math.log(max(1e-9, r["p_home"] if r["h_goals"] > r["a_goals"] else 1 - r["p_home"]))


def ll_reg3(r):
    k = 1 if r["end"] in ("OT", "SO") else (0 if r["h_goals"] > r["a_goals"] else 2)
    return -math.log(max(1e-9, (r["p_home_reg"], r["p_ot"], r["p_away_reg"])[k]))


def ll_tot(r, L):
    po = p_over(r["lam_home"], r["lam_away"], L)
    return -math.log(max(1e-9, po if r["h_goals"] + r["a_goals"] > L else 1 - po))


def site_check(rows, root):
    """Сверка с настоящими прогнозами сайта из history/ (утренние снимки): насколько бэктест воспроизводит сайт."""
    hist = {}
    for fn in sorted(glob.glob(os.path.join(root, "history", "*_am.json.gz"))):
        try:
            js = json.load(gzip.open(fn, "rt", encoding="utf-8"))
        except Exception:
            continue
        for g in (js.get("model") or {}).get("games", []):
            hist[g.get("id")] = g
    d = [(abs(r["p_home"] - hist[r["id"]]["p_home"]), r["id"]) for r in rows if r["id"] in hist]
    if not d: return None
    return dict(games=len(d), mean_abs_diff_p_home=round(sum(x for x, _ in d) / len(d), 4), max_abs_diff=round(max(x for x, _ in d), 4),
                same_favourite=round(sum((r["p_home"] >= .5) == (hist[r["id"]]["p_home"] >= .5) for r in rows if r["id"] in hist) / len(d), 4))


# ------------------------------------------------------------------ отчёт
def inc(m):
    return f"{m['incomplete_share']:.1%}" if 'incomplete_share' in m else "—"


def report_md(summ, labels, base):
    L = [f"# Бэктест модели — {summ['generated']}", "",
         f"Сезоны: {', '.join(summ['seasons'])}. Данные: результаты НХЛ, MoneyPuck (moneypuck.com). Кэфов нет.", "",
         "## Итог по всем сезонам", "",
         "| Версия | Матчей | Угадано | Лог-лосс | Брайер | 3 исхода осн. вр., лог-лосс | Тотал 5,5 | Тотал 6,5 | Неполные |",
         "|---|---|---|---|---|---|---|---|---|"]
    for lab in labels:
        m = summ["models"][lab]["all"]
        L.append(f"| {lab} | {m['games']} | {m['accuracy']:.1%} | {m['logloss']:.4f} | {m['brier']:.4f} | {m['reg3_logloss']:.4f} | "
                 f"{m['totals']['5.5']['logloss']:.4f} | {m['totals']['6.5']['logloss']:.4f} | {inc(m)} |")
    L += ["", "## По сезонам (угадано / лог-лосс победителя / лог-лосс 3 исходов)", "",
          "| Сезон | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    for s in summ["seasons"]:
        L.append(f"| {s} | " + " | ".join(f"{summ['models'][l]['by_season'][s]['accuracy']:.1%} / {summ['models'][l]['by_season'][s]['logloss']:.4f} / "
                                         f"{summ['models'][l]['by_season'][s]['reg3_logloss']:.4f}" for l in labels) + " |")
    if summ.get("pairs"):
        L += ["", f"## Разница с {base} на одних и тех же матчах (минус — лучше)", ""]
        for lab, p in summ["pairs"].items():
            L.append(f"- **{lab}**: лог-лосс победителя {p['win']['diff']:+.5f} ± {p['win']['se']:.5f}; "
                     f"3 исхода осн. времени {p['reg3']['diff']:+.5f} ± {p['reg3']['se']:.5f}; "
                     f"сезонов, где 3 исхода лучше: {p['reg3_better_seasons']}; тотал 5,5 {p['tot55']['diff']:+.5f} ± {p['tot55']['se']:.5f}, "
                 f"6,5 {p['tot65']['diff']:+.5f} ± {p['tot65']['se']:.5f}")
    L += ["", "## Голы и тоталы", ""]
    for lab in labels:
        m = summ["models"][lab]["all"]
        L.append(f"- {lab}: голов за матч ждали {m['goals']['predicted']:.2f}, было {m['goals']['actual']:.2f}; «больше 5,5» ждали {m['totals']['5.5']['over_predicted']:.1%}, "
                 f"было {m['totals']['5.5']['over_actual']:.1%}; «больше 6,5» ждали {m['totals']['6.5']['over_predicted']:.1%}, было {m['totals']['6.5']['over_actual']:.1%}")
    gm = [l for l in labels if summ["models"][l].get("goalie_miss")]
    if gm:
        L += ["", "## Вратарь не подтверждён: матчи, где ожидаемый стартовый не вышел", ""]
        for lab in gm:
            m = summ["models"][lab]["goalie_miss"]
            L.append(f"- {lab}: {m['games']} матчей, угадано {m['accuracy']:.1%}, лог-лосс {m['logloss']:.4f}, тотал 5,5 {m['totals']['5.5']['logloss']:.4f}")
    L += ["", "## Овертайм", ""]
    for lab in labels:
        m = summ["models"][lab]["all"]
        L.append(f"- {lab}: ничьих в осн. время {m['ot_share']['actual']:.1%} (модель {m['ot_share']['predicted']:.1%}); "
                 f"хозяева в ОТ/буллитах выиграли {m['ot_home']['actual']:.1%} (модель {m['ot_home']['predicted']:.1%}), {m['ot_home']['games']} матчей")
    L += ["", "## Калибровка (вероятность фаворита)", ""]
    for lab in labels:
        L.append(f"- {lab}: " + "; ".join(f"{c['range']}: {c['games']} матчей, ждали {c['predicted']:.1%}, вышло {c['actual']:.1%}"
                                         for c in summ["models"][lab]["all"]["calibration"]))
    if summ.get("site_check"):
        L += ["", "## Сверка с прогнозами сайта (history/)", ""]
        for lab, c in summ["site_check"].items():
            if c: L.append(f"- {lab}: {c['games']} матчей, средняя разница p_home {c['mean_abs_diff_p_home']:.3f}, макс {c['max_abs_diff']:.3f}, тот же фаворит {c['same_favourite']:.0%}")
    L += ["", "## Оговорки", "", "- Вратарь — фактический стартовый (как подтверждённый); травмы — по пропущенным матчам; смен тренеров нет; кэфов нет.",
          "- Это одинаково для всех версий, поэтому сравнение версий честное; абсолютные цифры могут отличаться от сайта."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="bt-data")
    ap.add_argument("--seasons", default="2021-2025")
    ap.add_argument("--model", action="append", required=True, help="метка=путь, можно несколько; первая — база для сравнения")
    ap.add_argument("--out", default="backtest/results/latest")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--max-days", type=int, default=0, help="для быстрой проверки: только первые N дней каждого сезона")
    a = ap.parse_args()
    if "-" in a.seasons:
        s0, s1 = map(int, a.seasons.split("-")); seasons = list(range(s0, s1 + 1))
    else:
        seasons = [int(x) for x in a.seasons.split(",")]
    models = []
    for x in a.model:
        lab, _, p = x.partition("=")
        if not p: lab, p = os.path.splitext(os.path.basename(x))[0], x
        p, _, q = p.partition("?")
        opt = dict(kv.split("=", 1) for kv in q.split("&") if "=" in kv)
        models.append((lab, os.path.abspath(p), opt))
    labels = [l for l, _, _ in models]
    os.makedirs(a.out, exist_ok=True)
    need = sorted({s - k for s in seasons for k in range(0, 6)})
    packs = {s: load_pack(a.data, s) for s in need}
    for s in seasons:
        if not packs.get(s) or not packs.get(s - 1):
            raise SystemExit(f"нет пакета данных для {s} или {s - 1} в {a.data}")
    prior_dir = os.path.join(a.out, "_prior"); os.makedirs(prior_dir, exist_ok=True)
    fit = load_model(models[0][1], "bt_fit").fit
    for s in seasons:
        json.dump(build_prior(packs, s, fit), open(os.path.join(prior_dir, f"prior_{s}.json"), "w"), ensure_ascii=False)
    tasks = []
    for s in seasons:
        days = sorted({g[1] for g in packs[s]["games"]})
        tasks += [(s, d) for d in (days[:a.max_days] if a.max_days else days)]
    del packs
    log(f"Дней: {len(tasks)}, версий: {len(models)}, процессов: {a.workers}")
    t0 = time.time(); rows = []
    with mp.Pool(a.workers, initializer=init, initargs=(a.data, need, models, prior_dir)) as pool:
        for i, r in enumerate(pool.imap_unordered(run_day, tasks, chunksize=4)):
            rows += r
            if (i + 1) % 100 == 0: log(f"  {i + 1}/{len(tasks)} дней, {time.time() - t0:.0f} с")
    rows.sort(key=lambda r: (r["model"], r["date"], r["id"]))
    by = defaultdict(list)
    for r in rows: by[r["model"]].append(r)
    for lab in labels:
        fn = os.path.join(a.out, f"preds_{lab}.csv.gz")
        keys = list(dict.fromkeys(k for r in by[lab] for k in r))
        with gzip.open(fn, "wt", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(by[lab])
    sname = {s: f"{s}-{(s + 1) % 100:02d}" for s in seasons}
    summ = dict(generated=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), seasons=[sname[s] for s in seasons],
                models={}, pairs={}, site_check={}, seconds=round(time.time() - t0))
    for lab, p, opt in models:
        rs = by[lab]
        summ["models"][lab] = dict(path=os.path.relpath(p, ROOT), options=opt, all=metrics(rs),
                                   goalie_miss=metrics([r for r in rs if r.get("proj_miss") == 1]) if any("proj_miss" in r for r in rs) else None,
                                   by_season={sname[s]: metrics([r for r in rs if r["season"] == s]) for s in seasons})
        summ["site_check"][lab] = site_check(rs, ROOT)
    base = labels[0]
    for lab in labels[1:]:
        summ["pairs"][lab] = dict(win=paired(by[base], by[lab], ll_win), reg3=paired(by[base], by[lab], ll_reg3),
                                  tot55=paired(by[base], by[lab], lambda r: ll_tot(r, 5.5)), tot65=paired(by[base], by[lab], lambda r: ll_tot(r, 6.5)),
                                  reg3_better_seasons=f"{sum(1 for s in seasons if (paired([r for r in by[base] if r['season'] == s], [r for r in by[lab] if r['season'] == s], ll_reg3) or {}).get('diff', 0) < 0)} из {len(seasons)}")
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(a.out, "report.md"), "w", encoding="utf-8").write(report_md(summ, labels, base))
    log(open(os.path.join(a.out, "report.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
