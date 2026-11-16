import os
import sys
import json
import time
import socket
import threading
import subprocess
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

from scanner import DriveScanner, format_size, CATEGORIES
from shortcuts import generate_shortcuts
from delete_helper import send_to_recycle_bin

# Global instances
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
scanner = DriveScanner(root_drive=r'C:\\', min_size_bytes=1024*1024)
SHORTCUTS_DIR = os.path.join(BASE_DIR, 'Shortcuts')
shortcuts_generated = False
shortcuts_lock = threading.Lock()

def auto_generate_shortcuts():
    global shortcuts_generated
    while scanner.is_scanning:
        time.sleep(0.5)
    
    # When scan finishes, generate shortcuts
    with shortcuts_lock:
        print("[*] Generating categorized Windows shortcuts in c:\\finder\\Shortcuts ...")
        total = generate_shortcuts(scanner.files, output_dir=SHORTCUTS_DIR)
        shortcuts_generated = True
        print(f"[+] Successfully generated {total} shortcuts in {SHORTCUTS_DIR}")

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>C: Drive Disk Space Analyzer & File Cleaner</title>
<style>
  :root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-card: #243247;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --danger: #ef4444;
    --danger-hover: #dc2626;
    --success: #22c55e;
    --warning: #f59e0b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --border: #334155;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body { background-color: var(--bg-primary); color: var(--text-primary); min-height: 100vh; padding: 24px; }
  .container { max-width: 1400px; margin: 0 auto; }

  /* Header */
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
  .logo-group h1 { font-size: 24px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
  .logo-group p { font-size: 14px; color: var(--text-secondary); margin-top: 4px; }
  .header-actions { display: flex; gap: 12px; }

  /* Buttons */
  .btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: all 0.2s; text-decoration: none; }
  .btn-primary { background-color: var(--accent); color: #0f172a; }
  .btn-primary:hover { background-color: var(--accent-hover); }
  .btn-outline { background-color: transparent; border-color: var(--border); color: var(--text-primary); }
  .btn-outline:hover { background-color: var(--bg-secondary); border-color: var(--accent); }
  .btn-danger { background-color: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #fca5a5; }
  .btn-danger:hover { background-color: var(--danger); color: white; }
  .btn-sm { padding: 5px 10px; font-size: 12px; border-radius: 6px; }

  /* Progress Card */
  .progress-card { background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; padding: 18px 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
  .status-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .status-badge { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 20px; }
  .badge-scanning { background-color: rgba(56, 189, 248, 0.15); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.3); }
  .badge-done { background-color: rgba(34, 197, 94, 0.15); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.3); }
  
  .progress-bar-bg { width: 100%; height: 8px; background-color: #334155; border-radius: 4px; overflow: hidden; margin-bottom: 12px; }
  .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #818cf8); border-radius: 4px; transition: width 0.3s; }
  .progress-pulse { animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 14px; }
  .stat-item { background: var(--bg-card); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); }
  .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-val { font-size: 18px; font-weight: 700; color: #fff; margin-top: 4px; }

  /* Category Filter Pills */
  .category-nav { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 20px; scrollbar-width: thin; }
  .cat-pill { display: flex; align-items: center; gap: 8px; padding: 8px 16px; background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 24px; font-size: 13px; color: var(--text-secondary); cursor: pointer; white-space: nowrap; transition: all 0.2s; user-select: none; }
  .cat-pill:hover { border-color: var(--accent); color: var(--text-primary); }
  .cat-pill.active { background-color: var(--accent); color: #0f172a; font-weight: 700; border-color: var(--accent); }
  .cat-pill .cat-size { font-size: 11px; opacity: 0.85; background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 10px; }

  /* Filter Toolbar */
  .filter-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
  .search-input { flex: 1; min-width: 280px; background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; color: #fff; font-size: 14px; outline: none; }
  .search-input:focus { border-color: var(--accent); }
  .select-filter { background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; color: #fff; font-size: 13px; outline: none; cursor: pointer; }

  /* Files Table */
  .table-card { background-color: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
  table { width: 100%; border-collapse: collapse; text-align: left; }
  th { background-color: #172033; padding: 14px 18px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
  td { padding: 14px 18px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; }
  tr:hover td { background-color: rgba(56, 189, 248, 0.04); }
  tr.recycled td { text-decoration: line-through; opacity: 0.4; }

  .rank-badge { font-weight: 700; color: var(--accent); font-size: 12px; background: rgba(56, 189, 248, 0.1); padding: 3px 8px; border-radius: 4px; display: inline-block; min-width: 32px; text-align: center; }
  .file-name-cell { max-width: 360px; }
  .file-name { font-weight: 600; color: #fff; word-break: break-all; margin-bottom: 3px; display: flex; align-items: center; gap: 6px; }
  .file-meta { font-size: 11px; color: var(--text-secondary); display: flex; gap: 8px; }
  .file-path { font-family: monospace; font-size: 11px; color: #94a3b8; max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .size-cell { min-width: 130px; }
  .size-text { font-weight: 700; color: #38bdf8; font-size: 14px; }
  .size-bar-bg { width: 100%; height: 5px; background: #334155; border-radius: 3px; margin-top: 5px; overflow: hidden; }
  .size-bar-fill { height: 100%; background: #38bdf8; border-radius: 3px; }

  .actions-cell { display: flex; gap: 8px; }

  /* Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); justify-content: center; align-items: center; z-index: 1000; }
  .modal { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 12px; max-width: 500px; width: 90%; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
  .modal-header { font-size: 18px; font-weight: 700; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; color: #ef4444; }
  .modal-body { font-size: 14px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 20px; word-break: break-all; }
  .modal-file-box { background: var(--bg-primary); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-top: 10px; }
  .modal-footer { display: flex; justify-content: flex-end; gap: 10px; }

  /* Toast */
  .toast { position: fixed; bottom: 24px; right: 24px; background: #1e293b; border: 1px solid var(--border); border-radius: 8px; padding: 12px 20px; color: #fff; font-size: 13px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.4); transform: translateY(100px); opacity: 0; transition: all 0.3s; z-index: 1001; display: flex; align-items: center; gap: 8px; }
  .toast.show { transform: translateY(0); opacity: 1; }
  .toast.toast-success { border-color: var(--success); color: #86efac; }
  .toast.toast-error { border-color: var(--danger); color: #fca5a5; }

  /* Empty state */
  .empty-state { text-align: center; padding: 48px 20px; color: var(--text-secondary); }
</style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <header>
    <div class="logo-group">
      <h1>🔍 C: Drive Large File Finder & Cleaner</h1>
      <p>Ranked by file size and category with direct shortcuts and 1-click recycling</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-primary" onclick="openShortcutsFolder()">📁 Open Shortcuts Folder</button>
      <button class="btn btn-outline" onclick="triggerRescan()">🔄 Rescan Drive C:</button>
    </div>
  </header>

  <!-- Progress Card -->
  <div class="progress-card">
    <div class="status-row">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span id="statusBadge" class="status-badge badge-scanning">⏳ Scanning C:\ Drive...</span>
        <span id="shortcutsNotice" style="font-size: 12px; color: var(--text-secondary);"></span>
      </div>
      <div id="elapsedTimer" style="font-size: 13px; color: var(--text-secondary); font-family: monospace;">0.0s</div>
    </div>
    <div class="progress-bar-bg">
      <div id="progressBar" class="progress-bar-fill progress-pulse" style="width: 10%;"></div>
    </div>
    <div style="font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 8px;">
      Scanning: <span id="currentFolderText" style="color: #cbd5e1; font-family: monospace;">C:\</span>
    </div>
    <div class="stats-grid">
      <div class="stat-item">
        <div class="stat-label">Total Files Scanned</div>
        <div id="statFilesScanned" class="stat-val">0</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Folders Scanned</div>
        <div id="statDirsScanned" class="stat-val">0</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Total Data Analyzed</div>
        <div id="statBytesScanned" class="stat-val">0 B</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Large Files (>1 MB) Found</div>
        <div id="statLargeFilesCount" class="stat-val" style="color: var(--accent);">0</div>
      </div>
    </div>
  </div>

  <!-- Category Pills -->
  <div id="categoryPills" class="category-nav">
    <!-- Populated by JS -->
  </div>

  <!-- Filter Toolbar -->
  <div class="filter-toolbar">
    <input type="text" id="searchInput" class="search-input" placeholder="🔎 Search by file name or folder path..." oninput="onSearchChange()">
    
    <select id="sizeFilter" class="select-filter" onchange="onFilterChange()">
      <option value="0">All Large Files (> 1 MB)</option>
      <option value="10">Minimum 10 MB</option>
      <option value="50">Minimum 50 MB</option>
      <option value="100">Minimum 100 MB</option>
      <option value="500">Minimum 500 MB</option>
      <option value="1024">Minimum 1 GB (Huge)</option>
    </select>

    <select id="sortFilter" class="select-filter" onchange="onFilterChange()">
      <option value="size_desc">Sort: Size (Largest First)</option>
      <option value="size_asc">Sort: Size (Smallest First)</option>
      <option value="name_asc">Sort: File Name (A to Z)</option>
      <option value="date_desc">Sort: Date Modified (Newest)</option>
    </select>
  </div>

  <!-- Table Card -->
  <div class="table-card">
    <table>
      <thead>
        <tr>
          <th style="width: 70px;">Rank</th>
          <th>File Name</th>
          <th style="width: 180px;">Size</th>
          <th>Location</th>
          <th style="width: 140px;">Modified</th>
          <th style="width: 220px; text-align: center;">Actions</th>
        </tr>
      </thead>
      <tbody id="filesTableBody">
        <tr>
          <td colspan="6" class="empty-state">Loading large files...</td>
        </tr>
      </tbody>
    </table>
  </div>
  
  <div id="paginationBar" style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding: 0 4px;">
    <span id="pageInfoText" style="font-size: 13px; color: var(--text-secondary);">Showing 0 files</span>
    <div style="display: flex; gap: 8px;">
      <button id="btnPrevPage" class="btn btn-outline btn-sm" onclick="changePage(-1)" disabled>◀ Previous</button>
      <button id="btnNextPage" class="btn btn-outline btn-sm" onclick="changePage(1)">Next ▶</button>
    </div>
  </div>
</div>

<!-- Recycle Confirmation Modal -->
<div id="recycleModal" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <span>🗑️ Move to Recycle Bin?</span>
    </div>
    <div class="modal-body">
      Are you sure you want to move this file to your Windows Recycle Bin?
      <div class="modal-file-box">
        <div id="modalFileName" style="font-weight: 700; color: #fff;">filename.ext</div>
        <div id="modalFileSize" style="color: var(--accent); font-size: 13px; margin: 4px 0;">Size: 0 MB</div>
        <div id="modalFilePath" style="font-family: monospace; font-size: 11px; color: var(--text-secondary);">C:\path</div>
      </div>
      <p style="margin-top: 12px; font-size: 12px; color: var(--text-secondary);">
        💡 Safe delete: This file is sent to the Windows Recycle Bin, so you can restore it if you change your mind.
      </p>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" onclick="closeRecycleModal()">Cancel</button>
      <button id="btnConfirmRecycle" class="btn btn-danger" onclick="confirmRecycle()">Yes, Move to Recycle Bin</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div id="toast" class="toast">Action message</div>

<script>
let currentCategory = 'all';
let currentOffset = 0;
const pageSize = 100;
let totalMatches = 0;
let fileToRecycle = null;
let maxFileSizeFound = 1;
let pollTimer = null;

const CATEGORY_META = {
  'all': { name: 'All Files', icon: '📁' },
  'video': { name: 'Videos & Movies', icon: '🎬' },
  'archive': { name: 'Archives & ISOs', icon: '📦' },
  'installer': { name: 'Installers & Apps', icon: '💿' },
  'audio': { name: 'Audio & Music', icon: '🎵' },
  'image': { name: 'Images & Photos', icon: '🖼️' },
  'document': { name: 'Documents & PDFs', icon: '📄' },
  'database': { name: 'Databases & Backups', icon: '💾' },
  'other': { name: 'Other Large Files', icon: '📁' }
};

function showToast(message, type='success') {
  const t = document.getElementById('toast');
  t.textContent = message;
  t.className = 'toast show toast-' + type;
  setTimeout(() => {
    t.className = 'toast';
  }, 3500);
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    document.getElementById('statFilesScanned').textContent = data.files_scanned.toLocaleString();
    document.getElementById('statDirsScanned').textContent = data.dirs_scanned.toLocaleString();
    document.getElementById('statBytesScanned').textContent = data.total_bytes_str;
    document.getElementById('statLargeFilesCount').textContent = data.large_files_count.toLocaleString();
    document.getElementById('elapsedTimer').textContent = data.elapsed_seconds + 's';
    document.getElementById('currentFolderText').textContent = data.current_folder || 'C:\\';

    const statusBadge = document.getElementById('statusBadge');
    const progressBar = document.getElementById('progressBar');

    if (data.is_scanning) {
      statusBadge.textContent = '⏳ Scanning C:\\ Drive...';
      statusBadge.className = 'status-badge badge-scanning';
      progressBar.style.width = '70%';
      progressBar.classList.add('progress-pulse');
    } else {
      statusBadge.textContent = '✅ Scan Finished!';
      statusBadge.className = 'status-badge badge-done';
      progressBar.style.width = '100%';
      progressBar.classList.remove('progress-pulse');
      document.getElementById('shortcutsNotice').innerHTML = '📂 Shortcuts updated in <b style="color:#fff;">C:\\finder\\Shortcuts</b>';
    }

    renderCategoryPills(data.category_stats, data.large_files_count);

    if (data.is_scanning) {
      setTimeout(fetchStatus, 800);
    }
  } catch(e) {
    console.error("Status fetch failed", e);
  }
}

function renderCategoryPills(stats, totalCount) {
  const container = document.getElementById('categoryPills');
  let html = `<div class="cat-pill ${currentCategory === 'all' ? 'active' : ''}" onclick="selectCategory('all')">
    <span>🌟 All Categories</span>
    <span class="cat-size">${totalCount}</span>
  </div>`;

  if (stats) {
    for (const [catKey, catInfo] of Object.entries(stats)) {
      const active = currentCategory === catKey ? 'active' : '';
      html += `<div class="cat-pill ${active}" onclick="selectCategory('${catKey}')">
        <span>${catInfo.icon} ${catInfo.name}</span>
        <span class="cat-size">${catInfo.bytes_str} (${catInfo.count})</span>
      </div>`;
    }
  }
  container.innerHTML = html;
}

function selectCategory(cat) {
  currentCategory = cat;
  currentOffset = 0;
  loadFiles();
  fetchStatus();
}

let searchDebounce = null;
function onSearchChange() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentOffset = 0;
    loadFiles();
  }, 250);
}

function onFilterChange() {
  currentOffset = 0;
  loadFiles();
}

function changePage(direction) {
  currentOffset += direction * pageSize;
  if (currentOffset < 0) currentOffset = 0;
  loadFiles();
}

async function loadFiles() {
  const minSize = document.getElementById('sizeFilter').value;
  const sortBy = document.getElementById('sortFilter').value;
  const search = document.getElementById('searchInput').value;

  const url = `/api/files?category=${encodeURIComponent(currentCategory)}&min_size_mb=${minSize}&sort_by=${sortBy}&search=${encodeURIComponent(search)}&limit=${pageSize}&offset=${currentOffset}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    totalMatches = data.total_matches;
    renderTable(data.files, currentOffset);

    // Update pagination
    const startNum = totalMatches === 0 ? 0 : currentOffset + 1;
    const endNum = Math.min(currentOffset + data.files.length, totalMatches);
    document.getElementById('pageInfoText').textContent = `Showing ${startNum} - ${endNum} of ${totalMatches.toLocaleString()} files`;
    document.getElementById('btnPrevPage').disabled = currentOffset <= 0;
    document.getElementById('btnNextPage').disabled = endNum >= totalMatches;

  } catch(e) {
    console.error("Failed to load files", e);
  }
}

function renderTable(files, baseOffset) {
  const tbody = document.getElementById('filesTableBody');
  if (!files || files.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No files found matching the criteria.</td></tr>`;
    return;
  }

  if (baseOffset === 0 && files.length > 0) {
    maxFileSizeFound = files[0].size || 1;
  }

  let html = '';
  files.forEach((f, idx) => {
    const rank = baseOffset + idx + 1;
    const percent = Math.max(3, Math.min(100, (f.size / maxFileSizeFound) * 100));
    const catMeta = CATEGORY_META[f.category] || CATEGORY_META['other'];
    const safePath = encodeURIComponent(f.path);
    const safeName = f.name.replace(/'/g, "\\'");

    html += `
      <tr id="row-${rank}">
        <td><span class="rank-badge">#${rank}</span></td>
        <td class="file-name-cell">
          <div class="file-name" title="${f.name}">
            <span>${catMeta.icon}</span>
            <span>${f.name}</span>
          </div>
          <div class="file-meta">
            <span>Type: ${catMeta.name}</span>
            <span>•</span>
            <span>Ext: ${f.ext}</span>
          </div>
        </td>
        <td class="size-cell">
          <div class="size-text">${f.size_str}</div>
          <div class="size-bar-bg">
            <div class="size-bar-fill" style="width: ${percent}%;"></div>
          </div>
        </td>
        <td>
          <div class="file-path" title="${f.path}">${f.path}</div>
        </td>
        <td style="color: var(--text-secondary); font-size: 12px;">
          ${f.mtime_str || '-'}
        </td>
        <td>
          <div class="actions-cell">
            <button class="btn btn-outline btn-sm" onclick="revealInExplorer('${safePath}')" title="Highlight this file in Windows File Explorer">
              📂 Open
            </button>
            <button class="btn btn-danger btn-sm" onclick="promptRecycle('${safePath}', '${safeName}', '${f.size_str}', 'row-${rank}')" title="Safely move to Windows Recycle Bin">
              🗑️ Recycle
            </button>
          </div>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

async function revealInExplorer(encodedPath) {
  const path = decodeURIComponent(encodedPath);
  try {
    const res = await fetch('/api/reveal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path })
    });
    const d = await res.json();
    if (d.success) {
      showToast("Opened file in Windows Explorer", "success");
    } else {
      showToast("Could not open: " + d.error, "error");
    }
  } catch(e) {
    showToast("Request failed", "error");
  }
}

async function openShortcutsFolder() {
  try {
    await fetch('/api/open_shortcuts_folder', { method: 'POST' });
    showToast("Opened Shortcuts folder in File Explorer", "success");
  } catch(e) {
    showToast("Could not open shortcuts folder", "error");
  }
}

function promptRecycle(encodedPath, name, sizeStr, rowId) {
  const path = decodeURIComponent(encodedPath);
  fileToRecycle = { path: path, name: name, sizeStr: sizeStr, rowId: rowId };
  document.getElementById('modalFileName').textContent = name;
  document.getElementById('modalFileSize').textContent = "Size: " + sizeStr;
  document.getElementById('modalFilePath').textContent = path;
  document.getElementById('recycleModal').style.display = 'flex';
}

function closeRecycleModal() {
  document.getElementById('recycleModal').style.display = 'none';
  fileToRecycle = null;
}

async function confirmRecycle() {
  if (!fileToRecycle) return;
  const target = fileToRecycle;
  closeRecycleModal();

  try {
    const res = await fetch('/api/recycle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: target.path })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Recycled: ${target.name}`, 'success');
      const row = document.getElementById(target.rowId);
      if (row) {
        row.classList.add('recycled');
        const actions = row.querySelector('.actions-cell');
        if (actions) actions.innerHTML = '<span style="color:var(--success);font-weight:600;font-size:11px;">✓ Recycled</span>';
      }
      fetchStatus();
    } else {
      showToast(`Failed: ${data.error}`, 'error');
    }
  } catch(e) {
    showToast("Recycle request error", "error");
  }
}

async function triggerRescan() {
  if (confirm("Do you want to re-scan the entire C: drive now?")) {
    await fetch('/api/rescan', { method: 'POST' });
    showToast("Rescan started!", "success");
    fetchStatus();
    setTimeout(loadFiles, 1000);
  }
}

// Initial boot
fetchStatus();
loadFiles();
setInterval(loadFiles, 3000);
</script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        elif parsed.path == '/api/status':
            status = scanner.get_status()
            self._send_json(status)
        elif parsed.path == '/api/files':
            qs = parse_qs(parsed.query)
            cat = qs.get('category', ['all'])[0]
            min_size = int(qs.get('min_size_mb', [0])[0])
            search = qs.get('search', [''])[0]
            limit = int(qs.get('limit', [200])[0])
            offset = int(qs.get('offset', [0])[0])
            sort_by = qs.get('sort_by', ['size_desc'])[0]

            res = scanner.query_files(category=cat, min_size_mb=min_size, search=search, limit=limit, offset=offset, sort_by=sort_by)
            self._send_json(res)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            data = {}

        if parsed.path == '/api/reveal':
            file_path = data.get('path', '')
            if file_path and os.path.exists(file_path):
                try:
                    subprocess.Popen(['explorer.exe', f'/select,{os.path.normpath(file_path)}'])
                    self._send_json({'success': True})
                except Exception as e:
                    self._send_json({'success': False, 'error': str(e)})
            else:
                self._send_json({'success': False, 'error': 'File not found'})

        elif parsed.path == '/api/recycle':
            file_path = data.get('path', '')
            if not file_path:
                self._send_json({'success': False, 'error': 'Missing file path'})
                return

            success, msg = send_to_recycle_bin(file_path)
            if success:
                scanner.remove_file_record(file_path)
                self._send_json({'success': True})
            else:
                self._send_json({'success': False, 'error': msg})

        elif parsed.path == '/api/open_shortcuts_folder':
            os.makedirs(SHORTCUTS_DIR, exist_ok=True)
            subprocess.Popen(['explorer.exe', os.path.normpath(SHORTCUTS_DIR)])
            self._send_json({'success': True})

        elif parsed.path == '/api/rescan':
            scanner.start_scan()
            threading.Thread(target=auto_generate_shortcuts, daemon=True).start()
            self._send_json({'success': True})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, obj):
        content = json.dumps(obj).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        # Silence routine HTTP access logging in the terminal
        return

def find_available_port(start_port=58234):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
            port += 1
    return start_port

def main():
    print("=" * 70)
    print("      C: DRIVE LARGE FILE FINDER & RANKER")
    print("=" * 70)
    print("Starting background scanner on Drive C:\\ ...")
    
    # 1. Start scanner
    scanner.start_scan()

    # 2. Start shortcut auto-generator thread
    threading.Thread(target=auto_generate_shortcuts, daemon=True).start()

    # 3. Start web server
    port = find_available_port()
    server = HTTPServer(('127.0.0.1', port), RequestHandler)
    url = f"http://127.0.0.1:{port}"

    print(f"[+] Web Dashboard running at: {url}")
    print(f"[+] Shortcuts will be saved at: {SHORTCUTS_DIR}")
    print("=" * 70)
    print("Opening web dashboard in your default browser...")
    print("Press Ctrl+C in this window anytime to exit.")
    print("=" * 70)

    # Launch browser after a brief pause
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nExiting program...")
        scanner.stop_scan()
        server.server_close()

if __name__ == '__main__':
    main()
