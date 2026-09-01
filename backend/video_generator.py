"""
video_generator.py
Generates synthetic MJPEG frames simulating a drone camera feed.
Uses OpenCV + NumPy — no external models required for dummy mode.
"""

import cv2
import numpy as np
import math
import time

# ── Frame settings ───────────────────────────────────────────────────────────
FRAME_W = 1280
FRAME_H = 720
_START = time.time()


def _make_terrain_layer(t: float) -> np.ndarray:
    """Scrolling noise texture that simulates ground below the drone."""
    x = np.linspace(0, 6, FRAME_W, dtype=np.float32)
    y = np.linspace(0, 4, FRAME_H, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    scroll_x = t * 0.04
    scroll_y = t * 0.025

    terrain = (
        np.sin((xx + scroll_x) * 3.1) * np.cos((yy + scroll_y) * 2.7) * 0.4
        + np.sin((xx + scroll_x) * 7.3 + 1.2) * np.cos((yy + scroll_y) * 6.1) * 0.25
        + np.sin((xx + scroll_x) * 15.0 + 2.5) * np.cos((yy + scroll_y) * 12.0) * 0.15
        + np.sin((xx + scroll_x) * 31.0 + 0.8) * np.cos((yy + scroll_y) * 28.0) * 0.10
    )
    # Normalise to 0-255
    terrain = ((terrain - terrain.min()) / (terrain.max() - terrain.min() + 1e-6) * 255).astype(np.uint8)
    return terrain


def _make_grid_overlay(frame: np.ndarray, t: float) -> np.ndarray:
    """Subtle perspective grid simulating ground plane."""
    overlay = frame.copy()
    colour = (0, 60, 0)
    # Horizontal lines
    for i in range(0, FRAME_H, 60):
        dy = int(math.sin(t * 0.3 + i * 0.01) * 2)
        cv2.line(overlay, (0, i + dy), (FRAME_W, i + dy), colour, 1)
    # Vanishing-point vertical lines
    vp_x = FRAME_W // 2 + int(math.sin(t * 0.07) * 80)
    for x in range(0, FRAME_W, 80):
        cv2.line(overlay, (vp_x, 0), (x, FRAME_H), colour, 1)
    return cv2.addWeighted(frame, 0.85, overlay, 0.15, 0)


def _draw_scan_line(frame: np.ndarray, t: float) -> np.ndarray:
    """Moving horizontal scan line for CRT/night-vision aesthetic."""
    y = int((t * 120) % FRAME_H)
    cv2.line(frame, (0, y), (FRAME_W, y), (0, 255, 100), 1)
    # Faint bands above
    for dy in range(1, 6):
        alpha_row = max(0, y - dy)
        if alpha_row < FRAME_H:
            frame[alpha_row] = (frame[alpha_row].astype(np.int32) + [0, 15, 5]).clip(0, 255).astype(np.uint8)
    return frame


def _draw_corner_brackets(frame: np.ndarray) -> np.ndarray:
    """Corner targeting brackets — classic drone camera HUD look."""
    col = (0, 220, 80)
    size = 40
    thick = 2
    corners = [
        (30, 30),
        (FRAME_W - 30, 30),
        (30, FRAME_H - 30),
        (FRAME_W - 30, FRAME_H - 30),
    ]
    for cx, cy in corners:
        sx = 1 if cx < FRAME_W // 2 else -1
        sy = 1 if cy < FRAME_H // 2 else -1
        # Horizontal arm
        cv2.line(frame, (cx, cy), (cx + sx * size, cy), col, thick)
        # Vertical arm
        cv2.line(frame, (cx, cy), (cx, cy + sy * size), col, thick)
    return frame


def _draw_crosshair(frame: np.ndarray) -> np.ndarray:
    """Centre crosshair."""
    cx, cy = FRAME_W // 2, FRAME_H // 2
    col = (0, 200, 80)
    gap = 18
    arm = 30
    thick = 1
    cv2.line(frame, (cx - arm - gap, cy), (cx - gap, cy), col, thick)
    cv2.line(frame, (cx + gap, cy), (cx + arm + gap, cy), col, thick)
    cv2.line(frame, (cx, cy - arm - gap), (cx, cy - gap), col, thick)
    cv2.line(frame, (cx, cy + gap), (cx, cy + arm + gap), col, thick)
    # Centre dot
    cv2.circle(frame, (cx, cy), 3, col, -1)
    return frame


def _draw_text_overlays(frame: np.ndarray, t: float) -> np.ndarray:
    """Burn timestamp, label, and frame counter into frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    col = (0, 220, 80)
    wall = time.strftime("%H:%M:%S", time.localtime())
    fps_label = f"CAM-01  |  {wall}  |  {int(t):05d}ms"
    cv2.putText(frame, fps_label, (12, FRAME_H - 12), font, 0.45, col, 1, cv2.LINE_AA)
    cv2.putText(frame, "INTERCEPTOR UAV  //  LIVE FEED", (12, 22), font, 0.50, col, 1, cv2.LINE_AA)
    cv2.putText(frame, "IR-RGB", (FRAME_W - 80, 22), font, 0.45, col, 1, cv2.LINE_AA)
    # Blinking REC indicator
    if int(t * 2) % 2 == 0:
        cv2.circle(frame, (FRAME_W - 20, FRAME_H - 18), 6, (0, 0, 220), -1)
        cv2.putText(frame, "REC", (FRAME_W - 55, FRAME_H - 12), font, 0.40, (0, 0, 220), 1, cv2.LINE_AA)
    return frame


def _vignette(frame: np.ndarray) -> np.ndarray:
    """Radial darkening towards corners."""
    rows, cols = frame.shape[:2]
    X = np.linspace(-1, 1, cols)
    Y = np.linspace(-1, 1, rows)
    xx, yy = np.meshgrid(X, Y)
    mask = 1.0 - np.clip(xx ** 2 + yy ** 2, 0, 1) * 0.55
    for c in range(3):
        frame[:, :, c] = (frame[:, :, c] * mask).astype(np.uint8)
    return frame


def generate_frame() -> bytes:
    """
    Produce one JPEG frame as bytes.
    Call this in a tight loop to build the MJPEG stream.
    """
    t = time.time() - _START

    # ── Background terrain ──────────────────────────────────────────────────
    terrain = _make_terrain_layer(t)

    # Colour-map to greenish night-vision tones
    coloured = cv2.applyColorMap(terrain, cv2.COLORMAP_BONE)
    # Tint towards green
    coloured[:, :, 0] = (coloured[:, :, 0] * 0.3).astype(np.uint8)   # B
    coloured[:, :, 1] = (coloured[:, :, 1] * 0.85).astype(np.uint8)  # G
    coloured[:, :, 2] = (coloured[:, :, 2] * 0.25).astype(np.uint8)  # R

    # ── Compositing ──────────────────────────────────────────────────────────
    frame = _make_grid_overlay(coloured, t)
    frame = _draw_scan_line(frame, t)
    frame = _draw_corner_brackets(frame)
    frame = _draw_crosshair(frame)
    frame = _draw_text_overlays(frame, t)
    frame = _vignette(frame)

    # ── Encode to JPEG ───────────────────────────────────────────────────────
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 82]
    _, buf = cv2.imencode(".jpg", frame, encode_param)
    return buf.tobytes()
