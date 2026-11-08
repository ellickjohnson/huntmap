/* ============================================================
   GPX import — waypoints AND tracks from onX, Garmin, Gaia, CalTopo.

   onX does not use <sym>. It writes
       <extensions><onx:icon>Camp</onx:icon><onx:color>rgba(...)</onx:color></extensions>
   so the icon has to be read by localName across the namespace, with
   <sym>/<type> kept as fallbacks for other apps and for our own export
   (which writes <type> = marker kind, making a round-trip lossless).

   Tracks are imported as polylines and simplified (Douglas-Peucker,
   ~9 m) before they are stored — a 1,500-point walk does not need
   1,500 vertices to look right on a phone.
   ============================================================ */

(function () {
  const OWN_KINDS = new Set(['camp', 'sighted', 'harvested', 'parked', 'waypoint', 'glassing', 'water', 'trailhead']);
  const KIND_LABEL = {
    camp: 'Camp', sighted: 'Sighted', harvested: 'Harvested', parked: 'Parked',
    waypoint: 'Waypoint', glassing: 'Glassing', water: 'Water', trailhead: 'Trailhead',
  };

  // onX icon names -> our kinds
  const ICON_KIND = {
    camp: 'camp', campground: 'camp', tent: 'camp', cabin: 'camp', shelter: 'camp',
    elk: 'sighted', deer: 'sighted', wildlife: 'sighted', animal: 'sighted', game: 'sighted',
    location: 'waypoint', pin: 'waypoint', marker: 'waypoint', flag: 'waypoint', stand: 'waypoint', blind: 'waypoint',
    water: 'water', spring: 'water', creek: 'water', tank: 'water', wallow: 'water', pond: 'water',
    parking: 'parked', vehicle: 'parked', truck: 'parked', gate: 'parked', road: 'parked',
    trail: 'trailhead', trailhead: 'trailhead', hiking: 'trailhead',
    glassing: 'glassing', binoculars: 'glassing', binos: 'glassing', observation: 'glassing', viewpoint: 'glassing', lookout: 'glassing',
    kill: 'harvested', harvest: 'harvested', harvested: 'harvested', blood: 'harvested', killsite: 'harvested',
  };

  const RULES = [
    [/\b(harvest(ed)?|kill(ed)?|down(ed)?|blood|recover(ed|y)?|gut(ting)?)\b/i, 'harvested'],
    [/\b(glass(ing)?|lookout|vantage|view ?point|scenic)\b/i, 'glassing'],
    [/\b(water|spring|creek|tank|pond|drink(ing)?|wallow|seep)\b/i, 'water'],
    [/\b(camp(ground)?|tent|shelter|cabin|spike)\b/i, 'camp'],
    [/\b(trail ?head|trailhead|hike|hiking)\b/i, 'trailhead'],
    [/\b(park(ing)?|vehicle|truck|pull ?out|gate|trail ?lot|staging)\b/i, 'parked'],
    [/\b(sight(ing|ed)?|seen|elk|deer|animal|game|herd|bull|cow)\b/i, 'sighted'],
    [/\b(blind|tree ?stand|stand|ambush|scrape|bed(ding)?)\b/i, 'waypoint'],
  ];

  /* ---------- small helpers ---------- */

  function localText(el, local) {
    if (!el) return '';
    const kids = el.getElementsByTagName('*');
    for (let i = 0; i < kids.length; i++) {
      const n = kids[i];
      if ((n.localName || n.nodeName) === local) return (n.textContent || '').trim();
    }
    return '';
  }

  function toHex(c) {
    if (!c) return '';
    const m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i.exec(c);
    if (m) return '#' + [m[1], m[2], m[3]].map(v => (+v).toString(16).padStart(2, '0')).join('').toUpperCase();
    if (/^#[0-9a-f]{6}$/i.test(c)) return c.toUpperCase();
    if (/^#[0-9a-f]{3}$/i.test(c)) return ('#' + c[1] + c[1] + c[2] + c[2] + c[3] + c[3]).toUpperCase();
    return '';
  }

  function mapKind(w) {
    const type = (w.type || '').trim().toLowerCase();
    if (OWN_KINDS.has(type)) return type;                    // our own export round-trips
    const icon = (w.icon || '').trim().toLowerCase();
    if (icon) {
      const key = icon.replace(/[^a-z]/g, '');
      if (ICON_KIND[key]) return ICON_KIND[key];
    }
    const probe = s => {
      for (const [re, kind] of RULES) if (s && re.test(s)) return kind;
      return null;
    };
    return probe(w.name) || probe(w.desc) || probe(w.sym) || 'waypoint';
  }

  /* ---------- geometry ---------- */

  function segLen(a, b) {
    const R = 6371000, toRad = Math.PI / 180;
    const dLat = (b[1] - a[1]) * toRad, dLon = (b[0] - a[0]) * toRad;
    const la1 = a[1] * toRad, la2 = b[1] * toRad;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function pathLen(pts) {
    let d = 0;
    for (let i = 1; i < pts.length; i++) d += segLen(pts[i - 1], pts[i]);
    return d;
  }

  // Douglas-Peucker in degrees (approx): 0.00008 deg ~ 9 m of latitude
  function simplify(pts, eps) {
    if (pts.length < 3) return pts.slice();
    const sq = eps * eps;
    const sqSegDist = (p, a, b) => {
      let x = a[0], y = a[1], dx = b[0] - x, dy = b[1] - y;
      if (dx !== 0 || dy !== 0) {
        const t = ((p[0] - x) * dx + (p[1] - y) * dy) / (dx * dx + dy * dy);
        if (t > 1) { x = b[0]; y = b[1]; } else if (t > 0) { x += dx * t; y += dy * t; }
      }
      dx = p[0] - x; dy = p[1] - y;
      return dx * dx + dy * dy;
    };
    const step = (first, last, out) => {
      let maxd = sq;
      let idx = -1;
      for (let i = first + 1; i < last; i++) {
        const d = sqSegDist(pts[i], pts[first], pts[last]);
        if (d > maxd) { idx = i; maxd = d; }
      }
      if (idx > 0) {
        if (idx - first > 1) step(first, idx, out);
        out.push(pts[idx]);
        if (last - idx > 1) step(idx, last, out);
      }
    };
    const out = [pts[0]];
    step(0, pts.length - 1, out);
    out.push(pts[pts.length - 1]);
    return out;
  }

  /* ---------- parse ---------- */

  function parse(text) {
    const doc = new DOMParser().parseFromString(text, 'text/xml');
    if (doc.getElementsByTagName('parsererror').length) throw new Error('That file is not valid GPX (XML parse error).');

    const wpts = Array.from(doc.getElementsByTagName('wpt'));
    const trks = Array.from(doc.getElementsByTagName('trk'));
    if (!wpts.length && !trks.length) throw new Error('No waypoints or tracks found in that GPX file.');

    const waypoints = [];
    for (const el of wpts) {
      const lat = parseFloat(el.getAttribute('lat'));
      const lon = parseFloat(el.getAttribute('lon'));
      if (!isFinite(lat) || !isFinite(lon)) continue;
      const w = {
        lat, lon,
        name: localText(el, 'name'),
        desc: [localText(el, 'desc'), localText(el, 'cmt')].filter(Boolean).join(' — '),
        sym: localText(el, 'sym'),
        type: localText(el, 'type'),
        icon: localText(el, 'icon'),          // onX
        color: toHex(localText(el, 'color')),
        time: localText(el, 'time'),
      };
      w.kind = mapKind(w);
      waypoints.push(w);
    }

    const tracks = [];
    let rawPts = 0;
    for (const tr of trks) {
      const name = localText(tr, 'name') || 'Track';
      const color = toHex(localText(tr, 'color')) || '#FF6B1A';
      const time = localText(tr, 'time');
      const coords = [];
      for (const p of Array.from(tr.getElementsByTagName('trkpt'))) {
        const lat = parseFloat(p.getAttribute('lat'));
        const lon = parseFloat(p.getAttribute('lon'));
        if (isFinite(lat) && isFinite(lon)) coords.push([lon, lat]);
      }
      if (coords.length < 2) continue;
      rawPts += coords.length;
      const dist = pathLen(coords);
      const simple = simplify(coords, 0.00008);
      const rec = {
        name, color,
        geojson: { type: 'LineString', coordinates: simple },
        points: coords.length,
        kept: simple.length,
        distance_m: Math.round(dist),
        created_at: null,
      };
      const t = time ? Date.parse(time) : NaN;
      if (isFinite(t)) rec.created_at = Math.round(t / 1000);
      tracks.push(rec);
    }

    return {
      waypoints, tracks, rawPts,
      routes: doc.getElementsByTagName('rte').length,
    };
  }

  function toPayload(w) {
    const rec = {
      kind: w.kind,
      name: (w.name || (KIND_LABEL[w.kind] + ' (imported)')).slice(0, 120),
      notes: w.desc ? w.desc.slice(0, 2000) : '',
      lat: w.lat, lon: w.lon,
    };
    const t = w.time ? Date.parse(w.time) : NaN;
    if (isFinite(t)) rec.created_at = Math.round(t / 1000);
    return rec;
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  const miles = m => (m / 1609.34).toFixed(1);

  /* ---------- UI ---------- */

  function mount() {
    const btn = document.getElementById('gpxImportBtn');
    const input = document.getElementById('gpxFile');
    const box = document.getElementById('gpxPreview');
    if (!btn || !input || !box) return;

    btn.addEventListener('click', () => input.click());

    input.addEventListener('change', async () => {
      const file = input.files && input.files[0];
      input.value = '';
      if (!file) return;
      box.innerHTML = '<div class="gpx-note">Reading ' + esc(file.name) + '…</div>';
      let data;
      try {
        data = parse(await file.text());
      } catch (e) {
        box.innerHTML = '<div class="gpx-note gpx-bad">' + esc(e.message) + '</div>';
        return;
      }
      renderPreview(box, file.name, data);
    });
  }

  function renderPreview(box, filename, data) {
    const counts = {};
    for (const w of data.waypoints) counts[w.kind] = (counts[w.kind] || 0) + 1;
    const chips = Object.entries(counts).sort((a, b) => b[1] - a[1])
      .map(([k, n]) => `<span class="gpx-chip"><b>${n}</b> ${esc(KIND_LABEL[k] || k)}</span>`).join('');

    const totalDist = data.tracks.reduce((s, t) => s + t.distance_m, 0);
    const keptPts = data.tracks.reduce((s, t) => s + t.kept, 0);

    box.innerHTML = `
      <div class="gpx-card">
        <div class="gpx-head"><b>${esc(filename)}</b></div>
        <div class="gpx-sub">${data.waypoints.length} waypoint${data.waypoints.length === 1 ? '' : 's'}${
          data.tracks.length ? ` · ${data.tracks.length} track${data.tracks.length === 1 ? '' : 's'}` : ''}</div>
        ${chips ? `<div class="gpx-chips">${chips}</div>` : ''}
        ${data.tracks.length ? `<div class="gpx-note"><b>${miles(totalDist)} mi</b> of track, ` +
          `${data.rawPts.toLocaleString()} points simplified to ${keptPts.toLocaleString()} for the map.</div>` : ''}
        <div class="gpx-actions">
          <button class="btn" id="gpxCancel">Cancel</button>
          <button class="btn btn-primary" id="gpxDo">Import ${data.waypoints.length}${data.tracks.length ? ' + ' + data.tracks.length + ' tracks' : ''}</button>
        </div>
        <div class="gpx-note" id="gpxResult"></div>
      </div>`;

    box.querySelector('#gpxCancel').addEventListener('click', () => { box.innerHTML = ''; });
    box.querySelector('#gpxDo').addEventListener('click', async () => {
      const doBtn = box.querySelector('#gpxDo');
      doBtn.disabled = true;
      doBtn.textContent = 'Importing…';
      try {
        const r = await fetch('/api/markers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'import',
            markers: data.waypoints.map(toPayload),
            tracks: data.tracks.map(t => ({
              name: t.name, color: t.color, geojson: t.geojson,
              points: t.points, distance_m: t.distance_m, created_at: t.created_at,
            })),
          }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        const bits = [`<b>${d.inserted}</b> waypoint${d.inserted === 1 ? '' : 's'} added`];
        if (d.skipped) bits.push(`${d.skipped} already on the map`);
        if (d.tracks_inserted) bits.push(`<b>${d.tracks_inserted}</b> track${d.tracks_inserted === 1 ? '' : 's'} added`);
        if (d.tracks_skipped) bits.push(`${d.tracks_skipped} track${d.tracks_skipped === 1 ? '' : 's'} already there`);
        if (d.invalid || d.tracks_invalid) bits.push(`${(d.invalid || 0) + (d.tracks_invalid || 0)} rejected`);
        box.querySelector('#gpxResult').innerHTML = bits.join(', ') + '.';
        doBtn.textContent = 'Done';
        if (typeof window.hmReloadMarkers === 'function') window.hmReloadMarkers();
        if (typeof window.hmReloadTracks === 'function') window.hmReloadTracks();
        document.dispatchEvent(new CustomEvent('hm:markers'));
      } catch (e) {
        box.querySelector('#gpxResult').innerHTML = '<span class="gpx-bad">Import failed: ' + esc(e.message) + '</span>';
        doBtn.disabled = false;
        doBtn.textContent = 'Retry';
      }
    });
  }

  window.hmGPXImport = { parse, mapKind, mount, toPayload, simplify, pathLen };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
