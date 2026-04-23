// app.js - 讀 data.json，feed / 表格 / 查詢模式
'use strict';

const REFRESH_INTERVAL = 30000;  // 30 秒
let allTrades = [];
let prevHashes = new Set();
let viewMode = 'table';  // 'feed' | 'table'，預設表格
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

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
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
    render();
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

// ─── 篩選 ─────────────────────────────────────────────────────
function applyFilters(trades) {
  const kw = filters.search.toLowerCase().trim();
  const min = +filters.minUsd || 0;
  return trades.filter(t => {
    if (filters.party !== 'ALL' && t.party !== filters.party) return false;
    if (filters.dir   !== 'ALL' && t.direction !== filters.dir) return false;
    if (min > 0 && (t.total || 0) < min) return false;
    if (kw) {
      const blob = ((t.name || '') + ' ' + t.wallet + ' ' + t.txhash).toLowerCase();
      if (!blob.includes(kw)) return false;
    }
    return true;
  });
}

// ─── 主渲染 ───────────────────────────────────────────────────
function render() {
  const filtered = applyFilters(allTrades);
  const isQuery = filters.search.trim().length > 0;
  const summaryEl = $('#querySummary');

  // 查詢模式 → 顯示統計卡 + 強制表格
  if (isQuery) {
    summaryEl.style.display = '';
    renderQuerySummary(filtered);
    renderTable(filtered);
  } else {
    summaryEl.style.display = 'none';
    if (viewMode === 'table') renderTable(filtered);
    else                      renderFeed(filtered);
  }
}

// ─── 查詢模式統計 ────────────────────────────────────────────
function renderQuerySummary(rows) {
  const el = $('#querySummary');
  if (!rows.length) {
    el.innerHTML = `<div class="empty">查詢「${escapeHtml(filters.search)}」無符合資料</div>`;
    return;
  }

  const agg = {};
  let totalBuyUsd = 0, totalSellUsd = 0;
  const wallets = new Set();
  const names = new Set();

  for (const t of rows) {
    const p = t.party;
    if (!agg[p]) agg[p] = { count: 0, buy_shares: 0, sell_shares: 0, buy_usd: 0, sell_usd: 0 };
    agg[p].count++;
    if (t.direction === 'BUY') {
      agg[p].buy_shares += t.shares || 0;
      agg[p].buy_usd    += t.total  || 0;
      totalBuyUsd       += t.total  || 0;
    } else {
      agg[p].sell_shares += t.shares || 0;
      agg[p].sell_usd    += t.total  || 0;
      totalSellUsd       += t.total  || 0;
    }
    wallets.add(t.wallet);
    if (t.name) names.add(t.name);
  }

  const partyHtml = Object.entries(agg).map(([p, d]) => `
    <div class="qcard ${p.toLowerCase()}">
      <div class="qparty">${p}</div>
      <div class="qrow"><span>筆數</span><b>${d.count}</b></div>
      <div class="qrow"><span>BUY shares</span><b>${fmt(d.buy_shares, 2)}</b></div>
      <div class="qrow"><span>BUY USD</span><b>$${fmt(d.buy_usd, 2)}</b></div>
      <div class="qrow"><span>SELL shares</span><b>${fmt(d.sell_shares, 2)}</b></div>
      <div class="qrow"><span>SELL USD</span><b>$${fmt(d.sell_usd, 2)}</b></div>
      <div class="qrow net"><span>淨持倉 shares</span><b>${fmt(d.buy_shares - d.sell_shares, 2)}</b></div>
      <div class="qrow net"><span>淨投入 USD</span><b>$${fmt(d.buy_usd - d.sell_usd, 2)}</b></div>
    </div>
  `).join('');

  const namesList = [...names].slice(0, 5).map(n =>
    `<span class="tag clickable" data-q="${escapeHtml(n)}" title="點擊只看此用戶">${escapeHtml(n)}</span>`
  ).join(' ');
  const walletList = [...wallets].slice(0, 3).map(w =>
    `<span class="tag mono clickable" data-q="${w}" title="點擊只看此錢包">${shortAddr(w)}</span>`
  ).join(' ');

  el.innerHTML = `
    <div class="qheader">
      <div class="qtitle">🔍 查詢結果：「${escapeHtml(filters.search)}」</div>
      <div class="qmeta">
        共 <b>${rows.length}</b> 筆 ｜
        ${wallets.size} 個錢包 ${walletList} ${wallets.size > 3 ? `+${wallets.size - 3}` : ''} ｜
        ${names.size > 0 ? `名稱：${namesList}` : '無命名'}
      </div>
      <div class="qmeta">
        合計 BUY <b>$${fmt(totalBuyUsd, 2)}</b> ｜ SELL <b>$${fmt(totalSellUsd, 2)}</b> ｜
        淨投入 <b style="color:${totalBuyUsd - totalSellUsd >= 0 ? '#4ade80' : '#f87171'}">
          $${fmt(totalBuyUsd - totalSellUsd, 2)}
        </b>
      </div>
    </div>
    <div class="qparties">${partyHtml}</div>
  `;
}

