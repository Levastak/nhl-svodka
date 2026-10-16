"""Разведка/эксперименты медиа. stage в третьей строке trigger/tg; music — поиск свободной музыки. Ничего не постит."""
import json, os, re, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lines = open(os.path.join(ROOT, "trigger", "tg")).read().split("\n")
stage = (lines[2].strip() if len(lines) > 2 else "") or "stage1"
if stage == "music":
    rep = {}
    for u in ["https://freepd.com/", "https://freepd.com/upbeat.php", "https://freepd.com/epic.php", "https://freepd.com/misc.php",
              "https://incompetech.com/music/royalty-free/music.html"]:
        try:
            t = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "replace")
            rep[u] = dict(len=len(t), mp3=sorted(set(re.findall(r'[\\w%/.\\-]+\\.mp3', t)))[:150], links=sorted(set(re.findall(r'href="([^"]+\\.php)"', t)))[:60])
        except Exception as ex:
            rep[u] = repr(ex)[:200]
    json.dump(rep, open(os.path.join(ROOT, "tg", "demo", "music_probe.json"), "w"), ensure_ascii=False, indent=1)
else:
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "video_demo.py"), stage])
