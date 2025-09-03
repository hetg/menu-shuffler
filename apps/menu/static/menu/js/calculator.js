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
    while(tbody.firstChild) tbody.removeChild(tbody.firstChild);
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
      nameTd.textContent = (d && d.name)!=null ? d.name : '';
      tr.appendChild(nameTd);
      if(includePortion){
        const portionTd = document.createElement('td');
        portionTd.textContent = (d && d.portion)!=null ? d.portion : 0;
        tr.appendChild(portionTd);
      }
      const kTd = document.createElement('td');
      const cal = (d && d.calories)!=null ? d.calories : 0;
      const p = (d && d.protein)!=null ? d.protein : 0;
      const f = (d && d.fat)!=null ? d.fat : 0;
      const c = (d && d.carbs)!=null ? d.carbs : 0;
      kTd.textContent = `${cal} / ${p} / ${f} / ${c}`;
      tr.appendChild(kTd);
      tbody.appendChild(tr);
    });
  }
  function ensurePanelsExist(scope, includePortion){
    const ids = scope==='llm' ? ['breakfast','first_snack','lunch','second_snack','dinner'] : ['breakfast','first_snack','lunch','second_snack','dinner'];
    const container = document.querySelector(`#${scope}-tabs .tab-body`);
    if(!container) return;
    ids.forEach((key, idx)=>{
      const dataPanel = `${scope}:${key}`;
      let panel = document.querySelector(`.tab-panel[data-panel="${dataPanel}"]`);
      if(!panel){
        panel = document.createElement('div');
        panel.className = 'tab-panel';
        panel.setAttribute('data-panel', dataPanel);
        if(scope==='llm' && key!=='breakfast') panel.style.display='none';
        if(scope==='calc' && key!=='breakfast') panel.style.display='none';
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
  function updateLlmTabs(menu){
    if(!menu) return;
    ensurePanelsExist('llm', false);
    const map = {
      breakfast: 'llm:breakfast',
      first_snack: 'llm:first_snack',
      lunch: 'llm:lunch',
      second_snack: 'llm:second_snack',
      dinner: 'llm:dinner'
    };
    Object.keys(map).forEach(k=>{
      const panel = document.querySelector(`.tab-panel[data-panel="${map[k]}"] tbody`);
      if(panel){ clearAndAppendRows(panel, menu[k], false); }
    });
    const tabs = document.getElementById('llm-tabs');
    if(tabs) tabs.classList.add('visible');
    // enable calc button
    const calcBtn = document.querySelector('button[name="action"][value="calc"]');
    if(calcBtn){ calcBtn.removeAttribute('disabled'); }
  }
  function updateCalcTabs(menu){
    ensurePanelsExist('calc', true);
    const map = {
      breakfast: 'calc:breakfast',
      first_snack: 'calc:first_snack',
      lunch: 'calc:lunch',
      second_snack: 'calc:second_snack',
      dinner: 'calc:dinner'
    };
    Object.keys(map).forEach(k=>{
      const panel = document.querySelector(`.tab-panel[data-panel="${map[k]}"] tbody`);
      if(panel){ clearAndAppendRows(panel, menu ? menu[k] : [], true); }
    });
    const tabs = document.getElementById('calc-tabs');
    if(tabs) tabs.classList.add('visible');
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
        const llmTabsEl = document.getElementById('llm-tabs');
        if(llmTabsEl){ llmTabsEl.classList.remove('visible'); }
        const calcBtnEl = document.querySelector('button[name="action"][value="calc"]');
        if(calcBtnEl){ calcBtnEl.setAttribute('disabled', 'disabled'); }
        const calcTabsEl = document.getElementById('calc-tabs');
        if(calcTabsEl){ calcTabsEl.classList.remove('visible'); }
        // Optionally clear visible table bodies to avoid stale data during loading
        document.querySelectorAll('.tab-panel[data-panel^="llm:"] tbody').forEach(tb=>tb.innerHTML='');
        document.querySelectorAll('.tab-panel[data-panel^="calc:"] tbody').forEach(tb=>tb.innerHTML='');
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
            const llmTabs = document.getElementById('llm-tabs');
            if(llmTabs){ llmTabs.classList.remove('visible'); }
            document.querySelectorAll('.tab-panel[data-panel^="llm:"] tbody').forEach(tb=>tb.innerHTML='');
            // Disable calc button and hide calc tabs and total
            const calcBtn = document.querySelector('button[name="action"][value="calc"]');
            if(calcBtn){ calcBtn.setAttribute('disabled','disabled'); }
            const calcTabs = document.getElementById('calc-tabs');
            if(calcTabs){ calcTabs.classList.remove('visible'); }

            document.querySelectorAll('.tab-panel[data-panel^="calc:"] tbody').forEach(tb=>tb.innerHTML='');
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