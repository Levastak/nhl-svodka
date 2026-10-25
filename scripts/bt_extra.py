#!/usr/bin/env python3
"""Доп. проверки к бэктесту: шанс гола игрока в матче.

Запуск (после scripts/backtest.py, в том же workflow):
  python3 scripts/bt_extra.py --data bt-data --results backtest/results/<метка>

Как считается шанс гола игрока (P = 1 − e^−λ, сыгравшие в матче полевые; в жизни — по составам DailyFaceoff):
  • naive  — голы за игру с начала сезона, притянутые к прошлым сезонам (не больше 20 матчей) и к среднему по позиции;
  • xg     — личный xG за игру (тот же принцип), без поправки на соперника;
  • xg_m   — xg × (ожидаемые голы команды в этом матче по модели / средние ожидаемые голы команды в сезоне до матча):
             соперник, площадка, вратарь, усталость;
  • blend_m — 70% xG + 30% голов за игру, с той же поправкой на матч.
Оценка — лог-лосс и калибровка «шанс забить хотя бы раз». Кэфов на игроков нет — сравнение только между вариантами.
"""
import argparse, csv, glob, gzip, json, math, os
from collections import defaultdict


def load(p):
    return json.load(gzip.open(p, "rt", encoding="utf-8")) if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="bt-data")
    ap.add_argument("--results", required=True)
    a = ap.parse_args()
    summ = json.load(open(os.path.join(a.results, "summary.json"), encoding="utf-8"))
    lab = next(iter(summ["models"]))
    preds = list(csv.DictReader(gzip.open(os.path.join(a.results, f"preds_{lab}.csv.gz"), "rt", encoding="utf-8")))
    by_season = defaultdict(list)
    for r in preds:
        by_season[int(r["season"])].append(r)
    V = ("naive", "xg", "xg_m", "blend_m")
    rows = []          # (season, variant P..., scored)
    star = []
    for s in sorted(by_season):
        pk = load(os.path.join(a.data, f"season_{s}.json.gz"))
        if not pk or not pk["skater"] or len(pk["skater"][0]) < 9:
            print(f"сезон {s}: нет голов игроков в пакете — пропуск"); continue
        prior = defaultdict(lambda: [0.0, 0.0, 0.0])          # pid → [матчи, xG, голы] с весом
        for k, w in ((1, 1.0), (2, 0.5)):
            pp = load(os.path.join(a.data, f"season_{s - k}.json.gz"))
            for x in (pp or {}).get("skater") or []:
                if len(x) < 9: continue
                q = prior[x[2]]; q[0] += w; q[1] += w * x[6]; q[2] += w * x[8]
        # средние по позиции (прошлый сезон) — для новичков
        pos_rate = defaultdict(lambda: [0.0, 0.0, 0.0])
        for x in (load(os.path.join(a.data, f"season_{s - 1}.json.gz")) or {}).get("skater") or []:
            if len(x) < 9: continue
            q = pos_rate["D" if x[4] == "D" else "F"]; q[0] += 1; q[1] += x[6]; q[2] += x[8]
        prate = {k: (v[1] / v[0], v[2] / v[0]) for k, v in pos_rate.items() if v[0]} or {"F": (0.2, 0.2), "D": (0.06, 0.06)}
        day_rows = defaultdict(list)
        for x in pk["skater"]:
            day_rows[x[0]].append(x)
        cur = defaultdict(lambda: [0, 0.0, 0])                 # pid → [матчи, xG, голы] с начала сезона
        lam_hist = defaultdict(list)                           # команда → ожидаемые голы по модели в прошлых матчах
        games = sorted(by_season[s], key=lambda r: (r["date"], r["id"]))
        gi = 0
        for day in sorted({r["date"] for r in games}):
            today = [r for r in games if r["date"] == day]
            for r in today:
                for side, t in (("home", r["home"]), ("away", r["away"])):
                    lam = float(r[f"lam_{side}"]); hist = lam_hist[t]
                    mf = lam / (sum(hist) / len(hist)) if len(hist) >= 3 else 1.0
                    for x in day_rows.get(day, []):
                        if x[1] != t: continue
                        pid, pos, scored = x[2], ("D" if x[4] == "D" else "F"), x[8] > 0
                        c = cur[pid]; pr = prior.get(pid)
                        gp = c[0]; xg = c[1]; gl = c[2]
                        if pr and pr[0] > 0:
                            w = min(1.0, 20 / pr[0]); gp += w * pr[0]; xg += w * pr[1]; gl += w * pr[2]
                        k = 5.0                                   # притяжение к среднему по позиции, «5 матчей»
                        rx = (xg + k * prate[pos][0]) / (gp + k); rg = (gl + k * prate[pos][1]) / (gp + k)
                        lam_v = dict(naive=rg, xg=rx, xg_m=rx * mf, blend_m=(0.7 * rx + 0.3 * rg) * mf)
                        P = {v: 1 - math.exp(-max(1e-6, lam_v[v])) for v in V}
                        rows.append((s, P, scored, gp))
                        if P["xg_m"] >= 0.3: star.append((s, P["xg_m"], scored))
                    lam_hist[t].append(lam)
            for x in day_rows.get(day, []):                   # после матчей дня — в статистику
                c = cur[x[2]]; c[0] += 1; c[1] += x[6]; c[2] += x[8]
    if not rows:
        print("нет данных"); return
    out = {}
    n = len(rows); base = sum(r[2] for r in rows) / n
    for v in V:
        ll = -sum(math.log(max(1e-9, r[1][v] if r[2] else 1 - r[1][v])) for r in rows) / n
        br = sum((r[1][v] - r[2]) ** 2 for r in rows) / n
        bins = defaultdict(lambda: [0, 0.0, 0])
        for r in rows:
            b = min(9, int(r[1][v] / 0.05)); bins[b][0] += 1; bins[b][1] += r[1][v]; bins[b][2] += r[2]
        out[v] = dict(logloss=round(ll, 5), brier=round(br, 5), mean_p=round(sum(r[1][v] for r in rows) / n, 4),
                      calibration=[dict(range=f"{b*5}-{b*5+5}%", n=x[0], predicted=round(x[1] / x[0], 3), actual=round(x[2] / x[0], 3)) for b, x in sorted(bins.items())])
    ll0 = -(base * math.log(base) + (1 - base) * math.log(1 - base))
    seas = sorted({r[0] for r in rows})
    by_s = {str(s): {v: round(-sum(math.log(max(1e-9, r[1][v] if r[2] else 1 - r[1][v])) for r in rows if r[0] == s) / sum(1 for r in rows if r[0] == s), 5) for v in V} for s in seas}
    res = dict(rows=n, base_rate=round(base, 4), logloss_constant=round(ll0, 5), variants=out, by_season=by_s,
               stars=dict(n=len(star), predicted=round(sum(x[1] for x in star) / max(1, len(star)), 3), actual=round(sum(x[2] for x in star) / max(1, len(star)), 3)))
    json.dump(res, open(os.path.join(a.results, "player_goals.json"), "w"), ensure_ascii=False, indent=1)
    L = ["# Шанс гола игрока — проверка", "", f"Игроко-матчей: {n}, забивали в {base:.1%}. Лог-лосс «всем одинаково»: {ll0:.5f}.", "",
         "| Вариант | Лог-лосс | Брайер | Средний прогноз |", "|---|---|---|---|"]
    for v in V:
        L.append(f"| {v} | {out[v]['logloss']:.5f} | {out[v]['brier']:.5f} | {out[v]['mean_p']:.1%} |")
    L += ["", "По сезонам (лог-лосс): " + "; ".join(f"{s}: " + ", ".join(f"{v} {x:.4f}" for v, x in d.items()) for s, d in by_s.items()), "",
          f"Звёзды (шанс по xg_m 30%+): {len(star)} игроко-матчей, ждали {res['stars']['predicted']:.1%}, забили {res['stars']['actual']:.1%}", "",
          "Калибровка xg_m: " + "; ".join(f"{c['range']}: {c['n']}, ждали {c['predicted']:.1%}, вышло {c['actual']:.1%}" for c in out["xg_m"]["calibration"])]
    open(os.path.join(a.results, "player_goals.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
