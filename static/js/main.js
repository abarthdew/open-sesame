// ── Tab switching ──────────────────────────────────────────────────────────────
function showTab(id, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}

// ── Shared format utils ────────────────────────────────────────────────────────
const fmt = n => Math.abs(n) >= 1e9
  ? (n / 1e9).toFixed(2) + 'B'
  : Math.abs(n) >= 1e6
    ? (n / 1e6).toFixed(1) + 'M'
    : Math.abs(n) >= 1e3
      ? (n / 1e3).toFixed(0) + 'K'
      : n.toLocaleString('en-US');

const fmtUSD = n => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });

function pctClass(v) { return v > 0 ? 'pos' : v < 0 ? 'neg' : 'neu'; }
function pctStr(v)   { return (v > 0 ? '+' : '') + v.toFixed(2) + '%'; }
function fmtDate(d)  { return d.slice(5).replace('-', '/'); }

// ── Initial load ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadPortfolio();
  loadSignals();
  loadEvents();
});
