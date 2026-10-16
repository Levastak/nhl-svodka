"""Разведка/эксперименты медиа. stage в третьей строке trigger/tg; music — поиск свободной музыки. Ничего не постит."""
import json, os, re, subprocess, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lines = open(os.path.join(ROOT, "trigger", "tg")).read().split("\n")
stage = (lines[2].strip() if len(lines) > 2 else "") or "stage1"
if stage == "dns":
    rep = {}
    for q in ["nhl-stats.ru&type=CAA", "nhl-stats.ru&type=A", "nhl-stats.ru&type=AAAA", "www.nhl-stats.ru&type=CNAME", "_github-pages-challenge-levastak.nhl-stats.ru&type=TXT"]:
        try:
            rep[q] = urllib.request.urlopen("https://dns.google/resolve?name=" + q, timeout=30).read().decode()[:500]
        except Exception as ex:
            rep[q] = repr(ex)
    for name, url in [("cloudflare", "https://cloudflare-dns.com/dns-query?name=nhl-stats.ru&type=A"), ("quad9", "https://dns.quad9.net:5053/dns-query?name=nhl-stats.ru&type=A"),
                      ("cloudflare-www", "https://cloudflare-dns.com/dns-query?name=www.nhl-stats.ru&type=CNAME")]:
        try:
            rep[name] = urllib.request.urlopen(urllib.request.Request(url, headers={"accept": "application/dns-json"}), timeout=30).read().decode()[:400]
        except Exception as ex:
            rep[name] = repr(ex)
    for cmd in ["dig +short A nhl-stats.ru @1.1.1.1", "dig +short A nhl-stats.ru @8.8.8.8", "dig +short A nhl-stats.ru @9.9.9.9", "dig +short NS nhl-stats.ru @a.dns.ripn.net", "dig +trace nhl-stats.ru A | tail -12", "curl -sI https://nhl-stats.ru/ | head -3", "curl -sI http://nhl-stats.ru/ | head -3", "curl -sI http://www.nhl-stats.ru/ | head -4"]:
        rep[cmd] = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40).stdout + subprocess.run(cmd.replace("-sI", "-sIv").split("|")[0] + " 2>&1 | grep -i 'subject\\|issuer\\|SSL' | head -4", shell=True, capture_output=True, text=True, timeout=40).stdout
    json.dump(rep, open(os.path.join(ROOT, "tg", "dns_probe.json"), "w"), ensure_ascii=False, indent=1)
elif stage == "music2":
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
