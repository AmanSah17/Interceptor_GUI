/**
 * app.js
 * Main application entry point.
 * Manages:
 *  - Header clock
 *  - WebSocket lifecycle (connect / auto-reconnect)
 *  - Mode toggle (REST API call)
 *  - Dispatching telemetry data to all sub-modules
 */

(function () {
  'use strict';

  const WS_URL       = `ws://${location.host}/ws/telemetry`;
  const RECONNECT_MS = 2500;

  let _ws             = null;
  let _reconnectTimer = null;
  let _isToggling     = false;

  // ── Clock ──────────────────────────────────────────────────────────────────
  function _tickClock() {
    const el = document.getElementById('headerClock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-GB', { hour12: false });
  }
  setInterval(_tickClock, 1000);
  _tickClock();

  // ── Connection status ──────────────────────────────────────────────────────
  function _setConnected(state) {
    const dot   = document.getElementById('connDot');
    const label = document.getElementById('connLabel');
    if (dot)   dot.classList.toggle('connected', state);
    if (label) label.textContent = state ? 'CONNECTED' : 'DISCONNECTED';

    const msg = document.getElementById('statusMsg');
    if (msg && !state) msg.textContent = 'RECONNECTING TO TELEMETRY…';
  }

  // ── WebSocket ──────────────────────────────────────────────────────────────
  function _connect() {
    if (_ws) { try { _ws.close(); } catch (_) {} }

    _ws = new WebSocket(WS_URL);

    _ws.onopen = () => {
      console.log('[WS] Connected');
      _setConnected(true);
      if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
    };

    _ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.ping || data.pong) return;

        if (window.Telemetry) Telemetry.update(data);
        if (window.Compass)   Compass.setHeading(data.heading);
        if (window.Minimap)   Minimap.updatePosition(data.lat, data.lon, data.heading);
        if (window.VideoHUD) {
          VideoHUD.updateBoxes(data.boxes);
          const pitch = Math.max(-15, Math.min(15, data.vspeed * 2));
          VideoHUD.updateHorizon(pitch, 0);
        }
      } catch (e) {
        console.warn('[WS] Parse error:', e);
      }
    };

    _ws.onclose = (ev) => {
      console.log('[WS] Closed:', ev.code, ev.reason);
      _setConnected(false);
      _scheduleReconnect();
    };

    _ws.onerror = () => {
      _setConnected(false);
    };
  }

  function _scheduleReconnect() {
    if (_reconnectTimer) return;
    _reconnectTimer = setTimeout(() => {
      _reconnectTimer = null;
      _connect();
    }, RECONNECT_MS);
  }

  // ── Mode toggle ────────────────────────────────────────────────────────────
  window.toggleMode = async function () {
    if (_isToggling) return;
    _isToggling = true;

    const badge = document.getElementById('modeBadge');
    if (badge) {
      badge.classList.add('toggling');
      badge.disabled = true;
    }

    try {
      const res  = await fetch('/api/mode/toggle', { method: 'POST' });
      const json = await res.json();
      // The WebSocket broadcast will update the badge via Telemetry.update()
      // but also update immediately for instant feedback:
      if (window.Telemetry && json.mode) {
        Telemetry._forceMode(json.mode);
      }
      console.log(`[MODE] Switched to ${json.mode}`);
    } catch (e) {
      console.error('[MODE] Toggle failed:', e);
    } finally {
      setTimeout(() => {
        _isToggling = false;
        if (badge) {
          badge.classList.remove('toggling');
          badge.disabled = false;
        }
      }, 500);
    }
  };

  // ── Video error handler ────────────────────────────────────────────────────
  window.handleVideoError = function () {
    const img = document.getElementById('videoFeed');
    if (img) img.style.opacity = '0.15';
    setTimeout(() => {
      const img2 = document.getElementById('videoFeed');
      if (img2) {
        img2.style.opacity = '1';
        img2.src = '/video_feed?' + Date.now();
      }
    }, 3000);
  };

  // ── Boot ───────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    console.log('[GCS] Interceptor Dashboard initialising…');
    _connect();
  });

})();
