// ── 포트폴리오 ────────────────────────────────────────────────────────────────
async function loadPortfolio() {
  const res = await fetch('/api/portfolio');
  const data = await res.json();
  const { summary, holdings, rate, account_totals } = data;

  document.getElementById('summary-cards').innerHTML = `
    <div class="card">
      <div class="card-label">총 자산 (원화환산)</div>
      <div class="card-value">${fmt(summary.total_krw)}원</div>
      <div class="card-sub">환율 ₩${rate.toLocaleString()}</div>
    </div>
    <div class="card">
      <div class="card-label">한국 주식</div>
      <div class="card-value">${fmt(summary.kr_stock)}원</div>
      <div class="card-sub">원화 기준</div>
    </div>
    <div class="card">
      <div class="card-label">미국 주식</div>
      <div class="card-value">${fmtUSD(summary.us_stock_usd)}</div>
      <div class="card-sub">≈ ${fmt(summary.us_stock_krw)}원</div>
    </div>
    <div class="card">
      <div class="card-label">현금 (원화)</div>
      <div class="card-value">${fmt(summary.cash_krw)}원</div>
      <div class="card-sub">실탄</div>
    </div>
    <div class="card">
      <div class="card-label">현금 (달러)</div>
      <div class="card-value">${fmtUSD(summary.cash_usd)}</div>
      <div class="card-sub">실탄</div>
    </div>
  `;

  function holdingRow(h) {
    const priceStr = h.market === 'KR'
      ? h.price.toLocaleString('ko-KR') + '원'
      : '$' + h.price.toFixed(2);
    const avgStr = h.market === 'KR'
      ? h.avg_price.toLocaleString('ko-KR') + '원'
      : '$' + h.avg_price.toFixed(2);
    const valStr = h.market === 'KR' ? fmt(h.value) + '원' : fmtUSD(h.value);

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
            ${labeled('보유 수량', h.qty + '주')}
            ${labeled('평균단가',  avgStr)}
            ${labeled('현재가',    priceStr)}
            ${labeled('평가금액',  valStr)}
          </div>
        </div>
        ${metaTag('수익률', `<span class="${pctClass(h.pct)} pct-main">${pctStr(h.pct)}</span>`)}
        ${metaTag('20일 등락', (() => {
          if (h.chg_20d === null) return `<span class="neu pct-sub">—</span>`;
          return `<span class="${pctClass(h.chg_20d)} pct-sub">${pctStr(h.chg_20d)}</span>`;
        })())}
        ${metaTag('추천', (() => {
          const map = { sell: ['매도 검토', 'badge-rec-sell'], hold: ['보유', 'badge-rec-hold'], buy: ['매수 검토', 'badge-rec-buy'] };
          const [txt, cls] = h.rec ? map[h.rec] : ['—', 'badge-rec-hold'];
          return `<span class="badge ${cls}">${txt}</span>`;
        })())}
        ${metaTag('경보', h.alert
          ? `<span class="badge badge-alert">급등</span>`
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
        <span class="account-total">${fmt(account_totals[acct] || 0)}원</span>
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
      <div class="bar-label"><span>한국 주식</span><span>${w.kr_stock}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.kr_stock}%;background:var(--green)"></div></div>
    </div>
    <div class="bar-wrap">
      <div class="bar-label"><span>미국 주식</span><span>${w.us_stock}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.us_stock}%;background:var(--blue)"></div></div>
    </div>
    <div class="bar-wrap">
      <div class="bar-label"><span>현금 (실탄)</span><span>${w.cash}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:${w.cash}%;background:#888780"></div></div>
    </div>
  `;
}

function toggleRecNote() {
  const el = document.getElementById('rec-note');
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function renderTreemap(holdings, summary, rate) {
  const labels     = ['전체'];
  const parents    = [''];
  const values     = [0];
  const colors     = ['transparent'];
  const customdata = [''];

  for (const h of holdings) {
    const val = h.market === 'KR' ? h.value : Math.round(h.value * rate);
    labels.push(h.name);
    parents.push('전체');
    values.push(val);
    customdata.push((h.pct > 0 ? '+' : '') + h.pct.toFixed(1) + '%');
    colors.push(h.market === 'KR' ? '#1D9E75' : '#378ADD');
  }

  if (summary.cash_krw > 0) {
    labels.push('현금 (KRW)'); parents.push('전체');
    values.push(summary.cash_krw); customdata.push(''); colors.push('#888780');
  }
  if (summary.cash_usd > 0) {
    labels.push('현금 (USD)'); parents.push('전체');
    values.push(Math.round(summary.cash_usd * rate)); customdata.push(''); colors.push('#aaa8a5');
  }

  Plotly.newPlot('treemap', [{
    type: 'treemap',
    labels, parents, values, customdata,
    texttemplate: '<b>%{label}</b><br>%{customdata}',
    hovertemplate: '<b>%{label}</b><br>%{value:,.0f}원<extra></extra>',
    marker: { colors, line: { width: 1.5, color: '#f5f5f3' } },
    pathbar: { visible: false },
  }], {
    margin: { t: 0, l: 0, r: 0, b: 0 },
    paper_bgcolor: 'transparent',
    height: 280,
  }, { displayModeBar: false, responsive: true });
}

async function reloadHoldings(btn) {
  btn.textContent = '처리 중…'; btn.disabled = true;
  await fetch('/api/portfolio/reload', { method: 'POST' });
  await loadPortfolio();
  btn.textContent = '종목 재로드'; btn.disabled = false;
}

async function refreshPrices() {
  const btn = document.querySelector('.refresh-btn');
  btn.textContent = '수집 중…';
  btn.disabled = true;
  await fetch('/api/refresh-prices');
  await loadPortfolio();
  btn.textContent = '가격 새로고침';
  btn.disabled = false;
}
