/* =========================================================
   Attend-X — Frontend Logic  (ES6+, no dependencies)

   Auth model:
     Page 1 – Mark Attendance: NO password, Unique ID + face match
     Page 2 – Register:        Employee Access Code ONLY
     Page 3 – Admin Dashboard: Manager Access Code ONLY
   ========================================================= */
'use strict';

// ── Tiny DOM helpers ──────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);

async function apiFetch(url, body) {
  const r = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  return r.json();
}

function showAlert(el, msg, type = 'error') {
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.style.display = 'block';
}
function hideAlert(el) { if (el) { el.style.display = 'none'; el.textContent = ''; } }

// ── Theme Management ─────────────────────────────────────────────────────────────
function initTheme() {
  const btn = $('#theme-toggle-btn');
  const icon = $('#theme-icon');
  
  const sunIcon = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;
  const moonIcon = `<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>`;

  function setTheme(isDark) {
    if (isDark) {
      document.body.classList.add('dark-theme');
      if (icon) icon.innerHTML = moonIcon;
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.remove('dark-theme');
      if (icon) icon.innerHTML = sunIcon;
      localStorage.setItem('theme', 'light');
    }
  }

  // Initial load
  const saved = localStorage.getItem('theme');
  if (saved === 'dark') setTheme(true);
  else if (saved === 'light') setTheme(false);
  else setTheme(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);

  if (btn) {
    btn.addEventListener('click', () => {
      setTheme(!document.body.classList.contains('dark-theme'));
    });
  }
}

// ── Navigation ─────────────────────────────────────────────────────────────────
function initNav() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#page-${btn.dataset.page}`).classList.add('active');
    });
  });

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

// ── Camera helpers ─────────────────────────────────────────────────────────────
async function startCamera(videoEl) {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
    audio: false,
  });
  videoEl.srcObject = stream;
  await new Promise(res => { videoEl.onloadedmetadata = res; });
  videoEl.play();
  return stream;
}

function stopCamera(stream) {
  if (stream) stream.getTracks().forEach(t => t.stop());
}

function captureFrame(videoEl, canvasEl, quality = 0.85) {
  canvasEl.width  = videoEl.videoWidth  || 640;
  canvasEl.height = videoEl.videoHeight || 480;
  canvasEl.getContext('2d').drawImage(videoEl, 0, 0);
  return canvasEl.toDataURL('image/jpeg', quality).split(',')[1]; // base64 only
}

