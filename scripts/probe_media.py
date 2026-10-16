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
for name, url in [] and [("espn", "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?limit=30"),
                  ("nhl_forge", "https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?$limit=20"),
                  ("nhl_forge2", "https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug=news&$limit=20")]:
    try:
        t = get(url)
        open(os.path.join(OUT, f"{name}.json"), "w").write(t[:400000])
        rep[name] = f"ok {len(t)}"
    except Exception as ex:
        rep[name] = repr(ex)[:200]
# видео: аккаунт Brightcove со страницы nhl.com и попытка скачать через players.brightcove.net
try:
    import re
    page = get("https://www.nhl.com/video/buf-tor-marchenko-scores-goal-against-ukko-pekka-luukkonen-6406934257112")
    rep["page_len"] = len(page)
    pats = {k: sorted(set(re.findall(v, page)))[:5] for k, v in {
        "bc_player": r"players\.brightcove\.net/(\d+)/([A-Za-z0-9_-]+)_default",
        "account": r"[\"']?account(?:Id|_id)?[\"']?\s*[:=]\s*[\"']?(\d{10,16})",
        "data_account": r"data-account=[\"'](\d+)",
        "mp4": r"https?://[^\"' ]+\.mp4",
        "m3u8": r"https?://[^\"' ]+\.m3u8",
        "og_video": r'<meta[^>]+property="og:video[^"]*"[^>]+content="([^"]+)"'}.items()}
    rep["patterns"] = pats
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"], check=False)
    accs = [a for a, _ in pats["bc_player"]] or pats["data_account"] or pats["account"] or ["6415718365001"]
    plays = [p for _, p in pats["bc_player"]] or ["default"]
    vid = "6406934257112"
    for acc in accs[:2]:
        for pl in plays[:2]:
            url = f"https://players.brightcove.net/{acc}/{pl}_default/index.html?videoId={vid}"
            fn = os.path.join(OUT, "t.mp4")
            r = subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "-f", "best[height<=720]/best", "-o", fn, url], capture_output=True, text=True, timeout=300)
            rep[f"bc_{acc}_{pl}"] = (r.returncode, r.stderr[-300:], os.path.getsize(fn) if os.path.exists(fn) else 0)
            if os.path.exists(fn):
                pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", fn], capture_output=True, text=True)
                rep["probe"] = pr.stdout[:300]
                os.remove(fn)
except Exception as ex:
    rep["video"] = repr(ex)[:300]
json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False)[:2000])
