#!/usr/bin/env python3
"""Сбор данных для «Сводки НХЛ» — запускается в GitHub Actions.

Режимы:
  am — утренний сбор (11:15 по Кирову): результаты ночи, таблица, статистика, составы и травмы,
       расписание, стартовые вратари, командная статистика, MoneyPuck, кэфы, оценка журнала.
  pm — предматчевый (23:20 по Кирову): подтверждённые вратари, травмы команд вечера, поздняя линия.

Скрипт только собирает данные. Тексты (превью, три звезды, колонка, разборы, новости, прогнозы)
пишет Claude поверх этих файлов; текстовые поля из прошлого data.json скрипт сохраняет.
Ключ The Odds API берётся из переменной окружения ODDS_API_KEY и никуда не пишется.
"""
import csv, io, json, os, re, sys, time, unicodedata, urllib.error, urllib.request
import datetime as dt
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SEASON_ID = "20262027"
MP_SEASON = "2026"
ET = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

TEAMS = {  # аббревиатура: (полное имя, слаг DailyFaceoff, дивизион)
    "ANA": ("Anaheim Ducks", "anaheim-ducks"), "BOS": ("Boston Bruins", "boston-bruins"),
    "BUF": ("Buffalo Sabres", "buffalo-sabres"), "CGY": ("Calgary Flames", "calgary-flames"),
    "CAR": ("Carolina Hurricanes", "carolina-hurricanes"), "CHI": ("Chicago Blackhawks", "chicago-blackhawks"),
    "COL": ("Colorado Avalanche", "colorado-avalanche"), "CBJ": ("Columbus Blue Jackets", "columbus-blue-jackets"),
    "DAL": ("Dallas Stars", "dallas-stars"), "DET": ("Detroit Red Wings", "detroit-red-wings"),
    "EDM": ("Edmonton Oilers", "edmonton-oilers"), "FLA": ("Florida Panthers", "florida-panthers"),
    "LAK": ("Los Angeles Kings", "los-angeles-kings"), "MIN": ("Minnesota Wild", "minnesota-wild"),
    "MTL": ("Montreal Canadiens", "montreal-canadiens"), "NSH": ("Nashville Predators", "nashville-predators"),
    "NJD": ("New Jersey Devils", "new-jersey-devils"), "NYI": ("New York Islanders", "new-york-islanders"),
    "NYR": ("New York Rangers", "new-york-rangers"), "OTT": ("Ottawa Senators", "ottawa-senators"),
    "PHI": ("Philadelphia Flyers", "philadelphia-flyers"), "PIT": ("Pittsburgh Penguins", "pittsburgh-penguins"),
    "SJS": ("San Jose Sharks", "san-jose-sharks"), "SEA": ("Seattle Kraken", "seattle-kraken"),
    "STL": ("St. Louis Blues", "st-louis-blues"), "TBL": ("Tampa Bay Lightning", "tampa-bay-lightning"),
    "TOR": ("Toronto Maple Leafs", "toronto-maple-leafs"), "UTA": ("Utah Mammoth", "utah-mammoth"),
    "VAN": ("Vancouver Canucks", "vancouver-canucks"), "VGK": ("Vegas Golden Knights", "vegas-golden-knights"),
    "WSH": ("Washington Capitals", "washington-capitals"), "WPG": ("Winnipeg Jets", "winnipeg-jets"),
}
MP_CODES = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL"}
INJ = {"ir": "IR", "ltir": "LTIR", "out": "Out", "dtd": "DTD", "day-to-day": "DTD"}

LOG = {"ok": [], "fail": []}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


NAME2ABBR = {norm(v[0]): k for k, v in TEAMS.items()}
NAME2ABBR.update({norm("St Louis Blues"): "STL", norm("Utah Hockey Club"): "UTA", norm("Utah HC"): "UTA",
                  norm("Montréal Canadiens"): "MTL"})
SLUG2ABBR = {v[1]: k for k, v in TEAMS.items()}


def team_abbr(name):
    return NAME2ABBR.get(norm(name))


def get(url, kind="json", tries=3, label=None):
    label = label or url.split("?")[0]
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                hdr = dict(r.headers)
            txt = raw.decode("utf-8", "replace")
            if kind == "json":
                return json.loads(txt), hdr
            return txt, hdr
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    LOG["fail"].append(label)
    return None, {}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def iso(t=None):
    return (t or now_utc()).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- архив результатов