// ═════════════════════════════════════════════════════════════════════════════
// PAGE 1: Mark Attendance
// No password prompt. Flow: Enter UID → check UID exists → open camera
// → send frames → check if detected face matches THIS UID's stored encoding
// ═════════════════════════════════════════════════════════════════════════════
function initAttendance() {
  const uidInput    = $('#att-uid');
  const errEl       = $('#att-uid-err');
  const startBtn    = $('#att-start-btn');
  const stopBtn     = $('#att-stop-btn');
  const camSection  = $('#att-camera-section');
  const resultsEl   = $('#att-results');
  const resultsList = $('#att-results-list');
  const scanLabel   = $('#att-scan-label');
  const video       = $('#att-video');
  const canvas      = $('#att-canvas');

  let cameraStream    = null;
  let recogTimer      = null;
  let timeoutTimer    = null;
  let recogBusy       = false;  // prevent concurrent recognition calls

  // Add a result item to the recognition log
  function logResult(msg, type) {
    const div = document.createElement('div');
    div.className = `result-item ${type}`;
    div.innerHTML = `<span class="result-dot"></span><span>${msg}</span>`;
    resultsList.prepend(div);
    resultsEl.style.display = 'block';
  }

  // Fully stop camera and reset UI
  function stopSession() {
    clearInterval(recogTimer); recogTimer = null;
    clearTimeout(timeoutTimer); timeoutTimer = null;
    recogBusy = false;
    stopCamera(cameraStream); cameraStream = null;
    camSection.style.display = 'none';
    stopBtn.style.display    = 'none';
    startBtn.style.display   = 'inline-flex';
    startBtn.disabled        = false;
  }

  // One recognition cycle
  async function runFrame() {
    if (!cameraStream || recogBusy) return;
    recogBusy = true;

    try {
      const uid      = uidInput.value.trim();
      const frameB64 = captureFrame(video, canvas);
      const data     = await apiFetch('/api/process-frame', { target_uid: uid, frame_b64: frameB64 });

      switch (data.result) {
        case 'no_face':
          scanLabel.textContent = 'Scanning for face…';
          break;

        case 'liveness_pending':
          scanLabel.textContent = data.message || 'Please blink to verify...';
          break;

        case 'mismatch':
          scanLabel.textContent = 'Face does not match';
          logResult(data.message, 'error');
          // Stop immediately — clear mismatch, don't keep scanning
          stopSession();
          break;

        case 'no_encoding':
          scanLabel.textContent = 'No face data for this ID';
          logResult(data.message, 'error');
          stopSession();
          break;

        case 'match':
          scanLabel.textContent = `Recognised: ${data.name}`;
          logResult(data.message, data.already_done ? 'warn' : 'success');
          // Stop after marking (success or already-done)
          stopSession();
          break;
      }
    } catch (_) { /* network hiccup — continue next cycle */ }

    recogBusy = false;
  }

  // Start button
  startBtn.addEventListener('click', async () => {
    const uid = uidInput.value.trim();
    if (!uid) {
      showAlert(errEl, 'Please enter your Unique Employee ID.');
      return;
    }

    hideAlert(errEl);
    startBtn.disabled    = true;
    startBtn.textContent = 'Checking ID…';

    // Test 1: verify UID exists before opening camera
    const check = await apiFetch('/api/check-uid', { uid });
    startBtn.textContent = 'Start Attendance';

    if (!check.exists) {
      showAlert(errEl, check.message);
      startBtn.disabled = false;
      return;
    }

    // Open camera
    try {
      cameraStream = await startCamera(video);
    } catch (e) {
      showAlert(errEl, `Camera access denied: ${e.message}`);
      startBtn.disabled = false;
      return;
    }

    camSection.style.display = 'block';
    startBtn.style.display   = 'none';
    stopBtn.style.display    = 'inline-flex';
    scanLabel.textContent    = 'Scanning for face…';

    // 10 second hard timeout
    timeoutTimer = setTimeout(() => {
      if (cameraStream) {
        scanLabel.textContent = 'Timeout: No face detected';
        logResult('Could not detect a face within the time limit. Please try again.', 'error');
        stopSession();
      }
    }, 10000);

    // Run recognition every 1.5 s; also fire immediately after 1 s warm-up
    recogTimer = setInterval(runFrame, 1500);
    setTimeout(runFrame, 1000);
  });

  // Stop button
  stopBtn.addEventListener('click', stopSession);

  // Clear error on typing
  uidInput.addEventListener('input', () => hideAlert(errEl));
}


