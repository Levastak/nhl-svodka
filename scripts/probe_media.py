"""Разведка: ленты новостей (ESPN, NHL.com) и видео голов (yt-dlp + ffmpeg). Пишет tg/probe/*.json. Ничего не постит."""
import json, os, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tg", "probe")
os.makedirs(OUT, exist_ok=True)
rep = {}
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NHL-STATS.RU"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")
for name, url in [("espn", "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?limit=30"),
                  ("nhl_forge", "https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?$limit=20"),
                  ("nhl_forge2", "https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=news&$limit=20")]:
    try:
        t = get(url)
        open(os.path.join(OUT, f"{name}.json"), "w").write(t[:400000])
        rep[name] = f"ok {len(t)}"
    except Exception as ex:
        rep[name] = repr(ex)[:200]
# видео: голы Марченко в матче 2026020108
try:
    land = json.loads(get("https://api-web.nhle.com/v1/gamecenter/2026020108/landing"))
    goals = [g for p in land["summary"]["scoring"] for g in p["goals"]]
    mg = [g for g in goals if g.get("lastName", {}).get("default") == "Marchenko"]
    rep["marchenko_goals"] = [(g.get("timeInPeriod"), g.get("highlightClipSharingUrl"), g.get("highlightClip")) for g in mg]
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"], check=False)
    files = []
    for i, g in enumerate(mg):
        fn = os.path.join(OUT, f"m{i}.mp4")
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "-f", "best[height<=720]/best", "-o", fn, g["highlightClipSharingUrl"]],
                           capture_output=True, text=True, timeout=300)
        rep[f"dl{i}"] = (r.returncode, r.stderr[-300:], os.path.getsize(fn) if os.path.exists(fn) else 0)
        if os.path.exists(fn):
            files.append(fn)
    if files:
        lst = os.path.join(OUT, "list.txt")
        open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
        out = os.path.join(OUT, "hattrick.mp4")
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "24", "-c:a", "aac", "-movflags", "+faststart", out], capture_output=True, text=True, timeout=600)
        rep["concat"] = (r.returncode, r.stderr[-300:], os.path.getsize(out) if os.path.exists(out) else 0)
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", out], capture_output=True, text=True)
        rep["probe"] = pr.stdout[:400]
        for f in files + [out, lst]:
            try:
                os.remove(f)
            except Exception:
                pass
except Exception as ex:
    rep["video"] = repr(ex)[:300]
json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False)[:2000])