def surname(full):
    s = str(full or "").strip()
    return s.split(". ", 1)[1] if ". " in s[:4] else s.split(" ")[-1]


def build_game(g):
    a, h = g["awayTeam"], g["homeTeam"]
    end = (g.get("gameOutcome") or {}).get("lastPeriodType") or (g.get("periodDescriptor") or {}).get("periodType") or "REG"
    goals, so = [], []
    for x in g.get("goals", []):
        per = (x.get("periodDescriptor") or {}).get("number") or x.get("period")
        ptype = (x.get("periodDescriptor") or {}).get("periodType")
        name = ((x.get("lastName") or {}).get("default")) or surname((x.get("name") or {}).get("default"))
        strength = x.get("strength") or "ev"
        if (x.get("goalModifier") or "") == "empty-net":
            strength = "en"
        ast = ",".join(((y.get("lastName") or {}).get("default")) or surname((y.get("name") or {}).get("default")) for y in x.get("assists", []))
        row = [name, x.get("teamAbbrev") if isinstance(x.get("teamAbbrev"), str) else (x.get("teamAbbrev") or {}).get("default"),
               strength, per, x.get("timeInPeriod", ""), ast]
        (so if ptype == "SO" or per == 5 else goals).append(row)
    if end == "SO":
        win = a["abbrev"] if a["score"] > h["score"] else h["abbrev"]
        w = [x for x in so if x[1] == win]
        goals.append([(w[-1][0] if w else ""), win, "ev", 5, "00:00", ""])
    rec = dict(id=g["id"], date=g.get("gameDate"), away=a["abbrev"], home=h["abbrev"], **{"as": a["score"], "hs": h["score"]},
               end=end, sog=[a.get("sog"), h.get("sog")], goals=goals)
    if g.get("threeMinRecap"):
        rec["video"] = "https://www.nhl.com" + g["threeMinRecap"]
    if g.get("gameCenterLink"):
        rec["gc"] = "https://www.nhl.com" + g["gameCenterLink"]
    return rec


def game_extras(gid, rec, idname):
    """Командная статистика, три звезды и полная статистика игроков матча."""
    rr, _ = get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/right-rail", label=f"right-rail {gid}")
    if rr:
        st = {x["category"]: (x["awayValue"], x["homeValue"]) for x in rr.get("teamGameStats", [])}
        def pair(k, f=lambda v: v):
            v = st.get(k)
            return [f(v[0]), f(v[1])] if v else None
        stats = dict(sog=pair("sog"), pp=pair("powerPlay"), pim=pair("pim"), hits=pair("hits"),
                     fo=pair("faceoffWinningPctg", lambda v: round(float(v) * 100)), blk=pair("blockedShots"))
        rec["stats"] = {k: v for k, v in stats.items() if v is not None}
    land, _ = get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/landing", label=f"landing {gid}")
    if land:
        stars = (land.get("summary") or {}).get("threeStars") or []
        if stars:
            rec["stars"] = [f'{surname((s.get("name") or {}).get("default"))} ({s.get("teamAbbrev")})' for s in sorted(stars, key=lambda s: s.get("star", 9))]
    box, _ = get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/boxscore", label=f"boxscore {gid}")
    players = []
    if box:
        for side, key in (("away", "awayTeam"), ("home", "homeTeam")):
            team = rec[side]
            grp = (box.get("playerByGameStats") or {}).get(key) or {}
            for pos in ("forwards", "defense"):
                for p in grp.get(pos, []):
                    players.append(dict(name=idname.get(p.get("playerId")) or (p.get("name") or {}).get("default"), team=team,
                                        pos=p.get("position"), g=p.get("goals", 0), a=p.get("assists", 0), pm=p.get("plusMinus", 0),
                                        sog=p.get("sog", 0), hits=p.get("hits", 0), blk=p.get("blockedShots", 0), pim=p.get("pim", 0),
                                        toi=p.get("toi"), give=p.get("giveaways", 0), take=p.get("takeaways", 0)))
            for p in grp.get("goalies", []):
                if not p.get("shotsAgainst") and p.get("toi") in (None, "00:00"):
                    continue
                players.append(dict(name=idname.get(p.get("playerId")) or (p.get("name") or {}).get("default"), team=team, pos="G",
                                    saves=p.get("saves", 0), shots=p.get("shotsAgainst", 0), ga=p.get("goalsAgainst", 0),
                                    toi=p.get("toi"), starter=p.get("starter")))
    return players


