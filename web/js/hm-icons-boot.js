/* ============================================================
   HuntMap icon set — hand-built 24px stroke icons.
   No emoji in chrome. <svg><use href="#i-name"/></svg>
   ============================================================ */

const ICONS = {
  /* navigation */
  map:        '<path d="M9 3 3.6 5.1A1 1 0 0 0 3 6v13a1 1 0 0 0 1.4.9L9 18l6 3 5.4-2.1A1 1 0 0 0 21 18V5a1 1 0 0 0-1.4-.9L15 6 9 3z"/><path d="M9 3v15"/><path d="M15 6v15"/>',
  layers:     '<path d="M12.8 2.2a1.8 1.8 0 0 0-1.6 0L2.6 6.1a1 1 0 0 0 0 1.8l8.6 3.9a1.8 1.8 0 0 0 1.6 0l8.6-3.9a1 1 0 0 0 0-1.8z"/><path d="M2.6 12.1 11.2 16a1.8 1.8 0 0 0 1.6 0l8.6-3.9"/><path d="M2.6 16.9 11.2 21a1.8 1.8 0 0 0 1.6 0l8.6-4.1"/>',
  search:     '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  pin:        '<path d="M20 10c0 4.9-5.7 10.3-7.4 11.8a1 1 0 0 1-1.3 0C9.7 20.3 4 15 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.6"/>',
  ai:         '<path d="M12 3.2l1.8 4.9a2 2 0 0 0 1.2 1.2l4.9 1.8-4.9 1.8a2 2 0 0 0-1.2 1.2L12 19l-1.8-4.9a2 2 0 0 0-1.2-1.2L4.1 11l4.9-1.8a2 2 0 0 0 1.2-1.2z"/><path d="M19 15.2l.6 1.6 1.6.6-1.6.6-.6 1.6-.6-1.6-1.6-.6 1.6-.6z"/>',
  user:       '<circle cx="12" cy="8" r="3.8"/><path d="M5 21a7 7 0 0 1 14 0"/>',
  shield:     '<path d="M12 2.5 4.5 5.6v5.1c0 4.8 3.3 9.2 7.5 10.5 4.2-1.3 7.5-5.7 7.5-10.5V5.6z"/><circle cx="12" cy="10.8" r="2.4"/><path d="M12 13.2V16"/>',
  logout:     '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  login:      '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
  settings:   '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-2.9-1.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 3 15a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.3-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 10 4.1V4a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 2.9 1.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1A1.7 1.7 0 0 0 21 11a2 2 0 1 1 0 4z"/>',

  /* map layers */
  terrain:    '<path d="M2.5 20.5 9 6l4.6 9.5"/><path d="M8 20.5 14.5 4l7 16.5z"/>',
  slope:      '<path d="M3 20h18L12 4z"/><path d="M9.5 15.5h4"/><path d="M12 4v3"/>',
  ruler:      '<path d="M15.5 3.5 20.5 8.5 8.5 20.5 3.5 15.5z"/><path d="m7 12 2 2"/><path d="m10 9 2 2"/><path d="m13 6 2 2"/>',
  parcels:    '<rect x="3" y="3" width="7.5" height="7.5" rx="1"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1"/>',
  trail:      '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19h5a3.5 3.5 0 0 0 0-7h-3a3.5 3.5 0 0 1 0-7h5"/>',
  burn:       '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
  hotspot:    '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.6"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  land:       '<path d="M12 2.5 7.5 9.5H10l-3.5 6H11v6h2v-6h4.5l-3.5-6h2.5z"/>',
  contour:    '<path d="M2 7c2.2 0 2.2 2 4.4 2S8.6 7 10.8 7s2.2 2 4.4 2 2.2-2 4.4-2 2.2 2 4.4 2"/><path d="M2 13c2.2 0 2.2 2 4.4 2s2.2-2 4.4-2 2.2 2 4.4 2 2.2-2 4.4-2 2.2 2 4.4 2"/><path d="M2 19c2.2 0 2.2 2 4.4 2s2.2-2 4.4-2 2.2 2 4.4 2 2.2-2 4.4-2 2.2 2 4.4 2"/>',

  /* marker kinds */
  tent:       '<path d="M3 20.5 12 4l9 16.5H3z"/><path d="M12 4v7"/><path d="m8.8 20.5 3.2-9 3.2 9"/>',
  eye:        '<path d="M2 12s3.6-6.8 10-6.8S22 12 22 12s-3.6 6.8-10 6.8S2 12 2 12z"/><circle cx="12" cy="12" r="2.9"/>',
  crosshair:  '<circle cx="12" cy="12" r="8.5"/><path d="M12 1.5v5"/><path d="M12 17.5v5"/><path d="M1.5 12h5"/><path d="M17.5 12h5"/><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
  car:        '<path d="M5 17H3.8a.9.9 0 0 1-.9-.9v-3.3c0-.9.7-1.7 1.5-1.9 1.8-.5 4.6-1.1 4.6-1.1s1.3-1.4 2.2-2.3c.5-.4 1.1-.7 1.8-.7H15c.6 0 1.1.4 1.4.9l1.4 2.9c.2.4.2.8.2 1.2v4.2a.9.9 0 0 1-.9.9H19"/><circle cx="7.2" cy="17.4" r="1.9"/><path d="M9.1 17.4h5.8"/><circle cx="16.8" cy="17.4" r="1.9"/><path d="M5 10.5h14"/>',
  flag:       '<path d="M4 15.5s1-1 4-1 5 2 8 2 4-1 4-1v-11s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-6.5"/>',
  binoculars: '<circle cx="6.6" cy="15.4" r="3.6"/><circle cx="17.4" cy="15.4" r="3.6"/><path d="M10.2 15.4h3.6"/><path d="M6.6 11.8 8 4.4h2l.8 3.4"/><path d="M17.4 11.8 16 4.4h-2l-.8 3.4"/>',
  droplet:    '<path d="M12 2.7s6 6.4 6 10.4a6 6 0 1 1-12 0c0-4 6-10.4 6-10.4z"/>',
  signpost:   '<path d="M5 4h11l3.5 3.5L16 11H5z"/><path d="M12 11v11"/><path d="M8.5 22h7"/>',

  /* ui atoms */
  plus:       '<path d="M12 5v14"/><path d="M5 12h14"/>',
  download:   '<path d="M12 3.5v11.5"/><path d="m7.5 11 4.5 4.5 4.5-4.5"/><path d="M4.5 20.5h15"/>',
  upload:     '<path d="M12 20.5V9"/><path d="m7.5 13 4.5-4.5 4.5 4.5"/><path d="M4.5 3.5h15"/>',
  check:      '<path d="M20 6.5 9.2 17.3 4 12.1"/>',
  x:          '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  chevronDown:'<path d="m6 9 6 6 6-6"/>',
  chevronLeft:'<path d="m15 18-6-6 6-6"/>',
  chevronRight:'<path d="m9 18 6-6-6-6"/>',
  undo:       '<path d="M3 8h11a5.5 5.5 0 0 1 0 11H8"/><path d="m7 4-4 4 4 4"/>',
  info:       '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="7.8" r=".9" fill="currentColor" stroke="none"/>',
  alert:      '<path d="M10.3 3.9 1.9 18a2 2 0 0 0 1.7 3h16.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4.5"/><circle cx="12" cy="17" r=".9" fill="currentColor" stroke="none"/>',
  ruler2:     '<path d="M3 17 17 3l3 3L6 20z"/><path d="m7.5 12.5 2 2"/><path d="m10.5 9.5 2 2"/><path d="m13.5 6.5 2 2"/>',
  compass:    '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
};

