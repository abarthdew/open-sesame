// ── 이벤트 캘린더 ────────────────────────────────────────────────────────────
function eventsParams() {
  const from = document.getElementById('ev-from').value;
  const to   = document.getElementById('ev-to').value;
  const p = new URLSearchParams();
  if (from) p.set('from', from);
  if (to)   p.set('to', to);
  return p.toString() ? '?' + p : '';
}

async function renderEvents() {
  const res = await fetch('/api/events' + eventsParams());
  const evs = await res.json();
  document.getElementById('events-list').innerHTML = evs.length
    ? evs.map(e => {
        const d = e.date.slice(5).replace('-', '/');
        const apiTag = e.source === 'api'
          ? '<span class="event-api-tag">API</span>'
          : '';
        return `
          <div class="event-row">
            <div class="event-day">${d}<br><span class="badge badge-${e.importance} event-badge">${e.importance}</span></div>
            <div>
              <div class="event-name">${e.name}${apiTag}</div>
              <div class="event-sc">${e.scenarios}</div>
            </div>
          </div>`;
      }).join('')
    : '<div style="color:var(--text3);font-size:13px;padding:8px 0">해당 기간에 이벤트가 없습니다.</div>';
}

async function renderNewsSentiment() {
  const res = await fetch('/api/news-sentiment');
  const items = await res.json();
  const el = document.getElementById('news-sentiment-list');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div style="color:var(--text3);font-size:13px">데이터 없음 (주간 브리핑 실행 후 자동 반영)</div>';
    return;
  }
  const labelClass = label => {
    const l = label.toLowerCase();
    if (l.includes('bullish')) return 'bullish';
    if (l.includes('bearish')) return 'bearish';
    return 'neutral';
  };
  const labelEmoji = label => {
    const l = label.toLowerCase();
    if (l.includes('bullish')) return '📈';
    if (l.includes('bearish')) return '📉';
    return '➖';
  };
  el.innerHTML = items.map(item => `
    <div class="news-item">
      <span class="news-emoji">${labelEmoji(item.label)}</span>
      <div>
        <div class="news-title">${item.title}</div>
        <div class="news-meta">
          <span class="news-label ${labelClass(item.label)}">${item.label}</span>
          — ${item.source}
          <span class="news-tickers">${item.tickers}</span>
        </div>
      </div>
    </div>`).join('');
}

async function loadEvents() {
  if (!document.getElementById('ev-from').value) {
    document.getElementById('ev-from').value = new Date().toISOString().slice(0, 10);
  }
  await renderEvents();
  await renderNewsSentiment();
}

async function queryEvents() {
  document.getElementById('events-list').innerHTML = '<div class="loading">로딩 중…</div>';
  await renderEvents();
}

async function reloadEvents() {
  const btn = event.target;
  btn.textContent = '처리 중…'; btn.disabled = true;
  await fetch('/api/events/reload', { method: 'POST' });
  await renderEvents();
  btn.textContent = '재로드'; btn.disabled = false;
}
