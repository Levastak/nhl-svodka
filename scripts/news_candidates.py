"""Кандидаты для задачи «Сводка НХЛ: новости в Telegram» (content/prompts/tg-news.md) → tg/news_candidates.json.

Задача запускается раз в 2 часа; чтобы Claude не перечитывал ленту, словарь и большой data.json, отбор делает скрипт:
отсекает уже написанное, уже вышедшее в канал, утренние новости сайта и пересказы матчей без рекордов и травм;
находит в заголовке, описании и тегах игроков (россиян, звёзд) и клубы; ставит уровень приоритета (решение Льва 16.10):
1 — россияне, 2 — звёзды и решения лиги/тренеры, 3 — клубы первой восьмёрки конференции, 4 — остальное.
status: "empty" — новых нет; "site" — дневной лимит канала выбран и нет кандидатов 1-го уровня: новости пишутся только для сайта (tg = false); "ok" — можно писать.
Запускается самой задачей первым шагом, сеть не нужна.
"""
import datetime as dt
import json
import os
import re
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE, TG = os.path.join(ROOT, "site"), os.path.join(ROOT, "tg")
MSK = ZoneInfo("Europe/Moscow")
FEED_CAP = 5
CONF = {"Atlantic": "E", "Metropolitan": "E", "Central": "W", "Pacific": "W"}
EN = {"ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres", "CAR": "Carolina Hurricanes", "CBJ": "Columbus Blue Jackets",
      "CGY": "Calgary Flames", "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "DAL": "Dallas Stars", "DET": "Detroit Red Wings",
      "EDM": "Edmonton Oilers", "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montreal Canadiens",
      "NJD": "New Jersey Devils", "NSH": "Nashville Predators", "NYI": "New York Islanders", "NYR": "New York Rangers", "OTT": "Ottawa Senators",
      "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins", "SEA": "Seattle Kraken", "SJS": "San Jose Sharks", "STL": "St. Louis Blues",
      "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs", "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
      "WPG": "Winnipeg Jets", "WSH": "Washington Capitals"}