/** Icon markup for template strings. */
function hmIcon(name, cls = '') {
  const id = ICONS[name] ? name : 'info';
  return `<svg class="i ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#i-${id}"/></svg>`;
}

/** Inject the sprite once. Safe to call repeatedly. */
function installSprite() {
  if (document.getElementById('hm-icons')) return;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.id = 'hm-icons';
  svg.setAttribute('aria-hidden', 'true');
  svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
  svg.innerHTML = Object.entries(ICONS).map(([k, v]) =>
    `<symbol id="i-${k}" viewBox="0 0 24 24">${v}</symbol>`).join('');
  const host = document.body || document.documentElement;
  host.insertBefore(svg, host.firstChild);
}

/** Marker kind -> icon name (map + lists). */
const KIND_ICON = {
  camp: 'tent', sighted: 'eye', harvested: 'crosshair', parked: 'car',
  waypoint: 'flag', glassing: 'binoculars', water: 'droplet', trailhead: 'signpost',
};

window.HM_ICONS = ICONS;
window.hmIcon = hmIcon;
window.HM_KIND_ICON = KIND_ICON;
window.hmInstallIcons = installSprite;

// Install immediately: this file is a blocking classic script in <head>, so the
// sprite symbols exist before any body markup that <use>s them is parsed.
(function boot(){
  if (document.body) installSprite();
  else document.addEventListener('DOMContentLoaded', installSprite, { once: true });
  // head-only execution: symbols must exist before first paint of <use>
  installSprite(true);
})();