// ═════════════════════════════════════════════════════════════════════════════
// PAGE 2: Register New Employee
// Requires COMMON EMPLOYEE ACCESS CODE only.
// Manager code must be rejected explicitly.
// ═════════════════════════════════════════════════════════════════════════════
function initRegister() {
  const codeInput   = $('#reg-emp-code');
  const codeErrEl   = $('#reg-code-err');
  const detailsDiv  = $('#reg-details');
  const openCamBtn  = $('#reg-open-cam-btn');
  const camSection  = $('#reg-camera-section');
  const captureBtn  = $('#reg-capture-btn');
  const cancelBtn   = $('#reg-cancel-cam-btn');
  const resultEl    = $('#reg-result');
  const video       = $('#reg-video');
  const canvas      = $('#reg-canvas');
  let   cameraStream = null;
  let   codeVerified = false;

  // Show employee details section once a code is typed (before verifying)
  codeInput.addEventListener('input', () => {
    hideAlert(codeErrEl);
    hideAlert(resultEl);
    codeVerified = false;
    detailsDiv.style.display = codeInput.value.length > 0 ? 'block' : 'none';
  });

  // "Open Camera" — verify code then open camera
  openCamBtn.addEventListener('click', async () => {
    const code = codeInput.value.trim();
    const uid  = $('#reg-uid').value.trim();
    const name = $('#reg-name').value.trim();

    hideAlert(codeErrEl);

    if (!uid || !name) {
      showAlert(codeErrEl, 'Please enter both Unique Employee ID and Full Name.');
      return;
    }

    // Verify employee access code server-side
    openCamBtn.disabled    = true;
    openCamBtn.textContent = 'Verifying…';
    const verify = await apiFetch('/api/verify-employee', { employee_code: code });
    openCamBtn.disabled    = false;
    openCamBtn.textContent = 'Open Camera';

    if (!verify.success) {
      showAlert(codeErrEl, verify.message || 'Incorrect Employee Access Code.');
      return;
    }

    codeVerified = true;

    // Open camera
    try {
      cameraStream = await startCamera(video);
    } catch (e) {
      showAlert(codeErrEl, `Camera access denied: ${e.message}`);
      return;
    }

    camSection.style.display = 'block';
    openCamBtn.style.display = 'none';
  });

  // "Capture Face"
  captureBtn.addEventListener('click', async () => {
    if (!codeVerified) {
      showAlert(codeErrEl, 'Please verify your Employee Access Code first.');
      return;
    }

    const uid  = $('#reg-uid').value.trim();
    const name = $('#reg-name').value.trim();
    const code = codeInput.value.trim();

    if (!uid || !name) {
      showAlert(codeErrEl, 'Please enter Unique Employee ID and Full Name.');
      return;
    }

    captureBtn.disabled    = true;
    captureBtn.textContent = 'Processing…';

    const frameB64 = captureFrame(video, canvas);
    const data = await apiFetch('/api/capture-register-frame', {
      employee_code: code, uid, name, frame_b64: frameB64,
    });

    captureBtn.disabled    = false;
    captureBtn.textContent = 'Capture Face';

    showAlert(resultEl, data.message, data.success ? 'success' : 'error');

    if (data.success) {
      stopCamera(cameraStream); cameraStream = null;
      cameraStream   = null;
      codeVerified   = false;
      camSection.style.display = 'none';
      openCamBtn.style.display = 'block';
      // Reset form
      codeInput.value      = '';
      $('#reg-uid').value  = '';
      $('#reg-name').value = '';
      detailsDiv.style.display = 'none';
    }
  });

  // "Cancel" camera
  cancelBtn.addEventListener('click', () => {
    stopCamera(cameraStream); cameraStream = null;
    camSection.style.display = 'none';
    openCamBtn.style.display = 'block';
  });
}


// ═════════════════════════════════════════════════════════════════════════════
// PAGE 3: Admin Dashboard
// Requires MANAGER ACCESS CODE only.
// Employee Access Code returns a clear rejection message.
// ═════════════════════════════════════════════════════════════════════════════
let _managerCode  = '';
let _searchData   = [];
let _monthlyData  = [];
let _todayData    = [];