def update_archive(archive, yesterday, idname):
    have = {g["id"] for g in archive["games"]}
    last = max((g["date"] for g in archive["games"]), default=yesterday)
    d = dt.date.fromisoformat(last)
    end = dt.date.fromisoformat(yesterday)
    box = []
    while d <= end:
        day = d.isoformat()
        s, _ = get(f"https://api-web.nhle.com/v1/score/{day}", label=f"score {day}")
        for g in (s or {}).get("games", []):
            if g.get("gameType") not in (2, 3) or g.get("gameState") not in ("OFF", "FINAL"):
                continue
            if g["id"] in have:
                continue
            rec = build_game(g)
            players = game_extras(g["id"], rec, idname)
            archive["games"].append(rec)
            have.add(g["id"])
            if day == yesterday:
                box.append(dict(id=rec["id"], away=rec["away"], home=rec["home"], score=f'{rec["as"]}:{rec["hs"]}', end=rec["end"],
                                stars=rec.get("stars", []), players=players))
        d += dt.timedelta(days=1)
    archive["games"].sort(key=lambda g: (g["date"], g["id"]))
    archive["updated"] = dt.date.today().isoformat()
    return box


# ---------------------------------------------------------------- таблица, статистика, ростеры
def standings():
    s, _ = get("https://api-web.nhle.com/v1/standings/now", label="standings")
    if not s:
        return None
    out = []
    for x in s.get("standings", []):
        out.append(dict(abbr=(x.get("teamAbbrev") or {}).get("default"), gp=x["gamesPlayed"], w=x["wins"], l=x["losses"],
                        otl=x["otLosses"], pts=x["points"], gf=x["goalFor"], ga=x["goalAgainst"],
                        l10=f'{x.get("l10Wins", 0)}-{x.get("l10Losses", 0)}-{x.get("l10OtLosses", 0)}',
                        streak=f'{x.get("streakCode", "")}{x.get("streakCount", "")}', div=x.get("divisionName"),
                        logo=x.get("teamLogo")))
    return out


def club_stats():
    skaters, goalies, idname = [], [], {}
    for t in TEAMS:
        c, _ = get(f"https://api-web.nhle.com/v1/club-stats/{t}/now", label=f"club-stats {t}")
        if not c:
            continue
        for p in c.get("skaters", []):
            nm = f'{p["firstName"]["default"]} {p["lastName"]["default"]}'
            idname[p["playerId"]] = nm
            skaters.append(dict(team=t, name=nm, pos=p.get("positionCode"), gp=p.get("gamesPlayed", 0), g=p.get("goals", 0),
                                a=p.get("assists", 0), pts=p.get("points", 0), pm=p.get("plusMinus", 0),
                                toi=round((p.get("avgTimeOnIcePerGame") or 0) / 60, 1)))
        for p in c.get("goalies", []):
            nm = f'{p["firstName"]["default"]} {p["lastName"]["default"]}'
            idname[p["playerId"]] = nm
            goalies.append(dict(team=t, name=nm, gp=p.get("gamesPlayed", 0), w=p.get("wins", 0), l=p.get("losses", 0),
                                otl=p.get("overtimeLosses", 0), sv=round(p.get("savePercentage") or 0, 3),
                                gaa=round(p.get("goalsAgainstAverage") or 0, 2), so=p.get("shutouts", 0)))
    return skaters, goalies, idname


def leaders(skaters):
    out = {}
    for k in ("points", "goals", "assists"):
        f = {"points": "pts", "goals": "g", "assists": "a"}[k]
        rows = sorted((s for s in skaters if s[f] > 0), key=lambda s: (-s[f], s["gp"], s["name"]))[:25]
        out[k] = [dict(name=s["name"], team=s["team"], pos=s["pos"], v=s[f]) for s in rows]
    return out


