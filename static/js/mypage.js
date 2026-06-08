// ── 마이페이지 ────────────────────────────────────────────────────────────────
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
  document.getElementById('mypage-table').innerHTML = '<div class="loading">로딩 중…</div>';
  document.getElementById('trades-table').innerHTML = '<div class="loading">로딩 중…</div>';
  const data = await fetchMypage();
  renderMypageTable(data);
  renderMypageBar(data);
  renderMypageLine(data);
  const trades = await fetchTrades();
  renderTrades(trades);
}

async function reloadSnapshots() {
  const btn = document.querySelector('#mypage .refresh-btn');
  btn.textContent = '처리 중…'; btn.disabled = true;
  const res = await fetch('/api/mypage/reload', { method: 'POST' });
  const data = await res.json();
  if (!res.ok) {
    const msg = data.error === 'date_missing'
      ? 'portfolio.toml의 [meta] updated 날짜가 없습니다'
      : `날짜 형식 오류: ${data.error}`;
    document.getElementById('mypage-table').innerHTML =
      `<div class="loading" style="color:#ff6b6b">${msg}</div>`;
    btn.textContent = '재로드'; btn.disabled = false;
    return;
  }
  mypageLoaded = false;
  document.getElementById('mypage-table').innerHTML = '<div class="loading">로딩 중…</div>';
  await loadMypage();
  btn.textContent = '재로드'; btn.disabled = false;
}

function renderMypageTable(data) {
  const { dates, accounts, totals, salary, spending, tax, net_savings, delta } = data;
  if (!dates.length) {
    document.getElementById('mypage-table').innerHTML =
      '<p style="color:var(--text3);font-size:13px">데이터 없음. data/account_history.toml을 편집한 후 재로드하세요.</p>';
    return;
  }

  let html = `<table class="snap-table"><thead><tr>
    <th>계좌</th>${dates.map(d => `<th>${fmtDate(d)}</th>`).join('')}
  </tr></thead><tbody>`;

  accounts.forEach((acct) => {
    html += `<tr><td>${acct.name}</td>${acct.values.map(v =>
      `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;
  });

  html += `<tr class="total-row"><td>총합</td>${totals.map(t => `<td>${fmt(t)}</td>`).join('')}</tr>`;

  const deltaCell = (i) => {
    if (i !== dates.length - 1 || !delta) return '<td>-</td>';
    const sign = delta.amount >= 0 ? '+' : '';
    const cls  = delta.amount >= 0 ? 'pos' : 'neg';
    return `<td class="${cls}">${sign}${fmt(delta.amount)} (${sign}${delta.pct}%)</td>`;
  };
  html += `<tr class="meta-row"><td>등락</td>${dates.map((_, i) => deltaCell(i)).join('')}</tr>`;

  html += `<tr class="meta-row"><td>월 급여</td>${salary.map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>소비 금액</td>${spending.map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>세금</td>${(tax || []).map(v =>
    `<td>${v > 0 ? fmt(v) : '-'}</td>`).join('')}</tr>`;

  html += `<tr class="meta-row"><td>순 저축</td>${net_savings.map(v => {
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
    hovertemplate: `<b>${acct.name}</b><br>%{y:,.0f}원<extra></extra>`,
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
    el.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:8px 0">매도 내역이 없습니다. portfolio.toml에 [[trades]] 항목을 추가하세요.</p>';
    return;
  }

  const fmtPrice = (v, market) => market === 'US' ? `$${v.toLocaleString()}` : `${v.toLocaleString()}원`;

  let html = `<table class="snap-table"><thead><tr>
    <th>매도일</th><th>계좌</th><th>종목</th><th>수량</th>
    <th>매입가</th><th>매도가</th><th>실현손익</th><th>세금</th><th>순손익</th><th>수익률</th>
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
    <td colspan="7">총 순손익 (세후)</td>
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
      name: '총합', x: xs, y: totals, yaxis: 'y',
      line: { color: '#378ADD', width: 2.5 },
      hovertemplate: '총합: %{y:,.0f}원<extra></extra>',
    },
    {
      name: '월 급여', x: xs, y: salary, yaxis: 'y2',
      line: { color: '#1D9E75', width: 1.5, dash: 'dot' },
      hovertemplate: '월 급여: %{y:,.0f}원<extra></extra>',
    },
    {
      name: '소비 금액', x: xs, y: spending, yaxis: 'y2',
      line: { color: '#D85A30', width: 1.5, dash: 'dot' },
      hovertemplate: '소비: %{y:,.0f}원<extra></extra>',
    },
    {
      name: '세금', x: xs, y: tax || xs.map(() => 0), yaxis: 'y2',
      line: { color: '#E67E22', width: 1.5, dash: 'dot' },
      hovertemplate: '세금: %{y:,.0f}원<extra></extra>',
    },
    {
      name: '순 저축', x: xs, y: net_savings, yaxis: 'y2',
      line: { color: '#9B59B6', width: 2 },
      hovertemplate: '순저축: %{y:,.0f}원<extra></extra>',
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
