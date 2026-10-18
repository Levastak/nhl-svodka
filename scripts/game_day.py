"""Completion checks shared by collection, fallback texts and Telegram. No network."""


def score_status(day, score):
    """Keep the full official slate even after the rolling schedule moves on."""
    if not isinstance(score, dict) or not isinstance(score.get("games"), list):
        return None
    if score.get("currentDate") and score["currentDate"] != day:
        return None
    games = [g for g in score["games"] if g.get("gameType") in (2, 3)
             and g.get("gameScheduleState") not in ("PPD", "CNCL")]
    return dict(date=day, scheduled_ids=sorted(g["id"] for g in games),
                finished_ids=sorted(g["id"] for g in games if g.get("gameState") in ("OFF", "FINAL")))


def expected_ids(data, day):
    status = data.get("results_status") or {}
    if status.get("date") == day:
        return set(status.get("scheduled_ids") or [])
    return {g["id"] for key in ("week", "upcoming") for g in data.get(key) or [] if g.get("date") == day}


def day_complete(data, archive, day=None, box=None):
    day = day or data.get("results_date")
    expected = expected_ids(data, day)
    if not day or not expected:
        return False  # No schedule is not evidence that the day ended.
    status = data.get("results_status") or {}
    if status.get("date") == day and not expected.issubset(status.get("finished_ids") or []):
        return False
    finished = {g["id"] for g in archive.get("games", []) if g.get("date") == day
                and g.get("as") is not None and g.get("hs") is not None}
    if finished != expected:
        return False
    if box is not None:
        protocols = {g["id"] for g in box.get("games", []) if g.get("players")} if box.get("date") == day else set()
        if not expected.issubset(protocols):
            return False
    return True


def daily_ready(data, archive, box=None):
    daily = data.get("daily") or {}
    day = data.get("results_date")
    return (daily.get("date") == day and day_complete(data, archive, day, box)
            and (not daily.get("auto") or set(daily.get("game_ids") or []) == expected_ids(data, day)))