def rosters():
    numbers, russians, seen, heads = {}, [], {}, {}
    for t in TEAMS:
        r, _ = get(f"https://api-web.nhle.com/v1/roster/{t}/current", label=f"roster {t}")
        if not r:
            continue
        for grp in ("forwards", "defensemen", "goalies"):
            for p in r.get(grp, []):
                nm = f'{p["firstName"]["default"]} {p["lastName"]["default"]}'
                hs = str(p.get("headshot") or "")
                if "/mugs/nhl/" in hs:
                    heads[nm] = hs.split("/mugs/nhl/")[1].rsplit(".", 1)[0]
                num, pos = p.get("sweaterNumber"), p.get("positionCode")
                if num is None:
                    continue
                if nm in seen and seen[nm] != (t, pos):
                    numbers[f"{nm}|{pos}"] = num
                    op = seen[nm]
                    numbers.setdefault(f"{nm}|{op[1]}", numbers.get(nm))
                else:
                    numbers[nm] = num
                seen[nm] = (t, pos)
                if p.get("birthCountry") == "RUS":
                    russians.append(dict(name=nm, team=t))
    return numbers, russians, heads


# ---------------------------------------------------------------- DailyFaceoff
def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    return json.loads(m.group(1))["props"]["pageProps"] if m else None


def dfo_team(t):
    html, _ = get(f"https://www.dailyfaceoff.com/teams/{TEAMS[t][1]}/line-combinations", kind="text", label=f"dfo {t}")
    pp = next_data(html)
    if not pp or not pp.get("combinations"):
        if html is not None:
            LOG["fail"].append(f"dfo-parse {t}")
        return None
    c = pp["combinations"]
    by = {}
    for p in c.get("players", []):
        by.setdefault(p.get("groupIdentifier"), []).append(p)
    order = {"lw": 0, "c": 1, "rw": 2, "ld": 0, "rd": 1, "g1": 0, "g2": 1, "sk1": 0, "sk2": 1, "sk3": 2, "sk4": 3, "sk5": 4}
    def names(g):
        return [p["name"] for p in sorted(by.get(g, []), key=lambda p: order.get(p.get("positionIdentifier"), 9))]
    inj = []
    for p in c.get("players", []):
        st = (p.get("injuryStatus") or "").lower()
        if st:
            inj.append(dict(name=p["name"], status=INJ.get(st, st.upper())))
        elif p.get("gameTimeDecision"):
            inj.append(dict(name=p["name"], status="DTD"))
    return dict(abbr=t, team=TEAMS[t][0], updated=c.get("updatedAt"),
                forwards=[names(f"f{i}") for i in range(1, 5) if by.get(f"f{i}")],
                defense=[names(f"d{i}") for i in range(1, 4) if by.get(f"d{i}")],
                goalies=names("g"), pp1=names("pp1"), pp2=names("pp2"), injuries=inj, extras=[],
                source=f'DailyFaceoff{(" / " + c["sourceName"]) if c.get("sourceName") else ""}')


def dfo_goalies(day):
    html, _ = get(f"https://www.dailyfaceoff.com/starting-goalies/{day}", kind="text", label=f"dfo-goalies {day}")
    pp = next_data(html)
    out = {}
    for g in (pp or {}).get("data", []) or []:
        for side in ("home", "away"):
            t = SLUG2ABBR.get(g.get(f"{side}TeamSlug")) or team_abbr(g.get(f"{side}TeamName"))
            nm = g.get(f"{side}GoalieName")
            if not t or not nm:
                continue
            strength = str(g.get(f"{side}NewsStrengthName") or "").lower()
            out[t] = (nm, "подтв." if "confirm" in strength else "не подтв.")
    return out


# ---------------------------------------------------------------- статистика команд и MoneyPuck
def team_summary():
    s, _ = get(f"https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId={SEASON_ID}%20and%20gameTypeId=2", label="team-summary")
    out = {}
    for x in (s or {}).get("data", []):
        t = team_abbr(x.get("teamFullName"))
        if not t:
            continue
        pct = lambda v: round((v or 0) * 100, 1)
        out[t] = dict(gp=x.get("gamesPlayed"), gf_pg=round(x.get("goalsForPerGame") or 0, 2), ga_pg=round(x.get("goalsAgainstPerGame") or 0, 2),
                      sf_pg=round(x.get("shotsForPerGame") or 0, 1), sa_pg=round(x.get("shotsAgainstPerGame") or 0, 1),
                      pp_pct=pct(x.get("powerPlayPct")), pk_pct=pct(x.get("penaltyKillPct")), fo_pct=pct(x.get("faceoffWinPct")))
    return out


