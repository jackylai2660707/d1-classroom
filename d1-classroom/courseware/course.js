(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  let dirty = false;
  let toastTimer;
  function downloadFile(text,name,type){
    const url=URL.createObjectURL(new Blob([text],{type}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download=name;
    document.body.append(anchor);anchor.click();anchor.remove();
    setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  function toast(message) {
    const target = $('.toast');
    target.textContent = message; target.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { target.hidden = true; }, 5000);
  }
  const dialog = $('#image-dialog');
  document.querySelectorAll('.image-zoom').forEach(button => button.addEventListener('click', () => {
    const source = button.querySelector('img');
    dialog.querySelector('img').src = source.src;
    dialog.querySelector('img').alt = source.alt;
    dialog.querySelector('p').textContent = source.alt;
    dialog.showModal();
  }));
  $('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  const lesson = Number(document.body.dataset.lesson);
  if (!lesson) return;
  const project=JSON.parse($('#project-data').textContent);
  $('#download-project').addEventListener('click',()=>downloadFile(JSON.stringify(project,null,2),`第${String(lesson).padStart(2,'0')}課.d1.json`,'application/json'));
  $('#download-python').addEventListener('click',()=>downloadFile(project.python,`第${String(lesson).padStart(2,'0')}課.py`,'text/x-python;charset=utf-8'));
  const stageButtons = [...document.querySelectorAll('[data-stage]')];
  let stage = 0;
  function showStage(index) {
    stage = Math.max(0, Math.min(3, Number(index) || 0));
    stageButtons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === stage)));
    document.querySelectorAll('[data-panel]').forEach(panel => { panel.hidden = Number(panel.dataset.panel) !== stage; });
    $('#stage-count').textContent = `第 ${stage + 1} 段，共 4 段`;
    $('#previous-stage').disabled = stage === 0;
    $('#next-stage').disabled = stage === 3;
    $('#next-stage').textContent = stage === 3 ? '已到最後一段' : '下一段 →';
  }
  stageButtons.forEach(button => button.addEventListener('click', () => showStage(button.dataset.stage)));
  $('#previous-stage').addEventListener('click', () => showStage(stage - 1));
  $('#next-stage').addEventListener('click', () => showStage(stage + 1));
  $('#projection').addEventListener('click', event => {
    const active = document.body.classList.toggle('projection');
    event.currentTarget.setAttribute('aria-pressed', String(active));
    event.currentTarget.textContent = active ? '一般閱讀' : '投影閱讀';
  });
  const fields = [...document.querySelectorAll('[data-field]')];
  fields.forEach(field => { if(field.tagName==='TEXTAREA')field.maxLength=5000;field.addEventListener('input', () => { dirty = true; }); });
  $('#export-record').addEventListener('click', () => {
    const values = Object.fromEntries(fields.map(field => [field.dataset.field, field.type === 'checkbox' ? field.checked : field.value]));
    const data = { format: 'd1-learning-record', version: 1, lesson, exportedAt: new Date().toISOString(), fields: values };
    downloadFile(JSON.stringify(data,null,2),`第${String(lesson).padStart(2,'0')}課_學習記錄.json`,'application/json');
    dirty = false;
    toast('已匯出記錄；請將下載檔存到老師指定的持久位置。');
  });
  $('#import-record').addEventListener('change', async event => {
    const input = event.currentTarget;
    try {
      const file = input.files[0]; if (!file) return;
      if (file.size > 1e6) throw Error('記錄檔過大。');
      const data = JSON.parse(await file.text());
      if (data.format !== 'd1-learning-record' || data.version !== 1 || data.lesson !== lesson || !data.fields || Array.isArray(data.fields) || typeof data.fields !== 'object') throw Error('請選擇本課匯出的學習記錄。');
      const updates = fields.map(field => {
        const value = data.fields[field.dataset.field];
        if (field.type === 'checkbox') {
          if (typeof value !== 'boolean') throw Error('記錄中的勾選欄位無效。');
        } else if (typeof value !== 'string' || value.length > 5000) throw Error('記錄中的文字欄位無效。');
        return { field, value };
      });
      if (dirty && !confirm('匯入會取代本頁尚未匯出的內容，確定匯入嗎？')) return;
      updates.forEach(({ field, value }) => { if (field.type === 'checkbox') field.checked = value; else field.value = value; });
      dirty = false; toast('本課記錄已匯入。');
    } catch (error) { toast(error instanceof SyntaxError ? '檔案不是有效的 JSON 記錄。' : error.message); }
    finally { input.value = ''; }
  });
  $('#print-lesson').addEventListener('click', () => window.print());
  window.addEventListener('beforeprint', () => {
    document.querySelectorAll('.print-value').forEach(node => node.remove());
    document.querySelectorAll('textarea').forEach(field => {
      const value = document.createElement('div'); value.className = 'print-value'; value.textContent = field.value;
      field.before(value);
    });
  });
  window.addEventListener('afterprint', () => document.querySelectorAll('.print-value').forEach(node => node.remove()));
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  showStage(0);
})();
