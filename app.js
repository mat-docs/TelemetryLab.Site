const LAP = __LAP_DATA__;

  /* ── the course catalogue's channel lanes ───────────────────────────
     A lane carries a real channel off the lap, drawn as a polyline. A course
     that does not exist yet gets a flat baseline, because that is what an
     unconnected channel looks like on an instrument — and it cannot be
     mistaken for a promise. */
  (function () {
    const NS = 'http://www.w3.org/2000/svg';
    const W = 1000, H = 132, PAD = 16;

    function el(name, attrs) {
      const n = document.createElementNS(NS, name);
      for (const k in attrs) n.setAttribute(k, attrs[k]);
      return n;
    }

    document.querySelectorAll('.lane').forEach(lane => {
      const svg = el('svg', {
        viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'none', 'aria-hidden': 'true',
      });

      if (lane.dataset.nosignal) {
        svg.appendChild(el('line', {
          x1: 0, y1: H / 2, x2: W, y2: H / 2,
          stroke: 'var(--line-2)', 'stroke-width': 1.5, 'stroke-dasharray': '3 7',
        }));
        lane.appendChild(svg);
        const tag = document.createElement('span');
        tag.className = 'nosignal';
        tag.textContent = 'No signal';
        lane.appendChild(tag);
        return;
      }

      const key = lane.dataset.channel;
      const ch = LAP.channels && LAP.channels[key];
      if (!ch) { lane.appendChild(svg); return; }

      const v = ch.v;
      const step = W / (v.length - 1);
      const y = t => PAD + (1 - t) * (H - PAD * 2);
      const d = v.map((t, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)},${y(t).toFixed(1)}`).join('');

      // Fill under the trace, then the trace. One hue: speed is a magnitude,
      // and a second hue would imply a midpoint that does not exist.
      const grad = el('linearGradient', { id: 'lanefill', x1: 0, y1: 0, x2: 0, y2: 1 });
      grad.appendChild(el('stop', { offset: '0%', 'stop-color': 'var(--accent)', 'stop-opacity': '0.20' }));
      grad.appendChild(el('stop', { offset: '100%', 'stop-color': 'var(--accent)', 'stop-opacity': '0' }));
      const defs = el('defs', {});
      defs.appendChild(grad);
      svg.appendChild(defs);

      svg.appendChild(el('path', { d: `${d}L${W},${H}L0,${H}Z`, fill: 'url(#lanefill)' }));
      svg.appendChild(el('path', {
        d, fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2,
        'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke',
      }));
      lane.appendChild(svg);

      const cap = document.createElement('span');
      cap.className = 'lane-cap';
      cap.innerHTML = `<b>${key}</b> · ${ch.units} · ${ch.rate} Hz · ` +
        `${ch.min.toFixed(1)}–${ch.max.toFixed(1)} ${ch.units} · one lap`;
      lane.appendChild(cap);
    });
  })();

  /* ── the hero ───────────────────────────────────────────────────────── */
  (function () {
    const canvas = document.getElementById('trackmap');
    const readout = document.getElementById('readout');
    if (!canvas || !LAP || !LAP.points) return;

    const ctx = canvas.getContext('2d');
    const pts = LAP.points;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Single-hue sequential ramp for speed. Speed is a magnitude, not a
    // polarity, so it gets one hue stepped in lightness — a two-hue gradient
    // would imply a meaningful midpoint, and 140 km/h is not a neutral value.
    const RAMP = ['#5A2609', '#A8480F', '#ED6D20', '#F9A463', '#FFD9B0'];

    function rampAt(t) {
      const x = Math.max(0, Math.min(1, t));
      const seg = x * (RAMP.length - 1);
      const i = Math.min(RAMP.length - 2, Math.floor(seg));
      const f = seg - i;
      const a = hex(RAMP[i]), b = hex(RAMP[i + 1]);
      return `rgb(${Math.round(a[0] + (b[0] - a[0]) * f)},${Math.round(a[1] + (b[1] - a[1]) * f)},${Math.round(a[2] + (b[2] - a[2]) * f)})`;
    }
    function hex(h) {
      return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
    }

    // Every cell is a real channel off the lap, read at the same fraction of
    // the lap the car has reached. An earlier version of this page derived
    // five of the six from the speed value with invented formulas, on a page
    // whose own copy says nothing here is hardcoded.
    // The units are read off the channel definition, not written here. On a page
    // that claims nothing is hardcoded, the readout should not be the exception.
    const CELLS = [
      { k: 'Speed',     ch: 'Speed',         dp: 1, live: true },
      { k: 'Throttle',  ch: 'Throttle',      dp: 0 },
      { k: 'Brake',     ch: 'Brake',         dp: 0 },
      { k: 'Steering',  ch: 'SteeringAngle', dp: 0 },
      { k: 'RPM',       ch: 'RPM',           dp: 0 },
      { k: 'Lat accel', ch: 'LatAccel',      dp: 1 },
    ];
    const unitsOf = n => ((LAP.channels || {})[n] || {}).units || '';
    readout.innerHTML = CELLS.map(c =>
      `<div class="cell${c.live ? ' live' : ''}"><span class="k">${c.k}</span><span class="v" data-k="${c.k}">—<small>${unitsOf(c.ch)}</small></span></div>`
    ).join('');
    const cells = {};
    CELLS.forEach(c => { cells[c.k] = readout.querySelector(`[data-k="${c.k}"]`); });

    // Denormalise: the JSON carries 0..1 plus the real min/max per channel.
    function channelAt(name, frac) {
      const ch = LAP.channels && LAP.channels[name];
      if (!ch || !ch.v.length) return null;
      const i = Math.min(ch.v.length - 1, Math.max(0, Math.round(frac * (ch.v.length - 1))));
      return ch.min + ch.v[i] * (ch.max - ch.min);
    }

    let W = 0, H = 0, scale = 1, ox = 0, oy = 0;

    function layout() {
      const r = canvas.getBoundingClientRect();
      // Bail if the box has not been laid out yet. Sizing a canvas from a
      // zero-width rect leaves a backing store of 0 px that nothing ever
      // corrects, and the hero renders blank — the ResizeObserver below is
      // what calls us again once the real size exists.
      if (r.width < 1 || r.height < 1) return false;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width; H = r.height;
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const [minX, minY, maxX, maxY] = LAP.bounds;
      const spanX = Math.max(1, maxX - minX), spanY = Math.max(1, maxY - minY);
      // Sit the map to the right of the headline on wide screens, centred on narrow.
      const wide = W > 860;
      const boxW = wide ? W * 0.60 : W * 0.92;
      const boxH = wide ? H * 0.66 : H * 0.46;
      scale = Math.min(boxW / spanX, boxH / spanY);
      const drawW = spanX * scale, drawH = spanY * scale;
      ox = (wide ? W * 0.42 : (W - drawW) / 2) - minX * scale;
      oy = (wide ? H * 0.14 : H * 0.28) + maxY * scale;
      return true;
    }

    const px = p => ox + p.x * scale;
    const py = p => oy - p.y * scale;

    function draw(upto) {
      ctx.clearRect(0, 0, W, H);

      // The rest of the circuit, dim, so the shape reads before the car gets there.
      ctx.beginPath();
      pts.forEach((p, i) => i ? ctx.lineTo(px(p), py(p)) : ctx.moveTo(px(p), py(p)));
      ctx.closePath();
      ctx.strokeStyle = '#1B2429';
      ctx.lineWidth = 7;
      ctx.lineJoin = 'round';
      ctx.stroke();

      // Speed-graded line, as far as the car has got.
      ctx.lineWidth = 6.5;
      ctx.lineCap = 'round';
      for (let i = 1; i <= upto && i < pts.length; i++) {
        ctx.beginPath();
        ctx.moveTo(px(pts[i - 1]), py(pts[i - 1]));
        ctx.lineTo(px(pts[i]), py(pts[i]));
        ctx.strokeStyle = rampAt(pts[i].v);
        ctx.stroke();
      }

      // The car.
      if (upto > 0 && upto < pts.length) {
        const p = pts[upto];
        ctx.beginPath();
        ctx.arc(px(p), py(p), 5.5, 0, Math.PI * 2);
        ctx.fillStyle = '#FFF6EE';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(px(p), py(p), 13, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,214,178,0.28)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    function update(i) {
      const frac = i / (pts.length - 1);
      CELLS.forEach(c => {
        const raw = channelAt(c.ch, frac);
        if (raw === null || !cells[c.k]) return;
        cells[c.k].innerHTML = `${raw.toFixed(c.dp)}<small>${unitsOf(c.ch)}</small>`;
      });
    }

    let i = 0, raf = null, last = 0;

    function tick(ts) {
      if (!last) last = ts;
      const dt = ts - last;
      // One lap in about nine seconds — slow enough to read, quick enough to
      // finish before anyone scrolls past.
      if (dt > 16) {
        last = ts;
        i += Math.max(1, Math.round(pts.length / (9000 / 16)));
        if (i >= pts.length) i = 0;
        draw(i);
        update(i);
      }
      raf = requestAnimationFrame(tick);
    }

    let running = false;

    function start() {
      // The readout is DOM text and needs no canvas geometry, so fill it before
      // the layout guard. Otherwise a hero that cannot size itself yet leaves
      // six em dashes on screen when it could be showing real samples.
      update(i);
      if (!layout()) return;      // not laid out yet; the observer will call back
      if (running) return;
      running = true;
      // Paint one frame synchronously. requestAnimationFrame does not fire in a
      // background or non-compositing tab, and without this the readout sits on
      // em dashes rather than showing a real sample.
      draw(i); update(i);
      if (reduce) { draw(pts.length - 1); update(pts.length - 1); return; }
      last = 0;
      raf = requestAnimationFrame(tick);
    }

    // A ResizeObserver rather than a window resize listener.
    //
    // The canvas can reach its real size well after this script runs — web
    // fonts settling, an iframe being sized by its host, a late reflow. A
    // window resize event never fires for any of those, so a page that only
    // listens for resize renders its hero blank and never recovers.
    if ('ResizeObserver' in window) {
      let t;
      new ResizeObserver(() => {
        clearTimeout(t);
        t = setTimeout(() => { if (layout()) { start(); draw(i); update(i); } }, 60);
      }).observe(canvas);
    } else {
      window.addEventListener('resize', () => { if (layout()) draw(i); });
    }

    start();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(start);
    window.addEventListener('load', start);
  })();
