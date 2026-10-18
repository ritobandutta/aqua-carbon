/* AquaCarbon DC landing page. No dependencies, no images: every visual is generated here.
   Motion policy: under prefers-reduced-motion nothing animates, the intro never runs, and each canvas draws one still frame. */
(() => {
  "use strict";

  const reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const TAU = Math.PI * 2;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const safe = (fn) => { try { fn(); } catch (e) { console.error(e); } };

  /* ---------- sizing and a visibility-gated 2D loop ---------- */
  function fit(canvas, cap) {
    const dpr = Math.min(window.devicePixelRatio || 1, cap || 2);
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width * dpr));
    const h = Math.max(1, Math.round(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    return { w, h, d: dpr };
  }

  // One requestAnimationFrame loop per canvas. It idles off-screen and while the tab is hidden.
  function loop(canvas, draw, still) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let visible = false, raf = 0;
    const t0 = performance.now();
    const frame = (now) => {
      raf = 0;
      const { w, h, d } = fit(canvas);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.lineCap = "round"; ctx.lineJoin = "round";
      draw(ctx, reduced ? (still || 1.7) : (now - t0) / 1000, w, h, d);
      if (visible && !reduced && !document.hidden) raf = requestAnimationFrame(frame);
    };
    const kick = () => { if (visible && !raf) raf = requestAnimationFrame(frame); };
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((es) => { visible = es[0].isIntersecting; kick(); }).observe(canvas);
    } else { visible = true; kick(); }
    document.addEventListener("visibilitychange", kick);
    window.addEventListener("resize", () => { if (visible && !raf) raf = requestAnimationFrame(frame); });
  }

  /* ---------- intro stage, then the per-glyph headline rise ---------- */
  function introStage() {
    const el = $("#intro");
    const ready = () => document.body.classList.add("is-ready");
    if (!el || reduced) { ready(); return; }
    setTimeout(() => el.classList.add("is-in"), 220);
    setTimeout(() => el.classList.add("is-lift"), 1500);
    setTimeout(() => { el.classList.add("is-out"); ready(); }, 2050);
    // failsafe: if anything above stalls, never leave the page hidden behind the stage
    setTimeout(() => { el.classList.add("is-out"); ready(); }, 4500);
  }

  function splitHeadline() {
    const h = $("#headline");
    if (!h) return;
    const text = h.textContent.trim();
    h.setAttribute("aria-label", text);
    h.textContent = "";
    let i = 0;
    const words = text.split(/\s+/);
    words.forEach((word, wi) => {
      const w = document.createElement("span");
      w.className = "w";
      w.setAttribute("aria-hidden", "true");
      Array.from(word).forEach((ch) => {
        const g = document.createElement("span");
        g.className = "g";
        g.textContent = ch;
        g.style.transitionDelay = (i++ * 42) + "ms";
        w.appendChild(g);
      });
      h.appendChild(w);
      if (wi < words.length - 1) h.appendChild(document.createTextNode(" "));
    });
  }

  /* ---------- hero: WebGL ribbons with a canvas-2D fallback ---------- */
  const VERT = "attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }";
  const FRAG = [
    "precision mediump float;",
    "uniform vec2 u_res; uniform float u_time;",
    "float ribbon(vec2 uv, float off, float f1, float f2, float width, float speed){",
    "  float y = 0.5 + 0.18*sin(uv.x*f1 + u_time*speed + off) + 0.10*sin(uv.x*f2 - u_time*speed*0.7 + off*1.7);",
    "  return 1.0 - smoothstep(0.0, width, abs(uv.y - y));",
    "}",
    "void main(){",
    "  vec2 uv = gl_FragCoord.xy / u_res;",
    "  vec3 indigo = vec3(0.388, 0.400, 0.945);",
    "  vec3 violet = vec3(0.545, 0.361, 0.965);",
    "  vec3 cyan   = vec3(0.133, 0.827, 0.933);",
    "  float a = ribbon(uv, 0.0, 3.1, 7.3, 0.11, 0.35);",
    "  float b = ribbon(uv, 2.1, 2.6, 6.1, 0.09, 0.28);",
    "  float c = ribbon(uv, 4.2, 3.7, 8.2, 0.07, 0.42);",
    "  vec3 col = indigo*a*0.9 + violet*b*0.8 + cyan*c*0.7;",           // additive: crossings brighten to a pale bloom
    "  vec2 q = (uv - vec2(0.5, 0.52)) * vec2(1.0, 1.6);",
    "  col += vec3(0.40, 0.42, 0.90) * exp(-dot(q, q) * 5.0) * 0.12;",   // soft centre glow
    "  float alpha = clamp(max(max(col.r, col.g), col.b), 0.0, 1.0);",    // alpha = clamped sum, the ground shows through
    "  gl_FragColor = vec4(col, alpha);",
    "}"
  ].join("\n");

  function compile(gl, type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
  }

  function startGL(canvas) {
    let gl = null;
    try { gl = canvas.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: false, powerPreference: "low-power" }); } catch (e) { gl = null; }
    if (!gl) return null;
    const vs = compile(gl, gl.VERTEX_SHADER, VERT), fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return null;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uRes = gl.getUniformLocation(prog, "u_res"), uTime = gl.getUniformLocation(prog, "u_time");
    return (t) => {
      const { w, h } = fit(canvas, 1.5);
      gl.viewport(0, 0, w, h);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniform2f(uRes, w, h); gl.uniform1f(uTime, t);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
  }

  const RIBBONS = [
    { off: 0.0, f1: 3.1, f2: 7.3, w: 0.11, s: 0.35, c: "99,102,241" },
    { off: 2.1, f1: 2.6, f2: 6.1, w: 0.09, s: 0.28, c: "139,92,246" },
    { off: 4.2, f1: 3.7, f2: 8.2, w: 0.07, s: 0.42, c: "34,211,238" }
  ];
  function draw2dRibbons(ctx, t, w, h) {
    ctx.globalCompositeOperation = "lighter";
    RIBBONS.forEach((r) => {
      ctx.beginPath();
      for (let x = 0; x <= w; x += 6) {
        const u = x / w;
        const y = 0.5 + 0.18 * Math.sin(u * r.f1 + t * r.s + r.off) + 0.10 * Math.sin(u * r.f2 - t * r.s * 0.7 + r.off * 1.7);
        if (x === 0) ctx.moveTo(x, h * (1 - y)); else ctx.lineTo(x, h * (1 - y));
      }
      ctx.lineWidth = r.w * h * 1.1;
      ctx.strokeStyle = "rgba(" + r.c + ",.34)";
      ctx.stroke();
    });
    ctx.globalCompositeOperation = "source-over";
  }

  function hero() {
    let canvas = $("#hero-canvas");
    const section = $(".hero");
    if (!canvas || !section) return;
    let render = startGL(canvas);
    canvas.dataset.renderer = render ? "webgl" : "2d";
    if (!render) {
      // a canvas that has handed out a WebGL context cannot hand out a 2D one, so swap in a fresh element
      const fresh = canvas.cloneNode(false);
      fresh.dataset.renderer = "2d";
      canvas.replaceWith(fresh); canvas = fresh;
      loop(canvas, (ctx, t, w, h) => draw2dRibbons(ctx, t, w, h), 3.0);
      return;
    }
    let visible = false, raf = 0;
    const t0 = performance.now();
    const frame = (now) => {
      raf = 0;
      render(reduced ? 3.0 : (now - t0) / 1000);
      if (visible && !reduced && !document.hidden) raf = requestAnimationFrame(frame);
    };
    const kick = () => { if (visible && !raf) raf = requestAnimationFrame(frame); };
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((es) => { visible = es[0].isIntersecting; kick(); }).observe(section);
    } else { visible = true; kick(); }
    document.addEventListener("visibilitychange", kick);
    window.addEventListener("resize", () => { if (visible && !raf) raf = requestAnimationFrame(frame); });
  }

  /* ---------- engine tiles: four independent canvases ---------- */
  const lw = (d) => 1.25 * d;

  // a travelling waveform whose amplitude is itself modulated along x
  function vizWave(ctx, t, w, h, d) {
    ctx.lineWidth = lw(d); ctx.strokeStyle = "rgba(255,255,255,.9)";
    ctx.beginPath();
    for (let x = 0; x <= w; x += 2) {
      const u = x / w;
      const amp = (0.25 + 0.75 * Math.abs(Math.sin(u * Math.PI * 1.5 + t * 0.4))) * h * 0.34;
      const y = h / 2 + Math.sin(u * TAU * 3 - t * 2.2) * amp;
      if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // a two-row grid of blocks whose alpha oscillates out of phase per block
  function vizGrid(ctx, t, w, h, d) {
    const cols = 14, rows = 2, gap = 3 * d;
    const bw = (w - gap * (cols - 1)) / cols, bh = (h - gap * (rows - 1)) / rows;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const a = 0.12 + 0.6 * (0.5 + 0.5 * Math.sin(t * 1.7 + c * 0.65 + r * Math.PI));
        ctx.fillStyle = "rgba(255,255,255," + a.toFixed(3) + ")";
        ctx.fillRect(c * (bw + gap), r * (bh + gap), bw, bh);
      }
    }
  }

  // four separated lines at increasing opacity, each waving at its own frequency: water, power, carbon, cost
  function vizStems(ctx, t, w, h, d) {
    const n = 4;
    for (let i = 0; i < n; i++) {
      const y0 = h * (i + 0.5) / n;
      ctx.lineWidth = lw(d);
      ctx.strokeStyle = "rgba(255,255,255," + (0.22 + i * 0.2).toFixed(2) + ")";
      ctx.beginPath();
      for (let x = 0; x <= w; x += 3) {
        const y = y0 + Math.sin((x / w) * TAU * (1.5 + i * 0.9) + t * (1 + i * 0.35)) * h * 0.07;
        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
  }

  // a ring with a sweeping arc and a centre dot
  function vizRing(ctx, t, w, h, d) {
    const cx = w / 2, cy = h / 2, r = Math.min(w, h) * 0.38;
    ctx.lineWidth = lw(d);
    ctx.strokeStyle = "rgba(255,255,255,.22)";
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.stroke();
    const a = t * 1.4;
    ctx.strokeStyle = "rgba(255,255,255,.95)";
    ctx.beginPath(); ctx.arc(cx, cy, r, a, a + 1.1); ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.beginPath(); ctx.arc(cx, cy, 2.5 * d, 0, TAU); ctx.fill();
  }

  const VIZ = { wave: vizWave, grid: vizGrid, stems: vizStems, ring: vizRing };
  function tiles() {
    $$("canvas[data-viz]").forEach((c) => { const fn = VIZ[c.dataset.viz]; if (fn) loop(c, fn, 1.7); });
  }

  /* ---------- the day: 24 modelled ambient temperatures with one selected band ---------- */
  // Bengaluru, annual average, 15 MW: ambient_temp_c for each hour from the dispatch model (engine/arbiter.py).
  // tests/test_ui_contract.py fails if this array drifts from the engine.
  const TEMPS = [24.5, 24.0, 23.7, 23.5, 23.3, 23.7, 25.0, 27.5, 30.0, 32.0, 33.5, 34.3, 34.5, 34.3, 33.7, 32.5, 31.0, 29.5, 28.0, 26.7, 26.0, 25.5, 25.0, 24.7];
  const BARS = 72;            // three bars per hour
  const SEL0 = 36, SEL1 = 51; // bars 36..50 = 12:00 to 17:00, the window the dispatch model defers flexible load out of
  const T_MIN = Math.min.apply(null, TEMPS), T_MAX = Math.max.apply(null, TEMPS);
  const tempAt = (h) => {
    const i = Math.floor(h) % 24, j = (i + 1) % 24, f = h - Math.floor(h);
    return TEMPS[i] * (1 - f) + TEMPS[j] * f;
  };

  function spectrum() {
    const canvas = $("#spectrum"), readout = $("#readout");
    if (!canvas) return;
    const DEFAULT = readout ? readout.textContent : "";
    if (readout) {
      const hourAt = (e) => {
        const r = canvas.getBoundingClientRect();
        return Math.max(0, Math.min(23, Math.floor(((e.clientX - r.left) / r.width) * 24)));
      };
      canvas.addEventListener("pointermove", (e) => {
        const hr = hourAt(e), inside = hr >= 12 && hr < 17;
        readout.textContent = String(hr).padStart(2, "0") + ":00 \u00b7 " + TEMPS[hr].toFixed(1) + "\u00b0C \u00b7 " + (inside ? "deferral window" : "normal dispatch");
      });
      canvas.addEventListener("pointerleave", () => { readout.textContent = DEFAULT; });
    }
    loop(canvas, (ctx, t, w, h, d) => {
      const narrow = window.innerWidth <= 820;
      const padTop = 22 * d, padBottom = (narrow ? 20 : 66) * d, base = h - padBottom, maxH = base - padTop;
      const gap = Math.max(2 * d, (w / BARS) * 0.28);
      const bw = (w - gap * (BARS - 1)) / BARS;
      let tallestSelected = 0;
      for (let i = 0; i < BARS; i++) {
        const norm = (tempAt((i / BARS) * 24) - T_MIN) / (T_MAX - T_MIN);
        const shimmer = 1 + 0.03 * Math.sin(i * 0.9 + t * 1.3);   // a little life; the readout carries the exact values
        const v = Math.min(1, Math.max(0.05, (0.12 + 0.88 * norm) * shimmer));
        const selected = i >= SEL0 && i < SEL1;
        const bh = v * maxH, x = i * (bw + gap);
        if (selected) tallestSelected = Math.max(tallestSelected, bh);
        ctx.fillStyle = selected ? "#6366F1" : "rgba(255,255,255,.16)";
        ctx.fillRect(x, base - bh, bw, bh);
      }
      ctx.fillStyle = "rgba(255,255,255,.18)";
      ctx.fillRect(0, base + 6 * d, w, d);
      // stroked marker box around exactly the selected run, sized to its tallest bar
      const mx = SEL0 * (bw + gap) - gap / 2, mw = (SEL1 - SEL0) * (bw + gap);
      const top = base - tallestSelected - 10 * d;
      ctx.lineWidth = d; ctx.strokeStyle = "rgba(255,255,255,.7)";
      ctx.strokeRect(mx + 0.5 * d, top, mw, base + 6 * d - top);
    }, 1.7);
  }

  /* ---------- scroll reveals ---------- */
  function reveals() {
    const els = $$(".rv");
    if (reduced || !("IntersectionObserver" in window)) { els.forEach((e) => e.classList.add("is-in")); return; }
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
    }, { threshold: 0.16, rootMargin: "0px 0px -8% 0px" });
    els.forEach((e) => io.observe(e));
  }

  document.addEventListener("DOMContentLoaded", () => {
    safe(splitHeadline);
    safe(reveals);
    safe(hero);
    safe(tiles);
    safe(spectrum);
    safe(introStage);
  });
})();
