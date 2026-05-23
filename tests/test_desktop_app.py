import unittest
from datetime import datetime, timezone

from desktop_app import SunTimes, civil_twilight, compute_clock_state, minute_label, sun_rise_set


class DesktopAppTests(unittest.TestCase):
    def test_sunrise_output_ranges(self):
        result = sun_rise_set(datetime(2024, 6, 1, tzinfo=timezone.utc), -122.4194, 37.7749)
        self.assertTrue(0 <= result.rise_min_utc < 24 * 60)
        self.assertTrue(0 <= result.set_min_utc < 24 * 60)
        self.assertTrue(0 <= result.south_min_utc < 24 * 60)

    def test_civil_twilight_output_ranges(self):
        result = civil_twilight(datetime(2024, 6, 1, tzinfo=timezone.utc), -122.4194, 37.7749)
        self.assertTrue(0 <= result.rise_min_utc < 24 * 60)
        self.assertTrue(0 <= result.set_min_utc < 24 * 60)

    def test_polar_day_horizon(self):
        state = compute_clock_state(
            SunTimes(rise_min_utc=0, set_min_utc=0, south_min_utc=720, status=1),
            timezone_offset_min=0,
            sun_orbit_radius=120,
        )
        self.assertEqual(state.horizon, -120)

    def test_polar_night_horizon(self):
        state = compute_clock_state(
            SunTimes(rise_min_utc=0, set_min_utc=0, south_min_utc=720, status=-1),
            timezone_offset_min=0,
            sun_orbit_radius=120,
        )
        self.assertEqual(state.horizon, 120)

    def test_minute_label_wraps(self):
        self.assertEqual(minute_label(0), "00:00")
        self.assertEqual(minute_label(24 * 60 + 5), "00:05")


if __name__ == "__main__":
    unittest.main()
