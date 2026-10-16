"""Разведка: скачать ассеты для макетов карточек (логотипы, портреты, фото из историй NHL.com) в tg/mock/. Ничего не постит."""
import json, os, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tg", "mock")
os.makedirs(OUT, exist_ok=True)
rep = {}
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NHL-STATS.RU"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()
def save(name, url):
    try:
        b = get(url); open(os.path.join(OUT, name), "wb").write(b); rep[name] = len(b)
    except Exception as ex:
        rep[name] = repr(ex)[:150]
for t in ["ANA", "BOS", "COL", "PIT"]:
    save(f"logo_{t}.svg", f"https://assets.nhle.com/logos/nhl/svg/{t}_dark.svg")
heads = ["20262027/COL/8478406", "20262027/PIT/8471675", "20262027/PIT/8481668", "20262027/COL/8477492", "20262027/COL/8475809",
         "20262027/PIT/8483703", "20262027/PIT/8474578", "20262027/ANA/8484153", "20262027/ANA/8484762", "20262027/BOS/8477956",
         "20262027/ANA/8478024", "20262027/BOS/8480022", "20262027/BOS/8480280", "20262027/ANA/8480843", "20262027/ANA/8475798", "20262027/BOS/8483489"]
for h in heads:
    save("head_" + h.split("/")[-1] + ".png", f"https://assets.nhle.com/mugs/nhl/{h}.png")
# фото из историй NHL.com по клубам
for slug in ["anaheim-ducks", "boston-bruins", "colorado-avalanche", "pittsburgh-penguins"]:
    try:
        j = json.loads(get(f"https://forge-dapi.d3.nhle.com/v2/content/en-us/stories?tags.slug={slug}&$limit=8"))
        k = 0
        for x in j.get("items", []):
            th = (x.get("thumbnail") or {}).get("templateUrl") or ""
            if not th:
                continue
            save(f"photo_{slug}_{k}.jpg", th.replace("{formatInstructions}", "t_ratio16_9-size100"))
            rep[f"photo_{slug}_{k}.title"] = x.get("headline")
            k += 1
            if k >= 3:
                break
    except Exception as ex:
        rep[slug] = repr(ex)[:150]
json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(rep, ensure_ascii=False, indent=1))
