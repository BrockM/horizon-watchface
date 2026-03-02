#!/usr/bin/env python3
"""Native desktop version of the Horizon Pebble watchface."""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import tkinter as tk

PALETTE = {
    "behind": "#d3d3d3",
    "below": "#4a90e2",
    "above": "#f4ef67",
    "within": "#ffffff",
    "marks": "#000000",
    "engraving": "#d3d3d3",
    "text": "#000000",
    "solar": "#ffffff",
    "capacity": "#555555",
    "charge": "#ffffff",
    "online": "#ffffff",
    "offline": "#555555",
}


@dataclass(frozen=True)
class SunTimes:
    rise_min_utc: int
    set_min_utc: int
    south_min_utc: int
    status: int


@dataclass(frozen=True)
class ClockState:
    horizon: int
    kilter_deg: float


def days_since_2000_jan_0(year: int, month: int, day: int) -> float:
    return 367 * year - (7 * (year + ((month + 9) // 12))) // 4 + (275 * month) // 9 + day - 730530


def revolution(degrees: float) -> float:
    return degrees - 360.0 * math.floor(degrees / 360.0)


def rev180(degrees: float) -> float:
    return degrees - 360.0 * math.floor(degrees / 360.0 + 0.5)


def gmst0(delta_days: float) -> float:
    return revolution((180.0 + 356.0470 + 282.9404) + (0.9856002585 + 4.70935e-5) * delta_days)


def sun_ra_dec(delta_days: float) -> tuple[float, float, float]:
    mean_anomaly = revolution(356.0470 + 0.9856002585 * delta_days)
    perihelion = 282.9404 + 4.70935e-5 * delta_days
    eccentricity = 0.016709 - 1.151e-9 * delta_days

    e_anomaly = mean_anomaly + (180.0 / math.pi) * eccentricity * math.sin(math.radians(mean_anomaly)) * (
        1.0 + eccentricity * math.cos(math.radians(mean_anomaly))
    )
    x = math.cos(math.radians(e_anomaly)) - eccentricity
    y = math.sqrt(1.0 - eccentricity * eccentricity) * math.sin(math.radians(e_anomaly))
    solar_distance = math.sqrt(x * x + y * y)
    true_anomaly = math.degrees(math.atan2(y, x))
    lon = true_anomaly + perihelion
    if lon >= 360.0:
        lon -= 360.0

    obliquity = 23.4393 - 3.563e-7 * delta_days
    xequat = solar_distance * math.cos(math.radians(lon))
    yequat = solar_distance * math.sin(math.radians(lon)) * math.cos(math.radians(obliquity))
    zequat = solar_distance * math.sin(math.radians(lon)) * math.sin(math.radians(obliquity))

    right_ascension = math.degrees(math.atan2(yequat, xequat))
    declination = math.degrees(math.atan2(zequat, math.sqrt(xequat * xequat + yequat * yequat)))
    return right_ascension, declination, solar_distance


def sun_rise_set(date_utc: datetime, longitude: float, latitude: float) -> SunTimes:
    delta_days = days_since_2000_jan_0(date_utc.year, date_utc.month, date_utc.day) + 0.5 - longitude / 360.0
    sidereal_time = revolution(gmst0(delta_days) + 180.0 + longitude)
    right_ascension, declination, solar_distance = sun_ra_dec(delta_days)

    south_hour = 12.0 - rev180(sidereal_time - right_ascension) / 15.0
    solar_radius = 0.2666 / solar_distance
    altitude = -35.0 / 60.0 - solar_radius

    cost = (math.sin(math.radians(altitude)) - math.sin(math.radians(latitude)) * math.sin(math.radians(declination))) / (
        math.cos(math.radians(latitude)) * math.cos(math.radians(declination))
    )

    if cost >= 1.0:
        status, arc_hour = -1, 0.0
    elif cost <= -1.0:
        status, arc_hour = 1, 12.0
    else:
        status, arc_hour = 0, math.degrees(math.acos(cost)) / 15.0

    rise = int(round((south_hour - arc_hour) * 60)) % (24 * 60)
    set_ = int(round((south_hour + arc_hour) * 60)) % (24 * 60)
    south = int(round(south_hour * 60)) % (24 * 60)
    return SunTimes(rise_min_utc=rise, set_min_utc=set_, south_min_utc=south, status=status)


def minute_to_degrees(minutes: int) -> float:
    return (minutes * 360.0) / (24 * 60)


def clock_point(cx: float, cy: float, radius: float, minutes: int, rotation_deg: float) -> tuple[float, float]:
    angle = (minute_to_degrees(minutes) + rotation_deg) % 360.0
    radians = math.radians(angle)
    return cx - math.sin(radians) * radius, cy + math.cos(radians) * radius


def compute_clock_state(sun: SunTimes, timezone_offset_min: int, sun_orbit_radius: float) -> ClockState:
    south_local = (sun.south_min_utc + timezone_offset_min) % (24 * 60)
    rise_local = (sun.rise_min_utc + timezone_offset_min) % (24 * 60)
    set_local = (sun.set_min_utc + timezone_offset_min) % (24 * 60)
    kilter_deg = minute_to_degrees((12 * 60 - south_local) % (24 * 60))

    if sun.status == 1:
        return ClockState(horizon=-int(sun_orbit_radius), kilter_deg=kilter_deg)
    if sun.status == -1:
        return ClockState(horizon=int(sun_orbit_radius), kilter_deg=kilter_deg)

    _, sunrise_y = clock_point(0.0, 0.0, sun_orbit_radius, rise_local, kilter_deg)
    _, sunset_y = clock_point(0.0, 0.0, sun_orbit_radius, set_local, kilter_deg)
    return ClockState(horizon=int((sunrise_y + sunset_y) / 2), kilter_deg=kilter_deg)


class HorizonDesktopApp:
    def __init__(self, latitude: float, longitude: float, battery: int, bluetooth: bool, window_size: int) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.battery = max(0, min(100, battery))
        self.bluetooth = bluetooth

        self.root = tk.Tk()
        self.root.title("Horizon Watchface (Desktop)")
        self.root.geometry(f"{window_size}x{window_size}")

        self.canvas = tk.Canvas(self.root, bg=PALETTE["behind"], highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())

        self._schedule_next_tick(initial=True)

    def draw(self) -> None:
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        cx, cy = width / 2.0, height / 2.0
        design_radius = max(40.0, min(width, height) / 2.0 - 16.0)

        sun_disc = design_radius * 3 / 25
        sun_orbit = design_radius - sun_disc * 1.3
        readout = sun_orbit - sun_disc * 1.4

        now = datetime.now().astimezone()
        sun = sun_rise_set(now.astimezone(timezone.utc), self.longitude, self.latitude)
        timezone_offset_min = int(now.utcoffset().total_seconds() / 60) if now.utcoffset() else 0
        clock_state = compute_clock_state(sun, timezone_offset_min, sun_orbit)

        horizon_y = cy + clock_state.horizon
        self.canvas.create_rectangle(0, 0, width, horizon_y, fill=PALETTE["above"], outline="")
        self.canvas.create_rectangle(0, horizon_y, width, height, fill=PALETTE["below"], outline="")
        self.canvas.create_line(0, horizon_y, width, horizon_y, fill=PALETTE["marks"])

        for hour in range(24):
            px, py = clock_point(cx, cy, sun_orbit, hour * 60, clock_state.kilter_deg)
            pip_radius = sun_disc if hour % 6 == 0 else sun_disc / 3
            self.canvas.create_oval(px - pip_radius, py - pip_radius, px + pip_radius, py + pip_radius, fill=PALETTE["marks"], outline="")
            if hour % 6 == 0:
                self.canvas.create_text(
                    px,
                    py,
                    text=f"{hour:02d}",
                    font=("Helvetica", max(8, int(sun_disc * 0.8)), "bold"),
                    fill=PALETTE["solar"],
                )

        now_local_min = now.hour * 60 + now.minute
        sx, sy = clock_point(cx, cy, sun_orbit, now_local_min, clock_state.kilter_deg)
        self.canvas.create_oval(
            sx - sun_disc,
            sy - sun_disc,
            sx + sun_disc,
            sy + sun_disc,
            fill=PALETTE["solar"],
            outline=PALETTE["marks"],
            width=2,
        )

        self.canvas.create_oval(cx - readout, cy - readout, cx + readout, cy + readout, fill=PALETTE["within"], outline=PALETTE["marks"], width=2)
        self.canvas.create_text(cx, cy, text=now.strftime("%H:%M"), font=("Helvetica", max(12, int(readout * 0.3)), "bold"), fill=PALETTE["text"])
        self.canvas.create_text(
            cx,
            cy - readout * 0.35,
            text=now.strftime("%a").upper(),
            font=("Helvetica", max(8, int(readout * 0.14)), "bold"),
            fill=PALETTE["text"],
        )
        self.canvas.create_text(
            cx,
            cy + readout * 0.35,
            text=now.strftime("%b %d").upper(),
            font=("Helvetica", max(8, int(readout * 0.14)), "bold"),
            fill=PALETTE["text"],
        )

        battery_text = f"BAT {self.battery:3d}%"
        bluetooth_text = "BT ON" if self.bluetooth else "BT OFF"
        bluetooth_color = PALETTE["online"] if self.bluetooth else PALETTE["offline"]
        self.canvas.create_text(cx, cy - readout * 0.75, text=battery_text, font=("Helvetica", max(8, int(readout * 0.12))), fill=PALETTE["capacity"])
        self.canvas.create_text(cx, cy + readout * 0.75, text=bluetooth_text, font=("Helvetica", max(8, int(readout * 0.12))), fill=bluetooth_color)

    def _schedule_next_tick(self, initial: bool = False) -> None:
        now = datetime.now()
        if initial:
            delay_ms = 50
        else:
            delay_ms = 1000 * (60 - now.second) - now.microsecond // 1000 + 5
        self.root.after(delay_ms, self.tick)

    def tick(self) -> None:
        self.draw()
        self._schedule_next_tick(initial=False)

    def run(self) -> None:
        self.root.mainloop()


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    return json.loads(path.read_text())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop Horizon watchface")
    parser.add_argument("--config", type=Path, help="Optional JSON config file")
    parser.add_argument("--latitude", type=float, default=37.7749)
    parser.add_argument("--longitude", type=float, default=-122.4194)
    parser.add_argument("--battery", type=int, default=76)
    parser.add_argument("--bluetooth", action="store_true", default=False)
    parser.add_argument("--window-size", type=int, default=480)
    parser.add_argument("--print-state", action="store_true", help="Print computed sun state and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    latitude = float(cfg.get("latitude", args.latitude))
    longitude = float(cfg.get("longitude", args.longitude))
    battery = int(cfg.get("battery", args.battery))
    bluetooth = bool(cfg.get("bluetooth", args.bluetooth))
    window_size = int(cfg.get("window_size", args.window_size))

    if args.print_state:
        now_utc = utc_now()
        sun = sun_rise_set(now_utc, longitude, latitude)
        print(
            json.dumps(
                {
                    "rise_min_utc": sun.rise_min_utc,
                    "set_min_utc": sun.set_min_utc,
                    "south_min_utc": sun.south_min_utc,
                    "status": sun.status,
                }
            )
        )
        return

    HorizonDesktopApp(latitude, longitude, battery, bluetooth, window_size).run()


if __name__ == "__main__":
    main()
