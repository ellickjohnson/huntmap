/* ============================================================
   Contour field — topographic shader background.
   WebGL2, one self-contained file, no dependencies.

   Politely GPU-aware (the pattern every good shader component uses):
     · pauses when the canvas is off-screen or the tab is hidden
     · caps device pixel ratio at 2 AND total pixels at ~1.6MP
     · renders a single still frame for prefers-reduced-motion
   ============================================================ */

const VERT = `#version 300 es
in vec2 a_pos;
void main(){ gl_Position = vec4(a_pos, 0.0, 1.0); }`;

const FRAG = `#version 300 es
precision highp float;
uniform vec2  u_res;
uniform float u_time;
uniform vec3  u_bg;      // ground
uniform vec3  u_line;    // contour ink
uniform vec3  u_hot;     // contour highlight (accent)
uniform float u_scale;   // feature scale: lower = broader landforms
uniform float u_strength;// 0..1 overall ink weight
uniform float u_density; // contour interval count
out vec4 outColor;

float hash(vec2 p){
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}
float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
mat2 ROT = mat2(0.80, 0.60, -0.60, 0.80);

float fbm(vec2 p){
  float v = 0.0, a = 0.50;
  for (int i = 0; i < 5; i++){
    v += a * vnoise(p);
    p = ROT * p * 2.03;
    a *= 0.5;
  }
  return v;
}

// ridged terrain: sharp crests read as topography, not clouds
float terrain(vec2 p){
  float n = fbm(p);
  float ridge = 1.0 - abs(n * 2.0 - 1.0);
  return mix(n, ridge, 0.45);
}

void main(){
  vec2 uv = gl_FragCoord.xy / u_res;
  vec2 p  = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y * u_scale;

  float t = u_time * 0.0085;
  // slow cartographic drift — the landform breathes, it does not fly
  vec2 warp = vec2(sin(p.y * 0.75 + t * 1.3), cos(p.x * 0.92 - t * 1.05)) * 0.55;
  float h = terrain(p * 1.10 + warp + t * 0.35);
  h += 0.22 * fbm(p * 2.7 - warp * 0.6 - t * 0.5);
  h = clamp(h, 0.0, 1.0);

  // contour bands
  float g  = h * u_density;
  float f  = fract(g);
  float d  = min(f, 1.0 - f);
  float aa = max(fwidth(g) * 1.15, 0.0009);
  float line = 1.0 - smoothstep(0.0, aa, d);

  // index contours every 5th line: heavier, warmer
  float isIndex = 1.0 - step(0.5, mod(floor(g), 5.0));
  float ink = mix(0.42, 1.0, isIndex);

  // depth: valleys recede, crests catch light
  float shade = smoothstep(0.15, 0.95, h);

  // vignette keeps the centre readable and the corners quiet
  float vig = smoothstep(1.35, 0.15, length((uv - 0.5) * vec2(1.35, 1.0)));

  vec3 col = mix(u_line, u_hot, shade * 0.50);
  float a = line * ink * u_strength * vig;

  // fine grain so flat areas are never plasticky
  float gr = hash(gl_FragCoord.xy * 1.7 + fract(u_time)) - 0.5;
  col += gr * 0.04;

  outColor = vec4(mix(u_bg, col, a), 1.0);
}`;

function cssColor(el, name, fallback) {
  const v = getComputedStyle(el).getPropertyValue(name).trim();
  return v || fallback;
}

function hexToRgb(hex) {
  const h = hex.replace('#', '').trim();
  const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
  const int = parseInt(n.slice(0, 6) || '000000', 16);
  return [((int >> 16) & 255) / 255, ((int >> 8) & 255) / 255, (int & 255) / 255];
}

/**
 * Mount a contour-field canvas.
 * @param {HTMLCanvasElement} canvas
 * @param {{scale?:number, strength?:number, density?:number}} opts
 */
