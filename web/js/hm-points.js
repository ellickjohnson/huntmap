/* ============================================================
   Draw points — profile card.

   The event log is the source of truth; the balance is the sum.
   Colorado rules as implemented:
     applied  +1   (you applied, preference point gained, no draw)
     drew      -> balance goes to 0   (limited tag drawn)
     bought   +1   (non-resident point purchase)
     adjust    -> set to a known balance
   ============================================================ */

const PT_KINDS = [
  ['applied', 'Applied, no draw'],
  ['drew', 'Drew a tag'],
  ['purchased', 'Bought a point'],
  ['adjust', 'Set balance'],
];

function hmPointsCard() {
  const el = document.createElement('div');
  el.className = 'pt-card';
  el.innerHTML = `
    <div class="pt-head">
      <span class="pt-title">Draw points · Elk</span>
      <span class="pt-bal"><b id="ptBal">0</b><span id="ptBalLbl">elk</span></span>
    </div>
    <div class="pt-seg" id="ptRes">
      <button data-v="res">Colorado res</button>
      <button data-v="nr">Non-resident</button>
    </div>
    <div class="pt-seg" id="ptWeap">
      <button data-v="rifle">Rifle</button>
      <button data-v="archery">Archery</button>
      <button data-v="muzzleloader">Muzzle</button>
    </div>
    <div class="pt-form">
      <select id="ptYear"></select>
      <select id="ptKind">${PT_KINDS.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select>
      <input id="ptPts" class="pt-wide" type="number" min="0" max="40" placeholder="Balance to set (only for Set balance)" style="display:none"/>
      <input id="ptNote" class="pt-wide" type="text" maxlength="120" placeholder="Note (unit 14 archery, etc.)"/>
      <button class="pt-add" id="ptAdd">Log it</button>
    </div>
    <div class="pt-list" id="ptList"><div class="pt-empty">No points logged yet.</div></div>
    <div class="pt-note">Applied and didn't draw adds <b>+1</b>. Drawing a limited tag zeroes the balance. Non-residents can buy a point without applying.</div>
  `;

  const $ = s => el.querySelector(s);
  const yearSel = $('#ptYear');
  const nowY = new Date().getFullYear();
  for (let y = nowY + 1; y >= nowY - 12; y--) {
    const o = document.createElement('option');
    o.value = y; o.textContent = y;
    yearSel.appendChild(o);
  }

  let state = { residency: 'res', weapon: 'rifle', species: 'elk', balances: {}, events: [] };

  const paint = () => {
    const bal = state.balances[state.species] || 0;
    $('#ptBal').textContent = bal;
    $('#ptBalLbl').textContent = state.species;
    el.querySelectorAll('#ptRes button').forEach(b => b.classList.toggle('on', b.dataset.v === state.residency));
    el.querySelectorAll('#ptWeap button').forEach(b => b.classList.toggle('on', b.dataset.v === state.weapon));
    const list = $('#ptList');
    if (!state.events.length) {
      list.innerHTML = '<div class="pt-empty">No points logged yet.</div>';
      return;
    }
    list.innerHTML = state.events.map(e => {
      const label = (PT_KINDS.find(k => k[0] === e.kind) || [e.kind, e.kind])[1];
      const sign = e.points > 0 ? 'pos' : (e.points < 0 ? 'neg' : '');
      const dTxt = e.points > 0 ? `+${e.points}` : (e.points < 0 ? `${e.points}` : '0');
      return `<div class="pt-ev" data-id="${e.id}">
        <span class="yr">${e.year}</span>
        <span>${label}${e.note ? ` · <span class="pt-note">${e.note.replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</span>` : ''}</span>
        <span class="d ${sign}">${dTxt}</span>
        <button class="pt-del" title="Delete">×</button>
      </div>`;
    }).join('');
  };

  const load = async () => {
    try {
      const r = await fetch('/api/points');
      if (!r.ok) return;
      const d = await r.json();
      state.residency = d.profile?.residency || 'res';
      state.weapon = d.profile?.weapon || 'rifle';
      state.species = d.profile?.species || 'elk';
      state.balances = d.balances || {};
      state.events = d.events || [];
      paint();
      window.hmPoints = state;   // decision engine reads this
    } catch (e) { /* offline: leave defaults */ }
  };

  const savePrefs = async patch => {
    try {
      await fetch('/api/profile/prefs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
    } catch (e) {}
    load();
  };

  el.querySelectorAll('#ptRes button').forEach(b => b.addEventListener('click', () => {
    state.residency = b.dataset.v; paint(); savePrefs({ residency: b.dataset.v });
  }));
  el.querySelectorAll('#ptWeap button').forEach(b => b.addEventListener('click', () => {
    state.weapon = b.dataset.v; paint(); savePrefs({ weapon: b.dataset.v });
  }));

  $('#ptKind').addEventListener('change', e => {
    $('#ptPts').style.display = e.target.value === 'adjust' ? '' : 'none';
  });

  $('#ptAdd').addEventListener('click', async () => {
    const btn = $('#ptAdd');
    btn.disabled = true;
    const payload = {
      action: 'add',
      species: state.species,
      year: parseInt(yearSel.value, 10),
      kind: $('#ptKind').value,
      note: $('#ptNote').value.trim(),
    };
    if (payload.kind === 'adjust') payload.points = parseInt($('#ptPts').value || '0', 10);
    try {
      const r = await fetch('/api/points', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) { btn.textContent = d.error || 'Failed'; setTimeout(() => btn.textContent = 'Log it', 1800); return; }
      $('#ptNote').value = '';
      state.balances = d.balances || {}; state.events = d.events || [];
      paint();
      window.hmPoints = { ...state };
      document.dispatchEvent(new CustomEvent('hm:points'));
    } finally {
      btn.disabled = false;
    }
  });

  $('#ptList').addEventListener('click', async e => {
    const b = e.target.closest('.pt-del');
    if (!b) return;
    const row = b.closest('.pt-ev');
    const id = row.dataset.id;
    await fetch('/api/points/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: Number(id) }) });
    load();
  });

  load();
  return el;
}

window.hmPointsCard = hmPointsCard;
