"""
telemetry_sim.py
Physics-aware dummy telemetry simulator for Interceptor UAV.
Generates realistic-looking flight data updated at ~60 Hz.
Mode can be toggled externally via set_mode().
"""

import math
import time
import threading

# ── Shared mutable state (thread-safe) ──────────────────────────────────────
_state_lock = threading.Lock()
_forced_mode: str | None = None     # None = auto-toggle; "MANUAL"/"AUTONOMOUS" = locked

# ── Base constants ──────────────────────────────────────────────────────────
_BASE_LAT = 28.6139       # Delhi area (change to your ops area)
_BASE_LON = 77.2090
_ORBIT_RADIUS = 0.003     # ~330 m radius circle
_SIM_START = time.time()

# Auto mode toggles every N seconds (only when not manually overridden)
_MODE_INTERVAL = 30.0

# Flight envelope
_MAX_SPEED_KMH = 85.0
_BASE_ALT_M    = 120.0
_ALT_VARIANCE  = 45.0


# ── Public: set mode externally ──────────────────────────────────────────────
def set_mode(mode: str):
    """
    Force the simulation to a specific mode.
    mode: "MANUAL" | "AUTONOMOUS"
    Pass None to revert to automatic toggling.
    """
    global _forced_mode
    with _state_lock:
        _forced_mode = mode.upper() if mode else None


def get_mode() -> str:
    """Return the current effective mode."""
    with _state_lock:
        if _forced_mode is not None:
            return _forced_mode
    t = time.time() - _SIM_START
    return "AUTONOMOUS" if int(t / _MODE_INTERVAL) % 2 == 0 else "MANUAL"


# ── Internal helpers ─────────────────────────────────────────────────────────
def _smooth_noise(t: float, freq: float = 1.0, seed: float = 0.0) -> float:
    """Deterministic smooth oscillation using sum of sinusoids."""
    return (
        math.sin(t * freq + seed) * 0.6
        + math.sin(t * freq * 2.3 + seed * 1.7) * 0.3
        + math.sin(t * freq * 5.1 + seed * 3.3) * 0.1
    )


# ── Main telemetry snapshot ──────────────────────────────────────────────────
def get_telemetry() -> dict:
    """
    Returns current simulated telemetry snapshot.
    Call as fast as needed — pure computation, no I/O.
    """
    t = time.time() - _SIM_START

    # ── Flight mode ─────────────────────────────────────────────────────────
    mode = get_mode()

    # ── GPS (circular orbit) ─────────────────────────────────────────────────
    orbit_speed = 0.08   # radians/sec
    angle = t * orbit_speed
    lat = _BASE_LAT + _ORBIT_RADIUS * math.sin(angle)
    lon = _BASE_LON + _ORBIT_RADIUS * math.cos(angle)

    # ── Heading (tangent to orbit + small drift) ──────────────────────────────
    heading_raw   = math.degrees(angle + math.pi / 2)
    heading_drift = _smooth_noise(t, freq=0.15, seed=9.9) * 8.0
    heading = (heading_raw + heading_drift) % 360

    # ── Altitude ─────────────────────────────────────────────────────────────
    alt_osc  = _smooth_noise(t, freq=0.12, seed=2.5)
    altitude = _BASE_ALT_M + alt_osc * _ALT_VARIANCE
    # In manual mode, add more turbulence
    if mode == "MANUAL":
        altitude += _smooth_noise(t, freq=0.8, seed=6.6) * 12.0
    altitude = max(10.0, altitude)

    # ── Speed ────────────────────────────────────────────────────────────────
    speed_osc = (_smooth_noise(t, freq=0.09, seed=5.1) + 1.0) / 2.0   # 0-1
    speed_kmh = speed_osc * _MAX_SPEED_KMH
    if mode == "MANUAL":
        speed_kmh *= 0.75   # manual = more conservative speed

    # ── Vertical speed ────────────────────────────────────────────────────────
    vspeed = _smooth_noise(t, freq=0.20, seed=7.7) * 4.5   # m/s

    # ── Battery (slow depletion) ──────────────────────────────────────────────
    drain_percent = (t / 600.0) * 100.0   # full drain in 600 s
    battery = max(0.0, min(100.0, 100.0 - drain_percent))

    # ── Signal strength ───────────────────────────────────────────────────────
    signal_base = 0.82 + _smooth_noise(t, freq=0.05, seed=1.2) * 0.18
    signal = max(0.0, min(1.0, signal_base))

    # ── Bounding boxes ────────────────────────────────────────────────────────
    boxes = _generate_boxes(t)

    # ── Ground distance from home ─────────────────────────────────────────────
    distance_m = _ORBIT_RADIUS * 111_320   # approx metres

    return {
        "timestamp": round(t, 3),
        "mode":      mode,
        "lat":       round(lat, 7),
        "lon":       round(lon, 7),
        "altitude":  round(altitude, 1),        # metres AGL
        "speed":     round(speed_kmh, 1),        # km/h
        "heading":   round(heading, 1),          # degrees 0-360
        "vspeed":    round(vspeed, 2),            # m/s (+ = climb)
        "battery":   round(battery, 1),           # %
        "signal":    round(signal, 3),            # 0.0-1.0
        "distance":  round(distance_m, 1),        # metres from home
        "boxes":     boxes,
    }


def _generate_boxes(t: float) -> list:
    """
    Generates 2-4 animated bounding boxes across the frame.
    Coordinates normalised 0.0-1.0 relative to frame dimensions.
    """
    boxes  = []
    specs  = [
        (1.0,  3.0, "Target",   0.91),
        (5.5,  7.5, "Vehicle",  0.76),
        (2.3, 11.0, "Target",   0.88),
        (8.8,  4.2, "Unknown",  0.62),
    ]
    n_visible = 2 + (int(t / 8) % 3)   # cycles 2-4

    for i, (xs, ys, label, conf_base) in enumerate(specs[:n_visible]):
        cx = 0.15 + 0.70 * ((math.sin(t * 0.07 + xs) + 1) / 2)
        cy = 0.15 + 0.70 * ((math.sin(t * 0.05 + ys) + 1) / 2)
        w  = 0.10 + 0.08 * ((math.sin(t * 0.13 + xs * 2) + 1) / 2)
        h  = w * (0.8 + 0.4 * math.sin(t * 0.09 + ys))
        conf = conf_base + _smooth_noise(t, freq=0.3, seed=float(i)) * 0.06
        conf = max(0.50, min(0.99, conf))
        boxes.append({
            "x":     round(cx - w / 2, 4),
            "y":     round(cy - h / 2, 4),
            "w":     round(w, 4),
            "h":     round(h, 4),
            "label": label,
            "conf":  round(conf, 2),
        })

    return boxes