export function mountContour(canvas, opts = {}) {
  const want = {
    scale: opts.scale ?? 2.1,
    strength: opts.strength ?? 0.55,
    density: opts.density ?? 26,
  };
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  let gl = null;
  try {
    gl = canvas.getContext('webgl2', {
      alpha: false, antialias: false, depth: false, stencil: false,
      powerPreference: 'low-power', preserveDrawingBuffer: false,
    });
  } catch (e) { /* fall through */ }
  if (!gl) return null; // caller keeps its CSS background

  const compile = (type, src) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.warn('contour shader:', gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  };
  const vs = compile(gl.VERTEX_SHADER, VERT);
  const fs = compile(gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) return null;

  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    console.warn('contour link:', gl.getProgramInfoLog(prog));
    return null;
  }
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const aPos = gl.getAttribLocation(prog, 'a_pos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const U = {
    res: gl.getUniformLocation(prog, 'u_res'),
    time: gl.getUniformLocation(prog, 'u_time'),
    bg: gl.getUniformLocation(prog, 'u_bg'),
    line: gl.getUniformLocation(prog, 'u_line'),
    hot: gl.getUniformLocation(prog, 'u_hot'),
    scale: gl.getUniformLocation(prog, 'u_scale'),
    strength: gl.getUniformLocation(prog, 'u_strength'),
    density: gl.getUniformLocation(prog, 'u_density'),
  };

  let w = 1, h = 1, raf = 0, visible = true, running = false, t0 = performance.now();

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let cw = Math.max(1, Math.round(rect.width * dpr));
    let ch = Math.max(1, Math.round(rect.height * dpr));
    // hard pixel budget: a background must never be the heaviest thing on screen
    const budget = 1_600_000;
    if (cw * ch > budget) {
      const k = Math.sqrt(budget / (cw * ch));
      cw = Math.max(1, Math.round(cw * k));
      ch = Math.max(1, Math.round(ch * k));
    }
    if (cw === w && ch === h) return false;
    w = cw; h = ch;
    canvas.width = w; canvas.height = h;
    gl.viewport(0, 0, w, h);
    return true;
  };

  const paintColors = () => {
    const el = canvas;
    const bg = cssColor(el, '--shader-bg', cssColor(el, '--bg', '#0B0F0D'));
    const line = cssColor(el, '--shader-line', cssColor(el, '--line2', '#33423A'));
    const hot = cssColor(el, '--shader-hot', cssColor(el, '--accent', '#FF6B1A'));
    gl.uniform3fv(U.bg, hexToRgb(bg));
    gl.uniform3fv(U.line, hexToRgb(line));
    gl.uniform3fv(U.hot, hexToRgb(hot));
  };

  const draw = (now) => {
    const t = (now - t0) / 1000;
    gl.uniform2f(U.res, w, h);
    gl.uniform1f(U.time, t);
    gl.uniform1f(U.scale, want.scale);
    gl.uniform1f(U.strength, want.strength);
    gl.uniform1f(U.density, want.density);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };

  const loop = (now) => {
    if (!running) return;
    draw(now);
    raf = requestAnimationFrame(loop);
  };

  const start = () => {
    if (running || reduced || !visible) return;
    running = true;
    raf = requestAnimationFrame(loop);
  };
  const stop = () => {
    running = false;
    cancelAnimationFrame(raf);
  };

  const refresh = () => {
    resize();
    paintColors();
    draw(performance.now());
  };

  refresh();
  if (reduced) return { refresh, start, stop, gl };

  // pause off-screen
  if ('IntersectionObserver' in window) {
    new IntersectionObserver((es) => {
      visible = es[0].isIntersecting;
      visible ? start() : stop();
    }, { threshold: 0.01 }).observe(canvas);
  }
  // pause on hidden tab
  document.addEventListener('visibilitychange', () => {
    document.hidden ? stop() : (visible && start());
  });
  // react to resize (debounced)
  let rt = 0;
  const ro = new ResizeObserver(() => {
    clearTimeout(rt);
    rt = setTimeout(refresh, 120);
  });
  ro.observe(canvas);

  start();
  return { refresh, start, stop, gl };
}

window.hmContour = mountContour;