// ─── 表格檢視（Excel 風格） ──────────────────────────────────
function renderTable(rows) {
  const feed = $('#feed');
  if (!rows.length) {
    feed.innerHTML = '<div class="empty">無符合資料</div>';
    return;
  }
  const list = rows.slice(0, 1000);
  const head = `
    <table class="trades-table">
      <thead>
        <tr>
          <th>時間 (UTC+8)</th>
          <th>政黨</th>
          <th>方向</th>
          <th>標的</th>
          <th class="num">Shares</th>
          <th class="num">價格</th>
          <th class="num">總金額</th>
          <th>名稱</th>
          <th>錢包</th>
          <th>Hash</th>
        </tr>
      </thead>
      <tbody>
  `;
  const body = list.map(t => `
    <tr class="${t.party.toLowerCase()}">
      <td class="time-cell">${localTime(t.timestamp)}</td>
      <td><span class="badge party-${t.party.toLowerCase()}">${t.party}</span></td>
      <td><span class="badge ${t.direction === 'BUY' ? 'dir-buy' : 'dir-sell'}">${t.direction}</span></td>
      <td>${t.outcome}</td>
      <td class="num">${fmt(t.shares, 2)}</td>
      <td class="num">$${fmt(t.price, 4)}</td>
      <td class="num"><b>$${fmt(t.total, 2)}</b></td>
      <td>${t.name
        ? `<a class="name" href="https://polymarket.com/profile/${t.wallet}" target="_blank">${escapeHtml(t.name)}</a>`
        : '<span class="unnamed">(未命名)</span>'}</td>
      <td><a class="mono" href="https://polygonscan.com/address/${t.wallet}" target="_blank" title="${t.wallet}">${shortAddr(t.wallet)}</a></td>
      <td><a class="mono" href="https://polygonscan.com/tx/${t.txhash}" target="_blank" title="${t.txhash}">${shortHash(t.txhash)}</a></td>
    </tr>
  `).join('');
  feed.innerHTML = head + body + `</tbody></table>
    <div class="table-foot">顯示 ${list.length} / ${rows.length} 筆${rows.length > 1000 ? '（前 1000 筆）' : ''}</div>`;
}

// ─── Feed 檢視（卡片） ───────────────────────────────────────
function renderFeed(filtered) {
  const feed = $('#feed');
  if (!filtered.length) {
    feed.innerHTML = '<div class="empty">沒有符合條件的交易</div>';
    return;
  }
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
          <div class="info-row"><span class="info-label">用戶名稱:</span> ${nameHtml}</div>
          <div class="info-row"><span class="info-label">用戶地址:</span> <a class="addr-link" href="https://polygonscan.com/address/${t.wallet}" target="_blank" title="${t.wallet}">${t.wallet}</a></div>
          <div class="info-row"><span class="info-label">Tx Hash:</span> <a class="hash-link" href="https://polygonscan.com/tx/${t.txhash}" target="_blank" title="${t.txhash}">${shortHash(t.txhash)}</a></div>
        </div>
        <div class="amount">
          <div class="shares">${fmt(t.shares, 2)} shares</div>
          <div class="price">@ $${fmt(t.price, 4)}</div>
          <div class="total">$${fmt(t.total, 2)}</div>
        </div>
      </div>
    `;
  }).join('');
  prevHashes = new Set(allTrades.map(t => t.txhash + t.wallet + t.direction));
}

// ─── 事件綁定 ─────────────────────────────────────────────────
$('#search').addEventListener('input', e => {
  filters.search = e.target.value;
  $('#searchClear').style.display = e.target.value ? '' : 'none';
  render();
});

$('#searchClear')?.addEventListener('click', () => {
  $('#search').value = '';
  filters.search = '';
  $('#searchClear').style.display = 'none';
  render();
  $('#search').focus();
});

// 點擊查詢統計區的標籤 → 改用該值精確查詢
document.addEventListener('click', e => {
  const tag = e.target.closest('.tag.clickable');
  if (!tag) return;
  const q = tag.dataset.q;
  if (!q) return;
  $('#search').value = q;
  filters.search = q;
  $('#searchClear').style.display = '';
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('#minUsd').addEventListener('input', e => {
  filters.minUsd = e.target.value;
  render();
});

$('#viewToggle').addEventListener('click', () => {
  viewMode = viewMode === 'feed' ? 'table' : 'feed';
  $('#viewToggle').textContent = viewMode === 'feed' ? '📋 表格檢視' : '📰 Feed 檢視';
  render();
});

document.querySelectorAll('.filter-btn[data-party]').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn[data-party]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    filters.party = b.dataset.party;
    render();
  });
});

document.querySelectorAll('.filter-btn[data-dir]').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn[data-dir]').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    filters.dir = b.dataset.dir;
    render();
  });
});

// ─── 主題切換 ─────────────────────────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.textContent = saved === 'light' ? '☀️' : '🌙';
    btn.addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = cur === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      btn.textContent = next === 'light' ? '☀️' : '🌙';
    });
  }
})();

// ─── CSV 下載 ─────────────────────────────────────────────────
function tradesToCsv(rows) {
  const headers = ['時間(UTC+8)','政黨','Outcome','方向','名稱','錢包地址','TxHash','Shares','單價','總額USD','備註'];
  const escape = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  };
  const lines = [headers.join(',')];
  rows.forEach(t => {
    lines.push([
      t.timestamp, t.party, t.outcome, t.direction,
      t.name || '', t.wallet, t.txhash,
      t.shares, t.price, t.total, t.note || ''
    ].map(escape).join(','));
  });
  return lines.join('\r\n');
}

function downloadCsv() {
  const filtered = applyFilters(allTrades);
  if (!filtered.length) {
    alert('目前篩選結果為空，無資料可下載');
    return;
  }
  // BOM + UTF-8 讓 Excel 正常顯示中文
  const csv = '\uFEFF' + tradesToCsv(filtered);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const fname = `polymarket_tw2026_${filtered.length}rows_${ts}.csv`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

document.getElementById('downloadCsv')?.addEventListener('click', downloadCsv);

// ─── 啟動 ─────────────────────────────────────────────────────
loadData();
setInterval(loadData, REFRESH_INTERVAL);
