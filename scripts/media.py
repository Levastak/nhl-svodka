"""Медиа для Telegram-канала: лента новостей (NHL.com + ESPN) и видео голов (официальные клипы НХЛ на Brightcove).

feed()        — свежие истории с фото → tg/feed.json (хранится 2 дня); новости из неё выбирает и пишет задача Claude (content/prompts/tg-news.md).
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
    cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    keep = sorted([x for x in items.values() if str(x.get("time") or "") >= cut], key=lambda x: str(x.get("time")), reverse=True)
    os.makedirs(TG, exist_ok=True)
    json.dump(dict(t=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), items=keep[:120]),
              open(f"{TG}/feed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    LOG["ok"].append(f"лента: {len(keep)} историй, новых {max(0, len(items) - n0)}")


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
