"""Разведка источников новостей (инсайды, россияне): RSS и агрегаторы. Пишет tg/sources_probe.json. Ничего не постит."""
import json, os, re, urllib.request, html
import xml.etree.ElementTree as ET
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
def get(url, n=600000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.geturl(), r.read(n).decode("utf-8", "replace")
SRC = {
 "gnews_miroshnichenko": "https://news.google.com/rss/search?q=Miroshnichenko+when:3d&hl=en-US&gl=US&ceid=US:en",
 "gnews_ru_players": "https://news.google.com/rss/search?q=(Kaprizov+OR+Kucherov+OR+Panarin+OR+Ovechkin+OR+Shesterkin+OR+Marchenko)+when:2d&hl=en-US&gl=US&ceid=US:en",
 "bing_miroshnichenko": "https://www.bing.com/news/search?q=Miroshnichenko&format=rss",
 "prohockeyrumors": "https://www.prohockeyrumors.com/feed",
 "sportsnet_nhl": "https://www.sportsnet.ca/hockey/nhl/feed/",
 "sportsnet_all": "https://www.sportsnet.ca/feed/",
 "dailyfaceoff": "https://www.dailyfaceoff.com/feed",
 "thehockeynews": "https://thehockeynews.com/.rss/full/",
 "thehockeynews2": "https://thehockeynews.com/rss",
 "rmnb": "https://russianmachineneverbreaks.com/feed/",
 "nhltraderumors": "https://nhltraderumors.me/feed/",
 "tsn_nhl": "https://www.tsn.ca/rss/nhl",
 "sportsru_nhl": "https://www.sports.ru/rss/rubric.xml?s=209",
 "championat_hockey": "https://www.championat.com/rss/news/hockey/",
}
rep = {}
for k, u in SRC.items():
    try:
        final, t = get(u)
        root = ET.fromstring(t.encode("utf-8")) if t.lstrip().startswith("<") else None
        items = root.findall(".//item") if root is not None else []
        if not items and root is not None:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        smp = []
        for it in items[:6]:
            title = (it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link = (it.findtext("link") or "").strip()
            img = bool(it.find("{http://search.yahoo.com/mrss/}content") is not None or it.find("{http://search.yahoo.com/mrss/}thumbnail") is not None or it.find("enclosure") is not None)
            smp.append(dict(title=title[:140], link=link[:200], pub=it.findtext("pubDate"), img=img))
        rep[k] = dict(ok=True, n=len(items), final=final[:120], sample=smp)
    except Exception as ex:
        rep[k] = dict(ok=False, err=repr(ex)[:200])
# og:image со страницы статьи (первые ссылки из RSS, кроме google)
og = {}
for k, v in rep.items():
    if not v.get("ok") or not v.get("sample") or k.startswith("gnews"):
        continue
    link = v["sample"][0]["link"]
    try:
        final, t = get(link, 300000)
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t) or re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', t)
        og[k] = dict(link=link[:150], final=final[:150], og=html.unescape(m.group(1))[:200] if m else None)
    except Exception as ex:
        og[k] = dict(link=link[:150], err=repr(ex)[:150])
# google news: можно ли раскрыть ссылку на статью
try:
    l = rep["gnews_miroshnichenko"]["sample"][0]["link"]
    final, t = get(l, 200000)
    og["gnews_resolve"] = dict(link=l[:150], final=final[:200], has_og=bool(re.search(r"og:image", t)))
except Exception as ex:
    og["gnews_resolve"] = dict(err=repr(ex)[:200])
rep["og_images"] = og
json.dump(rep, open(os.path.join(ROOT, "tg", "sources_probe.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: (v.get("n") if isinstance(v, dict) and "n" in v else v.get("err") if isinstance(v, dict) else "") for k, v in rep.items() if k != "og_images"}, ensure_ascii=False))
