/**
 * video.js
 * Manages the HUD canvas overlay on top of the MJPEG video feed.
 * Draws:
 *   - Bounding boxes with military bracket corners
 *   - Confidence labels
 *   - Artificial horizon (mini, top-left)
 *   - FPS counter
 */

(function () {
  'use strict';

  const ACCENT    = '#00ff88';
  const ACCENT_DIM = 'rgba(0,255,136,0.55)';
  const DANGER    = '#ff3355';
  const AMBER     = '#ffb300';

  let _canvas, _ctx, _img;
  let _boxes    = [];
  let _horizon  = { pitch: 0, roll: 0 };
  let _lastFrame = performance.now();
  let _fps       = 0;
  let _frameCount = 0;
  let _fpsTimer   = 0;

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    _canvas = document.getElementById('hudCanvas');
    _img    = document.getElementById('videoFeed');
    if (!_canvas || !_img) return;
    _ctx = _canvas.getContext('2d');

    // Resize canvas to match rendered image size
    _resizeCanvas();
    window.addEventListener('resize', _resizeCanvas);

    requestAnimationFrame(_drawLoop);
  }

  function _resizeCanvas() {
    if (!_canvas || !_img) return;
    const rect = _img.getBoundingClientRect();
    _canvas.width  = rect.width  || _img.clientWidth  || 1280;
    _canvas.height = rect.height || _img.clientHeight || 720;
    _canvas.style.width  = _canvas.width  + 'px';
    _canvas.style.height = _canvas.height + 'px';
  }

  // ── Main draw loop ────────────────────────────────────────────────────────
  function _drawLoop(now) {
    _canvas.width = _canvas.width; // fast clear

    const W = _canvas.width;
    const H = _canvas.height;

    // FPS calculation
    _frameCount++;
    _fpsTimer += now - _lastFrame;
    _lastFrame = now;
    if (_fpsTimer >= 500) {
      _fps = Math.round(_frameCount * (1000 / _fpsTimer));
      _frameCount = 0;
      _fpsTimer   = 0;
      const el = document.getElementById('fpsCounter');
      if (el) el.textContent = `${_fps} FPS`;
    }

    // Draw bounding boxes
    _boxes.forEach(box => _drawBox(box, W, H));

    // Draw mini artificial horizon
    _drawHorizon(W, H);

    requestAnimationFrame(_drawLoop);
  }

  // ── Bounding box rendering ────────────────────────────────────────────────
  function _drawBox(box, W, H) {
    const x = box.x * W;
    const y = box.y * H;
    const w = box.w * W;
    const h = box.h * H;
    const colour = box.label === 'Unknown' ? AMBER : ACCENT;

    _ctx.save();

    // Faint fill
    _ctx.fillStyle = `rgba(0,255,136,0.04)`;
    _ctx.fillRect(x, y, w, h);

    // Military corner brackets instead of full rect
    const arm = Math.min(w, h) * 0.25;
    _ctx.strokeStyle = colour;
    _ctx.lineWidth   = 1.8;
    _ctx.shadowColor = colour;
    _ctx.shadowBlur  = 8;

    // Top-left
    _ctx.beginPath(); _ctx.moveTo(x + arm, y); _ctx.lineTo(x, y); _ctx.lineTo(x, y + arm); _ctx.stroke();
    // Top-right
    _ctx.beginPath(); _ctx.moveTo(x + w - arm, y); _ctx.lineTo(x + w, y); _ctx.lineTo(x + w, y + arm); _ctx.stroke();
    // Bottom-left
    _ctx.beginPath(); _ctx.moveTo(x + arm, y + h); _ctx.lineTo(x, y + h); _ctx.lineTo(x, y + h - arm); _ctx.stroke();
    // Bottom-right
    _ctx.beginPath(); _ctx.moveTo(x + w - arm, y + h); _ctx.lineTo(x + w, y + h); _ctx.lineTo(x + w, y + h - arm); _ctx.stroke();

    // Label background
    const label  = `${box.label}  ${Math.round(box.conf * 100)}%`;
    const fSize  = Math.max(10, Math.min(14, w * 0.09));
    _ctx.font    = `bold ${fSize}px "Share Tech Mono", monospace`;
    const tw     = _ctx.measureText(label).width;
    const lx     = x;
    const ly     = y - fSize - 4;

    if (ly > 0) {
      _ctx.fillStyle = 'rgba(0,0,0,0.65)';
      _ctx.fillRect(lx - 2, ly - 2, tw + 8, fSize + 6);
      _ctx.fillStyle = colour;
      _ctx.shadowBlur = 6;
      _ctx.fillText(label, lx + 2, ly + fSize);
    }

    // Confidence arc (small corner indicator)
    const arcR = 8;
    _ctx.shadowBlur = 0;
    _ctx.strokeStyle = colour;
    _ctx.lineWidth   = 1.5;
    _ctx.beginPath();
    _ctx.arc(x + w - 5, y + h - 5, arcR, -Math.PI / 2, -Math.PI / 2 + (2 * Math.PI * box.conf));
    _ctx.stroke();

    _ctx.restore();
  }

  // ── Artificial horizon (mini, top-left) ──────────────────────────────────
  function _drawHorizon(W, H) {
    const cx = 90, cy = H - 90;
    const radius = 55;

    _ctx.save();
    _ctx.translate(cx, cy);
    _ctx.rotate(_horizon.roll * Math.PI / 180);

    // Clip to circle
    _ctx.beginPath();
    _ctx.arc(0, 0, radius, 0, Math.PI * 2);
    _ctx.clip();

    // Sky (top half)
    const pitchOffset = _horizon.pitch * 1.2;
    const grad = _ctx.createLinearGradient(0, -radius, 0, radius);
    grad.addColorStop(0, 'rgba(0,30,60,0.75)');
    grad.addColorStop(0.5 + pitchOffset / (radius * 2), 'rgba(0,30,60,0.75)');
    grad.addColorStop(0.5 + pitchOffset / (radius * 2), 'rgba(20,50,20,0.75)');
    grad.addColorStop(1, 'rgba(20,50,20,0.75)');
    _ctx.fillStyle = grad;
    _ctx.fillRect(-radius, -radius, radius * 2, radius * 2);

    // Horizon line
    _ctx.strokeStyle = ACCENT;
    _ctx.lineWidth   = 1.5;
    _ctx.shadowColor = ACCENT;
    _ctx.shadowBlur  = 6;
    _ctx.beginPath();
    _ctx.moveTo(-radius, pitchOffset);
    _ctx.lineTo(radius,  pitchOffset);
    _ctx.stroke();

    // Pitch ladder lines
    _ctx.lineWidth  = 0.8;
    _ctx.shadowBlur = 0;
    [-20, -10, 10, 20].forEach(p => {
      const py = pitchOffset - p * 1.2;
      if (py > -radius && py < radius) {
        const lw = Math.abs(p) === 20 ? 20 : 12;
        _ctx.beginPath();
        _ctx.moveTo(-lw, py); _ctx.lineTo(lw, py);
        _ctx.stroke();
      }
    });

    _ctx.restore();

    // Outer ring
    _ctx.save();
    _ctx.translate(cx, cy);
    _ctx.beginPath();
    _ctx.arc(0, 0, radius, 0, Math.PI * 2);
    _ctx.strokeStyle = ACCENT;
    _ctx.lineWidth   = 1;
    _ctx.shadowColor = ACCENT;
    _ctx.shadowBlur  = 6;
    _ctx.stroke();

    // Fixed aircraft reference
    _ctx.strokeStyle = '#fff';
    _ctx.shadowBlur  = 0;
    _ctx.lineWidth   = 2;
    _ctx.beginPath(); _ctx.moveTo(-20, 0); _ctx.lineTo(-6, 0); _ctx.lineTo(-2, 4); _ctx.stroke();
    _ctx.beginPath(); _ctx.moveTo( 20, 0); _ctx.lineTo( 6, 0); _ctx.lineTo( 2, 4); _ctx.stroke();
    _ctx.beginPath(); _ctx.arc(0, 0, 2, 0, Math.PI * 2); _ctx.fillStyle = '#fff'; _ctx.fill();

    // Label
    _ctx.font      = '8px "Share Tech Mono", monospace';
    _ctx.fillStyle = ACCENT;
    _ctx.textAlign = 'center';
    _ctx.fillText('AH', 0, radius + 12);
    _ctx.restore();
  }

  // ── Public API ────────────────────────────────────────────────────────────
  function updateBoxes(boxes) {
    _boxes = boxes || [];
  }

  function updateHorizon(pitch, roll) {
    _horizon.pitch = pitch || 0;
    _horizon.roll  = roll  || 0;
  }

  document.addEventListener('DOMContentLoaded', init);
  window.VideoHUD = { updateBoxes, updateHorizon };

})();
