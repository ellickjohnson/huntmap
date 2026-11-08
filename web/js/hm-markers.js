/* ============================================================
   HuntMap map markers — filled badge sprites.

   Map symbols read at 24-44px on a busy basemap, where a 1.6px
   stroke glyph turns to mush. These are filled silhouettes on a
   squircle badge with a pointer tail, drawn at 2x and registered
   with map.addImage({pixelRatio: 2}).

   window.HM_MARKER_KINDS  kind -> {label, icon, color, glyph}
   window.hmMarkerSprite(kind, opts) -> {svg, url, size, anchor}
   ============================================================ */

/* Kind palette: distinguishable on light and dark basemaps, and never
   competing with the blaze accent (reserved for selection). */
const MARKER_KINDS = {
  camp:      { label: 'Camp',        icon: 'tent',    color: '#2F7A55' },
  sighted:   { label: 'Elk sighted', icon: 'binos',   color: '#B5761E' },
  harvested: { label: 'Harvested',   icon: 'elk',     color: '#FF6B1A' },
  glassing:  { label: 'Glassing',    icon: 'eye',     color: '#3E7C8C' },
  water:     { label: 'Water',       icon: 'droplet', color: '#2E6E9E' },
  trailhead: { label: 'Trailhead',   icon: 'hiker',   color: '#6B6357' },
  parked:    { label: 'Parked',      icon: 'car',     color: '#5A6470' },
  waypoint:  { label: 'Waypoint',    icon: 'flag',    color: '#8A5FA8' },
};

/* Filled silhouettes, drawn in a 24x24 box. `f` = fill, `s` = stroke. */
const GLYPHS = {
  tent: (f, s) =>
    `<path d="M12 2.9 2.6 21.1h18.8z" fill="${f}"/>` +
    `<path d="M12 8.4 7.6 21.1h8.8z" fill="${s}" opacity=".55"/>` +
    `<path d="M12 2.9v4.2" stroke="${s}" stroke-width="1.5" opacity=".75"/>`,

  /* elk head, front-on: vertical antler tines are what stop this reading as a bird */
  elk: (f, s) =>
    `<g stroke="${f}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none">` +
    /* beams rise from the crown, tines branch straight up */
    `<path d="M10.3 9.3C9.4 7.2 9 5.4 8.9 2.9"/><path d="M13.7 9.3c.9-2.1 1.3-3.9 1.4-6.4"/>` +
    `<path d="M9.7 7.5V4.4"/><path d="M9.1 5.3 7.7 3.4"/>` +
    `<path d="M14.3 7.5V4.4"/><path d="M14.9 5.3 16.3 3.4"/>` +
    /* ears out to the sides, angled down */
    `<path d="M9.5 11.1 6.6 12.4"/><path d="M14.5 11.1 17.4 12.4"/>` +
    `</g>` +
    /* long muzzle: narrow at the nose, so the head is not a circle */
    `<path d="M12 21.6c-1.6 0-2.8-1.15-2.8-2.85 0-1.15.55-2 .78-3.25.24-1.3 1.02-2.35 2.02-2.35s1.78 1.05 2.02 2.35c.23 1.25.78 2.1.78 3.25 0 1.7-1.2 2.85-2.8 2.85z" fill="${f}"/>` +
    `<circle cx="10.6" cy="15.6" r=".75" fill="${s}" opacity=".5"/><circle cx="13.4" cy="15.6" r=".75" fill="${s}" opacity=".5"/>`,

  binos: (f, s) =>
    `<rect x="1.7" y="11.9" width="7.4" height="9" rx="3.7" fill="${f}"/>` +
    `<rect x="14.9" y="11.9" width="7.4" height="9" rx="3.7" fill="${f}"/>` +
    `<path d="M8.4 14.6h7.2" stroke="${f}" stroke-width="2.6" stroke-linecap="round"/>` +
    `<path d="M5.4 11.9V5.2h3.1l1.1 4.6M18.6 11.9V5.2h-3.1l-1.1 4.6" stroke="${f}" stroke-width="1.7" stroke-linejoin="round" fill="none"/>`,

  eye: (f, s) =>
    `<path d="M12 4.9c5.2 0 9.4 4.7 9.4 7.1S17.2 19.1 12 19.1 2.6 14.4 2.6 12 6.8 4.9 12 4.9z" fill="${f}"/>` +
    `<circle cx="12" cy="12" r="3.1" fill="${s}" opacity=".8"/>` +
    `<circle cx="12" cy="12" r="1.15" fill="${f}"/>`,

  droplet: (f, s) =>
    `<path d="M12 2.6c3.4 4.2 6.1 7.6 6.1 10.9a6.1 6.1 0 1 1-12.2 0c0-3.3 2.7-6.7 6.1-10.9z" fill="${f}"/>` +
    `<path d="M9.3 14.2a2.8 2.8 0 0 0 2.7 2.8" stroke="${s}" stroke-width="1.4" fill="none" opacity=".55" stroke-linecap="round"/>`,

  /* hiker mid-stride, pack on the back, trekking pole in hand */
  hiker: (f, s) =>
    `<circle cx="9.4" cy="4.15" r="2.15" fill="${f}"/>` +
    `<rect x="11" y="8.1" width="2.9" height="3.6" rx="1.3" fill="${f}"/>` +
    `<g stroke="${f}" stroke-width="2.55" stroke-linecap="round" stroke-linejoin="round" fill="none">` +
    `<path d="M9.7 7.1v5.3"/>` +
    `<path d="M9.7 8.8 7 10.9"/><path d="M9.7 8.8 13.4 10.3"/>` +
    `<path d="M9.7 12.4 7.2 16.2 7.9 20.7"/>` +
    `<path d="M9.7 12.4 12.8 15.9 12.4 20.5"/>` +
    `</g>` +
    `<path d="M16.6 7.6 18 20.9" stroke="${f}" stroke-width="1.7" stroke-linecap="round"/>`,

  car: (f, s) =>
    `<path d="M4.1 16.2v-2.6c0-.7.5-1.3 1.2-1.5l1.4-.3 1.5-2.6c.4-.7 1.1-1.1 1.9-1.1h4.9c.8 0 1.5.4 1.9 1.1l1.6 2.8 1.2.3c.7.2 1.2.8 1.2 1.5v2.4c0 .6-.5 1.1-1.1 1.1H5.2c-.6 0-1.1-.5-1.1-1.1z" fill="${f}"/>` +
    `<circle cx="7.6" cy="17.6" r="1.9" fill="${f}"/><circle cx="16.4" cy="17.6" r="1.9" fill="${f}"/>` +
    `<path d="M6.4 11.9h11.2" stroke="${s}" stroke-width="1.2" opacity=".45"/>`,

  flag: (f, s) =>
    `<path d="M5.1 3.2c2.6-1.2 4.9-.4 7.2.4 2.3.8 4.5 1.6 6.6.5v9.4c-2.1 1.1-4.3.3-6.6-.5-2.3-.8-4.6-1.6-7.2-.4z" fill="${f}"/>` +
    `<path d="M5.1 3.2v18.2" stroke="${f}" stroke-width="2" stroke-linecap="round"/>`,
};

