"""Разведка: DNS и ответ nhl-stats.ru. Пишет tg/dns_probe.json. Ничего не постит."""
import json, os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rep = {}
for cmd in ["curl -s 'https://dns.google/resolve?name=nhl-stats.ru&type=A'", "curl -s 'https://dns.google/resolve?name=www.nhl-stats.ru&type=CNAME'",
            "curl -sI http://nhl-stats.ru/ | head -5", "curl -sI https://levastak.github.io/nhl-svodka/ | head -4"]:
    rep[cmd] = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40).stdout[-700:]
json.dump(rep, open(os.path.join(ROOT, "tg", "dns_probe.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False))