NICK = {a: n.split(" ")[-1] for a, n in EN.items()}
NICK.update({"TOR": "Maple Leafs", "DET": "Red Wings", "CBJ": "Blue Jackets", "VGK": "Golden Knights", "UTA": "Mammoth"})
JUNK = r"betmgm|draftkings|fanduel|sportsbook|projected lineup|daily digest|fantasy|betting|odds|best bets|picks|prop|power rankings|mailbag|notebook|prospect|chl |ahl |ohl |whl |qmjhl|podcast|quiz|how to watch|watch:|tickets|hockey fights cancer"
HOT = r"\b(record|milestone|first ever|suspend|suspension|fired|hired|named coach|head coach|trade[ds]?|acquire[ds]?|sign(s|ed)?|extension|contract|surgery|out for season|out indefinitely|injur|retire)"


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def norm(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def main():
    now = dt.datetime.now(dt.timezone.utc)
    D = load(f"{SITE}/data.json", {})
    NR = load(f"{SITE}/names_ru.json", {}) or {}
    feed = (load(f"{TG}/feed.json", {}) or {}).get("items", [])
    queue = (load(f"{TG}/news_queue.json", {}) or {}).get("items", [])
    state = load(f"{TG}/state.json", {}) or {}
    P = state.get("posted") or {}
    done_ids = {q.get("id") for q in queue} | {k[5:] for k in P if k.startswith("feed:")}
    site_urls = {n.get("url") for n in D.get("news") or []}
    today = now.astimezone(MSK).date()
    hotq = {f"feed:{q.get('id')}" for q in queue if q.get("hot")}
    fed_today = sum(1 for k, v in P.items() if k.startswith("feed:")
                    and dt.datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(MSK).date() == today)
    queued = [q for q in queue if f"feed:{q.get('id')}" not in P and q.get('tg') is not False]  # ждут выхода в канал и едят лимит (горячие тоже, решение 17.10)

    # кто есть кто
    rus = {x["name"] for x in D.get("russians") or []}
    sk = sorted(D.get("skaters") or [], key=lambda s: (-s.get("pts", 0), -s.get("g", 0)))
    top100 = {s["name"] for s in sk[:100]}
    best = {}
    for s in sk:
        best.setdefault(s["team"], s["name"])
    gk = {}
    for g in sorted(D.get("goalies") or [], key=lambda g: -g.get("gp", 0)):
        gk.setdefault(g.get("team"), g.get("name"))
    stars = top100 | set(best.values()) | set(gk.values())
    team_of = {s["name"]: s["team"] for s in sk}
    team_of.update({g.get("name"): g.get("team") for g in D.get("goalies") or []})
    st = D.get("standings") or []
    place = {}
    for c in ("E", "W"):
        rows = sorted([x for x in st if CONF.get(x.get("div")) == c], key=lambda x: (-x.get("pts", 0), x.get("gp", 0)))
        for i, x in enumerate(rows):
            place[x["abbr"]] = (i + 1, "Запад" if c == "W" else "Восток", x.get("pts"), x.get("gp"))
    people = set(NR) | rus | set(team_of)
    by_last = {}
    for n in people:
        by_last.setdefault(norm(n.split(" ")[-1]), set()).add(n)

    cands = []
    for x in feed:
        if x.get("id") in done_ids or x.get("url") in site_urls:
            continue
        text = f"{x.get('title') or ''}. {x.get('summary') or ''}. {' '.join(x.get('tags') or [])}"
        nt = norm(text)
        hot = bool(re.search(HOT, nt))
        # актуальность (решение Льва 17.10): только свежее (до 18 ч), без пересказов и видео уже обсуждённых матчей
        try:
            age_h = (now - dt.datetime.fromisoformat(str(x.get("time")).replace("Z", "+00:00"))).total_seconds() / 3600
        except Exception:
            age_h = 0
        if age_h > 18:
            continue
        if x.get("kind") == "recap" or re.search(r"goal of|video|highlight|hat trick|hat-trick|game recap|takeaways|observations|rapid reaction|wanted credit|warmup", nt):
            if not re.search(r"injur|record|milestone|suspen|trade|sign", nt):
                continue
        if re.search(JUNK, norm(x.get("title") or "")):
            continue
        found = set()
        for n in people:
            if norm(n) in nt:
                found.add(n)
        teams = [a for a in EN if norm(EN[a]) in nt or re.search(r"\b" + norm(NICK[a]) + r"\b", nt)]
        tier = 4
        why = []
        ttl = norm(x.get("title") or "")
        rus_title = {n for n in found & rus if norm(n.split(" ")[-1]) in ttl}
        if rus_title:
            tier, why = 1, [f"россиянин в заголовке: {', '.join(NR.get(n, n) for n in rus_title)}"]
        elif found & rus:
            tier, why = 2, [f"упоминается россиянин: {', '.join(NR.get(n, n) for n in found & rus)}"]
        elif found & stars or re.search(r"commissioner|bettman|suspend|fired|named coach|head coach|\brecord", nt):
            tier, why = 2, [f"звёзды: {', '.join(NR.get(n, n) for n in found & stars)}" if found & stars else "лига / тренеры / рекорд"]
        elif any(place.get(t, (99,))[0] <= 8 for t in teams):
            tier, why = 3, ["клуб из первой восьмёрки конференции"]
        cands.append(dict(id=x["id"], tier=tier, why="; ".join(why), maybe_hot=hot or None, insider=x.get("kind") == "insider" or None,
                          source=x.get("source"), kind=x.get("kind"),
                          time=x.get("time"), title=x.get("title"), summary=x.get("summary"), article=x.get("body"), url=x.get("url"), image=x.get("image"),
                          players=[{k: v for k, v in dict(name=n, ru=NR.get(n), team=team_of.get(n), russian=n in rus or None, star=n in stars or None).items() if v}
                                   for n in sorted(found)],
                          teams=[dict(abbr=t, place=f"{place[t][0]}-е, {place[t][1]}", pts=place[t][2], gp=place[t][3]) for t in teams if t in place]))
    cands.sort(key=lambda c: (c["tier"], str(c.get("time") or "")), reverse=False)
    cands = sorted(cands, key=lambda c: (c["tier"], -(dt.datetime.fromisoformat(str(c["time"]).replace("Z", "+00:00")).timestamp() if c.get("time") else 0)))[:12]
    left = FEED_CAP - fed_today - len(queued)
    if not cands:
        status = "empty"
    elif left <= 0:
        status = "site"  # канал на сегодня полон — пишем только для сайта (tg = false)
    else:
        status = "ok"
    out = dict(t=now.strftime("%Y-%m-%dT%H:%M:%SZ"), status=status, cap=FEED_CAP, posted_today=fed_today, queued_not_posted=len(queued),
               slots_left=max(0, left), msk_now=now.astimezone(MSK).strftime("%H:%M"),
               recent_titles=[q.get("title") for q in queue[-16:]] + [x.get("title") for x in (load(f"{SITE}/stories.json", []) or [])[:4] if isinstance(x, dict)], morning_site_news=[n.get("title") for n in D.get("news") or []],
               candidates=cands)
    json.dump(out, open(f"{TG}/news_candidates.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"news_candidates: {status}, кандидатов {len(cands)} (уровни {[c['tier'] for c in cands]}), сегодня вышло {fed_today}, в очереди {len(queued)}")


if __name__ == "__main__":
    main()
