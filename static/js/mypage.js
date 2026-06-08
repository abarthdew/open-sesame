// ── My page ────────────────────────────────────────────────────────────────────
const ACCOUNT_COLORS = [
  '#378ADD','#1D9E75','#E67E22','#9B59B6',
  '#E74C3C','#1ABC9C','#F39C12','#7F8C8D','#BDC3C7',
];

let mypageLoaded = false;

async function fetchMypage() {
  const from = document.getElementById('mp-from').value;
  const to   = document.getElementById('mp-to').value;
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to)   params.set('to', to);
  const res = await fetch('/api/mypage' + (params.toString() ? '?' + params : ''));
  return res.json();
}

async function loadMypage() {
  if (mypageLoaded) return;
  mypageLoaded = true;
  if (!document.getElementById('mp-from').value) {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    document.getElementById('mp-from').value = d.toISOString().slice(0, 10);
  }
  const data = await fetchMypage();
  renderMypageTable(data);
  renderMypageBar(data);
  renderMypageLine(data);
  const trades = await fetchTrades();
  renderTrades(trades);
}

async function queryMypage() {
  document.getElementById('mypage-table').innerHTML = '<div class="loading">Loading…</div>';
  document.getElementById('trades-table').innerHTML = '<div class="loading">Loading…</div>';
  const data = await fetchMypage();
  renderMypageTable(data);
  renderMypageBar(data);
  renderMypageLine(data);
  const trades = await fetchTrades();
  renderTrades(trades);
}

async function reloadSnapshots() {
  const btn = document.querySelector('#mypage .refresh-btn');
  btn.textContent = 'Processing…'; btn.disabled = true;
  const res = await fetch('/api/mypage/reload', { method: 'POST' });
  const data = await res.json();
  if (!res.ok) {
    const msg = data.error === 'date_missing'
      ? 'No [meta] updated date in portfolio.toml'
      : `Date format error: ${data.error}`;
    document.getElementById('mypage-table').innerHTML =
      `<div class="loading" style="color:#ff6b6b">${msg}</div>`;
    btn.textContent = 'Reload'; btn.disabled = false;
    return;
  }
  mypageLoaded = false;
  document.getElementById('mypage-table').innerHTML = '<div class="loading">Loading…</div>';
  await loadMypage();
  btn.textContent = 'Reload'; btn.disabled = false;
}

function renderMypageTable(data) {
  const { dates, accounts, totals, salary, spending, tax, net_savings, delta } = data;
  if (!dates.length) {
    document.getElementById('mypage-table').innerHTML =
      '<p style="color:var(--text3);font-size:13px">No data. Edit data/account_history.toml, then reload.</p>';
    return;
  }

  let html = `<table class="snap-table"><thead><tr>
    <th>Account</th>${dates.map(d => `<th>${fmtDate(d)}</th>`).join('')}
  </tr></thead><tbody>`;

  accounts.forEach((acct) => {
    html += `<tr><td>${acct.name}</td>${acct.values.map(v =>
      `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;
  });

  html += `<tr class="total-row"><td>Total</td>${totals.map(t => `<td>${fmt(t)}</td>`).join('')}</tr>`;

  const deltaCell = (i) => {
    if (i !== dates.length - 1 || !delta) return '<td>-</td>';
    const sign = delta.amount >= 0 ? '+' : '';
    const cls  = delta.amount >= 0 ? 'pos' : 'neg';
    return `<td class="${cls}">${sign}${fmt(delta.amount)} (${sign}${delta.pct}%)</td>`;
  };
  html += `<tr class="meta-row"><td>Change</td>${dates.map((_, i) => deltaCell(i)).join('')}</tr>`;

  html += `<tr class="meta-row"><td>Salary</td>${salary.map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>Spending</td>${spending.map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>Tax</td>${(tax || []).map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>Net Savings</td>${net_savings.map(v => {
    if (v === 0) return '<td>-</td>';
    const cls = v > 0 ? 'pos' : 'neg';
    return `<td class="${cls}">${v > 0 ? '+' : ''}${fmt(v)}</td>`;
  }).join('')}</tr>`;

  html += '</tbody></table>';
  document.getElementById('mypage-table').innerHTML = html;
}