def mp_csv(kind):
    txt, _ = get(f"https://moneypuck.com/moneypuck/playerData/seasonSummary/{MP_SEASON}/regular/{kind}.csv", kind="text", label=f"moneypuck {kind}")
    if not txt:
        return []
    return list(csv.DictReader(io.StringIO(txt)))


def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def moneypuck():
    team_xg, goalie_xg, skater_xg = {}, {}, {}
    rows = mp_csv("teams")
    by = {}
    for r in rows:
        t = MP_CODES.get(r.get("team"), r.get("team"))
        by.setdefault(t, {})[r.get("situation")] = r
    for t, s in by.items():
        a, e = s.get("all"), s.get("5on5")
        if not a or t not in TEAMS:
            continue
        x = dict(gp=int(f(a["games_played"])), xgf=round(f(a["xGoalsFor"]), 2), xga=round(f(a["xGoalsAgainst"]), 2),
                 xg_pct=round(f(a["xGoalsPercentage"]) * 100, 1), gf=int(f(a["goalsFor"])), ga=int(f(a["goalsAgainst"])),
                 ld_xgf=round(f(a.get("lowDangerxGoalsFor")), 2), ld_xga=round(f(a.get("lowDangerxGoalsAgainst")), 2))
        if e:
            x.update(xgf_5v5=round(f(e["xGoalsFor"]), 2), xga_5v5=round(f(e["xGoalsAgainst"]), 2),
                     xg_pct_5v5=round(f(e["xGoalsPercentage"]) * 100, 1),
                     cf_5v5=int(f(e.get("shotAttemptsFor"))), ca_5v5=int(f(e.get("shotAttemptsAgainst"))))
        team_xg[t] = x
    for r in mp_csv("goalies"):
        if r.get("situation") != "all":
            continue
        goalie_xg[r["name"]] = dict(team=MP_CODES.get(r["team"], r["team"]), gp=int(f(r["games_played"])),
                                    xga=round(f(r["xGoals"]), 2), ga=int(f(r["goals"])))
    for r in mp_csv("skaters"):
        if r.get("situation") != "all":
            continue
        skater_xg[r["name"]] = dict(team=MP_CODES.get(r["team"], r["team"]), gp=int(f(r["games_played"])), ixg=round(f(r["I_F_xGoals"]), 2))
    return team_xg, goalie_xg, skater_xg


# ---------------------------------------------------------------- кэфы
def odds_events():
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        LOG["fail"].append("odds: нет ключа")
        return None, None
    t = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey={key}&regions=eu&markets=h2h,totals"
           f"&oddsFormat=decimal&dateFormat=iso&commenceTimeFrom={t}")
    ev, hdr = get(url, label="odds")
    rem = {k.lower(): v for k, v in hdr.items()}.get("x-requests-remaining")
    return ev, rem


def book_lines(ev):
    """Pinnacle (двухисходный, с ОТ), 1xBet и Марафон (трёхисходные, основное время)."""
    home, away = ev["home_team"], ev["away_team"]
    res = {}
    for b in ev.get("bookmakers", []):
        m = {mk["key"]: mk for mk in b.get("markets", [])}
        h2h = {o["name"]: o["price"] for o in (m.get("h2h") or {}).get("outcomes", [])}
        tot = {o["name"].lower(): o for o in (m.get("totals") or {}).get("outcomes", [])}
        x = {}
        if home in h2h and away in h2h:
            x.update(home=h2h[home], away=h2h[away])
            if "Draw" in h2h:
                x["draw"] = h2h["Draw"]
        if "over" in tot and "under" in tot:
            x.update(total=tot["over"].get("point"), over=tot["over"]["price"], under=tot["under"]["price"])
        if x:
            res[b["key"]] = x
    out = {}
    pin = res.get("pinnacle")
    if not pin or "draw" in pin:
        pin = next((res[k] for k in ("betonlineag", "matchbook", "williamhill", "betsson") if k in res and "draw" not in res[k]), None)
        src = next((k for k in ("betonlineag", "matchbook", "williamhill", "betsson") if k in res and "draw" not in res[k]), None)
    else:
        src = "Pinnacle"
    if pin:
        out["odds"] = dict(away=pin.get("away"), home=pin.get("home"), total=pin.get("total"), over=pin.get("over"),
                           under=pin.get("under"), source=src)
    if "onexbet" in res:
        o = res["onexbet"]
        out["odds_1x"] = {k: o.get(k) for k in ("home", "draw", "away", "total", "over", "under") if o.get(k) is not None}
    books = {k: res[k] for k in ("marathonbet",) if k in res}
    if books:
        out["books"] = books
    return out


