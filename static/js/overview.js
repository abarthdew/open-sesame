// ── Portfolio ──────────────────────────────────────────────────────────────────
async function loadPortfolio() {
  const res = await fetch('/api/portfolio');
  const data = await res.json();
  const { summary, holdings, rate, account_totals } = data;

  document.getElementById('summary-cards').innerHTML = `
    <div class="card">
      <div class="card-label">Total Assets (KRW equiv.)</div>
      <div class="card-value">₩${fmt(summary.total_krw)}</div>
      <div class="card-sub">FX ₩${rate.toLocaleString()}</div>
    </div>
    <div class="card">
      <div class="card-label">KR Stocks</div>
      <div class="card-value">₩${fmt(summary.kr_stock)}</div>
      <div class="card-sub">KRW basis</div>
    </div>
    <div class="card">
      <div class="card-label">US Stocks</div>
      <div class="card-value">${fmtUSD(summary.us_stock_usd)}</div>
      <div class="card-sub">≈ ₩${fmt(summary.us_stock_krw)}</div>
    </div>
    <div class="card">
      <div class="card-label">Cash (KRW)</div>
      <div class="card-value">₩${fmt(summary.cash_krw)}</div>
      <div class="card-sub">dry powder</div>
    </div>
    <div class="card">
      <div class="card-label">Cash (USD)</div>
      <div class="card-value">${fmtUSD(summary.cash_usd)}</div>
      <div class="card-sub">dry powder</div>
    </div>
  `;

  function holdingRow(h) {
    const priceStr = h.market === 'KR'
      ? '₩' + h.price.toLocaleString('en-US')
      : '$' + h.price.toFixed(2);
    const avgStr = h.market === 'KR'
      ? '₩' + h.avg_price.toLocaleString('en-US')
      : '$' + h.avg_price.toFixed(2);
    const valStr = h.market === 'KR' ? '₩' + fmt(h.value) : fmtUSD(h.value);

    const labeled = (label, value) =>
      `<span class="meta-key">${label}</span>&nbsp;<span class="meta-val">${value}</span>`;

    const metaTag = (label, content) => `
      <div class="meta-col">
        <div class="meta-label">${label}</div>
        ${content}
      </div>`;

    return `
      <div class="row">
        <div class="row-main">
          <div class="row-name">${h.name}</div>
          <div class="row-sub">
            ${labeled('Qty',       h.qty)}
            ${labeled('Avg Price', avgStr)}
            ${labeled('Price',     priceStr)}
            ${labeled('Value',     valStr)}
          </div>
        </div>
        ${metaTag('Return', `<span class="${pctClass(h.pct)} pct-main">${pctStr(h.pct)}</span>`)}
        ${metaTag('20d Change', (() => {
          if (h.chg_20d === null) return `<span class="neu pct-sub">—</span>`;
          return `<span class="${pctClass(h.chg_20d)} pct-sub">${pctStr(h.chg_20d)}</span>`;
        })())}
        ${metaTag('Signal', (() => {
          const map = { sell: ['Review Sell', 'badge-rec-sell'], hold: ['Hold', 'badge-rec-hold'], buy: ['Review Buy', 'badge-rec-buy'] };
          const [txt, cls] = h.rec ? map[h.rec] : ['—', 'badge-rec-hold'];
          return `<span class="badge ${cls}">${txt}</span>`;
        })())}
        ${metaTag('Alert', h.alert
          ? `<span class="badge badge-alert">Surge</span>`
          : `<span class="neu" style="font-size:13px">—</span>`)}
      </div>`;
  }

  function groupByAccount(items) {
    const groups = {};
    items.forEach(h => {
      if (!groups[h.account]) groups[h.account] = [];
      groups[h.account].push(h);
    });
    return groups;
  }

  function renderGrouped(items, el) {
    const groups = groupByAccount(items);
    el.innerHTML = Object.entries(groups).map(([acct, hs]) => `
      <div class="account-label">
        ${acct}
        <span class="account-total">₩${fmt(account_totals[acct] || 0)}</span>
      </div>
      ${hs.map(holdingRow).join('')}
    `).join('');
  }

  const kr = holdings.filter(h => h.market === 'KR');
  const us = holdings.filter(h => h.market === 'US');
  renderGrouped(kr, document.getElementById('kr-holdings'));
  renderGrouped(us, document.getElementById('us-holdings'));

  renderTreemap(holdings, summary, rate);

  const w = summary.weight;
  document.getElementById('weight-bars').innerHTML = `
    <div class="bar-wrap">
      <div class="bar-label"><span>KR Stocks</span><span>${w.kr_stock}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.kr_stock}%;background:var(--green)"></div></div>
    </div>
    <div class="bar-wrap">
      <div class="bar-label"><span>US Stocks</span><span>${w.us_stock}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.us_stock}%;background:var(--blue)"></div></div>
    </div>
    <div class="bar-wrap">
      <div class="bar-label"><span>Cash</span><span>${w.cash}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.cash}%;background:#888780"></div></div>
    </div>
  `;
}

function toggleRecNote() {
  const el = document.getElementById('rec-note');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function renderTreemap(holdings, summary, rate) {
  const labels     = ['Total'];
  const parents    = [''];
  const values     = [0];
  const colors     = ['transparent'];
  const customdata = [''];

  for (const h of holdings) {
    const val = h.market === 'KR' ? h.value : Math.round(h.value * rate);
    labels.push(h.name);
    parents.push('Total');
    values.push(val);
    customdata.push((h.pct > 0 ? '+' : '') + h.pct.toFixed(1) + '%');
    colors.push(h.market === 'KR' ? '#1D9E75' : '#378ADD');
  }

  if (summary.cash_krw > 0) {
    labels.push('Cash (KRW)'); parents.push('Total');
    values.push(summary.cash_krw); customdata.push(''); colors.push('#888780');
  }
  if (summary.cash_usd > 0) {
    labels.push('Cash (USD)'); parents.push('Total');
    values.push(Math.round(summary.cash_usd * rate)); customdata.push(''); colors.push('#aaa8a5');
  }

  Plotly.newPlot('treemap', [{
    type: 'treemap',
    labels, parents, values, customdata,
    texttemplate: '<b>%{label}</b><br>%{customdata}',
    hovertemplate: '<b>%{label}</b><br>₩%{value:,.0f}<extra></extra>',
    marker: { colors, line: { width: 1.5, color: '#f5f5f3' } },
    pathbar: { visible: false },
  }], {
    margin: { t: 0, l: 0, r: 0, b: 0 },
    paper_bgcolor: 'transparent',
    height: 280,
  }, { displayModeBar: false, responsive: true });
}

async function reloadHoldings(btn) {
  btn.textContent = 'Processing…'; btn.disabled = true;
  await fetch('/api/portfolio/reload', { method: 'POST' });
  await loadPortfolio();
  btn.textContent = 'Reload Holdings'; btn.disabled = false;
}

async function refreshPrices() {
  const btn = document.querySelector('.refresh-btn');
  btn.textContent = 'Fetching…';
  btn.disabled = true;
  await fetch('/api/refresh-prices');
  await loadPortfolio();
  btn.textContent = 'Refresh Prices';
  btn.disabled = false;
}