/* Badge geometry — squircle with a short pointer tail. */
function badgePath(w, h, r) {
  const cx = w / 2;
  const bodyBottom = h - 9;
  return `M${r},0 H${w - r} A${r},${r} 0 0 1 ${w},${r} V${bodyBottom - r} ` +
    `A${r},${r} 0 0 1 ${w - r},${bodyBottom} H${cx + 5.5} L${cx},${h} L${cx - 5.5},${bodyBottom} ` +
    `H${r} A${r},${r} 0 0 1 0,${bodyBottom - r} V${r} A${r},${r} 0 0 1 ${r},0 Z`;
}

/**
 * @param {string} kind  key of MARKER_KINDS
 * @param {{selected?:boolean, muted?:boolean}} opts
 */
function hmMarkerSprite(kind, opts = {}) {
  const def = MARKER_KINDS[kind] || MARKER_KINDS.waypoint;
  const W = 44, H = 56, R = 13;                 // logical px, drawn at 2x
  const color = opts.muted ? '#6F7A74' : def.color;
  const ink = '#FFFFFF';
  const glyph = (GLYPHS[def.icon] || GLYPHS.flag)(ink, color);
  const ring = opts.selected
    ? `<path d="${badgePath(W - 6, H - 6, R - 2)}" transform="translate(3,3)" fill="none" stroke="#FF6B1A" stroke-width="2.4"/>`
    : `<path d="${badgePath(W - 3, H - 3, R - 1)}" transform="translate(1.5,1.5)" fill="none" stroke="#FFFFFF" stroke-opacity=".22" stroke-width="1.4"/>`;
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W * 2}" height="${H * 2}" viewBox="0 0 ${W} ${H}">` +
    `<defs><filter id="sh" x="-30%" y="-20%" width="160%" height="160%">` +
    `<feDropShadow dx="0" dy="1.6" stdDeviation="1.7" flood-color="#000" flood-opacity=".45"/></filter></defs>` +
    `<g filter="url(#sh)">` +
    `<path d="${badgePath(W, H, R)}" fill="${color}"/>` +
    `<path d="${badgePath(W, H, R)}" fill="#fff" fill-opacity=".07"/>` +
    `</g>` +
    ring +
    // centre the 24-unit glyph in the badge BODY (0..H-9), not the whole shape,
    // or everything reads top-heavy because the pointer tail is empty
    `<g transform="translate(${(W - 26) / 2},${((H - 9) - 26) / 2 + 2.25}) scale(1.083)">${glyph}</g>` +
    `</svg>`;
  return {
    svg,
    url: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg),
    size: [W, H],
    anchor: 'bottom',
  };
}

window.HM_MARKER_KINDS = MARKER_KINDS;
window.hmMarkerSprite = hmMarkerSprite;
