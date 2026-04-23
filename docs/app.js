// app.js - 讀 data.json，feed / 表格 / 查詢模式
'use strict';

const REFRESH_INTERVAL = 30000;  // 30 秒
let allTrades = [];
let prevHashes = new Set();
let viewMode = 'table';  // 'feed' | 'table'，預設表格
let filters = {
  parties:   new Set(),  // 空 = 全部
  dirs:      new Set(),  // 空 = 全部
  search:    '',
  minUsd:    '',
  maxUsd:    '',
  timeStart: '',  // 'YYYY-MM-DD' UTC+8 起點
  timeEnd:   '',  // 'YYYY-MM-DD' UTC+8 終點（含當日）
};

// 排序狀態：col = 'timestamp' | 'shares' | 'price' | 'total'
let sortCol = 'timestamp';
let sortDir = 'desc';  // 'asc' | 'desc'

// 分頁狀態
let pageSize = 50;
let currentPage = 1;

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

// 把 'YYYY-MM-DD'（UTC+8 整日）轉為 UTC 毫秒；end=true 表示當日 23:59:59.999
function dateStrToMs(val, endOfDay = false) {
  if (!val) return null;
  const t = endOfDay ? 'T23:59:59.999' : 'T00:00:00.000';
  return new Date(val + t + '+08:00').getTime();
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
  const min = filters.minUsd === '' ? null : +filters.minUsd;
  const max = filters.maxUsd === '' ? null : +filters.maxUsd;
  const tsStart = dateStrToMs(filters.timeStart, false);
  const tsEnd   = dateStrToMs(filters.timeEnd,   true);

  return trades.filter(t => {
    if (filters.parties.size > 0 && !filters.parties.has(t.party)) return false;
    if (filters.dirs.size    > 0 && !filters.dirs.has(t.direction)) return false;
    if (min !== null && (t.total || 0) < min) return false;
    if (max !== null && (t.total || 0) > max) return false;
    if (kw) {
      const blob = ((t.name || '') + ' ' + t.wallet + ' ' + t.txhash).toLowerCase();
      if (!blob.includes(kw)) return false;
    }
    if (tsStart !== null) {
      const tms = new Date(t.timestamp).getTime();
      if (tms < tsStart) return false;
    }
    if (tsEnd !== null) {
      const tms = new Date(t.timestamp).getTime();
      if (tms > tsEnd) return false;
    }
    return true;
  });
}

// ─── 排序 ─────────────────────────────────────────────────────
function applySorting(rows) {
  const sorted = [...rows];
  sorted.sort((a, b) => {
    let va, vb;
    if (sortCol === 'timestamp') {
      va = new Date(a.timestamp).getTime();
      vb = new Date(b.timestamp).getTime();
    } else {
      va = a[sortCol] || 0;
      vb = b[sortCol] || 0;
    }
    return sortDir === 'asc' ? va - vb : vb - va;
  });
  return sorted;
}

function setSort(col) {
  if (col === 'timestamp') {
    // 時間欄：在 desc / asc 間切換（預設就是 timestamp desc）
    if (sortCol === 'timestamp') {
      sortDir = sortDir === 'desc' ? 'asc' : 'desc';
    } else {
      sortCol = 'timestamp';
      sortDir = 'desc';
    }
  } else {
    // 其他欄位：三段式 升序 → 降序 → 回預設(timestamp desc)
    if (sortCol !== col) {
      sortCol = col;
      sortDir = 'asc';
    } else if (sortDir === 'asc') {
      sortDir = 'desc';
    } else {
      sortCol = 'timestamp';
      sortDir = 'desc';
    }
  }
  currentPage = 1;
  render();
}

function sortIcon(col) {
  if (sortCol !== col) return '<span class="sort-icon muted">⇅</span>';
  return sortDir === 'desc'
    ? '<span class="sort-icon active">↓</span>'
    : '<span class="sort-icon active">↑</span>';
}

