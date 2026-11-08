/* ============================================================
   PLAN panel — the decision view, with receipts.

   Every row can be expanded to show WHY: the draw cutoff, the
   applicants and successful draws at your exact point level, the
   harvest evidence for the code, the unit's multi-year record,
   and the public-land share. No number on screen is unexplained.

   Ranking metric: expected = P(draw | my points) x P(harvest | drew),
   where success uses the shrunk lower bound so a 4-hunter code
   cannot outrank a 300-hunter code on one lucky year.
   ============================================================ */

const PL_SEASON = { 1: '1st season', 2: '2nd season', 3: '3rd season', 4: '4th season', 5: 'late season', 6: 'late season' };
const PL_SEX = { bull: 'bull', cow: 'cow', either: 'either-sex' };

function hmPlanPanel() {
  const el = document.createElement('div');
  el.className = 'pl-wrap';
  el.innerHTML = `
    <div class="pl-head">
      <div class="pt-seg pl-wpn" id="plWeapon">
        <button data-v="archery">Archery</button>
        <button data-v="muzzleloader">Muzzle</button>
        <button data-v="rifle">Rifle</button>
      </div>
      <div class="pl-sum" id="plSum">Loading draw odds…</div>
      <div class="pl-filters">
        <div class="pt-seg" id="plSex">
          <button data-v="bull">Bull</button>
          <button data-v="cow">Cow</button>
          <button data-v="either">Either</button>
        </div>
        <label class="pl-chk"><input type="checkbox" id="plPlo"/> private</label>
        <label class="pl-chk"><input type="checkbox" id="plOtc"/> OTC</label>
      </div>
    </div>
    <div class="pl-list" id="plList"></div>
  `;
  const $ = s => el.querySelector(s);
  let DATA = null;
  // Archery first: that is the household's weapon, and CO archery is mostly
  // over-the-counter, so OTC codes must not be filtered out by default.
  const me = { points: 0, residency: 'res', weapon: 'archery' };
  // Most archery tags are either-sex (74 of 88 in the recap); defaulting the sex
  // filter to bull would hide nearly every archery opportunity.
  const WEAPON_SEX = { archery: 'either', muzzleloader: 'bull', rifle: 'bull' };
  const oddsCache = {};

  const odds = c => (me.residency === 'nr' ? c.odds_nr : c.odds_res);
  const oddsAt = c => (odds(c)[Math.min(me.points, 6)] || 0);
  const need = c => (me.residency === 'nr' ? c.need_nr : c.need_res);

  /* ---------- evidence helpers ---------- */
  function unitHistory(unit) {
    const h = window.HARVEST_HISTORY && window.HARVEST_HISTORY[unit];
    if (!h) return null;
    const years = Object.keys(h).map(Number).sort();
    const pts = years.map(y => [y, h[y].hunters, h[y].total, h[y].success]).filter(r => r[1] > 0);
    if (!pts.length) return null;
    const rates = pts.map(r => r[2] / r[1]);
    const avg = rates.reduce((a, b) => a + b, 0) / rates.length;
    return { first: pts[0][0], last: pts[pts.length - 1][0], n: pts.length, avg, min: Math.min(...rates), max: Math.max(...rates), pts };
  }

  async function drawEvidence(code) {
    if (oddsCache[code] !== undefined) return oddsCache[code];
    try {
      const r = await fetch('/api/drawodds?code=' + encodeURIComponent(code));
      oddsCache[code] = r.ok ? await r.json() : null;
    } catch (e) { oddsCache[code] = null; }
    return oddsCache[code];
  }

  function pct(x) { return Math.round((x || 0) * 100); }

  async function whyHTML(c) {
    const d = await drawEvidence(c.code);
    const hist = unitHistory(c.unit);
    const isNr = me.residency === 'nr';
    const lvl = Math.min(me.points, 6);
    const rows = d ? d.rows : [];
    const mine = rows.find(r => r[0] === lvl);
    const lvlTxt = me.points === 1 ? '1 point' : me.points + ' points';
    const cutoffRes = d ? String(d.cutoff || '').split(/\s{2,}|(?=\d Pref|No Apps|Leftover)/)[0] : '';

    const cut = isNr ? c.cut_nr : c.cut_res;
    const resLbl = isNr ? 'non-resident' : 'resident';
    let drawLine;
    if (cut === null || cut === undefined) {
      drawLine = mine
        ? `<b>${isNr ? mine[3] : mine[1]}</b> ${resLbl}s applied with ${lvlTxt}, <b>${(isNr ? mine[4] : mine[2]) || 0}</b> drew → <b>${pct(oddsAt(c))}%</b>`
        : `No cut-off published for this code; no ${resLbl} applicants on record at ${lvlTxt}.`;
    } else if (me.points > cut) {
      drawLine = `Cut-off was <b>${cut} point${cut === 1 ? '' : 's'}</b> — your ${me.points} clear it, ` +
        `so the tag is <b>yours if you apply</b>.`;
    } else if (me.points === cut) {
      drawLine = `You are <b>on the cut-off</b> (${cut} point${cut === 1 ? '' : 's'}): ` +
        (mine ? `<b>${isNr ? mine[3] : mine[1]}</b> ${resLbl}s applied at that level, <b>${(isNr ? mine[4] : mine[2]) || 0}</b> drew → <b>${pct(oddsAt(c))}%</b>.`
               : `everyone at that level drew.`);
    } else {
      drawLine = `Cut-off was <b>${cut} points</b>. You have ${me.points} — ` +
        `<b>${cut - me.points} more point${cut - me.points === 1 ? '' : 's'}</b> (${cut - me.points} year${cut - me.points === 1 ? '' : 's'} of applying) gets you there.`;
    }

    const succPct = pct(c.success);
    const statePct = 19.9;
    const mult = (c.success / (statePct / 100)).toFixed(1);

    const histLine = hist
      ? `Unit-wide ${hist.first}–${hist.last}: <b>${pct(hist.avg)}%</b> averaged over ${hist.n} years ` +
        `(range ${pct(hist.min)}–${pct(hist.max)}%) — all seasons and weapons in this GMU`
      : 'no multi-year record for this unit';

    const trendLine = Math.abs(c.trend_pp) >= 0.25
      ? `Trend <b>${c.trend_pp > 0 ? '+' : ''}${c.trend_pp.toFixed(2)} points of success per year</b> ${c.trend_pp > 0 ? '(improving)' : '(declining)'}`
      : 'Trend flat within noise';

    return `<div class="pl-why">
      <div class="pl-why-row"><span class="pl-k">DRAW</span><span>${drawLine}</span></div>
      <div class="pl-why-row"><span class="pl-k">CUTOFF</span><span>${cutoffRes || 'not published for this code'}</span></div>
      <div class="pl-why-row"><span class="pl-k">THIS TAG</span><span><b>${succPct}%</b> in 2025 (${c.harvest} of ${c.hunters} hunters) — ` +
        `<b>${mult}×</b> the statewide ${statePct}%</span></div>
      <div class="pl-why-row"><span class="pl-k">HISTORY</span><span>${histLine}</span></div>
      <div class="pl-why-row"><span class="pl-k">ACCESS</span><span>${Math.round(c.public_pct)}% public land · quota ${c.quota ?? '—'} · ${c.cls_label.toLowerCase()}</span></div>
      <div class="pl-why-row"><span class="pl-k">TREND</span><span>${trendLine}</span></div>
      <div class="pl-why-foot">Expected if you draw: <b>${pct(c.success)}%</b> · expected from applying: ` +
        `<b>${pct(oddsAt(c) * c.success_lb)}%</b> (${pct(oddsAt(c))}% draw × ${pct(c.success_lb)}% success)</div>
    </div>`;
  }

  function setSex(v) {
    el.querySelectorAll('#plSex button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  }

  function render() {
    if (!DATA) return;
    const sex = el.querySelector('#plSex button.on')?.dataset.v || 'bull';
    const showPlo = $('#plPlo').checked;
    const showOtc = $('#plOtc').checked;

    const rows = DATA.codes.filter(c =>
      c.weapon === me.weapon && c.sex === sex &&
      (showPlo || c.cls !== 'plo') && (showOtc || !c.otc));
    rows.forEach(c => {
      c._score = oddsAt(c) * c.success_lb;                 // expected outcome
      // Access is a rank multiplier only: a 40%-success unit that is 2% public
      // is not a place you can hunt, so it must not lead the list. The number
      // shown in the row stays the honest expected probability.
      c._fit = c._score * Math.min(1, (c.public_pct || 0) / 40);
    });

    const now = rows.filter(c => oddsAt(c) >= 0.4).sort((a, b) => b._fit - a._fit);
    const soon = rows.filter(c => oddsAt(c) < 0.4 && need(c) <= me.points + 2 && need(c) < 12)
      .sort((a, b) => (need(a) - need(b)) || (b._fit - a._fit));
    const later = rows.filter(c => need(c) > me.points + 2 && need(c) < 12 && oddsAt(c) < 0.4)
      .sort((a, b) => (need(a) - need(b)) || (b.success - a.success));

    const best = now[0];
    $('#plSum').innerHTML =
      `<b>${me.points}</b> elk point${me.points === 1 ? '' : 's'} · ` +
      `${me.residency === 'nr' ? 'non-resident' : 'Colorado resident'} · <b>${me.weapon === 'muzzleloader' ? 'muzzleloader' : me.weapon}</b><br>` +
      `<span>${now.length} ${sex} codes you can draw this year` +
      (best ? `. Best fit: <b>unit ${best.unit}</b>, ${PL_SEASON[best.season]} — ` +
        `${Math.round(best.success * 100)}% success on ${best.hunters} hunters, ` +
        `${Math.round(best.public_pct)}% public, ${Math.round(best._score * 100)}% expected</span>` : '') +
      `<br><span class="pl-hint">Tap any row for the evidence behind it.</span>`;

    const html = [];
    if (now.length) html.push('<div class="pl-grp">Draw it now</div>' + now.slice(0, 12).map(r => rowHTML(r, 'now')).join(''));
    if (soon.length) html.push('<div class="pl-grp">Reachable with more points</div>' + soon.slice(0, 10).map(r => rowHTML(r, 'soon')).join(''));
    if (later.length) html.push('<div class="pl-grp">Long game</div>' + later.slice(0, 8).map(r => rowHTML(r, 'later')).join(''));
    if (!html.length) html.push('<div class="pl-empty">Nothing matches those filters. Try allowing private land or another weapon.</div>');
    $('#plList').innerHTML = html.join('');

    $('#plList').querySelectorAll('.pl-row').forEach(r => {
      r.addEventListener('click', async ev => {
        if (ev.target.closest('.pl-why')) return;
        const code = r.dataset.code;
        const isOpen = r.classList.contains('open');
        $('#plList').querySelectorAll('.pl-row.open').forEach(o => { o.classList.remove('open'); const w = o.querySelector('.pl-why'); if (w) w.remove(); });
        if (isOpen) return;
        r.classList.add('open');
        const holder = document.createElement('div');
        holder.innerHTML = '<div class="pl-why"><div class="pl-why-row"><span class="pl-k">…</span><span>reading the draw recap</span></div></div>';
        r.appendChild(holder.firstChild);
        const c = DATA.codes.find(x => x.code === code);
        const why = await whyHTML(c);
        const old = r.querySelector('.pl-why');
        if (old) old.outerHTML = why;
      });
    });
  }

  function rowHTML(c, group) {
    const od = oddsAt(c), nd = need(c), yrs = Math.max(0, nd - me.points);
    const tr = c.trend_pp;
    const arrow = tr > 0.25 ? '<span class="pl-up" title="success trending up">▲</span>'
      : tr < -0.25 ? '<span class="pl-dn" title="success trending down">▼</span>' : '';
    const when = group === 'now' ? `<b>${Math.round(od * 100)}%</b><span>draw now</span>`
      : yrs > 0 ? `<b>${yrs}y</b><span>+${yrs} pt${yrs === 1 ? '' : 's'}</span>`
        : `<b>${Math.round(od * 100)}%</b><span>draw odds</span>`;
    return `<div class="pl-row" data-code="${c.code}" data-unit="${c.unit}">
      <div class="pl-u">${c.unit}</div>
      <div class="pl-mid">
        <div class="pl-t">${PL_SEASON[c.season] || 's' + c.season} ${c.weapon} · ${PL_SEX[c.sex] || c.sex}${c.cls === 'plo' ? ' <span class="pl-tag">private</span>' : ''}${c.otc ? ' <span class="pl-tag">otc</span>' : ''}</div>
        <div class="pl-sub">${c.code} · quota ${c.quota ?? '—'} · ${Math.round(c.public_pct)}% public ${arrow}</div>
      </div>
      <div class="pl-su"><b>${Math.round(c.success * 100)}%</b><span>success</span></div>
      <div class="pl-od">${when}</div>
    </div>`;
  }

  async function load() {
    try {
      const [plan, pts] = await Promise.all([
        fetch('/data/plan.json?v=' + Date.now()).then(r => r.ok ? r.json() : null),
        fetch('/api/points').then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      DATA = plan;
      if (pts) {
        me.points = (pts.balances && pts.balances.elk) || 0;
        me.residency = pts.profile?.residency || 'res';
      }
      me.weapon = localStorage.getItem('hm-plan-weapon') || 'archery';
      $('#plWeapon').querySelectorAll('button').forEach(b =>
        b.classList.toggle('on', b.dataset.v === me.weapon));
      $('#plOtc').checked = me.weapon === 'archery';
      setSex(WEAPON_SEX[me.weapon] || 'bull');
      render();
    } catch (e) {
      $('#plSum').textContent = 'Could not load draw odds.';
    }
  }

  el.querySelectorAll('#plWeapon button').forEach(b => b.addEventListener('click', () => {
    el.querySelectorAll('#plWeapon button').forEach(x => x.classList.toggle('on', x === b));
    me.weapon = b.dataset.v;
    localStorage.setItem('hm-plan-weapon', me.weapon);
    $('#plOtc').checked = me.weapon === 'archery';   // OTC is the archery norm
    setSex(WEAPON_SEX[me.weapon] || 'bull');
    // keep the profile in step so the Setup card and the Plan agree
    fetch('/api/profile/prefs', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ weapon: me.weapon, residency: me.residency }),
    }).catch(() => {});
    render();
  }));
  el.querySelectorAll('#plSex button').forEach(b => b.addEventListener('click', () => {
    el.querySelectorAll('#plSex button').forEach(x => x.classList.toggle('on', x === b));
    render();
  }));
  $('#plPlo').addEventListener('change', render);
  $('#plOtc').addEventListener('change', render);
  document.addEventListener('hm:points', () => load());
  load();
  return el;
}

window.hmPlanPanel = hmPlanPanel;
