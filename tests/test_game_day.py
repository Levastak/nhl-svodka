"""Never turn the first completed game into a full-day roundup."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from game_day import day_complete, daily_ready, score_status
import texts
import tg
import fetch

DAY = "2026-10-17"


def fixture():
    games = [dict(id=i, date=DAY, home="WSH", away="NJD", hs=4, **{"as": 2}, end="REG", goals=[]) for i in (1, 2)]
    data = dict(results_date=DAY, upcoming_date="2026-10-18", upcoming=[],
                week=[dict(id=i, date=DAY) for i in (1, 2)], russians=[dict(name="Early Star")],
                journal=[dict(result=None, score=None)], final=dict(t="unchanged"))
    box = dict(date=DAY, games=[dict(id=i, home="WSH", away="NJD", players=[
        dict(name=name, team="WSH", pos="R", g=g, a=0, pm=0, sog=4)])
        for i, name, g in [(1, "Early Star", 1), (2, "Late Star", 4)]])
    return data, dict(games=games), box


class GameDayRules(unittest.TestCase):
    def test_running_day_and_missing_schedule_are_not_complete(self):
        d, a, b = fixture()
        a["games"].pop()
        self.assertFalse(day_complete(d, a, box=b))
        d.pop("week")
        self.assertFalse(day_complete(d, a, box=b))

    def test_full_results_still_need_matching_protocols(self):
        d, a, b = fixture()
        self.assertTrue(day_complete(d, a, box=b))
        b["games"].pop()
        self.assertFalse(day_complete(d, a, box=b))
        b["date"] = "2026-10-16"
        self.assertFalse(day_complete(d, a, box=b))

    def test_official_slate_survives_schedule_rollover_and_postponement(self):
        d, a, b = fixture()
        d.pop("week")
        score = dict(games=[dict(id=1, gameType=2, gameState="OFF"),
                            dict(id=2, gameType=2, gameState="FINAL"),
                            dict(id=3, gameType=2, gameState="FUT", gameScheduleState="PPD")])
        d["results_status"] = score_status(DAY, score)
        self.assertTrue(day_complete(d, a, box=b))
        score["games"][1]["gameState"] = "LIVE"
        d["results_status"] = score_status(DAY, score)
        self.assertFalse(day_complete(d, a, box=b))
        self.assertIsNone(score_status(DAY, None))

    def test_old_automatic_stars_are_removed_then_late_star_can_win(self):
        d, a, b = fixture()
        d["daily"] = dict(date=DAY, auto=True, heroes=[dict(name="Early Star")])
        protected = copy.deepcopy({k: d[k] for k in ("journal", "upcoming", "final")})
        full = copy.deepcopy(a)
        a["games"].pop()
        self.assertTrue(texts.refresh_daily(d, a, b))
        self.assertNotIn("heroes", d["daily"])
        self.assertFalse(daily_ready(d, a, b))
        self.assertTrue(texts.refresh_daily(d, full, b))
        self.assertEqual(d["daily"]["heroes"][0]["name"], "Late Star")
        self.assertTrue(daily_ready(d, full, b))
        self.assertNotIn("полезность", json.dumps(d["daily"], ensure_ascii=False).lower())
        self.assertNotIn("0+", d["daily"]["heroes"][0]["text"])
        self.assertEqual({k: d[k] for k in protected}, protected)
        self.assertFalse(texts.refresh_daily(d, full, b))

    def test_manual_complete_day_selection_is_preserved(self):
        d, a, b = fixture()
        d["daily"] = dict(date=DAY, heroes=[dict(name="Editor's choice")])
        old = copy.deepcopy(d["daily"])
        self.assertFalse(texts.refresh_daily(d, a, b))
        self.assertEqual(d["daily"], old)

    def test_bot_drops_roundups_but_keeps_independent_news(self):
        d, a, b = fixture()
        texts.refresh_daily(d, a, b)
        with tempfile.TemporaryDirectory() as tmp:
            site, queue = Path(tmp) / "site", Path(tmp) / "tg"
            site.mkdir(); queue.mkdir()
            (site / "box.json").write_text(json.dumps(b))
            (queue / "news_queue.json").write_text(json.dumps(dict(items=[dict(
                id="new", title="Новость", text="Независимое событие", ready="2026-10-18T10:00:00Z")])))
            with patch.object(tg, "SITE", str(site)), patch.object(tg, "TG", str(queue)):
                n = tg.Names()
                complete = tg.build(d, a, {}, {}, [], n)
                self.assertTrue(any(x["key"] == f"stars:{DAY}" for x in complete))
                a["games"].pop()
                partial = tg.build(d, a, {}, {}, [], n)
                self.assertFalse(any(x["key"].startswith(("am:", "stars:", "rus:", "modelweek:")) for x in partial))
                self.assertTrue(any(x["key"] == "feed:new" for x in partial))

    def test_night_with_no_new_results_still_clears_premature_stars(self):
        d, a, b = fixture()
        d["daily"] = dict(date=DAY, auto=True, heroes=[dict(name="Early Star")])
        a["games"].pop()
        now = dt.datetime(2026, 10, 18, 1, tzinfo=dt.timezone.utc)
        score = dict(games=[dict(id=1, gameType=2, gameState="OFF"), dict(id=2, gameType=2, gameState="LIVE")])
        def load(path, default=None):
            return copy.deepcopy(d if path.endswith("data.json") else a if path.endswith("archive.json") else b)
        with patch.object(fetch, "load", side_effect=load), patch.object(fetch, "get", return_value=(score, None)), \
                patch.object(fetch, "now_utc", return_value=now), patch.object(fetch, "save") as save, \
                patch.object(fetch, "LOG", dict(ok=[], fail=[])):
            self.assertTrue(fetch.night())
            saved = save.call_args.args[1]
            self.assertNotIn("heroes", saved["daily"])
            self.assertEqual(saved["journal"], d["journal"])

    def test_last_nightly_result_rebuilds_stars_without_running_forecast_fallback(self):
        d, a, b = fixture()
        d["daily"] = dict(date=DAY, auto=True, heroes=[dict(name="Early Star")])
        last_game = a["games"].pop()
        last_box = b["games"].pop()
        now = dt.datetime(2026, 10, 18, 1, tzinfo=dt.timezone.utc)
        score = dict(games=[dict(id=i, gameType=2, gameState="OFF") for i in (1, 2)])
        def load(path, default=None):
            return copy.deepcopy(d if path.endswith("data.json") else a if path.endswith("archive.json") else b)
        def get(url, **kwargs):
            return (score if url.endswith(DAY) else dict(games=[])), None
        with patch.object(fetch, "load", side_effect=load), patch.object(fetch, "get", side_effect=get), \
                patch.object(fetch, "now_utc", return_value=now), patch.object(fetch, "save") as save, \
                patch.object(fetch, "club_stats", return_value=([], [], {})), \
                patch.object(fetch, "build_game", return_value=last_game), \
                patch.object(fetch, "game_extras", return_value=last_box["players"]), \
                patch.object(fetch, "standings", return_value=None), \
                patch.object(fetch, "team_summary", return_value=[]), patch.object(fetch, "grade_journal"), \
                patch.object(texts, "fallback", side_effect=AssertionError("must not update forecasts")), \
                patch.object(fetch, "LOG", dict(ok=[], fail=[])):
            self.assertTrue(fetch.night())
            saved = next(call.args[1] for call in save.call_args_list if call.args[0].endswith("data.json"))
            self.assertEqual(saved["daily"]["heroes"][0]["name"], "Late Star")
            self.assertEqual(saved["upcoming"], d["upcoming"])
            self.assertEqual(saved["final"], d["final"])


if __name__ == "__main__":
    unittest.main()
