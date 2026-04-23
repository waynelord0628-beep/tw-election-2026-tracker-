// app.js - 讀 data.json，渲染 feed，篩選 + 自動刷新
'use strict';

const REFRESH_INTERVAL = 30000;  // 30 秒
const DATA_URL = 'data.json?t=' + Date.now();

let allTrades = [];
let prevHashes = new Set();
let filters = {
  party:   'ALL',
  dir:     'ALL',
  search:  '',
  minUsd:  0,
};

const $ = sel => document.querySelector(sel);

// ─── 工具 ─────────────────────────────────────────────────────
function fmt(n, d = 2) {
  if (n === null || n === undefined || isNaN(n)) return '-';
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });
}

function shortAddr(a) { return a ? a.slice(0, 6) + '…' + a.slice(-4) : ''; }
function shortHash(h) { return h ? h.slice(0, 10) + '…' + h.slice(-6) : ''; }

function timeAgo(isoStr) {
  const t = new Date(isoStr).getTime();
  const diff = (Date.now() - t) / 1000;
  if (diff < 60)        return Math.floor(diff) + ' 秒前';
  if (diff < 3600)      return Math.floor(diff / 60) + ' 分前';
  if (diff < 86400)     return Math.floor(diff / 3600) + ' 小時前';
  return Math.floor(diff / 86400) + ' 天前';
}

function localTime(isoStr) {
  try {
    const d = new Date(isoStr);
    const tw = new Date(d.getTime() + 8 * 3600 * 1000);
    return tw.toISOString().slice(0, 19).replace('T', ' ');
  } catch { return isoStr; }
}

// ─── 載入資料 ─────────────────────────────────────────────────
async function loadData() {
  try {
    const r = await fetch('data.json?t=' + Date.now(), { cache: 'no-store' });
    const data = await r.json();

    allTrades = data.trades;
    $('#lastUpdate').textContent = '最後更新：' + data.updated_at;
    $('#totalCount').textContent = data.total_count.toLocaleString();

    renderStats(data.stats);
    renderFeed();
  } catch (e) {
    $('#feed').innerHTML = `<div class="empty">⚠️ 載入失敗：${e.message}</div>`;
  }
}

function renderStats(s) {
  for (const p of ['kmt', 'dpp', 'tpp']) {
    const d = s[p.toUpperCase()] || {};
    $(`#${p}Count`).textContent = (d.count || 0).toLocaleString();
    $(`#${p}Buy`).textContent   = fmt(d.buy_shares,  0);
    $(`#${p}Sell`).textContent  = fmt(d.sell_shares, 0);
    $(`#${p}Vol`).textContent   = '$' + fmt(d.volume_usd, 0);
  }
}

// ─── 篩選 + 渲染 ──────────────────────────────────────────────
function applyFilters(trades) {
  const kw = filters.search.toLowerCase().trim();
  const min = +filters.minUsd || 0;
  return trades.filter(t => {
    if (filters.party !== 'ALL' && t.party !== filters.party) return false;
    if (filters.dir   !== 'ALL' && t.direction !== filters.dir) return false;
    if (min > 0 && (t.total || 0) < min) return false;
    if (kw) {
      const blob = (t.name + ' ' + t.wallet + ' ' + t.txhash).toLowerCase();
      if (!blob.includes(kw)) return false;
    }
    return true;
  });
}

function renderFeed() {
  const filtered = applyFilters(allTrades);
  const feed = $('#feed');

  if (!filtered.length) {
    feed.innerHTML = '<div class="empty">沒有符合條件的交易</div>';
    return;
  }

  // 取最新 200 筆
  const list = filtered.slice(0, 200);
  feed.innerHTML = list.map(t => {
    const isNew = !prevHashes.has(t.txhash + t.wallet + t.direction);
    const partyLow = t.party.toLowerCase();
    const dirClass = t.direction === 'BUY' ? 'dir-buy' : 'dir-sell';
    const dirIcon  = t.direction === 'BUY' ? '▲ BUY'  : '▼ SELL';

    const nameHtml = t.name
      ? `<a class="name" href="https://polymarket.com/profile/${t.wallet}" target="_blank">${escapeHtml(t.name)}</a>`
      : `<span class="name unnamed">(未命名)</span>`;

    return `
      <div class="trade ${partyLow} ${isNew ? 'new' : ''}">
        <div class="time" title="${localTime(t.timestamp)}">${timeAgo(t.timestamp)}</div>
        <div class="badges">
          <span class="badge party-${partyLow}">${t.party}</span>
          <span class="badge outcome">${t.outcome}</span>
          <span class="badge ${dirClass}">${dirIcon}</span>
        </div>
        <div class="info">
          ${nameHtml}
          <div class="addr">
            <a href="https://polygonscan.com/address/${t.wallet}" target="_blank" title="${t.wallet}">${t.wallet}</a>
          </div>
          <div class="hash">
            <a href="https://polygonscan.com/tx/${t.txhash}" target="_blank" title="${t.txhash}">${shortHash(t.txhash)}</a>
          </div>
        </div>
        <div class="amount">
          <div class="shares">${fmt(t.shares, 2)} shares</div>
          <div class="price">@ $${fmt(t.price, 4)}</div>
          <div class="total">$${fmt(t.total, 2)}</div>
        </div>
      </div>
    `;
  }).join('');

  // 記錄這次的 hash，下次比對誰是新的
  prevHashes = new Set(allTrades.map(t => t.txhash + t.wallet + t.direction));
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ─── 事件綁定 ─────────────────────────────────────────────────
$('#search').addEventListener('input', e => {
  filters.search = e.target.value;
  renderFeed();
});

$('#minUsd').addEventListener('input', e => {
  filters.minUsd = e.target.value;
  renderFeed();
});

document.querySelectorAll('.filter-btn[data-party]').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn[data-party]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    filters.party = b.dataset.party;
    renderFeed();
  });
});

document.querySelectorAll('.filter-btn[data-dir]').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn[data-dir]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    filters.dir = b.dataset.dir;
    renderFeed();
  });
});

// ─── 啟動 ─────────────────────────────────────────────────────
loadData();
setInterval(loadData, REFRESH_INTERVAL);
