"""Свежие новости для сайта: те же тексты, что задача Claude пишет для Telegram (tg/news_queue.json), → site/news_live.json.

Запускается задачей новостей (content/prompts/tg-news.md) после записи очереди; push в site/ публикует сайт.
На сайте они встают в ленту «Новости» и в «Главное» сверху (по времени), с фото из статьи; дубли утренних новостей сайт отсекает по адресу.
Храним 3 дня, как и утренние новости.
"""
import datetime as dt
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RU = {"ANA": "Анахайм", "BOS": "Бостон", "BUF": "Баффало", "CAR": "Каролин", "CBJ": "Коламбус", "CGY": "Калгари",
      "CHI": "Чикаго", "COL": "Колорадо", "DAL": "Даллас", "DET": "Детройт", "EDM": "Эдмонтон", "FLA": "Флорид",
      "LAK": "Лос-Анджелес", "MIN": "Миннесот", "MTL": "Монреал", "NJD": "Нью-Джерси", "NSH": "Нэшвилл",
      "NYI": "Айлендерс", "NYR": "Рейнджерс", "OTT": "Оттав", "PHI": "Филадельфи", "PIT": "Питтсбург",
      "SEA": "Сиэтл", "SJS": "Сан-Хосе", "STL": "Сент-Луис", "TBL": "Тамп", "TOR": "Торонто", "UTA": "Ют",
      "VAN": "Ванкувер", "VGK": "Вегас", "WPG": "Виннипег", "WSH": "Вашингтон"}


def main():
    try:
        q = json.load(open(os.path.join(ROOT, "tg", "news_queue.json"), encoding="utf-8")).get("items", [])
    except Exception:
        q = []
    cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    out = []
    for x in q:
        t = str(x.get("ready") or x.get("written") or "")
        if not x.get("text") or not x.get("title") or t < cut:
            continue
        txt = f"{x['title']} {x['text']}"
        teams = sorted({a for a, n in RU.items() if re.search(r"«" + re.escape(n), txt)}, key=lambda a: txt.find("«" + RU[a]))
        out.append(dict(id=x["id"], title=x["title"], text=x["text"], image=x.get("image"), url=x.get("url"), source=x.get("source"),
                        time=t, teams=teams[:2]))
    out.sort(key=lambda x: x["time"], reverse=True)
    json.dump(dict(t=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), items=out),
              open(os.path.join(ROOT, "site", "news_live.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"news_live: {len(out)}")


if __name__ == "__main__":
    main()
