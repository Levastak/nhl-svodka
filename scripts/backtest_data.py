#!/usr/bin/env python3
"""Данные для бэктеста модели «Сводки НХЛ»: полная история по сезонам, в компактном виде.

Запуск:  python3 scripts/backtest_data.py --out bt-data --seasons 2016-2026
Сезон называется по году начала, как у MoneyPuck: 2021 = 2021-22.

Источники (всё публичное и перечислено на https://moneypuck.com/data.htm, данные MoneyPuck —
только для некоммерческого использования, со ссылкой на MoneyPuck.com):
  • результаты, счёт и как закончился матч (REG / OT / SO) — API НХЛ api-web.nhle.com/v1/schedule;
  • поматчевая статистика команд (xG, xG с неопасных позиций, попытки бросков 5 на 5) —
    moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv;
  • поматчевая статистика вратарей и полевых (время, xG против, голы, личный xG, очки) —
    peter-tanner.com/moneypuck/downloads/seasonPlayersSummary/{goalies|skaters}/<сезон>.zip.

На выходе по файлу на сезон: <out>/season_<год>.json.gz
  games:  [id, дата, гости, хозяева, голы гостей, голы хозяев, REG|OT|SO]   (только регулярка)
  team:   [дата, команда, xGF, xGA, xGF неопасные, xGA неопасные, попытки 5на5 за, против]
  goalie: [дата, команда, id, имя, секунд на льду, xG против, голы, броски в створ]
  skater: [дата, команда, id, имя, позиция, секунд на льду, личный xG, очки]
и <out>/report.json — сколько чего собрано и где не сошлось.
Уже собранные прошлые сезоны не перекачиваются (кроме текущего), --force — собрать заново.
"""
import argparse, csv, datetime as dt, gzip, io, json, os, sys, time, urllib.error, urllib.request, zipfile

UA = "Mozilla/5.0 (nhl-svodka backtest; github.com/Levastak/nhl-svodka)"
MP_CODES = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL"}
TEAMS_URL = "https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv"
ZIP_URL = "https://peter-tanner.com/moneypuck/downloads/seasonPlayersSummary/{kind}/{season}.zip"
csv.field_size_limit(10 ** 9)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fetch(url, path=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                if path:
                    with open(path, "wb") as fh:
                        while True:
                            b = r.read(1 << 20)
                            if not b:
                                break
                            fh.write(b)
                    return path
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log(f"  {url}: HTTP {e.code}, повтор {i + 1}")
        except Exception as e:
            log(f"  {url}: {e}, повтор {i + 1}")
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"не скачалось: {url}")


def code(t):
    return MP_CODES.get(t, t)


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except Exception:
        return None


def mp_date(s):
    s = str(s).strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else s[:10]


def need(header, cols, what):
    miss = [c for c in cols if c not in header]
    if miss:
        raise SystemExit(f"{what}: нет колонок {miss}. Есть: {header[:80]}")


# ------------------------------------------------------------------ результаты (API НХЛ)
def nhl_games(season):
    """Все матчи регулярки сезона: неделя за неделей по расписанию НХЛ."""
    d = dt.date(season, 9, 20); end = dt.date(season + 1, 7, 15); out = {}
    today = dt.date.today()
    while d <= end and d <= today + dt.timedelta(days=7):
        raw = fetch(f"https://api-web.nhle.com/v1/schedule/{d.isoformat()}")
        js = json.loads(raw) if raw else {}
        for wk in js.get("gameWeek", []):
            for g in wk.get("games", []):
                if g.get("gameType") != 2 or int(str(g["id"])[:4]) != season:
                    continue
                a, h = g["awayTeam"], g["homeTeam"]
                if g.get("gameState") not in ("OFF", "FINAL") or a.get("score") is None:
                    continue
                end_ = (g.get("gameOutcome") or {}).get("lastPeriodType") or "REG"
                out[g["id"]] = [g["id"], wk["date"], a["abbrev"], h["abbrev"], a["score"], h["score"], end_]
        d += dt.timedelta(days=7)
        time.sleep(0.3)
    return sorted(out.values(), key=lambda r: (r[1], r[0]))


# ------------------------------------------------------------------ MoneyPuck: команды
def mp_teams(path, seasons):
    """all_teams.csv: строка = команда × матч × ситуация. Берём all и 5on5, только регулярку."""
    by = {}
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames or []
        need(hdr, ["season", "gameId", "gameDate", "situation", "xGoalsFor", "xGoalsAgainst",
                   "lowDangerxGoalsFor", "lowDangerxGoalsAgainst", "shotAttemptsFor", "shotAttemptsAgainst"], "all_teams.csv")
        tcol = "playerTeam" if "playerTeam" in hdr else "team"
        for r in rd:
            try:
                s = int(r["season"])
            except Exception:
                continue
            if s not in seasons or r["situation"] not in ("all", "5on5"):
                continue
            gid = str(r["gameId"])
            if len(gid) >= 6 and gid[4:6] != "02":
                continue
            if str(r.get("playoffGame", "0")) not in ("0", "", "0.0"):
                continue
            k = (s, mp_date(r["gameDate"]), code(r[tcol]))
            x = by.setdefault(k, [None] * 6)
            if r["situation"] == "all":
                x[0], x[1] = num(r["xGoalsFor"]), num(r["xGoalsAgainst"])
                x[2], x[3] = num(r["lowDangerxGoalsFor"]), num(r["lowDangerxGoalsAgainst"])
            else:
                x[4], x[5] = num(r["shotAttemptsFor"]), num(r["shotAttemptsAgainst"])
    res = {}
    for (s, d, t), x in by.items():
        res.setdefault(s, []).append([d, t] + [None if v is None else round(v, 3) for v in x])
    return res


