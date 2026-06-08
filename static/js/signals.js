// ── Signals ────────────────────────────────────────────────────────────────────
async function loadSignals() {
  loadTriggers();
  const res = await fetch('/api/signals');
  const sigs = await res.json();

  function renderSignal(s) {
    const checked = s.checked ? 'checked' : '';
    const icon = s.checked ? '<i class="ti ti-check" style="font-size:12px;color:white"></i>' : '';
    return `
      <div class="chk-item" onclick="toggleSignal(${s.id}, this)">
        <div class="chk-box ${checked}">${icon}</div>
        <div>
          <div class="chk-text">${s.text}</div>
          <div class="chk-hint">${s.hint}</div>
        </div>
      </div>`;
  }

  const sells = sigs.filter(s => s.type === 'sell');
  const buys  = sigs.filter(s => s.type === 'buy');
  document.getElementById('sell-signals').innerHTML = sells.map(renderSignal).join('');
  document.getElementById('buy-signals').innerHTML  = buys.map(renderSignal).join('');
}

async function toggleSignal(id, el) {
  const box  = el.querySelector('.chk-box');
  const res  = await fetch(`/api/signals/${id}/toggle`, { method: 'POST' });
  const data = await res.json();
  if (data.checked) {
    box.classList.add('checked');
    box.innerHTML = '<i class="ti ti-check" style="font-size:12px;color:white"></i>';
  } else {
    box.classList.remove('checked');
    box.innerHTML = '';
  }
}

// ── Triggers ──────────────────────────────────────────────────────────────────

async function loadTriggers() {
  const res = await fetch('/api/triggers');
  renderTriggers(await res.json());
}

function renderTriggers(triggers) {
  const el = document.getElementById('triggers-list');
  if (!triggers.length) {
    el.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:4px 0">No triggers. Press Sync to load from reports.</p>';
    return;
  }
  el.innerHTML = triggers.map(renderTrigger).join('');
}

function renderTrigger(t) {
  const checked  = t.checked ? 'checked' : '';
  const icon     = t.checked ? '<i class="ti ti-check" style="font-size:12px;color:white"></i>' : '';
  const badge    = t.event_date
    ? `<span style="font-size:11px;background:var(--bg3);color:var(--text2);padding:1px 6px;border-radius:3px;margin-right:6px">${t.event_date}</span>`
    : '';
  const src      = t.source_file.split('/').pop().replace(/\.log$/, '').replace(/^\[\d{4}-\d{2}-\d{2}\]\[[\w]+\]/, '');
  const actionHtml = t.action ? `<div class="chk-hint">→ ${t.action}</div>` : '';
  const opacity  = t.checked ? 'opacity:0.4' : '';
  return `
    <div class="chk-item" onclick="toggleTrigger(${t.id}, this)" style="${opacity}">
      <div class="chk-box ${checked}">${icon}</div>
      <div style="flex:1;min-width:0">
        <div class="chk-text">${badge}${t.condition || t.text}</div>
        ${actionHtml}
        <div class="chk-tag">${src}</div>
      </div>
    </div>`;
}

async function toggleTrigger(id, el) {
  const box = el.querySelector('.chk-box');
  const res = await fetch(`/api/triggers/${id}/toggle`, { method: 'POST' });
  const data = await res.json();
  if (data.checked) {
    box.classList.add('checked');
    box.innerHTML = '<i class="ti ti-check" style="font-size:12px;color:white"></i>';
    el.style.opacity = '0.4';
  } else {
    box.classList.remove('checked');
    box.innerHTML = '';
    el.style.opacity = '1';
  }
}

async function reloadTriggers() {
  const btn = document.getElementById('trigger-sync-btn');
  btn.textContent = 'Processing…'; btn.disabled = true;
  const res  = await fetch('/api/triggers/reload', { method: 'POST' });
  const data = await res.json();
  await loadTriggers();
  btn.textContent = 'Sync'; btn.disabled = false;
}

// ── FOMO ──────────────────────────────────────────────────────────────────────
let fomoGood = 0, fomoBad = 0;

function fomoToggle(el, type) {
  const box = el.querySelector('.chk-box');
  const on = box.classList.toggle('checked');
  box.innerHTML = on ? '<i class="ti ti-check" style="font-size:12px;color:white"></i>' : '';
  if (type === 'good') fomoGood += on ? 1 : -1;
  else                 fomoBad  += on ? 1 : -1;
  updateFomoResult();
}

function updateFomoResult() {
  const el = document.getElementById('fomo-result');
  if (fomoGood + fomoBad === 0) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  if (fomoBad >= 2) {
    el.style.background = '#faece7'; el.style.color = 'var(--red)';
    el.textContent = '⚠️ FOMO signal detected — wait one day.';
  } else if (fomoGood >= 1 && fomoBad === 0) {
    el.style.background = '#dff0e8'; el.style.color = 'var(--green)';
    el.textContent = '✓ Conditions met — split entry can proceed.';
  } else {
    el.style.background = 'var(--bg2)'; el.style.color = 'var(--text2)';
    el.textContent = `${fomoBad} bad reason(s) · ${fomoGood} good reason(s) — judge carefully.`;
  }
}
