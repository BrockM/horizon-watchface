# Horizon Watch Face

This repository now includes a **native desktop Python app** (`desktop_app.py`) that recreates the Horizon Pebble watchface concept:
- 24-hour solar orbit ring
- sunrise/sunset-based horizon placement
- central time/day/date readout
- optional battery + bluetooth text
- optional solar-event readout (civil sunrise, sunrise, noon, sunset, civil sunset)

## Run desktop app

```bash
python3 desktop_app.py
```

Optional flags:

```bash
python3 desktop_app.py --latitude 51.5072 --longitude -0.1276 --battery 62 --bluetooth --window-size 640
```

Hide Bluetooth/battery text:

```bash
python3 desktop_app.py --hide-status-text
```

Show solar event details:

```bash
python3 desktop_app.py --show-solar-events
```

Use a JSON config file:

```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "battery": 88,
  "bluetooth": true,
  "window_size": 600,
  "hide_status_text": false,
  "show_solar_events": true
}
```

```bash
python3 desktop_app.py --config ./watchface-config.json
```

For non-GUI verification (useful in CI/headless):

```bash
python3 desktop_app.py --print-state
```

The headless command prints sunrise/sunset/noon minutes in **UTC**, plus civil twilight and polar-day/night status.
