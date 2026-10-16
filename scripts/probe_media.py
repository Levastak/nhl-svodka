"""Разведка/эксперименты медиа. stage в третьей строке trigger/tg; music — поиск свободной музыки. Ничего не постит."""
import json, os, re, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lines = open(os.path.join(ROOT, "trigger", "tg")).read().split("\n")
stage = (lines[2].strip() if len(lines) > 2 else "") or "stage1"
if stage == "music2":
    import urllib.parse
    names = ["Volatile Reaction", "Movement Proposition", "Take a Chance", "Exhilarate", "Hit n Smash", "Rhinoceros", "Crusade - Heavy Industry",
             "Big Rock", "Hard Boiled", "Interloper", "Raving Energy", "Rock Angel", "Rollin at 5", "Hot Swing", "Overcast", "Ready Aim Fire",
             "Pump", "Aggressor", "Malicious", "Dark Rock", "Funk Game Loop", "Club Diver", "Five Armies", "Prelude and Action", "Killers"]
    rep = {}
    os.makedirs("/tmp/mus", exist_ok=True)
    for n in names:
        u = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + urllib.parse.quote(n) + ".mp3"
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
            fn = f"/tmp/mus/{n.replace(' ', '_')}.mp3"; open(fn, "wb").write(b)
            r = subprocess.run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{fn}'", shell=True, capture_output=True, text=True)
            rep[n] = dict(ok=True, size=len(b), dur=r.stdout.strip())
            # 20-секундный отрывок из середины для прослушивания
            subprocess.run(f"ffmpeg -y -loglevel error -ss 20 -t 20 -i '{fn}' -b:a 96k '{ROOT}/tg/demo/m_{n.replace(' ', '_')}.mp3'", shell=True)
        except Exception as ex:
            rep[n] = repr(ex)[:120]
    json.dump(rep, open(os.path.join(ROOT, "tg", "demo", "music_probe.json"), "w"), ensure_ascii=False, indent=1)
elif stage == "music":
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
