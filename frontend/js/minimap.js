/**
 * minimap.js
 * Leaflet-based minimap showing drone GPS position and trail.
 */

(function () {
  'use strict';

  const TRAIL_MAX   = 250;    // max GPS points in trail polyline
  const TRAIL_COLOR = '#00ff88';
  const DRONE_COLOR = '#00ff88';

  let _map         = null;
  let _droneMarker = null;
  let _trailLine   = null;
  let _trailPoints = [];
  let _initialised = false;

  // ── Initialise Leaflet map ───────────────────────────────────────────────
  function init(lat, lon) {
    if (_initialised) return;
    _initialised = true;

    _map = L.map('minimap', {
      center: [lat, lon],
      zoom: 15,
      zoomControl: true,
      attributionControl: false,
    });

    // OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '',
    }).addTo(_map);

    // Trail polyline
    _trailLine = L.polyline([], {
      color: TRAIL_COLOR,
      weight: 1.5,
      opacity: 0.65,
    }).addTo(_map);

    // Custom drone icon
    const icon = L.divIcon({
      className: '',
      iconSize:  [20, 20],
      iconAnchor:[10, 10],
      html: _droneIconHTML(),
    });

    _droneMarker = L.marker([lat, lon], { icon, zIndexOffset: 1000 }).addTo(_map);
  }

  // ── Update drone position ────────────────────────────────────────────────
  function updatePosition(lat, lon, heading) {
    if (!_map) {
      init(lat, lon);
    }

    // Move marker
    _droneMarker.setLatLng([lat, lon]);

    // Rotate drone icon
    const el = _droneMarker.getElement();
    if (el) {
      const inner = el.querySelector('.drone-icon-inner');
      if (inner) inner.style.transform = `rotate(${heading}deg)`;
    }

    // Append to trail
    _trailPoints.push([lat, lon]);
    if (_trailPoints.length > TRAIL_MAX) _trailPoints.shift();
    _trailLine.setLatLngs(_trailPoints);

    // Pan map to keep drone centred (with some lag)
    _map.panTo([lat, lon], { animate: true, duration: 0.5 });
  }

  // ── SVG drone icon HTML ──────────────────────────────────────────────────
  function _droneIconHTML() {
    return `
      <div class="drone-icon-inner" style="width:20px;height:20px;transform-origin:center;">
        <svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <!-- Drone body -->
          <polygon points="10,2 13,10 10,8 7,10" fill="${DRONE_COLOR}" opacity="0.95"/>
          <circle cx="10" cy="10" r="2.5" fill="${DRONE_COLOR}" opacity="0.8"/>
          <!-- Rotor lines -->
          <line x1="10" y1="10" x2="3"  y2="3"  stroke="${DRONE_COLOR}" stroke-width="1" opacity="0.6"/>
          <line x1="10" y1="10" x2="17" y2="3"  stroke="${DRONE_COLOR}" stroke-width="1" opacity="0.6"/>
          <line x1="10" y1="10" x2="3"  y2="17" stroke="${DRONE_COLOR}" stroke-width="1" opacity="0.6"/>
          <line x1="10" y1="10" x2="17" y2="17" stroke="${DRONE_COLOR}" stroke-width="1" opacity="0.6"/>
          <!-- Rotors -->
          <circle cx="3"  cy="3"  r="2" stroke="${DRONE_COLOR}" stroke-width="0.8" fill="none" opacity="0.7"/>
          <circle cx="17" cy="3"  r="2" stroke="${DRONE_COLOR}" stroke-width="0.8" fill="none" opacity="0.7"/>
          <circle cx="3"  cy="17" r="2" stroke="${DRONE_COLOR}" stroke-width="0.8" fill="none" opacity="0.7"/>
          <circle cx="17" cy="17" r="2" stroke="${DRONE_COLOR}" stroke-width="0.8" fill="none" opacity="0.7"/>
        </svg>
      </div>
    `;
  }

  window.Minimap = { updatePosition };

})();
