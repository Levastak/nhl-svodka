"""Разведка: проверка DNS домена nhl-stats.ru снаружи (Google DNS и NS-серверы зоны). Пишет tg/dns_probe.json. Ничего не постит."""
import json, os, subprocess, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rep = {}
for name, typ in [("nhl-stats.ru", "NS"), ("nhl-stats.ru", "A"), ("www.nhl-stats.ru", "CNAME"), ("nhl-stats.ru", "SOA")]:
    try:
        with urllib.request.urlopen(f"https://dns.google/resolve?name={name}&type={typ}", timeout=20) as r:
            rep[f"google {name} {typ}"] = json.loads(r.read())
    except Exception as ex:
        rep[f"google {name} {typ}"] = repr(ex)
for cmd in ["dig +short NS nhl-stats.ru", "dig +short A nhl-stats.ru @ns1.reg.ru", "dig +short CNAME www.nhl-stats.ru @ns1.reg.ru",
            "dig +short NS nhl-stats.ru @a.dns.ripn.net", "whois nhl-stats.ru"]:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
    rep[cmd] = (r.stdout + r.stderr)[-1500:]
json.dump(rep, open(os.path.join(ROOT, "tg", "dns_probe.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False)[:3000])
