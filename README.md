# Interceptor GCS — Ground Control Station

<div align="center">

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-Desktop_App-41CD52?style=flat-square&logo=qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![CUDA](https://img.shields.io/badge/CUDA-12.6-76B900?style=flat-square&logo=nvidia&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A real-time standalone desktop Ground Control Station for the Interceptor UAV.**  
Live camera feed · AI bounding boxes · Flight telemetry · Compass · GPS minimap · Mode control

</div>

---

## Overview

**Interceptor GCS** is a fully standalone native desktop application built with **PyQt6** that provides a real-time ground control interface for the Interceptor drone system. It displays a live camera feed with AI detection overlays, flight telemetry data, a rotating compass, a GPS trail minimap, and a mode toggle — all in a dark military-grade HUD aesthetic.

The application runs entirely **without a browser or external server** — all components (video rendering, telemetry simulation, database logging) operate as Python modules within a single process.

---

## Screenshots

> *Application running with dummy telemetry and simulated video feed*

```
┌─ INTERCEPTOR  GCS  v2.0 ──────────────────────── [⏵ AUTONOMOUS]  15:48:32  ● LIVE ─┐
│                                                                                       │
│  ┌─ Live Camera Feed + HUD ─────────────────┐  ┌─ FLIGHT TELEMETRY ────────────────┐ │
│  │                                          │  │  ALTITUDE      SPEED              │ │
│  │  [INTERCEPTOR UAV // LIVE FEED]          │  │   119.4 m      37.2 km/h          │ │
│  │                                          │  │  HEADING       V·SPEED            │ │
│  │      ┌──┐ Target 91%  ┌──┐              │  │   045.3°       +1.2 m/s           │ │
│  │      └──┘             └──┘              │  │  BATTERY ██████████░░░░ 78%       │ │
│  │                                          │  │  SIGNAL  ████░  82%               │ │
│  │  (AH)    ✛    [corner brackets]         │  ├─ COMPASS ────────────────────────┤ │
│  │                                          │  │      [Rotating Rose]  045°  NE   │ │
│  └──────────────────────────────────────────┘  ├─ ACTIVE DETECTIONS ───────────────┤ │
│                                                 │  Target    91%  [0.24, 0.18]     │ │
│  GPS: 28.614200 / 77.211400  DIST: 333m        │  Vehicle   76%  [0.61, 0.42]     │ │
└─────────────────────────────────────────────────┴───────────────────────────────────┘
```

---

## Features

| Feature | Description |
|---|---|
| **Live Video Feed** | OpenCV-generated frames at ~30 FPS rendered as QPixmap |
| **Bounding Boxes** | Military corner-bracket style overlays with label + confidence % |
| **Artificial Horizon** | Mini AH widget with sky/ground gradient, pitch ladder, roll |
| **Flight Telemetry** | Altitude, Speed, Heading, Vertical Speed updating at 60 Hz |
| **Battery & Signal** | Progress bar and bar indicator with colour-coded warning levels |
| **Mode Toggle** | One-click AUTONOMOUS ↔ MANUAL switch with instant visual feedback |
| **Compass Rose** | Custom QPainter compass with smooth heading interpolation |
| **GPS Minimap** | Offline QPainter map — drone arrow, GPS trail, home marker, range ring |
| **Detection List** | Live list of detected targets with confidence scores |
| **SQLite Logging** | All telemetry, mode changes, and detections persisted per flight session |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **GUI Framework** | PyQt6 (Qt 6.x) |
| **Rendering** | QPainter (compass, minimap, HUD), QPixmap (video) |
| **Threading** | QThread — `TelemetryWorker` (60 Hz) + `VideoWorker` (30 FPS) |
| **Computer Vision** | OpenCV 4.13 + NumPy 2.4 |
| **Database** | SQLite 3 (WAL mode, per-thread connections) |
| **Python Runtime** | Python 3.14 · CUDA 12.6 · PyTorch 2.12+cu126 |
| **Virtual Env** | `D:\CUDA_ENV\CUDA_ENV` (CUDA-enabled) |

---

## Project Structure

```
Interceptor_GUI/
│
├── run_app.py                  ← Launcher — run this file
│
├── app/                        ← PyQt6 desktop application
│   ├── main_window.py          ← Main window layout & logic
│   ├── video_panel.py          ← Video display + QPainter HUD overlay
│   ├── compass_widget.py       ← Custom compass rose widget
│   ├── minimap_widget.py       ← Offline GPS trail minimap
│   ├── workers.py              ← QThread workers (telemetry + video)
│   └── theme.py                ← Dark QSS stylesheet + QPalette
│
└── backend/                    ← Core logic (used as Python libraries)
    ├── telemetry_sim.py        ← Physics-aware UAV telemetry simulator
    ├── video_generator.py      ← OpenCV synthetic camera feed generator
    ├── database.py             ← SQLite persistence layer
    └── server.py               ← FastAPI server (optional, for future web use)
```

---

## Getting Started

### Prerequisites

- Windows 10/11
- CUDA-enabled Python virtual environment at `D:\CUDA_ENV\CUDA_ENV`
- PyQt6, OpenCV, NumPy (pre-installed in the venv)

### Run

```powershell
D:\CUDA_ENV\CUDA_ENV\Scripts\python.exe run_app.py
```

No server to start. No browser to open. The application launches as a native Windows desktop window.

---

## Database Schema

All flight data is persisted to `backend/interceptor_gcs.db` (SQLite).

| Table | Contents |
|---|---|
| `flight_sessions` | One row per application run (start/end timestamps) |
| `telemetry_log` | 1 Hz sampled: altitude, speed, heading, GPS, battery, signal |
| `mode_history` | Every MANUAL ↔ AUTONOMOUS switch with timestamp |
| `detection_log` | Bounding box label, confidence, coordinates per frame |

---

## Roadmap

- [ ] Integrate real MAVLink/ROS2 telemetry stream
- [ ] Replace dummy video with live RTSP / WebRTC drone camera
- [ ] Add real YOLO inference on GPU for live bounding boxes
- [ ] Waypoint mission planning overlay on minimap
- [ ] Multi-drone fleet view
- [ ] Export flight logs to CSV / KML

---

## License

MIT © 2026 AmanSah17