function renderMypageBar(data) {
  const { dates, accounts } = data;
  if (!dates.length) return;

  const traces = accounts.map((acct, i) => ({
    type: 'bar',
    name: acct.name,
    x: dates.map(fmtDate),
    y: acct.values,
    marker: { color: ACCOUNT_COLORS[i % ACCOUNT_COLORS.length] },
    hovertemplate: `<b>${acct.name}</b><br>₩%{y:,.0f}<extra></extra>`,
  }));

  Plotly.newPlot('mypage-bar', traces, {
    barmode: 'stack',
    margin: { t: 8, l: 60, r: 10, b: 40 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#5a5a58', size: 11 },
    xaxis: { tickfont: { size: 11 }, gridcolor: '#e0e0de' },
    yaxis: { tickformat: ',.0f', tickfont: { size: 11 }, gridcolor: '#e0e0de' },
    legend: { font: { size: 11 }, orientation: 'h', y: -0.2 },
    height: 300,
  }, { displayModeBar: false, responsive: true });
}

async function fetchTrades() {
  const from = document.getElementById('mp-from').value;
  const to   = document.getElementById('mp-to').value;
  const params = new URLSearchParams();
  if (from) params.set('from', from);
  if (to)   params.set('to', to);
  const res = await fetch('/api/trades' + (params.toString() ? '?' + params : ''));
  return res.json();
}

function renderTrades(data) {
  const el = document.getElementById('trades-table');
  const { trades, total_pnl } = data;
  if (!trades || !trades.length) {
    el.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:8px 0">No trade records. Add [[trades]] entries to portfolio.toml.</p>';
    return;
  }

  const fmtPrice = (v, market) => market === 'US' ? `$${v.toLocaleString()}` : `₩${v.toLocaleString()}`;

  let html = `<table class="snap-table"><thead><tr>
    <th>Date</th><th>Account</th><th>Ticker</th><th>Qty</th>
    <th>Buy Price</th><th>Sell Price</th><th>Gross P&amp;L</th><th>Tax</th><th>Net P&amp;L</th><th>Return</th>
  </tr></thead><tbody>`;

  for (const t of trades) {
    const grossCls  = pctClass(t.realized_pnl);
    const netCls    = pctClass(t.net_pnl);
    const pctCls    = pctClass(t.pct);
    const grossSign = t.realized_pnl >= 0 ? '+' : '';
    const netSign   = t.net_pnl >= 0 ? '+' : '';
    html += `<tr>
      <td>${t.sell_date}</td>
      <td>${t.account}</td>
      <td>${t.name} <span style="color:var(--text3);font-size:11px">${t.ticker}</span></td>
      <td>${t.qty}</td>
      <td>${fmtPrice(t.avg_price, t.market)}</td>
      <td>${fmtPrice(t.sell_price, t.market)}</td>
      <td class="${grossCls}">${grossSign}${fmt(t.realized_pnl)}</td>
      <td>${t.tax > 0 ? '-' + fmt(t.tax) : '-'}</td>
      <td class="${netCls}">${netSign}${fmt(t.net_pnl)}</td>
      <td class="${pctCls}">${pctStr(t.pct)}</td>
    </tr>`;
  }

  const totalCls  = pctClass(total_pnl);
  const totalSign = total_pnl >= 0 ? '+' : '';
  html += `<tr class="total-row">
    <td colspan="7">Total Net P&amp;L (after tax)</td>
    <td></td>
    <td class="${totalCls}">${totalSign}${fmt(total_pnl)}</td>
    <td>-</td>
  </tr>`;

  html += '</tbody></table>';
  el.innerHTML = html;
}

function renderMypageLine(data) {
  const { dates, totals, salary, spending, tax, net_savings } = data;
  if (!dates.length) return;

  const xs = dates.map(fmtDate);
  const traces = [
    {
      name: 'Total', x: xs, y: totals, yaxis: 'y',
      line: { color: '#378ADD', width: 2.5 },
      hovertemplate: 'Total: ₩%{y:,.0f}<extra></extra>',
    },
    {
      name: 'Salary', x: xs, y: salary, yaxis: 'y2',
      line: { color: '#1D9E75', width: 1.5, dash: 'dot' },
      hovertemplate: 'Salary: ₩%{y:,.0f}<extra></extra>',
    },
    {
      name: 'Spending', x: xs, y: spending, yaxis: 'y2',
      line: { color: '#D85A30', width: 1.5, dash: 'dot' },
      hovertemplate: 'Spending: ₩%{y:,.0f}<extra></extra>',
    },
    {
      name: 'Tax', x: xs, y: tax || xs.map(() => 0), yaxis: 'y2',
      line: { color: '#E67E22', width: 1.5, dash: 'dot' },
      hovertemplate: 'Tax: ₩%{y:,.0f}<extra></extra>',
    },
    {
      name: 'Net Savings', x: xs, y: net_savings, yaxis: 'y2',
      line: { color: '#9B59B6', width: 2 },
      hovertemplate: 'Net savings: ₩%{y:,.0f}<extra></extra>',
    },
  ];

  Plotly.newPlot('mypage-line', traces, {
    margin: { t: 8, l: 60, r: 65, b: 40 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: '#5a5a58', size: 11 },
    xaxis: { tickfont: { size: 11 }, gridcolor: '#e0e0de' },
    yaxis: {
      tickformat: ',.0f', tickfont: { size: 11, color: '#378ADD' },
      gridcolor: '#e0e0de', autorange: true,
    },
    yaxis2: {
      tickformat: ',.0f', tickfont: { size: 11, color: '#9B59B6' },
      overlaying: 'y', side: 'right', gridcolor: 'transparent', autorange: true,
    },
    legend: { font: { size: 11 }, orientation: 'h', y: -0.2 },
    height: 280,
  }, { displayModeBar: false, responsive: true });
}
