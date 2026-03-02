import unittest
from datetime import datetime, timezone

from desktop_app import SunTimes, compute_clock_state, sun_rise_set


class DesktopAppTests(unittest.TestCase):
    def test_sunrise_ordering(self):
        result = sun_rise_set(datetime(2024, 6, 1, tzinfo=timezone.utc), -122.4194, 37.7749)
        self.assertTrue(0 <= result.rise_min_utc < 24 * 60)
        self.assertTrue(0 <= result.set_min_utc < 24 * 60)
        self.assertTrue(0 <= result.south_min_utc < 24 * 60)

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


if __name__ == "__main__":
    unittest.main()
