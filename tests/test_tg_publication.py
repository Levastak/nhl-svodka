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
    def run_news_recard(self, text, media_error=False):
        key = "feed:existing"
        photo = "https://example.com/replacement.jpg"
        item = {"key": key, "text": text, "photo": photo,
                "due": dt.datetime(2026, 10, 30, 10, tzinfo=dt.timezone.utc)}
        calls = []

        def api(method, fields, files=None):
            calls.append((method, fields))
            if media_error and method == "editMessageMedia":
                raise RuntimeError("message is a text post")
            return True

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site, queue = root / "site", root / "tg"
            site.mkdir()
            queue.mkdir()
            for filename, data in {"state.json": {"posted": {key: "2026-10-30T10:00:00Z"},
                                                   "messages": {key: [296]}},
                                   "config.json": {"chat_id": 1}, "feed.json": {"items": []}}.items():
                (queue / filename).write_text(json.dumps(data), encoding="utf-8")
            with patch.object(tg, "SITE", str(site)), patch.object(tg, "TG", str(queue)), \
                    patch.object(tg, "LOG", {"ok": [], "fail": []}), \
                    patch.object(tg, "build", return_value=[item]), patch.object(tg, "_call", side_effect=api):
                tg.main("recard", key)
                self.assertEqual(tg.LOG["fail"], [])
        return calls

    def test_news_recard_replaces_photo_on_same_message(self):
        calls = self.run_news_recard("<b>Existing caption</b>")
        self.assertEqual([method for method, _ in calls], ["editMessageMedia"])
        fields = calls[0][1]
        self.assertEqual(fields["message_id"], 296)
        self.assertEqual(fields["media"]["media"], "https://example.com/replacement.jpg")
        self.assertEqual(fields["media"]["caption"], "<b>Existing caption</b>")

    def test_long_news_recard_changes_preview_without_exceeding_caption_limit(self):
        calls = self.run_news_recard("x" * 1100)
        self.assertEqual([method for method, _ in calls], ["editMessageText"])
        self.assertEqual(calls[0][1]["link_preview_options"]["url"], "https://example.com/replacement.jpg")

    def test_news_recard_can_update_existing_text_fallback(self):
        calls = self.run_news_recard("Existing text", media_error=True)
        self.assertEqual([method for method, _ in calls], ["editMessageMedia", "editMessageText"])
        self.assertTrue(all(fields["message_id"] == 296 for _, fields in calls))

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
