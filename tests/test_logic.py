import datetime as dt
import unittest

from commute_alert.logic import compute_leave_by, decide_send, should_run_today


class TestLogic(unittest.TestCase):
    def test_compute_leave_by(self):
        now = dt.datetime(2024, 1, 1, 7, 0, tzinfo=dt.timezone.utc)
        duration = dt.timedelta(minutes=30)
        leave_by, notify_at = compute_leave_by(
            now, "08:00", duration, buffer_minutes=10, lead_minutes=15
        )
        self.assertEqual(leave_by.time(), dt.time(7, 20))
        self.assertEqual(notify_at.time(), dt.time(7, 5))

    def test_should_run_today(self):
        now = dt.datetime(2024, 1, 1, 7, 0, tzinfo=dt.timezone.utc)  # Monday
        self.assertTrue(should_run_today(["mon", "tue"], now))
        self.assertFalse(should_run_today(["sat"], now))

    def test_idempotency_primary_window(self):
        now = dt.datetime(2024, 1, 1, 7, 5, tzinfo=dt.timezone.utc)
        travel = dt.timedelta(minutes=30)
        config = {
            "commute": {
                "arrival_time": "08:00",
                "buffer_minutes": 10,
                "lead_minutes": 15,
            },
            "notifications": {
                "grace_minutes": 10,
                "leave_grace_minutes": 10,
                "quiet_hours": {"enabled": False},
            },
        }
        state = {"last_sent_date": None, "last_sent_type": None}
        decision = decide_send(now, config, travel, state)
        self.assertTrue(decision.send)
        state = {"last_sent_date": "2024-01-01", "last_sent_type": "primary"}
        decision = decide_send(now, config, travel, state)
        self.assertFalse(decision.send)


if __name__ == "__main__":
    unittest.main()