def match_odds(events, games):
    """events → {game_id: {odds, odds_1x, books}} по командам и времени начала (±8 ч)."""
    res = {}
    for ev in events or []:
        a, h = team_abbr(ev.get("away_team")), team_abbr(ev.get("home_team"))
        try:
            ct = dt.datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        except Exception:
            continue
        for g in games:
            if g["away"] == a and g["home"] == h:
                st = dt.datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
                if abs((st - ct).total_seconds()) < 8 * 3600:
                    res[g["id"]] = book_lines(ev)
    return res


# ---------------------------------------------------------------- журнал (оценка результатов)
def grade_journal(journal, archive):
    by = {(g["date"], g["away"], g["home"]): g for g in archive["games"]}
    by2 = {(g["away"], g["home"]): g for g in archive["games"]}
    def find(date, a, h):
        return by.get((date, a, h)) or (by2.get((a, h)) if date is None else None)
    def sc(g):
        return f'{g["as"]}:{g["hs"]}' + (" ОТ" if g["end"] == "OT" else " Б" if g["end"] == "SO" else "")
    def win(leg, g):
        side = leg.get("side") or ("home" if leg.get("pick") == g["home"] else "away")
        return (g["hs"] > g["as"]) == (side == "home")
    for j in journal:
        if j.get("result") is not None:
            continue
        t = j.get("type")
        if t == "express":
            gs = [find(j["date"], l["away"], l["home"]) for l in j.get("legs", [])]
            if not gs or any(g is None for g in gs):
                continue
            j["result"] = "hit" if all(win(l, g) for l, g in zip(j["legs"], gs)) else "miss"
            j["score"] = "; ".join(sc(g) for g in gs)
            continue
        g = find(j.get("date"), j.get("away"), j.get("home"))
        if not g:
            continue
        j["score"] = sc(g)
        if t == "win":
            j["result"] = "hit" if win(j, g) else "miss"
        elif t == "total":
            tot = g["as"] + g["hs"]
            line = float(j.get("line"))
            side = j.get("side") or ("over" if "Б" in str(j.get("pick")) else "under")
            j["result"] = "void" if tot == line else ("hit" if (tot > line) == (side in ("over", "больше")) else "miss")


# ---------------------------------------------------------------- расписание
TEXT_KEYS = ("factors", "pick", "pick_side", "lean", "total_pick", "pick_am", "pick_side_am", "total_pick_am", "pick_changed",
             "goalie_changed")


def schedule(today):
    s, _ = get(f"https://api-web.nhle.com/v1/schedule/{today}", label="schedule")
    week = []
    for d in (s or {}).get("gameWeek", []):
        for g in d.get("games", []):
            if g.get("gameType") not in (2, 3):
                continue
            x = dict(date=d["date"], id=g["id"], away=g["awayTeam"]["abbrev"], home=g["homeTeam"]["abbrev"], start=g["startTimeUTC"])
            if g.get("neutralSite"):
                x["neutral"] = True
            week.append(x)
    return week


def run_model():
    rc = os.system(f'python3 "{ROOT}/scripts/model.py" "{SITE}/archive.json" "{SITE}/data.json" "{ROOT}/scripts/prior.json" > "{SITE}/model.json.tmp"')
    if rc == 0 and os.path.getsize(f"{SITE}/model.json.tmp") > 100:
        os.replace(f"{SITE}/model.json.tmp", f"{SITE}/model.json")
        LOG["ok"].append("model")
    else:
        LOG["fail"].append("model")
        try:
            os.remove(f"{SITE}/model.json.tmp")
        except OSError:
            pass