# ------------------------------------------------------------------ MoneyPuck: игроки
def mp_players(kind, season, tmp):
    zp = os.path.join(tmp, f"{kind}_{season}.zip")
    if not os.path.exists(zp) and not fetch(ZIP_URL.format(kind=kind, season=season), zp):
        return None
    rows = []
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        for n in names:
            with z.open(n) as fh:
                rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline=""))
                hdr = rd.fieldnames or []
                base = ["playerId", "name", "gameId", "gameDate", "situation", "icetime"]
                need(hdr, base + (["xGoals", "goals", "ongoal"] if kind == "goalies" else ["position", "I_F_xGoals", "I_F_points"]),
                     f"{kind} {season} ({n})")
                tcol = "playerTeam" if "playerTeam" in hdr else "team"
                for r in rd:
                    if r["situation"] != "all":
                        continue
                    gid = str(r["gameId"])
                    if len(gid) >= 6 and gid[4:6] != "02":
                        continue
                    if str(r.get("playoffGame", "0")) not in ("0", "", "0.0"):
                        continue
                    ice = num(r["icetime"]) or 0
                    if ice <= 0:
                        continue
                    d, t = mp_date(r["gameDate"]), code(r[tcol])
                    if kind == "goalies":
                        rows.append([d, t, r["playerId"], r["name"], round(ice), num(r["xGoals"]), num(r["goals"]), num(r["ongoal"])])
                    else:
                        rows.append([d, t, r["playerId"], r["name"], r["position"], round(ice),
                                     round(num(r["I_F_xGoals"]) or 0, 3), int(num(r["I_F_points"]) or 0)])
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bt-data")
    ap.add_argument("--seasons", default="2016-2026", help="год начала сезона, диапазон или список через запятую")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skaters-from", type=int, default=2019, help="полевые нужны только с этого сезона (вратари — для истории сейвов — раньше)")
    a = ap.parse_args()
    if "-" in a.seasons:
        s0, s1 = map(int, a.seasons.split("-")); seasons = list(range(s0, s1 + 1))
    else:
        seasons = [int(x) for x in a.seasons.split(",")]
    os.makedirs(a.out, exist_ok=True); tmp = os.path.join(a.out, "_tmp"); os.makedirs(tmp, exist_ok=True)
    today = dt.date.today(); cur = today.year if today.month >= 9 else today.year - 1
    todo = [s for s in seasons if a.force or s >= cur or not os.path.exists(os.path.join(a.out, f"season_{s}.json.gz"))]
    report = json.load(open(os.path.join(a.out, "report.json"))) if os.path.exists(os.path.join(a.out, "report.json")) else {}
    if not todo:
        log("Все сезоны уже собраны."); return
    log("Собираю сезоны:", todo)
    tp = os.path.join(tmp, "all_teams.csv")
    log("MoneyPuck: команды по матчам (один большой файл)…")
    fetch(TEAMS_URL, tp)
    teams = mp_teams(tp, set(todo))
    for s in todo:
        log(f"Сезон {s}-{(s + 1) % 100:02d}: результаты НХЛ…")
        games = nhl_games(s)
        log(f"  матчей {len(games)}; вратари…")
        goalies = mp_players("goalies", s, tmp) or []
        log(f"  строк вратарей {len(goalies)}; полевые…")
        skaters = (mp_players("skaters", s, tmp) or []) if s >= a.skaters_from else []
        log(f"  строк полевых {len(skaters)}")
        tm = sorted(teams.get(s, []))
        # сверка: у каждой команды в каждом матче должна быть строка MoneyPuck
        have = {(r[0], r[1]) for r in tm}
        miss = [g for g in games if (g[1], g[2]) not in have or (g[1], g[3]) not in have]
        gk = {(r[0], r[1]) for r in goalies}
        miss_g = [g for g in games if (g[1], g[2]) not in gk or (g[1], g[3]) not in gk]
        pack = dict(season=s, built=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), games=games, team=tm, goalie=goalies, skater=skaters)
        with gzip.open(os.path.join(a.out, f"season_{s}.json.gz"), "wt", encoding="utf-8") as fh:
            json.dump(pack, fh, ensure_ascii=False, separators=(",", ":"))
        report[str(s)] = dict(games=len(games), team_rows=len(tm), goalie_rows=len(goalies), skater_rows=len(skaters),
                              games_without_team_xg=len(miss), games_without_goalie=len(miss_g),
                              examples_missing=[g[:4] for g in (miss + miss_g)[:5]])
        log("  ", report[str(s)])
        for k in ("goalies", "skaters"):
            p = os.path.join(tmp, f"{k}_{s}.zip")
            if os.path.exists(p): os.remove(p)
    json.dump(report, open(os.path.join(a.out, "report.json"), "w"), ensure_ascii=False, indent=1)
    if os.path.exists(tp): os.remove(tp)


if __name__ == "__main__":
    main()
