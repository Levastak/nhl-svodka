"""Медиа для Telegram-канала: лента новостей (NHL.com + ESPN) и видео голов (официальные клипы НХЛ на Brightcove).

feed()        — свежие истории с фото (NHL.com, ESPN, инсайды и издания по RSS, поиск по россиянам) → tg/feed.json (хранится 2 дня); новости из неё выбирает и пишет задача Claude (content/prompts/tg-news.md).
highlights()  — выбор моментов ночи из gamecenter НХЛ: хет-трики (склейка всех голов), голы в овертайме, сравнивания в концовке,
                голы россиян → data.highlights; подписи пишет задача Opus (data.tg.videos).
clip()/concat()/probe() — скачать клип (yt-dlp через плеер Brightcove НХЛ), склеить (ffmpeg), узнать размер и длительность.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.path.join(ROOT, "tg")
BC = "https://players.brightcove.net/6415718365001/D3UCGynRWU_default/index.html?videoId={}"
UA = {"User-Agent": "Mozilla/5.0 (NHL-STATS.RU; +https://levastak.github.io/nhl-svodka/)"}


def _get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


# ---------------------------------------------------------------- лента новостей
# Источники (разведка 16.10): официальные (NHL.com, ESPN), инсайды и издания (ProHockeyRumors — сводка слухов и
# сообщений инсайдеров с источником, Sportsnet — Фридман, Daily Faceoff, The Hockey News), RMNB — «Вашингтон»
# и его россияне, плюс поиск Bing News по фамилиям всех россиян лиги (любые издания).
RSS = [("ProHockeyRumors", "https://www.prohockeyrumors.com/feed"),
       ("Sportsnet", "https://www.sportsnet.ca/hockey/nhl/feed/"),
       ("Daily Faceoff", "https://www.dailyfaceoff.com/feed"),
       ("The Hockey News", "https://thehockeynews.com/.rss/full/"),
       ("RMNB", "https://russianmachineneverbreaks.com/feed/")]
INSIDER = r"friedman|lebrun|seravalli|dreger|pagnotta|kypreos|mckenzie|32 thoughts|insider|rumou?r|reportedly|according to|keeping tabs|interest in|trade talk|could be moved|on the block|request(ed)? a trade"
BUA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def _txt(url, n=600000, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=BUA), timeout=timeout) as r:
        return r.read(n).decode("utf-8", "replace")


def _iso(pub):
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(pub).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _rss(source, url, LOG, limit=40):
    import html as _h
    import xml.etree.ElementTree as ET
    MR = "{http://search.yahoo.com/mrss/}"
    out = []
    try:
        root = ET.fromstring(_txt(url).encode("utf-8"))
    except Exception as ex:
        # отдельный источник ленты недоступен — не сбой канала: пишем в журнал, Льва не тревожим
        LOG.setdefault("warn", []).append(f"лента {source}: {ex!r}"[:150])
        return out
    for it in root.findall(".//item")[:limit]:
        link = (it.findtext("link") or "").strip()
        title = _h.unescape((it.findtext("title") or "").strip())
        if not link or not title or "sn-collection" in link or title.lower().endswith("featured"):
            continue
        src = source
        if "bing.com" in link:  # Bing отдаёт ссылку-переадресацию, настоящий адрес — в параметре url
            q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
            link = (q.get("url") or [link])[0]
            src = (it.findtext("{http://www.bing.com:80/news/search/}Source") or urllib.parse.urlparse(link).netloc.replace("www.", ""))
        img = None
        for tag in (MR + "content", MR + "thumbnail", "enclosure"):
            el = it.find(tag)
            if el is not None and el.get("url") and (tag != "enclosure" or "image" in (el.get("type") or "image")):
                img = el.get("url")
                break
        desc = re.sub(r"<[^>]+>", " ", _h.unescape(it.findtext("description") or ""))
        desc = re.sub(r"\s+", " ", desc).strip()[:600]
        cats = [c.text for c in it.findall("category") if c.text][:10]
        blob = f"{title} {desc}".lower()
        out.append(dict(id=f"{source.lower().replace(' ', '')}:{re.sub(r'[^a-z0-9]+', '-', urllib.parse.urlparse(link).path.lower()).strip('-')[-80:]}",
                        source=src, title=title, summary=desc, image=img, url=link, time=_iso(it.findtext("pubDate")),
                        kind="insider" if re.search(INSIDER, blob) else "story", tags=cats))
    return out


def _og(url):
    import html as _h
    try:
        t = _txt(url, 300000, 20)
    except Exception:
        return None
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t)
         or re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', t))
    u = _h.unescape(m.group(1)) if m else None
    return u if u and not re.search(r"logo|\.svg", u, re.I) else None


def feed(LOG):
    items = {x["id"]: x for x in _load(f"{TG}/feed.json", {}).get("items", [])}
    n0 = len(items)
    try:
        j = _get("https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=nhl&$limit=30")
        for x in j.get("items", []):
            tags = [t.get("slug") for t in x.get("tags") or []]
            th = (x.get("thumbnail") or {}).get("templateUrl") or ""
            if not th:
                continue
            items[f"nhl:{x['slug']}"] = dict(id=f"nhl:{x['slug']}", source="NHL.com", title=x.get("headline") or x.get("title"),
                                             summary=x.get("summary") or "", image=th.replace("{formatInstructions}", "t_ratio16_9-size50"),
                                             url=f"https://www.nhl.com/news/{x['slug']}", time=x.get("contentDate"),
                                             kind="recap" if "game-recap" in tags else "story", tags=tags[:10])
    except Exception as ex:
        LOG["fail"].append(f"feed nhl: {ex!r}"[:150])
    try:
        j = _get("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?limit=40")
        for a in j.get("articles", []):
            if a.get("type") in ("Preview", "Media") or not a.get("images"):
                continue
            img = max(a["images"], key=lambda i: (i.get("width") or 0))
            items[f"espn:{a.get('id')}"] = dict(id=f"espn:{a.get('id')}", source="ESPN", title=a.get("headline"), summary=a.get("description") or "",
                                                image=img.get("url"), url=((a.get("links") or {}).get("web") or {}).get("href"),
                                                time=a.get("published"), kind="recap" if a.get("type") == "Recap" else "story",
                                                tags=[c.get("description") for c in a.get("categories") or [] if c.get("description")][:10])
    except Exception as ex:
        LOG["fail"].append(f"feed espn: {ex!r}"[:150])
    # инсайды и издания
    for src, url in RSS:
        for x in _rss(src, url, LOG):
            items.setdefault(x["id"], x)
    # россияне — поиск Bing News по фамилиям (группами по 6), любые издания
    try:
        D = _load(os.path.join(ROOT, "site", "data.json"), {})
        last = sorted({r["name"].split(" ")[-1] for r in D.get("russians") or [] if r.get("name")})
        for i in range(0, len(last), 6):
            q = "(" + " OR ".join(last[i:i + 6]) + ") NHL"
            for x in _rss("Bing", "https://www.bing.com/news/search?format=rss&q=" + urllib.parse.quote(q), LOG, 25):
                x["id"] = "web:" + re.sub(r"[^a-z0-9]+", "-", (urllib.parse.urlparse(x["url"]).netloc + urllib.parse.urlparse(x["url"]).path).lower()).strip("-")[-90:]
                x["russian_search"] = True
                items.setdefault(x["id"], x)
    except Exception as ex:
        LOG["fail"].append(f"feed bing: {ex!r}"[:150])
    # дубли одной истории (одинаковый заголовок у разных разделов и изданий) — оставляем первую по времени
    seen, uniq = set(), {}
    for x in sorted(items.values(), key=lambda x: str(x.get("time"))):
        k = re.sub(r"\W+", "", str(x.get("title") or "").lower())[:80]
        if k in seen:
            continue
        seen.add(k)
        uniq[x["id"]] = x
    items = uniq
    cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    keep = sorted([x for x in items.values() if str(x.get("time") or "") >= cut], key=lambda x: str(x.get("time")), reverse=True)[:250]
    # фото: у кого нет картинки в ленте — берём обложку статьи (og:image), не больше 25 запросов за запуск
    tries = 0
    for x in keep:
        if x.get("image") or x.get("og_tried") or tries >= 25:
            continue
        tries += 1
        x["image"] = _og(x["url"])
        x["og_tried"] = True
    os.makedirs(TG, exist_ok=True)
    json.dump(dict(t=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), items=keep),
              open(f"{TG}/feed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    by = {}
    for x in keep:
        by[x["source"]] = by.get(x["source"], 0) + 1
    LOG["ok"].append(f"лента: {len(keep)} историй, новых {max(0, len(keep) - n0)}; " + ", ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:8]))


# ---------------------------------------------------------------- моменты ночи
def highlights(get, data, archive, day, LOG):
    """data.highlights: до 3 видео-моментов ночи. Приоритет: хет-трик (лучше россиянина) → гол в овертайме → сравнивание
    в последние 2 минуты → гол россиянина. У каждого: key, kind, player, team, game, clips[{id,url,period,time}], note."""
    rus = {x.get("name") for x in data.get("russians") or []}
    games = [g for g in archive.get("games", []) if g.get("date") == day]
    cands = []
    for g in games:
        land, _ = get(f"https://api-web.nhle.com/v1/gamecenter/{g['id']}/landing", label=f"highlights {g['id']}")
        if not land:
            continue
        goals = []
        for per in (land.get("summary") or {}).get("scoring") or []:
            pn = (per.get("periodDescriptor") or {}).get("number")
            pt = (per.get("periodDescriptor") or {}).get("periodType")
            for x in per.get("goals") or []:
                if not x.get("highlightClip"):
                    continue
                name = f"{(x.get('firstName') or {}).get('default', '')} {(x.get('lastName') or {}).get('default', '')}".strip()
                goals.append(dict(id=x["highlightClip"], url=x.get("highlightClipSharingUrl"), period=pn, ptype=pt, time=x.get("timeInPeriod"),
                                  player=name, team=x.get("teamAbbrev", {}).get("default") if isinstance(x.get("teamAbbrev"), dict) else x.get("teamAbbrev"),
                                  away=x.get("awayScore"), home=x.get("homeScore"), strength=x.get("strength"), mod=x.get("goalModifier")))
        by = {}
        for x in goals:
            by.setdefault(x["player"], []).append(x)
        for p, gl in by.items():
            if len(gl) >= 3:
                cands.append(dict(score=100 + (20 if p in rus else 0) + len(gl), kind="hattrick", player=p, team=gl[0]["team"], game=g["id"], clips=gl))
        for x in goals:
            mm = int(str(x.get("time") or "0:0").split(":")[0])
            if x.get("ptype") == "OT":
                cands.append(dict(score=80 + (10 if x["player"] in rus else 0), kind="ot_winner", player=x["player"], team=x["team"], game=g["id"], clips=[x]))
            elif x.get("period") == 3 and mm >= 18 and x.get("away") == x.get("home"):
                cands.append(dict(score=75 + (10 if x["player"] in rus else 0), kind="late_equalizer", player=x["player"], team=x["team"], game=g["id"], clips=[x]))
            elif x["player"] in rus:
                cands.append(dict(score=40, kind="russian_goal", player=x["player"], team=x["team"], game=g["id"], clips=[x]))
    cands.sort(key=lambda c: -c["score"])
    out, used_games, used_players = [], set(), set()
    for c in cands:
        if c["player"] in used_players or c["game"] in used_games:
            continue
        if c["kind"] == "hattrick" and any(o["kind"] == "hattrick" for o in out):
            continue  # одна склейка хет-трика в день, дальше — отдельные голы
        # голы из уже взятой склейки хет-трика не повторяем
        if any(c["clips"][0]["id"] in [k["id"] for k in o["clips"]] for o in out):
            continue
        c["key"] = f"video:{day}:{c['kind']}:{c['clips'][0]['id']}"
        out.append(c)
        used_games.add(c["game"])
        used_players.add(c["player"])
        if len(out) >= 3:
            break
    for c in out:
        c.pop("score", None)
    data["highlights"] = dict(date=day, items=out)
    LOG["ok"].append(f"видео-моменты: {len(out)} ({', '.join(c['kind'] for c in out)})")


# ---------------------------------------------------------------- видео
def tools(LOG):
    ok = True
    try:
        import yt_dlp  # noqa: F401
    except Exception:
        ok = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"], capture_output=True).returncode == 0
    if not shutil.which("ffmpeg"):
        r = subprocess.run("sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg", shell=True, capture_output=True, text=True)
        if r.returncode:
            LOG["fail"].append(f"ffmpeg: {r.stderr[-150:]}")
            ok = False
    return ok


def clip(cid, out_dir):
    fn = os.path.join(out_dir, f"{cid}.mp4")
    if not os.path.exists(fn):
        subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "-f", "best[height<=720]/best", "-o", fn, BC.format(cid)],
                       capture_output=True, text=True, timeout=300)
    return fn if os.path.exists(fn) else None


def concat(paths, out):
    lst = out + ".txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in paths))
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "scale=-2:720", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "25", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out],
                       capture_output=True, text=True, timeout=900)
    os.remove(lst)
    return out if r.returncode == 0 and os.path.exists(out) else None


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        s = (j.get("streams") or [{}])[0]
        return s.get("width"), s.get("height"), int(float((j.get("format") or {}).get("duration") or 0))
    except Exception:
        return None, None, None


def thumb(path, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", path, "-frames:v", "1", "-vf", "scale=320:-2", out], capture_output=True)
    return out if os.path.exists(out) else None