function initDashboard() {
  const mgrInput = $('#dash-mgr-code');
  const authBtn  = $('#dash-auth-btn');
  const errEl    = $('#dash-auth-err');
  const authCard = $('#dash-auth-card');
  const content  = $('#dash-content');

  authBtn.addEventListener('click', async () => {
    const code = mgrInput.value.trim();
    if (!code) { showAlert(errEl, 'Please enter the Manager Access Code.'); return; }

    hideAlert(errEl);
    authBtn.disabled    = true;
    authBtn.textContent = 'Verifying…';

    const data = await apiFetch('/api/dashboard/verify', { manager_code: code });
    authBtn.disabled    = false;
    authBtn.textContent = 'Unlock Dashboard';

    if (!data.success) {
      // Shows "Manager access required. The Employee Access Code cannot unlock this page."
      // if employee code was entered, or generic wrong-code message.
      showAlert(errEl, data.message || 'Incorrect Manager Access Code.');
      return;
    }

    _managerCode = code;

    // Animated reveal
    authCard.style.cssText = 'opacity:0;transform:translateY(-8px);transition:all 0.28s ease;';
    setTimeout(() => {
      authCard.style.display = 'none';
      content.style.cssText  = 'display:block;opacity:0;transform:translateY(10px);transition:all 0.32s ease;';
      requestAnimationFrame(() => requestAnimationFrame(() => {
        content.style.opacity   = '1';
        content.style.transform = 'translateY(0)';
      }));
      loadTodayData();
    }, 280);
  });

  $('#dash-lock-btn').addEventListener('click', () => {
    _managerCode = null;
    mgrInput.value = '';
    
    // Animated hide of content and reveal of auth card
    content.style.cssText = 'display:block;opacity:1;transform:translateY(0);transition:all 0.28s ease;';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      content.style.opacity   = '0';
      content.style.transform = 'translateY(10px)';
      
      setTimeout(() => {
        content.style.display = 'none';
        authCard.style.cssText = 'display:block;opacity:0;transform:translateY(-8px);transition:all 0.32s ease;';
        requestAnimationFrame(() => requestAnimationFrame(() => {
          authCard.style.opacity   = '1';
          authCard.style.transform = 'translateY(0)';
        }));
      }, 280);
    }));
  });

  mgrInput.addEventListener('keydown', e => { if (e.key === 'Enter') authBtn.click(); });
  mgrInput.addEventListener('input',   () => hideAlert(errEl));

  // ── Today ────────────────────────────────────────────────
  async function loadTodayData() {
    const data = await apiFetch('/api/dashboard/today', { manager_code: _managerCode });
    if (!data.success) return;
    const m = data.metrics;
    $('#kpi-total').textContent   = m.total;
    $('#kpi-present').textContent = m.present;
    $('#kpi-late').textContent    = m.late;
    $('#kpi-absent').textContent  = m.absent;
    _todayData = data.records;
    renderTable(data.records, $('#today-table-wrap'));
  }

  $('#export-today-btn').addEventListener('click',
    () => exportCSV(_todayData, 'today_attendance.csv'));

  // ── Search ───────────────────────────────────────────────
  const searchBy      = $('#search-by');
  const searchValWrap = $('#search-val-wrap');
  const dateRangeWrap = $('#date-range-wrap');

  searchBy.addEventListener('change', () => {
    const isDate = searchBy.value === 'date';
    searchValWrap.style.display = isDate ? 'none'  : '';
    dateRangeWrap.style.display = isDate ? 'flex'  : 'none';
  });

  $('#search-btn').addEventListener('click', async () => {
    const by   = searchBy.value;
    const body = { manager_code: _managerCode, search_type: by };
    if (by === 'date') {
      body.start_date = $('#date-start').value;
      body.end_date   = $('#date-end').value;
    } else {
      body.search_val = $('#search-val').value.trim();
    }
    const data = await apiFetch('/api/dashboard/search', body);
    _searchData = data.records || [];
    renderTable(_searchData, $('#search-table-wrap'));
    $('#export-search-btn').style.display = _searchData.length ? '' : 'none';
  });

  $('#export-search-btn').addEventListener('click',
    () => exportCSV(_searchData, 'search_results.csv'));

  // ── Monthly ──────────────────────────────────────────────
  $('#month-btn').addEventListener('click', async () => {
    const month = $('#month-input').value;
    if (!month) return;
    const data = await apiFetch('/api/dashboard/monthly', { manager_code: _managerCode, month });
    _monthlyData = data.records || [];
    renderTable(_monthlyData, $('#monthly-table-wrap'));
    $('#export-month-btn').style.display = _monthlyData.length ? '' : 'none';
  });

  $('#export-month-btn').addEventListener('click', () => {
    exportCSV(_monthlyData, `summary_${$('#month-input').value || 'export'}.csv`);
  });
  // ── Leaves ──────────────────────────────────────────────
  async function loadLeavesData() {
    const data = await apiFetch('/api/dashboard/leaves', { manager_code: _managerCode });
    if (data.success) renderTable(data.records || [], $('#leaves-table-wrap'));
  }
  
  $('#add-leave-btn').addEventListener('click', async () => {
    const uid = $('#leave-uid').value.trim();
    const date = $('#leave-date').value;
    const type = $('#leave-type').value;
    if (!uid || !date) { alert('Please provide UID and Date.'); return; }
    
    const btn = $('#add-leave-btn');
    btn.disabled = true;
    const res = await apiFetch('/api/dashboard/leaves/add', { manager_code: _managerCode, uid, date, leave_type: type });
    if (res.success) {
      alert('Leave/Holiday added successfully.');
      loadLeavesData();
    } else {
      alert(res.message || 'Error adding leave.');
    }
    btn.disabled = false;
  });

  // ── Employees ────────────────────────────────────────────
  async function loadEmployeesData() {
    const data = await apiFetch('/api/dashboard/employees', { manager_code: _managerCode });
    if (data.success) renderEmployeesTable(data.records || [], $('#employees-table-wrap'));
  }
  
  // Custom render for employees to add edit/delete buttons
  function renderEmployeesTable(records, wrap) {
    if (!records || records.length === 0) {
      wrap.innerHTML = '<div class="alert" style="display:block">No employees found.</div>';
      return;
    }
    const cols = Object.keys(records[0]);
    const heads = cols.map(c => `<th>${fmtCol(c)}</th>`).join('') + '<th>Actions</th>';
    const rows = records.map(r => {
      const cells = cols.map(c => `<td>${r[c]}</td>`).join('');
      const acts = `<td>
        <button class="btn btn-outline btn-sm edit-emp-btn" data-uid="${r.unique_id}" data-name="${r.name}" style="padding:4px 8px; font-size:11px">Edit</button>
        <button class="btn btn-primary btn-sm del-emp-btn" data-uid="${r.unique_id}" style="padding:4px 8px; font-size:11px; background:var(--red); border-color:var(--red)">Delete</button>
      </td>`;
      return `<tr>${cells}${acts}</tr>`;
    }).join('');
    wrap.innerHTML = `<div class="table-wrap"><table><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
    
    // Bind actions
    wrap.querySelectorAll('.edit-emp-btn').forEach(b => {
      b.addEventListener('click', async () => {
        const uid = b.dataset.uid;
        const oldName = b.dataset.name;
        const newName = prompt(`Enter new name for ${uid}:`, oldName);
        if (newName && newName !== oldName) {
          const res = await apiFetch('/api/dashboard/employees/update', { manager_code: _managerCode, uid, new_name: newName });
          if (res.success) loadEmployeesData();
          else alert('Error updating employee.');
        }
      });
    });
    wrap.querySelectorAll('.del-emp-btn').forEach(b => {
      b.addEventListener('click', async () => {
        const uid = b.dataset.uid;
        if (confirm(`Are you sure you want to delete employee ${uid}? This will also delete their face data.`)) {
          const res = await apiFetch('/api/dashboard/employees/delete', { manager_code: _managerCode, uid });
          if (res.success) loadEmployeesData();
          else alert('Error deleting employee.');
        }
      });
    });
  }

  // Hook into tab clicks to load data lazily
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.tab === 'leaves') loadLeavesData();
      if (btn.dataset.tab === 'employees') loadEmployeesData();
    });
  });
}

// ── Table rendering ───────────────────────────────────────────────────────────
function renderTable(records, wrap) {
  if (!records || records.length === 0) {
    wrap.innerHTML = `
      <div class="empty-state">
        <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"
             style="display:block;margin:0 auto 10px;opacity:.35">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        No records found.
      </div>`;
    return;
  }
  const cols  = Object.keys(records[0]);
  const heads = cols.map(c => `<th>${fmtCol(c)}</th>`).join('');
  const rows  = records.map(r => {
    const cells = cols.map(c => {
      const v = r[c] ?? '—';
      return c === 'status' ? `<td>${statusBadge(v)}</td>` : `<td>${v}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  wrap.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr>${heads}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function fmtCol(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function statusBadge(s) {
  const cls = { present: 'badge-present', late: 'badge-late',
                absent: 'badge-absent' }[(s || '').toLowerCase()] || 'badge-incomplete';
  return `<span class="badge ${cls}">${s || '—'}</span>`;
}

// ── CSV export ─────────────────────────────────────────────────────────────────
function exportCSV(data, filename) {
  if (!data || !data.length) return;
  const cols = Object.keys(data[0]);
  const rows = [cols.join(','), ...data.map(r => cols.map(c => `"${r[c] ?? ''}"`).join(','))];
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
  Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob), download: filename,
  }).click();
}

// ── Bootstrap ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNav();
  initAttendance();
  initRegister();
  initDashboard();
});
