(function(){
  function setupTabs(scope){
    const headers = document.querySelector('.tab-headers[data-tabs="'+scope+'"]');
    if(!headers) return;
    headers.addEventListener('click', function(e){
      if(e.target.tagName !== 'BUTTON') return;
      const tab = e.target.getAttribute('data-tab');
      headers.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
      e.target.classList.add('active');
      document.querySelectorAll('.tab-panel[data-panel^="'+scope+':"]').forEach(p=>{
        if(p.getAttribute('data-panel') === scope+':'+tab){ p.style.display='block'; }
        else { p.style.display='none'; }
      });
    });
  }
  setupTabs('llm');
  setupTabs('calc');
})();
// Async handlers for LLM generation and calculation
(function(){
  // Utilities and shared constants
  const SCOPES = { LLM: 'llm', CALC: 'calc' };
  const MEAL_KEYS = ['breakfast','first_snack','lunch','second_snack','dinner'];
  const panelIdFor = (scope, key) => `${scope}:${key}`;
  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));
  const setVisible = (el, visible) => { if (el) el.classList.toggle('visible', !!visible); };
  const setDisabled = (el, disabled) => { if (el) el.toggleAttribute('disabled', !!disabled); };
  const isButton = (el) => el && el.tagName === 'BUTTON';
  const clearTbody = (tbody) => { if (tbody) tbody.innerHTML = ''; };

  function getCsrf(){
    const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : '';
  }
  function setLoading(btn, loading){
    if(!btn) return;
    if(loading){
      btn.dataset.oldText = btn.textContent;
      btn.textContent = 'Завантаження...';
      btn.setAttribute('disabled','disabled');
    } else {
      if(btn.dataset.oldText) btn.textContent = btn.dataset.oldText;
      btn.removeAttribute('disabled');
    }
  }
  function clearAndAppendRows(tbody, list, includePortion){
    if(!tbody) return;
    clearTbody(tbody);
    const items = Array.isArray(list) ? list : [];
    if(items.length === 0){
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = includePortion ? 3 : 2;
      td.className = 'muted';
      td.textContent = 'Немає даних';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    items.forEach(d=>{
      const tr = document.createElement('tr');
      const nameTd = document.createElement('td');
      nameTd.textContent = d && d.name != null ? d.name : '';
      tr.appendChild(nameTd);
      if(includePortion){
        const portionTd = document.createElement('td');
        portionTd.textContent = d && d.portion != null ? d.portion : 0;
        tr.appendChild(portionTd);
      }
      const kTd = document.createElement('td');
      const cal = d && d.calories != null ? d.calories : 0;
      const p = d && d.protein != null ? d.protein : 0;
      const f = d && d.fat != null ? d.fat : 0;
      const c = d && d.carbs != null ? d.carbs : 0;
      kTd.textContent = `${cal} / ${p} / ${f} / ${c}`;
      tr.appendChild(kTd);
      tbody.appendChild(tr);
    });
  }
  function ensurePanelsExist(scope, includePortion){
    const container = document.querySelector(`#${scope}-tabs .tab-body`);
    if(!container) return;
    MEAL_KEYS.forEach((key)=>{
      const dataPanel = panelIdFor(scope, key);
      let panel = document.querySelector(`.tab-panel[data-panel="${dataPanel}"]`);
      if(!panel){
        panel = document.createElement('div');
        panel.className = 'tab-panel';
        panel.setAttribute('data-panel', dataPanel);
        if(key!=='breakfast') panel.style.display='none';
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tr = document.createElement('tr');
        const thName = document.createElement('th'); thName.textContent = 'Страва'; tr.appendChild(thName);
        if(includePortion){ const thPortion = document.createElement('th'); thPortion.textContent = 'Порція'; tr.appendChild(thPortion); }
        const thKbjv = document.createElement('th'); thKbjv.textContent = 'КБЖВ'; tr.appendChild(thKbjv);
        thead.appendChild(tr);
        const tbody = document.createElement('tbody');
        table.appendChild(thead);
        table.appendChild(tbody);
        panel.appendChild(table);
        container.appendChild(panel);
      }
    });
  }
  let _llm_week = null;
  let _llm_day = 0;
  let _calc_week = null;
  let _calc_day = 0;
  function renderDay(scope){
    const isCalc = scope===SCOPES.CALC;
    const week = isCalc ? _calc_week : _llm_week;
    const dayIdx = isCalc ? _calc_day : _llm_day;
    const day = Array.isArray(week) ? (week[dayIdx] || {}) : (week || {});
    MEAL_KEYS.forEach(k=>{
      const panelTbody = document.querySelector(`.tab-panel[data-panel="${panelIdFor(scope, k)}"] tbody`);
      if(panelTbody){ clearAndAppendRows(panelTbody, day ? day[k] : [], isCalc); }
    });
  }
  function setupDayHeaders(){
    [['llm','llm-day-headers'], ['calc','calc-day-headers']].forEach(([scope, id])=>{
      const headers = document.getElementById(id);
      if(!headers) return;
      headers.addEventListener('click', function(e){
        if(!isButton(e.target)) return;
        headers.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
        e.target.classList.add('active');
        const day = parseInt(e.target.getAttribute('data-day')||'0',10) || 0;
        if(scope===SCOPES.LLM){ _llm_day = day; }
        else { _calc_day = day; }
        renderDay(scope);
      });
    });
  }
  setupDayHeaders();

  // Visibility helpers for tabs and calc button
  function setTabsVisible(scope, visible){
    const tabs = document.getElementById(`${scope}-tabs`);
    setVisible(tabs, visible);
  }
  function setCalcButtonEnabled(enabled){
    const calcBtn = document.querySelector('button[name="action"][value="calc"]');
    setDisabled(calcBtn, !enabled);
  }

  // Hydrate from server-rendered data on initial load
  try {
    if (window.__MENU_FROM_LLM__) {
      _llm_week = Array.isArray(window.__MENU_FROM_LLM__) ? window.__MENU_FROM_LLM__ : [window.__MENU_FROM_LLM__];
      ensurePanelsExist(SCOPES.LLM, false);
      renderDay(SCOPES.LLM);
      setTabsVisible(SCOPES.LLM, true);
      setCalcButtonEnabled(true);
    }
    if (window.__MENU_CALC__) {
      _calc_week = Array.isArray(window.__MENU_CALC__) ? window.__MENU_CALC__ : [window.__MENU_CALC__];
      ensurePanelsExist(SCOPES.CALC, true);
      renderDay(SCOPES.CALC);
      setTabsVisible(SCOPES.CALC, true);
    }
  } catch(e) { /* ignore */ }
  function updateLlmTabs(menu){
    if(!menu) return;
    _llm_week = Array.isArray(menu) ? menu : [menu];
    ensurePanelsExist(SCOPES.LLM, false);
    renderDay(SCOPES.LLM);
    setTabsVisible(SCOPES.LLM, true);
    setCalcButtonEnabled(true);
  }
  function updateCalcTabs(menu){
    _calc_week = Array.isArray(menu) ? menu : [menu];
    ensurePanelsExist(SCOPES.CALC, true);
    renderDay(SCOPES.CALC);
    setTabsVisible(SCOPES.CALC, true);
  }
  // Intercept LLM form
  const llmForm = document.querySelector('#llm-form');
  if(llmForm){
    llmForm.addEventListener('submit', function(e){
      const submitter = e.submitter; // button
      if(!(submitter && submitter.name==='action')) return;
      const action = submitter.value;
      if(action==='llm'){
        e.preventDefault();
        const btn = submitter;
        setLoading(btn, true);
        // Hide both sections and disable calculate while generating
        setTabsVisible(SCOPES.LLM, false);
        setTabsVisible(SCOPES.CALC, false);
        setCalcButtonEnabled(false);
        // Optionally clear visible table bodies to avoid stale data during loading
        qsa('.tab-panel[data-panel^="llm:"] tbody').forEach(clearTbody);
        qsa('.tab-panel[data-panel^="calc:"] tbody').forEach(clearTbody);
        const data = new FormData(llmForm);
        // Ensure action is sent explicitly (FormData may omit submitter)
        if(submitter && submitter.name){ data.append(submitter.name, submitter.value); }
        fetch(window.location.href, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrf()
          },
          body: data
        }).then(r=>r.json()).then(js=>{
          if(js && js.ok){
            updateLlmTabs(js.menu_from_llm);
          }
        }).catch(()=>{}).finally(()=>{
          setLoading(btn, false);
        });
      } else if(action==='clear'){
        e.preventDefault();
        const btn = submitter;
        setLoading(btn, true);
        const data = new FormData();
        data.append('action','clear');
        fetch(window.location.href, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrf()
          },
          body: data
        }).then(r=>r.json()).then(js=>{
          if(js && js.ok && js.cleared){
            // Hide LLM tabs and clear their bodies
            setTabsVisible(SCOPES.LLM, false);
            qsa('.tab-panel[data-panel^="llm:"] tbody').forEach(clearTbody);
            // Disable calc button and hide calc tabs and total
            setCalcButtonEnabled(false);
            setTabsVisible(SCOPES.CALC, false);
            qsa('.tab-panel[data-panel^="calc:"] tbody').forEach(clearTbody);
          }
        }).catch(()=>{}).finally(()=>{
          setLoading(btn, false);
        });
      }
    });
  }
  // Intercept Calc form
  const calcForm = document.querySelectorAll('form')[1];
  if(calcForm){
    calcForm.addEventListener('submit', function(e){
      const submitter = e.submitter;
      if(submitter && submitter.name==='action' && submitter.value==='calc'){
        e.preventDefault();
        const btn = submitter;
        setLoading(btn, true);
        const data = new FormData(calcForm);
        // Ensure action is sent explicitly
        if(submitter && submitter.name){ data.append(submitter.name, submitter.value); }
        fetch(window.location.href, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrf()
          },
          body: data
        }).then(r=>r.json()).then(js=>{
          if(js && js.ok){
            updateCalcTabs(js.menu_calculated);
          }
        }).catch(()=>{}).finally(()=>{
          setLoading(btn, false);
        });
      }
    });
  }
})();