# ---------------------------------------------------------------- режимы
def am():
    data = load(f"{SITE}/data.json", {})
    archive = load(f"{SITE}/archive.json", {"season": "2026-27", "games": []})
    now_et = now_utc().astimezone(ET)
    today = now_et.date().isoformat()
    yesterday = (now_et.date() - dt.timedelta(days=1)).isoformat()

    skaters, goalies, idname = club_stats()
    if skaters:
        data["skaters"], data["goalies"], data["leaders"] = skaters, goalies, leaders(skaters)
        LOG["ok"].append("club-stats")
    box = update_archive(archive, yesterday, idname)
    cur = load(f"{SITE}/box.json", {})
    if not box and (cur.get("date") != yesterday or not cur.get("games")):
        for g in [g for g in archive["games"] if g["date"] == yesterday]:
            players = game_extras(g["id"], dict(g), idname)
            box.append(dict(id=g["id"], away=g["away"], home=g["home"], score=f'{g["as"]}:{g["hs"]}', end=g["end"],
                            stars=g.get("stars", []), players=players))
    if box or cur.get("date") != yesterday:
        save(f"{SITE}/box.json", dict(date=yesterday, games=box))
    LOG["ok"].append(f"archive +{len(box)}")
    data["results_date"] = yesterday

    st = standings()
    if st:
        data["standings"] = st
        LOG["ok"].append("standings")
    numbers, russians, heads = rosters()
    if len(numbers) > 500:
        data["numbers"], data["russians"] = numbers, russians
    if len(heads) > 500:
        data["heads"] = heads
        LOG["ok"].append("rosters")

    teams = dict(data.get("teams") or {})
    for t in TEAMS:
        x = dfo_team(t)
        if x:
            teams[t] = x
        time.sleep(0.5)
    data["teams"] = teams

    ts = team_summary()
    if len(ts) >= 30:
        data["team_stats"], data["team_stats_updated"] = ts, iso()
        LOG["ok"].append("team-summary")
    txg, gxg, sxg = moneypuck()
    if len(txg) >= 30:
        data["team_xg"], data["team_xg_updated"] = txg, iso()
        LOG["ok"].append("moneypuck teams")
    if gxg:
        data["goalie_xg"] = gxg
    if sxg:
        data["skater_xg"] = sxg

    week = schedule(today)
    if week:
        old_up = {u["id"]: u for u in data.get("upcoming", [])}
        days = sorted({w["date"] for w in week if w["date"] >= today})
        up_day = days[0] if days else today
        upcoming = []
        for w in week:
            if w["date"] != up_day:
                continue
            u = dict(w)
            for k in TEXT_KEYS:
                if k in (old_up.get(w["id"]) or {}):
                    u[k] = old_up[w["id"]][k]
            upcoming.append(u)
        gl = dfo_goalies(up_day)
        for u in upcoming:
            u["goalies"] = [f"{gl[t][0]} ({gl[t][1]})" if t in gl else "не объявлен" for t in (u["away"], u["home"])]
        data["week"], data["upcoming"], data["upcoming_date"] = week, upcoming, up_day
        LOG["ok"].append(f"schedule {len(week)}")

        ev, rem = odds_events()
        if ev is not None:
            m = match_odds(ev, week)
            for lst in (data["upcoming"], data["week"]):
                for g in lst:
                    for k in ("odds", "odds_1x", "books"):
                        g.pop(k, None)
                    g.update(m.get(g["id"], {}))
            data["odds_updated"] = data["week_odds_updated"] = iso()
            data["odds_remaining"] = rem
            LOG["ok"].append(f"odds {len(m)} матчей, осталось {rem}")

    grade_journal(data.get("journal", []), archive)
    data["generated"] = iso()
    data["fetch"] = dict(mode="am", t=iso(), ok=LOG["ok"], fail=LOG["fail"])
    save(f"{SITE}/archive.json", archive)
    save(f"{SITE}/data.json", data)
    run_model()
    data["fetch"] = dict(mode="am", t=iso(), ok=LOG["ok"], fail=LOG["fail"])
    save(f"{SITE}/data.json", data)