// ─── 主渲染 ───────────────────────────────────────────────────
function render() {
  const filtered = applyFilters(allTrades);
  const isQuery = filters.search.trim().length > 0;
  const summaryEl = $('#querySummary');

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

  const sorted = applySorting(rows);
  const totalRows = sorted.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * pageSize;
  const list  = sorted.slice(start, start + pageSize);

  // 可點擊欄位標頭
  const thTime   = `<th class="sortable" data-sort="timestamp">時間 (UTC+8) ${sortIcon('timestamp')}</th>`;
  const thShares = `<th class="num sortable" data-sort="shares">Shares ${sortIcon('shares')}</th>`;
  const thPrice  = `<th class="num sortable" data-sort="price">價格 ${sortIcon('price')}</th>`;
  const thTotal  = `<th class="num sortable" data-sort="total">總金額 ${sortIcon('total')}</th>`;

  const head = `
    <table class="trades-table">
      <thead>
        <tr>
          ${thTime}
          <th>政黨</th>
          <th>方向</th>
          <th>標的</th>
          ${thShares}
          ${thPrice}
          ${thTotal}
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
      <td class="num">${(t.price * 100).toFixed(1)}¢</td>
      <td class="num"><b>$${Math.round(t.total)}</b></td>
      <td>${t.name
        ? `<a class="name" href="https://polymarket.com/profile/${t.wallet}" target="_blank">${escapeHtml(t.name)}</a>`
        : '<span class="unnamed">(未命名)</span>'}</td>
      <td><a class="mono" href="https://polygonscan.com/address/${t.wallet}" target="_blank" title="${t.wallet}">${shortAddr(t.wallet)}</a></td>
      <td><a class="mono" href="https://polygonscan.com/tx/${t.txhash}" target="_blank" title="${t.txhash}">${shortHash(t.txhash)}</a></td>
    </tr>
  `).join('');

  // 分頁控制列
  const pagination = buildPagination(totalRows, totalPages);

  feed.innerHTML = head + body + `</tbody></table>${pagination}`;

  // 排序標頭事件
  feed.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => setSort(th.dataset.sort));
  });

  // 分頁事件
  bindPaginationEvents(totalPages);
}

// ─── 分頁列 HTML ──────────────────────────────────────────────
function buildPagination(totalRows, totalPages) {
  const pageSizeOptions = [10, 20, 50, 100].map(n =>
    `<option value="${n}" ${pageSize === n ? 'selected' : ''}>${n}</option>`
  ).join('');

  const btnFirst = `<button class="pg-btn" id="pgFirst" ${currentPage === 1 ? 'disabled' : ''} title="第一頁">«</button>`;
  const btnPrev  = `<button class="pg-btn" id="pgPrev"  ${currentPage === 1 ? 'disabled' : ''} title="上一頁">‹</button>`;
  const btnNext  = `<button class="pg-btn" id="pgNext"  ${currentPage === totalPages ? 'disabled' : ''} title="下一頁">›</button>`;
  const btnLast  = `<button class="pg-btn" id="pgLast"  ${currentPage === totalPages ? 'disabled' : ''} title="最後一頁">»</button>`;

  const start = (currentPage - 1) * pageSize + 1;
  const end   = Math.min(currentPage * pageSize, totalRows);

  return `
    <div class="pagination">
      <div class="pg-left">
        每頁顯示：<select id="pgSize">${pageSizeOptions}</select>
        <span class="pg-info">${start}–${end} / 共 ${totalRows} 筆</span>
      </div>
      <div class="pg-nav">
        ${btnFirst}${btnPrev}
        <span class="pg-pages">${buildPageButtons(totalPages)}</span>
        ${btnNext}${btnLast}
      </div>
    </div>
  `;
}

