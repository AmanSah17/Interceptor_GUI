/**
 * telemetry.js
 * Renders all telemetry data received from WebSocket into the UI.
 */

(function () {
  'use strict';

  // Cache DOM references
  const $ = id => document.getElementById(id);

  let _prev = {};

  // ── Main update function ──────────────────────────────────────────────────
  function update(data) {
    _setValue('valAltitude', data.altitude.toFixed(1), _prev.altitude, data.altitude);
    _setValue('valSpeed',    data.speed.toFixed(1),    _prev.speed,    data.speed);
    _setValue('valHeading',  data.heading.toFixed(1) + '°', _prev.heading, data.heading);
    _setVspeed(data.vspeed);
    _setBattery(data.battery);
    _setSignal(data.signal);
    _setMode(data.mode);
    _setHeadingDir(data.heading);
    _setStatusBar(data);
    _setDetections(data.boxes);

    _prev = { ...data };
  }

  // ── Individual updaters ──────────────────────────────────────────────────
  function _setValue(id, text, prevRaw, currRaw) {
    const el = $(id);
    if (!el) return;
    if (prevRaw !== undefined && Math.abs(currRaw - prevRaw) > 0.5) {
      el.classList.remove('value-flash');
      void el.offsetWidth; // reflow to restart animation
      el.classList.add('value-flash');
    }
    el.textContent = text;
  }

  function _setVspeed(v) {
    const el = $('valVspeed');
    if (!el) return;
    const sign = v >= 0 ? '+' : '';
    el.textContent = sign + v.toFixed(1);
    el.className = 'telem-value ' + (v >= 0 ? 'climbing' : 'descending');
  }

  function _setBattery(pct) {
    const valEl = $('valBattery');
    const barEl = $('batteryBar');
    if (valEl) valEl.textContent = pct.toFixed(1) + '%';
    if (barEl) {
      barEl.style.width = pct + '%';
      barEl.className = 'battery-bar-fill ' + (
        pct > 50 ? 'high' : pct > 20 ? 'mid' : 'low'
      );
    }
  }

  function _setSignal(sig) {
    const pct = Math.round(sig * 100);
    const el  = $('valSignal');
    if (el) el.textContent = pct + '%';

    const bars = document.querySelectorAll('#signalBars .signal-bar');
    const activeCount = Math.round(sig * 5);
    bars.forEach((b, i) => {
      b.classList.toggle('active', i < activeCount);
    });
  }

  function _setMode(mode) {
    const badge = $('modeBadge');
    if (!badge) return;
    const isAuto = mode === 'AUTONOMOUS';
    const icon   = isAuto ? '&#9654;' : '&#9646;&#9646;';
    badge.innerHTML = `<span>${icon}</span> ${isAuto ? 'AUTONOMOUS' : 'MANUAL'}`;
    badge.className = 'mode-badge ' + (isAuto ? 'autonomous' : 'manual');
  }

  function _setHeadingDir(h) {
    const el = $('valHeadingDir');
    if (!el) return;
    const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
    el.textContent = dirs[Math.round(h / 22.5) % 16];
  }

  function _setStatusBar(data) {
    const gpsEl  = $('statusGps');
    const distEl = $('statusDist');
    const msgEl  = $('statusMsg');
    const timeEl = $('statusTime');

    if (gpsEl)  gpsEl.textContent  = `GPS: ${data.lat.toFixed(6)} / ${data.lon.toFixed(6)}`;
    if (distEl) distEl.textContent = `DIST: ${data.distance.toFixed(0)} m`;
    if (msgEl)  msgEl.textContent  = `MODE: ${data.mode}  |  HDG: ${data.heading.toFixed(1)}°  |  ALT: ${data.altitude.toFixed(1)} m`;

    const now = new Date();
    if (timeEl) timeEl.textContent = `UTC ${now.toUTCString().split(' ')[4]}`;
  }

  function _setDetections(boxes) {
    const list = $('detection-list');
    if (!list) return;

    if (!boxes || boxes.length === 0) {
      list.innerHTML = '<div class="detection-item" style="color:var(--text-dim);justify-content:center;">No targets detected</div>';
      return;
    }

    list.innerHTML = boxes.map(b => {
      const confPct = Math.round(b.conf * 100);
      return `
        <div class="detection-item">
          <span class="detection-label">${b.label}</span>
          <div class="conf-bar-mini">
            <div class="conf-fill" style="width:${confPct}%"></div>
          </div>
          <span class="detection-conf">${confPct}%</span>
        </div>
      `;
    }).join('');
  }

  window.Telemetry = { update, _forceMode: _setMode };

})();
