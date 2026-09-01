"""
server.py
FastAPI backend for Interceptor GCS Dashboard.

Endpoints
---------
GET  /                   -> serves frontend/index.html
GET  /static/*           -> serves frontend assets (css, js)
GET  /video_feed         -> MJPEG multipart stream at ~30 FPS
WS   /ws/telemetry       -> 60 Hz JSON telemetry broadcast
POST /api/mode/toggle    -> toggle MANUAL <-> AUTONOMOUS
GET  /api/mode           -> current mode
GET  /api/telemetry/history  -> last N telemetry rows from DB
GET  /api/session/stats  -> current session statistics

Run with:
    D:\\CUDA_ENV\\CUDA_ENV\\Scripts\\python.exe backend/server.py
"""

import asyncio
import time
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ── Resolve paths ─────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent.parent
FRONT_DIR  = ROOT_DIR / "frontend"
INDEX_HTML = FRONT_DIR / "index.html"

# ── Local imports ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from telemetry_sim import get_telemetry, get_mode, set_mode
from video_generator import generate_frame
import database as db


# =============================================================================
# WebSocket Connection Manager
# =============================================================================
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.append(ws)
        print(f"[WS] Client connected. Total: {len(self.active)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self.active:
                self.active.remove(ws)
        print(f"[WS] Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        """Send to all clients; remove any that have gone dead."""
        dead = []
        async with self._lock:
            targets = list(self.active)
        for ws in targets:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


# =============================================================================
# Background telemetry broadcast loop (60 Hz)
# =============================================================================
async def telemetry_broadcast_loop():
    interval = 1.0 / 60.0   # ~16.6 ms
    while True:
        t0 = time.monotonic()
        if manager.active:
            data = get_telemetry()
            db.log_telemetry(data)          # throttled to 1 Hz inside the fn
            await manager.broadcast(data)
        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, interval - elapsed))


# =============================================================================
# Lifespan (startup / shutdown)
# =============================================================================
@asynccontextmanager
async def lifespan(application: FastAPI):
    # --- startup ---
    db.init_db()
    db.start_session()
    asyncio.create_task(telemetry_broadcast_loop())
    print("[SERVER] Telemetry broadcast loop started at 60 Hz")
    print("[SERVER] Dashboard -> http://127.0.0.1:8000")
    print("[SERVER] Video     -> http://127.0.0.1:8000/video_feed")
    print("[SERVER] WS        -> ws://127.0.0.1:8000/ws/telemetry")
    yield
    # --- shutdown ---
    db.end_session()


# =============================================================================
# App setup
# =============================================================================
app = FastAPI(title="Interceptor GCS", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONT_DIR)), name="static")


# =============================================================================
# Routes — Frontend
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML.read_text(encoding="utf-8")


# =============================================================================
# Routes — WebSocket
# =============================================================================
@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Block here waiting for any client message (mode toggle, etc.)
        # WebSocketDisconnect is raised when client closes tab/connection
        while True:
            msg = await websocket.receive_text()
            # Handle optional client->server commands (future expansion)
            if msg == "ping":
                await websocket.send_json({"pong": True})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        await manager.disconnect(websocket)


# =============================================================================
# Routes — REST API
# =============================================================================
@app.post("/api/mode/toggle")
async def toggle_mode():
    """Toggle between AUTONOMOUS and MANUAL. Returns new mode."""
    current = get_mode()
    new_mode = "MANUAL" if current == "AUTONOMOUS" else "AUTONOMOUS"
    db.log_mode_change(current, new_mode)
    set_mode(new_mode)
    # Broadcast the mode change immediately to all connected clients
    data = get_telemetry()
    await manager.broadcast(data)
    return JSONResponse({"mode": new_mode, "previous": current})


@app.post("/api/mode/set/{mode}")
async def set_mode_endpoint(mode: str):
    """Explicitly set mode: MANUAL or AUTONOMOUS."""
    mode = mode.upper()
    if mode not in ("MANUAL", "AUTONOMOUS"):
        return JSONResponse({"error": "Mode must be MANUAL or AUTONOMOUS"}, status_code=400)
    current = get_mode()
    if current != mode:
        db.log_mode_change(current, mode)
        set_mode(mode)
        data = get_telemetry()
        await manager.broadcast(data)
    return JSONResponse({"mode": mode})


@app.get("/api/mode")
async def get_mode_endpoint():
    return JSONResponse({"mode": get_mode()})


@app.get("/api/telemetry/history")
async def telemetry_history(limit: int = 100):
    rows = db.get_recent_telemetry(limit=limit)
    return JSONResponse({"data": rows, "count": len(rows)})


@app.get("/api/mode/history")
async def mode_history(limit: int = 50):
    rows = db.get_mode_history(limit=limit)
    return JSONResponse({"data": rows, "count": len(rows)})


@app.get("/api/session/stats")
async def session_stats():
    stats = db.get_session_stats()
    return JSONResponse(stats)


# =============================================================================
# Routes — MJPEG Video Stream
# =============================================================================
async def _mjpeg_generator():
    """Async generator yielding MJPEG multipart chunks at ~30 FPS."""
    interval = 1.0 / 30.0
    boundary = b"--frame\r\n"
    header   = b"Content-Type: image/jpeg\r\n\r\n"

    while True:
        t0 = time.monotonic()
        try:
            frame_bytes = generate_frame()
        except Exception as e:
            print(f"[VIDEO] Frame error: {e}")
            await asyncio.sleep(0.1)
            continue

        yield boundary + header + frame_bytes + b"\r\n"
        await asyncio.sleep(max(0.0, interval - (time.monotonic() - t0)))


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control":     "no-cache, no-store",
            "Pragma":            "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        loop="asyncio",
    )
