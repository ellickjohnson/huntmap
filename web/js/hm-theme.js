/* ============================================================
   HuntMap theme system — single source of truth for every page.
   Loaded as a blocking classic script in <head> so the saved
   palette is applied before first paint (no flash).
   ============================================================ */
(function () {
  const THEMES = {
    'ridgeline': { name:'Ridgeline', mode:'dark', vars:{
      '--bg':'#0B0F0D','--bg2':'#0E1411','--panel':'#111714','--panel2':'#172019','--panel3':'#1D2820',
      '--line':'#24302A','--line2':'#33423A','--txt':'#E9EEEA','--txt2':'#9AA79F','--txt3':'#7F8D85',
      '--accent':'#FF6B1A','--accent-ink':'#170A02','--accent2':'#58C8A8',
      '--ok':'#5FBF8A','--warn':'#D9A03C','--danger':'#E0603A',
      '--heat-1':'#1B2E27','--heat-2':'#2C5E4C','--heat-3':'#5E8C57','--heat-4':'#A98A3E','--heat-5':'#B4462C' }},

    'spruce': { name:'Spruce', mode:'dark', vars:{
      '--bg':'#08110F','--bg2':'#0B1614','--panel':'#0E1A17','--panel2':'#132320','--panel3':'#18302B',
      '--line':'#1E322D','--line2':'#2B443E','--txt':'#E6F0EC','--txt2':'#93A9A2','--txt3':'#77908A',
      '--accent':'#EF8A3C','--accent-ink':'#150B02','--accent2':'#5FC9BE',
      '--ok':'#5FBF8A','--warn':'#D9A03C','--danger':'#E0603A',
      '--heat-1':'#152F2A','--heat-2':'#26655A','--heat-3':'#4E8F6E','--heat-4':'#9C9A4A','--heat-5':'#AC4E30' }},

    'quarry': { name:'Quarry', mode:'dark', vars:{
      '--bg':'#0D0C0A','--bg2':'#12100D','--panel':'#171410','--panel2':'#1E1A15','--panel3':'#26211A',
      '--line':'#2E2822','--line2':'#3E362C','--txt':'#EFE9E1','--txt2':'#A89E90','--txt3':'#8A8071',
      '--accent':'#E8913F','--accent-ink':'#170E03','--accent2':'#9FB06B',
      '--ok':'#6BA97C','--warn':'#D9A03C','--danger':'#D95F3B',
      '--heat-1':'#2A241B','--heat-2':'#5A4A2E','--heat-3':'#8A7440','--heat-4':'#B58A45','--heat-5':'#B4552F' }},

    'nightwatch': { name:'Nightwatch', mode:'dark', vars:{
      '--bg':'#090D13','--bg2':'#0C1219','--panel':'#101822','--panel2':'#16202C','--panel3':'#1C2836',
      '--line':'#22303F','--line2':'#2F4155','--txt':'#E8EEF6','--txt2':'#95A5B8','--txt3':'#7B8CA0',
      '--accent':'#FF7A3D','--accent-ink':'#170A03','--accent2':'#6FA8DC',
      '--ok':'#5FBF8A','--warn':'#D9A03C','--danger':'#E0603A',
      '--heat-1':'#17263A','--heat-2':'#2C5273','--heat-3':'#4E7F86','--heat-4':'#A8863F','--heat-5':'#B4552F' }},

    'quad': { name:'Quad sheet', mode:'light', vars:{
      '--bg':'#F2EFE6','--bg2':'#EAE6DA','--panel':'#FBF9F3','--panel2':'#F1EDE1','--panel3':'#E6E0D1',
      '--line':'#D6CEBC','--line2':'#BFB5A0','--txt':'#221D15','--txt2':'#5E5748','--txt3':'#756E5E',
      '--accent':'#C2410C','--accent-ink':'#FFF8F3','--accent2':'#2F6B5A',
      '--ok':'#2F7D4F','--warn':'#A66A10','--danger':'#B3261E',
      '--heat-1':'#C9D6CC','--heat-2':'#7FA98F','--heat-3':'#5E8C57','--heat-4':'#C08A2E','--heat-5':'#B4462C' }},

    'alpine': { name:'Alpine', mode:'light', vars:{
      '--bg':'#EEF1EE','--bg2':'#E6EAE6','--panel':'#FAFBF9','--panel2':'#EFF2EF','--panel3':'#E3E8E3',
      '--line':'#CBD3CB','--line2':'#AFBAB1','--txt':'#1B231D','--txt2':'#57625A','--txt3':'#6D786F',
      '--accent':'#B4501E','--accent-ink':'#FFF9F4','--accent2':'#2C6B72',
      '--ok':'#2F7D4F','--warn':'#A66A10','--danger':'#B3261E',
      '--heat-1':'#CBDAD4','--heat-2':'#7FA99C','--heat-3':'#55907A','--heat-4':'#BE8C36','--heat-5':'#B0482C' }},
  };

  window.HM_THEMES = THEMES;

  window.hmApplyTheme = function (id, remember) {
    const known = Object.prototype.hasOwnProperty.call(THEMES, id);
    const t = known ? THEMES[id] : THEMES['ridgeline'];
    const key = known ? id : 'ridgeline';
    const root = document.documentElement;
    root.classList.add('theming');
    for (const [k, v] of Object.entries(t.vars)) root.style.setProperty(k, v);
    root.style.colorScheme = t.mode === 'light' ? 'light' : 'dark';
    root.dataset.themeMode = t.mode;
    if (remember !== false) { try { localStorage.setItem('hm-theme', key); } catch (e) {} }
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', t.vars['--bg']);
    requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theming')));
    window.dispatchEvent(new CustomEvent('hm:theme', { detail: { id: key, mode: t.mode } }));
    return key;
  };

  let saved = null;
  try { saved = localStorage.getItem('hm-theme'); } catch (e) {}
  const valid = saved && Object.prototype.hasOwnProperty.call(THEMES, saved);
  window.hmApplyTheme(valid ? saved : 'ridgeline', !valid);
})();
