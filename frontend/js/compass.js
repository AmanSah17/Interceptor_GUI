/**
 * compass.js
 * Draws an SVG compass rose and updates its rotation from telemetry.
 */

(function () {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const ACCENT  = '#00ff88';
  const DIM     = '#2a4a35';
  const RED     = '#ff3355';
  const TEXT_DIM = '#4a7060';

  let _currentHeading = 0;
  let _targetHeading  = 0;
  let _animFrame      = null;

  // ── Build the static SVG compass rose ──────────────────────────────────
  function buildCompassSVG() {
    const svg = document.getElementById('compass-svg');
    if (!svg) return;
    svg.innerHTML = '';

    const cx = 65, cy = 65, r = 60;

    // Outer ring
    _circle(svg, cx, cy, r,       { stroke: ACCENT, 'stroke-width': '1',   fill: 'none', opacity: '0.35' });
    _circle(svg, cx, cy, r - 8,   { stroke: ACCENT, 'stroke-width': '0.5', fill: 'none', opacity: '0.20' });
    _circle(svg, cx, cy, 6,       { fill: '#0a0e14', stroke: ACCENT, 'stroke-width': '1.2' });

    // Tick marks
    for (let deg = 0; deg < 360; deg += 5) {
      const major = deg % 45 === 0;
      const mid   = deg % 15 === 0 && !major;
      const len   = major ? 10 : (mid ? 6 : 3);
      const strokeW = major ? 1.5 : 0.8;
      const colour  = major ? ACCENT : (mid ? '#2a5a40' : DIM);
      const rad = (deg - 90) * Math.PI / 180;
      const x1 = cx + (r - 2) * Math.cos(rad);
      const y1 = cy + (r - 2) * Math.sin(rad);
      const x2 = cx + (r - 2 - len) * Math.cos(rad);
      const y2 = cy + (r - 2 - len) * Math.sin(rad);
      _line(svg, x1, y1, x2, y2, { stroke: colour, 'stroke-width': String(strokeW) });
    }

    // Cardinal labels
    const cardinals = [
      { label: 'N', deg: 0,   colour: RED },
      { label: 'E', deg: 90,  colour: ACCENT },
      { label: 'S', deg: 180, colour: ACCENT },
      { label: 'W', deg: 270, colour: ACCENT },
    ];
    const labelR = r - 18;
    cardinals.forEach(({ label, deg, colour }) => {
      const rad = (deg - 90) * Math.PI / 180;
      const x = cx + labelR * Math.cos(rad);
      const y = cy + labelR * Math.sin(rad) + 4;
      const t = _text(svg, label, x, y, {
        fill: colour,
        'font-size': '8',
        'font-family': 'Orbitron, monospace',
        'font-weight': '700',
        'text-anchor': 'middle',
        'dominant-baseline': 'middle',
        filter: `drop-shadow(0 0 3px ${colour})`,
      });
    });

    // Heading arrow (N-pointing)
    const arrow = document.createElementNS(SVG_NS, 'polygon');
    arrow.setAttribute('id', 'compassArrow');
    arrow.setAttribute('points', `${cx},${cy - 45} ${cx - 7},${cy + 10} ${cx},${cy + 5} ${cx + 7},${cy + 10}`);
    arrow.setAttribute('fill', RED);
    arrow.setAttribute('opacity', '0.9');
    arrow.setAttribute('filter', `drop-shadow(0 0 4px ${RED})`);
    svg.appendChild(arrow);

    // South arrow (opposite, dimmer)
    const arrowS = document.createElementNS(SVG_NS, 'polygon');
    arrowS.setAttribute('points', `${cx},${cy + 45} ${cx - 5},${cy - 5} ${cx},${cy} ${cx + 5},${cy - 5}`);
    arrowS.setAttribute('fill', ACCENT);
    arrowS.setAttribute('opacity', '0.5');
    svg.appendChild(arrowS);
  }

  // ── Heading update (smooth interpolation) ───────────────────────────────
  function setHeading(heading) {
    _targetHeading = heading;
    if (!_animFrame) _animate();
  }

  function _animate() {
    // Shortest-path interpolation
    let diff = _targetHeading - _currentHeading;
    if (diff > 180)  diff -= 360;
    if (diff < -180) diff += 360;

    if (Math.abs(diff) < 0.2) {
      _currentHeading = _targetHeading;
      _animFrame = null;
    } else {
      _currentHeading += diff * 0.12;
      _animFrame = requestAnimationFrame(_animate);
    }

    // Rotate the entire compass BODY (not the arrow — arrow always points N)
    // We rotate the SVG group holding the rose, arrow stays fixed
    const svg = document.getElementById('compass-svg');
    if (svg) {
      svg.style.transform = `rotate(${-_currentHeading}deg)`;
    }

    // Update text displays
    const hDisp = document.getElementById('compassHeading');
    const dDisp = document.getElementById('compassDir');
    if (hDisp) hDisp.textContent = `${Math.round(_currentHeading).toString().padStart(3, '0')}°`;
    if (dDisp) dDisp.textContent = _headingToDir(_currentHeading);
  }

  function _headingToDir(h) {
    const dirs = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
    return dirs[Math.round(h / 22.5) % 16];
  }

  // ── SVG helpers ─────────────────────────────────────────────────────────
  function _circle(svg, cx, cy, r, attrs) {
    const el = document.createElementNS(SVG_NS, 'circle');
    el.setAttribute('cx', cx); el.setAttribute('cy', cy); el.setAttribute('r', r);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    svg.appendChild(el);
    return el;
  }

  function _line(svg, x1, y1, x2, y2, attrs) {
    const el = document.createElementNS(SVG_NS, 'line');
    el.setAttribute('x1', x1); el.setAttribute('y1', y1);
    el.setAttribute('x2', x2); el.setAttribute('y2', y2);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    svg.appendChild(el);
    return el;
  }

  function _text(svg, content, x, y, attrs) {
    const el = document.createElementNS(SVG_NS, 'text');
    el.setAttribute('x', x); el.setAttribute('y', y);
    el.textContent = content;
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    svg.appendChild(el);
    return el;
  }

  // ── Init on DOM ready ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', buildCompassSVG);

  // ── Public API ───────────────────────────────────────────────────────────
  window.Compass = { setHeading };

})();