def pm():
    data = load(f"{SITE}/data.json", {})
    lines = load(f"{SITE}/lines.json", {"games": []})
    now = now_utc()
    pending = [u for u in data.get("upcoming", []) if dt.datetime.fromisoformat(u["start"].replace("Z", "+00:00")) > now]
    gl = dfo_goalies(data.get("upcoming_date"))
    for u in pending:
        old = [str(x).split(" (")[0] for x in u.get("goalies", [])]
        new = [f"{gl[t][0]} ({gl[t][1]})" if t in gl else (u.get("goalies") or ["не объявлен"] * 2)[i] for i, t in enumerate((u["away"], u["home"]))]
        if [x.split(" (")[0] for x in new] != old and all(o and o != "не объявлен" for o in old):
            u["goalie_changed"] = True
        u["goalies"] = new
    teams = dict(data.get("teams") or {})
    for t in sorted({t for u in pending for t in (u["away"], u["home"])}):
        x = dfo_team(t)
        if x:
            teams[t] = x
        time.sleep(0.5)
    data["teams"] = teams
    if not any(x.get("logo") for x in data.get("standings") or []):
        st = standings()
        if st:
            data["standings"] = st
    if not data.get("heads"):
        _, _, heads = rosters()
        if len(heads) > 500:
            data["heads"] = heads

    ev, rem = odds_events()
    if ev is not None:
        m = match_odds(ev, data.get("week", []))
        t = iso()
        by_id = {g["id"]: g for g in lines["games"]}
        for u in pending:
            new = m.get(u["id"])
            if not new or "odds" not in new:
                continue
            rec = by_id.get(u["id"]) or dict(id=u["id"], date=u.get("date"), away=u["away"], home=u["home"], start=u["start"])
            rec["open"] = dict(u.get("odds") or {}, t=data.get("odds_updated"))
            rec["late"] = dict(new["odds"], t=t)
            rec["pick_am"] = u.get("pick_side")
            if u.get("total_pick"):
                rec["total_pick_am"] = {k: u["total_pick"].get(k) for k in ("side", "line")}
            if u["id"] not in by_id:
                lines["games"].append(rec)
            u["odds_am"] = u.get("odds")
            u.update(new)
        up_ids = {u["id"] for u in data.get("upcoming", [])}
        for w in data.get("week", []):
            if w["id"] in up_ids or w["id"] not in m:
                continue
            for k in ("odds", "odds_1x", "books"):
                w.pop(k, None)
            w.update(m[w["id"]])
        lines["updated"] = t
        data["odds_updated"] = data["week_odds_updated"] = t
        data["odds_remaining"] = rem
        LOG["ok"].append(f"late odds {len(m)}, осталось {rem}")
    data["lines_updated"] = iso()
    data["fetch"] = dict(mode="pm", t=iso(), ok=LOG["ok"], fail=LOG["fail"])
    save(f"{SITE}/lines.json", lines)
    save(f"{SITE}/data.json", data)
    run_model()
    data["fetch"] = dict(mode="pm", t=iso(), ok=LOG["ok"], fail=LOG["fail"])
    save(f"{SITE}/data.json", data)


SNAP_KEYS = ("upcoming", "upcoming_date", "week", "standings", "skaters", "goalies", "teams", "team_stats", "team_xg",
             "goalie_xg", "skater_xg", "coach_changes", "odds_updated")


def snapshot(mode):
    """Снимок входных данных и прогнозов на момент сбора — для честной проверки вариантов модели на живом сезоне."""
    import gzip
    data = load(f"{SITE}/data.json", {})
    model = load(f"{SITE}/model.json", {})
    snap = dict(t=iso(), mode=mode, data={k: data.get(k) for k in SNAP_KEYS},
                model={k: model.get(k) for k in ("generated", "games", "horizon", "league")})
    os.makedirs(f"{ROOT}/history", exist_ok=True)
    day = now_utc().astimezone(ET).date().isoformat()
    with gzip.open(f"{ROOT}/history/{day}_{mode}.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, separators=(",", ":"))
    LOG["ok"].append("snapshot")


def news_images(data=None):
    """Главное фото статьи-источника (og:image) для новостей без картинки — показываем со ссылкой и подписью источника."""
    import html as _h
    own = data is None
    data = data if data is not None else load(f"{SITE}/data.json", {})
    n = 0
    for x in data.get("news") or []:
        if x.get("image") or not x.get("url"):
            continue
        page, _ = get(x["url"], kind="text", tries=2, label=f"og:image {x['url'][:60]}")
        if not page:
            continue
        m = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]*content=["\']([^"\']+)', page, re.I) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\'](?:og:image|twitter:image)', page, re.I)
        if m:
            x["image"] = _h.unescape(m.group(1))
            x.setdefault("image_source", x.get("source"))
            n += 1
    if own and n:
        save(f"{SITE}/data.json", data)
    LOG["ok"].append(f"news images +{n}")
    return n


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "am"
    if mode == "img":
        news_images()
        print(json.dumps(LOG, ensure_ascii=False))
        sys.exit(0)
    {"am": am, "pm": pm}[mode]()
    news_images()
    snapshot(mode)
    print(json.dumps(LOG, ensure_ascii=False))