function buildPageButtons(totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
      .map(p => `<button class="pg-btn pg-num ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`)
      .join('');
  }
  // 顯示首尾 + 當前頁附近
  const pages = new Set([1, totalPages, currentPage,
    currentPage - 1, currentPage + 1,
    currentPage - 2, currentPage + 2]);
  const sorted = [...pages].filter(p => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  let html = '';
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) html += `<span class="pg-ellipsis">…</span>`;
    html += `<button class="pg-btn pg-num ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    prev = p;
  }
  return html;
}

function bindPaginationEvents(totalPages) {
  const feed = $('#feed');
  feed.querySelector('#pgSize')?.addEventListener('change', e => {
    pageSize = +e.target.value;
    currentPage = 1;
    render();
  });
  feed.querySelector('#pgFirst')?.addEventListener('click', () => { currentPage = 1; render(); });
  feed.querySelector('#pgPrev')?.addEventListener('click',  () => { if (currentPage > 1) { currentPage--; render(); } });
  feed.querySelector('#pgNext')?.addEventListener('click',  () => { if (currentPage < totalPages) { currentPage++; render(); } });
  feed.querySelector('#pgLast')?.addEventListener('click',  () => { currentPage = totalPages; render(); });
  feed.querySelectorAll('.pg-num').forEach(btn => {
    btn.addEventListener('click', () => {
      currentPage = +btn.dataset.page;
      render();
    });
  });
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
          <div class="price">@ ${(t.price * 100).toFixed(1)}¢</div>
          <div class="total">$${Math.round(t.total)}</div>
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
  currentPage = 1;
  render();
});

$('#searchClear')?.addEventListener('click', () => {
  $('#search').value = '';
  filters.search = '';
  $('#searchClear').style.display = 'none';
  currentPage = 1;
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
  currentPage = 1;
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

$('#minUsd').addEventListener('input', e => {
  filters.minUsd = e.target.value;
  currentPage = 1;
  updatePillLabels();
  render();
});
document.getElementById('maxUsd')?.addEventListener('input', e => {
  filters.maxUsd = e.target.value;
  currentPage = 1;
  updatePillLabels();
  render();
});

$('#viewToggle').addEventListener('click', () => {
  viewMode = viewMode === 'feed' ? 'table' : 'feed';
  $('#viewToggle').textContent = viewMode === 'feed' ? '📋 表格' : '📰 Feed';
  render();
});

// ─── Pill 下拉系統 ───────────────────────────────────────────
function closeAllPills(except) {
  document.querySelectorAll('.pill-dropdown.open').forEach(d => {
    if (d !== except) d.classList.remove('open');
  });
}
document.querySelectorAll('.pill-dropdown').forEach(dd => {
  const trigger = dd.querySelector('.pill-trigger');
  trigger.addEventListener('click', e => {
    e.stopPropagation();
    const wasOpen = dd.classList.contains('open');
    closeAllPills();
    if (!wasOpen) {
      dd.classList.add('open');
      if (dd.dataset.pill === 'date') renderCalendar();
    }
  });
  dd.querySelector('.pill-panel')?.addEventListener('click', e => e.stopPropagation());
});
document.addEventListener('click', () => closeAllPills());
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAllPills(); });

// 確認鈕：只是關閉面板（變動已即時生效）
document.querySelectorAll('[data-confirm]').forEach(b => {
  b.addEventListener('click', () => closeAllPills());
});

// 重設鈕：清除該 pill 的篩選
document.querySelectorAll('[data-reset]').forEach(b => {
  b.addEventListener('click', () => {
    const which = b.dataset.reset;
    if (which === 'party') {
      filters.parties.clear();
      document.querySelectorAll('[data-party-check]').forEach(c => c.checked = false);
    } else if (which === 'dir') {
      filters.dirs.clear();
      document.querySelectorAll('[data-dir-check]').forEach(c => c.checked = false);
    } else if (which === 'amount') {
      filters.minUsd = '';
      filters.maxUsd = '';
      const minEl = document.getElementById('minUsd');
      const maxEl = document.getElementById('maxUsd');
      if (minEl) minEl.value = '';
      if (maxEl) maxEl.value = '';
    } else if (which === 'date') {
      filters.timeStart = '';
      filters.timeEnd   = '';
      calRangeStart = null;
      calRangeEnd   = null;
      renderCalendar();
    }
    currentPage = 1;
    updatePillLabels();
    render();
  });
});

// 多選 checkbox
document.querySelectorAll('[data-party-check]').forEach(c => {
  c.addEventListener('change', () => {
    if (c.checked) filters.parties.add(c.value);
    else           filters.parties.delete(c.value);
    currentPage = 1;
    updatePillLabels();
    render();
  });
});
document.querySelectorAll('[data-dir-check]').forEach(c => {
  c.addEventListener('change', () => {
    if (c.checked) filters.dirs.add(c.value);
    else           filters.dirs.delete(c.value);
    currentPage = 1;
    updatePillLabels();
    render();
  });
});

// ─── Pill 標籤更新 ───────────────────────────────────────────
function updatePillLabels() {
  // 政黨
  const partyDD = document.querySelector('.pill-dropdown[data-pill="party"]');
  const partyText = partyDD.querySelector('.pill-text');
  if (filters.parties.size === 0) {
    partyText.textContent = '政黨';
    partyDD.classList.remove('has-value');
  } else {
    partyText.textContent = '政黨：' + [...filters.parties].join('+');
    partyDD.classList.add('has-value');
  }
  // 方向
  const dirDD = document.querySelector('.pill-dropdown[data-pill="dir"]');
  const dirText = dirDD.querySelector('.pill-text');
  if (filters.dirs.size === 0) {
    dirText.textContent = '方向';
    dirDD.classList.remove('has-value');
  } else {
    dirText.textContent = '方向：' + [...filters.dirs].join('+');
    dirDD.classList.add('has-value');
  }
  // 金額
  const amtDD = document.querySelector('.pill-dropdown[data-pill="amount"]');
  const amtText = amtDD.querySelector('.pill-text');
  const min = filters.minUsd, max = filters.maxUsd;
  if (min === '' && max === '') {
    amtText.textContent = '金額';
    amtDD.classList.remove('has-value');
  } else if (min !== '' && max === '') {
    amtText.textContent = `金額 ≥ $${min}`;
    amtDD.classList.add('has-value');
  } else if (min === '' && max !== '') {
    amtText.textContent = `金額 ≤ $${max}`;
    amtDD.classList.add('has-value');
  } else {
    amtText.textContent = `金額 $${min}–$${max}`;
    amtDD.classList.add('has-value');
  }
  // 日期
  const dateDD = document.querySelector('.pill-dropdown[data-pill="date"]');
  const dateText = dateDD.querySelector('.pill-text');
  if (!filters.timeStart && !filters.timeEnd) {
    dateText.textContent = '日期';
    dateDD.classList.remove('has-value');
  } else {
    const s = filters.timeStart ? filters.timeStart.slice(5) : '…';
    const e = filters.timeEnd   ? filters.timeEnd.slice(5)   : '…';
    dateText.textContent = `日期：${s} → ${e}`;
    dateDD.classList.add('has-value');
  }
  // 日曆面板上方的範圍顯示
  const sLab = document.getElementById('calStartLabel');
  const eLab = document.getElementById('calEndLabel');
  if (sLab) {
    if (filters.timeStart) { sLab.textContent = filters.timeStart; sLab.classList.remove('cal-label-empty'); }
    else                   { sLab.textContent = '開始日期'; sLab.classList.add('cal-label-empty'); }
  }
  if (eLab) {
    if (filters.timeEnd)   { eLab.textContent = filters.timeEnd; eLab.classList.remove('cal-label-empty'); }
    else                   { eLab.textContent = '結束日期'; eLab.classList.add('cal-label-empty'); }
  }
}

// ─── 雙月曆 ──────────────────────────────────────────────────
let calCursor = new Date();         // 左側月份的「年月」
calCursor.setDate(1);
let calRangeStart = null;           // YYYY-MM-DD
let calRangeEnd   = null;

function ymd(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function renderCalendar() {
  const wrap = document.getElementById('calWrap');
  if (!wrap) return;
  // 同步當前篩選值到 cal state
  calRangeStart = filters.timeStart || null;
  calRangeEnd   = filters.timeEnd   || null;

  const left  = new Date(calCursor.getFullYear(), calCursor.getMonth(), 1);
  const right = new Date(calCursor.getFullYear(), calCursor.getMonth() + 1, 1);
  wrap.innerHTML = renderMonth(left, 'left') + renderMonth(right, 'right');

  // 月份切換
  wrap.querySelector('[data-cal-prev]')?.addEventListener('click', () => {
    calCursor = new Date(calCursor.getFullYear(), calCursor.getMonth() - 1, 1);
    renderCalendar();
  });
  wrap.querySelector('[data-cal-next]')?.addEventListener('click', () => {
    calCursor = new Date(calCursor.getFullYear(), calCursor.getMonth() + 1, 1);
    renderCalendar();
  });

  // 點日期
  wrap.querySelectorAll('.cal-day:not(.other)').forEach(el => {
    el.addEventListener('click', () => {
      const d = el.dataset.date;
      if (!calRangeStart || (calRangeStart && calRangeEnd)) {
        calRangeStart = d;
        calRangeEnd   = null;
      } else {
        if (d < calRangeStart) {
          calRangeEnd   = calRangeStart;
          calRangeStart = d;
        } else {
          calRangeEnd = d;
        }
      }
      filters.timeStart = calRangeStart || '';
      filters.timeEnd   = calRangeEnd   || '';
      currentPage = 1;
      updatePillLabels();
      renderCalendar();
      render();
    });
  });
}

function renderMonth(monthDate, side) {
  const y = monthDate.getFullYear();
  const m = monthDate.getMonth();
  const monthNames = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
  const dows = ['日','一','二','三','四','五','六'];

  const firstDow = monthDate.getDay();              // 0~6
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const daysInPrev  = new Date(y, m, 0).getDate();

  const today = ymd(new Date());

  let cells = '';
  // 上個月的補白
  for (let i = firstDow - 1; i >= 0; i--) {
    cells += `<div class="cal-day other">${daysInPrev - i}</div>`;
  }
  // 本月
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const cls = ['cal-day'];
    if (dateStr === today) cls.push('today');
    if (calRangeStart && calRangeEnd) {
      if (dateStr === calRangeStart && dateStr === calRangeEnd) cls.push('range-only');
      else if (dateStr === calRangeStart)                       cls.push('range-start');
      else if (dateStr === calRangeEnd)                         cls.push('range-end');
      else if (dateStr > calRangeStart && dateStr < calRangeEnd) cls.push('in-range');
    } else if (calRangeStart && dateStr === calRangeStart) {
      cls.push('range-only');
    }
    cells += `<div class="${cls.join(' ')}" data-date="${dateStr}">${d}</div>`;
  }
  // 下個月補白讓總格 = 6 列 * 7
  const filled = firstDow + daysInMonth;
  const trailing = (7 - (filled % 7)) % 7;
  for (let i = 1; i <= trailing; i++) {
    cells += `<div class="cal-day other">${i}</div>`;
  }

  const navPrev = side === 'left'
    ? `<button class="cal-nav" type="button" data-cal-prev title="上個月">‹</button>`
    : `<button class="cal-nav invisible" type="button">‹</button>`;
  const navNext = side === 'right'
    ? `<button class="cal-nav" type="button" data-cal-next title="下個月">›</button>`
    : `<button class="cal-nav invisible" type="button">›</button>`;

  return `
    <div class="cal-month">
      <div class="cal-month-header">
        ${navPrev}
        <span>${y} ${monthNames[m]}</span>
        ${navNext}
      </div>
      <div class="cal-grid">
        ${dows.map(d => `<div class="cal-dow">${d}</div>`).join('')}
        ${cells}
      </div>
    </div>
  `;
}

// 初次標籤同步
updatePillLabels();

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
