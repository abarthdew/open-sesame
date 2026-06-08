// ── 탭 전환 ───────────────────────────────────────────────────────────────────
function showTab(id, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}

// ── 공유 포맷 유틸 ────────────────────────────────────────────────────────────
const fmt = n => Math.abs(n) >= 1e8
  ? (n / 1e8).toFixed(1) + '억'
  : Math.abs(n) >= 1e4
    ? (n / 1e4).toFixed(0) + '만'
    : n.toLocaleString('ko-KR');

const fmtUSD = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

function pctClass(v) { return v > 0 ? 'pos' : v < 0 ? 'neg' : 'neu'; }
function pctStr(v)   { return (v > 0 ? '+' : '') + v.toFixed(2) + '%'; }
function fmtDate(d)  { return d.slice(5).replace('-', '/'); }

// ── 초기 로드 ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadPortfolio();
  loadSignals();
  loadEvents();
});
