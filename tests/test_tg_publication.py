"""Publication rules exercised through the bot's automatic posting path, offline."""

import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tg


class PublicationRules(unittest.TestCase):
    def run_auto(self, local_time, key="feed:new", gap_minutes=60, posted=None, hot=False):
        now = dt.datetime.fromisoformat(local_time).astimezone(dt.timezone.utc)

        class Clock(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return now.astimezone(tz) if tz else now.replace(tzinfo=None)

        item = {"key": key, "due": now - dt.timedelta(hours=1),
                "expires": now + dt.timedelta(hours=1), "text": "Проверяемый пост", "hot": hot}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site, queue = root / "site", root / "tg"
            site.mkdir()
            queue.mkdir()
            state = {"posted": posted or {}, "messages": {},
                     "last_post": (now - dt.timedelta(minutes=gap_minutes)).isoformat()}
            for filename, data in {"state.json": state, "config.json": {"chat_id": 1},
                                   "feed.json": {"t": now.isoformat(), "items": []}}.items():
                (queue / filename).write_text(json.dumps(data), encoding="utf-8")
            with patch.object(tg, "SITE", str(site)), patch.object(tg, "TG", str(queue)), \
                    patch.object(tg, "LOG", {"ok": [], "fail": []}), \
                    patch.object(tg.dt, "datetime", Clock), \
                    patch.object(tg, "build", return_value=[item]), \
                    patch.object(tg, "inbox"), patch.object(tg, "apply_edits"), \
                    patch.object(tg, "send", return_value=[123]) as send:
                tg.main("auto")
                after = json.loads((queue / "state.json").read_text())
                return send.call_count, after

    def test_news_waits_during_quiet_hours_even_when_already_due(self):
        for time in ["2026-10-18T23:00:00+03:00", "2026-10-19T00:30:00+03:00",
                     "2026-10-19T07:59:59+03:00"]:
            with self.subTest(time=time):
                calls, state = self.run_auto(time)
                self.assertEqual(calls, 0)
                self.assertNotIn("feed:new", state["posted"])

    def test_news_allowed_at_daytime_boundaries(self):
        for time in ["2026-10-19T08:00:00+03:00", "2026-10-18T22:59:59+03:00"]:
            with self.subTest(time=time):
                calls, state = self.run_auto(time)
                self.assertEqual(calls, 1)
                self.assertIn("feed:new", state["posted"])

    def test_final_post_respects_same_twenty_minute_gap(self):
        calls, state = self.run_auto("2026-10-18T23:45:00+03:00", key="final:today", gap_minutes=19)
        self.assertEqual(calls, 0)
        self.assertNotIn("final:today", state["posted"])
        calls, state = self.run_auto("2026-10-18T23:45:00+03:00", key="final:today", gap_minutes=20)
        self.assertEqual(calls, 1)

    def test_hot_news_does_not_bypass_daily_cap(self):
        posted = {f"feed:{i}": f"2026-10-18T{8+i:02}:00:00Z" for i in range(5)}
        calls, state = self.run_auto("2026-10-18T19:00:00+03:00", posted=posted, hot=True)
        self.assertEqual(calls, 0)
        self.assertEqual(len(state["posted"]), 5)

    def test_hot_news_does_not_bypass_seventy_five_minute_gap(self):
        posted = {"feed:previous": "2026-10-18T14:00:00Z"}
        calls, state = self.run_auto("2026-10-18T18:14:00+03:00", posted=posted, hot=True)
        self.assertEqual(calls, 0)
        calls, state = self.run_auto("2026-10-18T18:15:00+03:00", posted=posted, hot=True)
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
