/* =========================================================
   Attend-X — Frontend Logic  (ES6+, no dependencies)

   Auth model:
     Page 1 – Mark Attendance:  NO password; Unique ID + face match
     Page 2 – Register:         Employee Access Code ONLY
     Page 3 – Admin Dashboard:  Manager Access Code ONLY
   ========================================================= */
'use strict';

// ── DOM helpers ───────────────────────────────────────────────────────────────
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
function hideAlert(el) {
  if (el) { el.style.display = 'none'; el.textContent = ''; }
}

// ── Theme ─────────────────────────────────────────────────────────────────────
function initTheme() {
  const btn  = $('#theme-toggle-btn');
  const icon = $('#theme-icon');

  const moonPath = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;
  const sunPaths = `<circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>`;

  function setTheme(dark) {
    document.body.classList.toggle('dark-theme', dark);
    if (icon) icon.innerHTML = dark ? sunPaths : moonPath;
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }

  const saved = localStorage.getItem('theme');
  if (saved) setTheme(saved === 'dark');
  else setTheme(window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false);

  btn?.addEventListener('click', () => setTheme(!document.body.classList.contains('dark-theme')));
}

// ── Navigation ────────────────────────────────────────────────────────────────
function initNav() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#page-${btn.dataset.page}`)?.classList.add('active');
    });
  });

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#tab-${btn.dataset.tab}`)?.classList.add('active');
    });
  });
}

// ── Camera helpers ────────────────────────────────────────────────────────────
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
  return canvasEl.toDataURL('image/jpeg', quality).split(',')[1];
}

// ═════════════════════════════════════════════════════════════════════════════
// PAGE 1: Mark Attendance
// NO password at all. Flow: Enter UID → check UID exists → open camera →
// send frames → compare face against THIS UID's stored encoding → mark
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

  let cameraStream = null;
  let recogTimer   = null;
  let timeoutTimer = null;
  let recogBusy    = false;
  let currentUid   = '';

  function logResult(msg, type) {
    const div = document.createElement('div');
    div.className = `result-item ${type}`;
    div.innerHTML = `<span class="result-dot"></span><span>${msg}</span>`;
    resultsList.prepend(div);
    resultsEl.style.display = 'block';
  }

  function resetUIAfterStop() {
    stopCamera(cameraStream); cameraStream = null;
    clearInterval(recogTimer); recogTimer = null;
    clearTimeout(timeoutTimer); timeoutTimer = null;
    recogBusy = false;
    camSection.style.display = 'none';
    stopBtn.style.display    = 'none';
    startBtn.style.display   = 'inline-flex';
    startBtn.disabled        = false;
    startBtn.innerHTML = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
      </svg>
      Start Attendance`;
  }

  async function runFrame() {
    if (!cameraStream || recogBusy) return;
    recogBusy = true;
    try {
      const frameB64 = captureFrame(video, canvas);
      const data     = await apiFetch('/api/process-frame', {
        target_uid: currentUid,
        frame_b64:  frameB64,
      });

      switch (data.result) {
        case 'no_face':
          // Keep scanning — do nothing, label stays "Scanning for face..."
          break;

        case 'mismatch':
          // Stop immediately on mismatch
          clearInterval(recogTimer); recogTimer = null;
          clearTimeout(timeoutTimer); timeoutTimer = null;
          scanLabel.textContent = 'Face does not match';
          logResult(data.message, 'error');
          setTimeout(resetUIAfterStop, 2000);
          break;

        case 'no_encoding':
          clearInterval(recogTimer); recogTimer = null;
          clearTimeout(timeoutTimer); timeoutTimer = null;
          scanLabel.textContent = 'No face data on file';
          logResult(data.message, 'error');
          setTimeout(resetUIAfterStop, 2000);
          break;

        case 'match':
          clearInterval(recogTimer); recogTimer = null;
          clearTimeout(timeoutTimer); timeoutTimer = null;
          scanLabel.textContent = `Recognised: ${data.name}`;
          logResult(data.message, data.already_done ? 'warn' : 'success');
          setTimeout(resetUIAfterStop, 2500);
          break;
      }
    } catch (_) { /* network hiccup — continue */ }
    recogBusy = false;
  }

  startBtn.addEventListener('click', async () => {
    const uid = uidInput.value.trim();
    if (!uid) {
      showAlert(errEl, 'Please enter your Unique Employee ID.');
      return;
    }

    hideAlert(errEl);
    startBtn.disabled    = true;
    startBtn.textContent = 'Checking ID…';

    const check = await apiFetch('/api/check-uid', { uid });
    if (!check.exists) {
      showAlert(errEl, check.message);
      startBtn.disabled    = false;
      startBtn.textContent = 'Start Attendance';
      startBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
        </svg>
        Start Attendance`;
      return;
    }

    currentUid = uid;
    try {
      cameraStream = await startCamera(video);
    } catch (e) {
      showAlert(errEl, `Camera access denied: ${e.message}`);
      startBtn.disabled = false;
      startBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
        </svg>
        Start Attendance`;
      return;
    }

    camSection.style.display = 'block';
    startBtn.style.display   = 'none';
    stopBtn.style.display    = 'inline-flex';
    scanLabel.textContent    = 'Scanning for face…';

    // 30 second hard timeout — prevents indefinite hang
    timeoutTimer = setTimeout(() => {
      if (cameraStream) {
        scanLabel.textContent = 'Timed out — no face detected';
        logResult('Could not detect a face within 30 seconds. Please try again.', 'error');
        resetUIAfterStop();
      }
    }, 30000);

    // Run recognition every 1.2 seconds; first attempt after 1 second (camera warm-up)
    setTimeout(runFrame, 1000);
    recogTimer = setInterval(runFrame, 1200);
  });

  stopBtn.addEventListener('click', resetUIAfterStop);
  uidInput.addEventListener('input', () => hideAlert(errEl));
}


// ═════════════════════════════════════════════════════════════════════════════
// PAGE 2: Register New Employee
// Requires COMMON EMPLOYEE ACCESS CODE only.
// Manager code is explicitly rejected.
// Unique ID: any non-empty string (numeric, alphabetic, or mixed).
// ═════════════════════════════════════════════════════════════════════════════
function initRegister() {
  const codeInput  = $('#reg-emp-code');
  const codeErrEl  = $('#reg-code-err');
  const detailsDiv = $('#reg-details');
  const openCamBtn = $('#reg-open-cam-btn');
  const camSection = $('#reg-camera-section');
  const captureBtn = $('#reg-capture-btn');
  const cancelBtn  = $('#reg-cancel-cam-btn');
  const resultEl   = $('#reg-result');
  const video      = $('#reg-video');
  const canvas     = $('#reg-canvas');
  let cameraStream = null;
  let codeVerified = false;

  codeInput.addEventListener('input', () => {
    hideAlert(codeErrEl);
    hideAlert(resultEl);
    codeVerified = false;
    detailsDiv.style.display = codeInput.value.length > 0 ? 'block' : 'none';
  });

  openCamBtn.addEventListener('click', async () => {
    const code = codeInput.value.trim();
    const uid  = $('#reg-uid').value.trim();
    const name = $('#reg-name').value.trim();

    hideAlert(codeErrEl);

    if (!uid)  { showAlert(codeErrEl, 'Please enter the Unique Employee ID.'); return; }
    if (!name) { showAlert(codeErrEl, 'Please enter the Employee Full Name.'); return; }

    openCamBtn.disabled    = true;
    openCamBtn.textContent = 'Verifying…';
    const verify = await apiFetch('/api/verify-employee', { employee_code: code });
    openCamBtn.disabled    = false;
    openCamBtn.innerHTML   = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
      Open Camera`;

    if (!verify.success) {
      showAlert(codeErrEl, verify.message || 'Incorrect Employee Access Code.');
      return;
    }

    codeVerified = true;
    try {
      cameraStream = await startCamera(video);
    } catch (e) {
      showAlert(codeErrEl, `Camera access denied: ${e.message}`);
      return;
    }
    camSection.style.display = 'block';
    openCamBtn.style.display = 'none';
  });

  captureBtn.addEventListener('click', async () => {
    if (!codeVerified) {
      showAlert(codeErrEl, 'Please verify your Employee Access Code first.');
      return;
    }

    const uid  = $('#reg-uid').value.trim();
    const name = $('#reg-name').value.trim();
    const code = codeInput.value.trim();

    if (!uid)  { showAlert(codeErrEl, 'Please enter the Unique Employee ID.'); return; }
    if (!name) { showAlert(codeErrEl, 'Please enter the Employee Full Name.'); return; }

    captureBtn.disabled    = true;
    captureBtn.textContent = 'Processing…';

    const frameB64 = captureFrame(video, canvas);
    const data = await apiFetch('/api/capture-register-frame', {
      employee_code: code, uid, name, frame_b64: frameB64,
    });

    captureBtn.disabled  = false;
    captureBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/>
      </svg>
      Capture Face`;

    showAlert(resultEl, data.message, data.success ? 'success' : 'error');

    if (data.success) {
      stopCamera(cameraStream); cameraStream = null;
      codeVerified = false;
      camSection.style.display = 'none';
      openCamBtn.style.display = 'block';
      codeInput.value       = '';
      $('#reg-uid').value   = '';
      $('#reg-name').value  = '';
      detailsDiv.style.display = 'none';
    }
  });

  cancelBtn.addEventListener('click', () => {
    stopCamera(cameraStream); cameraStream = null;
    camSection.style.display = 'none';
    openCamBtn.style.display = 'block';
  });
}


// ═════════════════════════════════════════════════════════════════════════════
// PAGE 3: Admin Dashboard
// Requires MANAGER ACCESS CODE only — separate from Employee code.
// ═════════════════════════════════════════════════════════════════════════════
let _managerCode = '';
let _todayData   = [];
let _searchData  = [];
let _monthlyData = [];
let _detailData  = { rows: [], days: [] };

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
      showAlert(errEl, data.message || 'Incorrect Manager Access Code.');
      return;
    }

    _managerCode = code;
    authCard.style.display = 'none';
    content.style.display  = 'block';
    loadTodayData();
  });

  $('#dash-lock-btn').addEventListener('click', () => {
    _managerCode = '';
    mgrInput.value = '';
    content.style.display  = 'none';
    authCard.style.display = 'block';
    hideAlert(errEl);
  });

  mgrInput.addEventListener('keydown', e => { if (e.key === 'Enter') authBtn.click(); });
  mgrInput.addEventListener('input',   () => hideAlert(errEl));

  // ── Today's Roster ────────────────────────────────────────
  async function loadTodayData() {
    const data = await apiFetch('/api/dashboard/today', { manager_code: _managerCode });
    if (!data.success) return;
    const m = data.metrics;
    $('#kpi-total').textContent   = m.total;
    $('#kpi-present').textContent = m.present;
    $('#kpi-late').textContent    = m.late;
    $('#kpi-absent').textContent  = m.absent;
    _todayData = data.records;
    renderTable(_todayData, $('#today-table-wrap'));
  }

  $('#export-today-btn').addEventListener('click',
    () => exportCSV(_todayData, 'today_attendance.csv'));

  // ── Search Records ────────────────────────────────────────
  const searchBy      = $('#search-by');
  const searchValWrap = $('#search-val-wrap');
  const dateRangeWrap = $('#date-range-wrap');

  searchBy.addEventListener('change', () => {
    const isDate = searchBy.value === 'date';
    searchValWrap.style.display = isDate ? 'none' : '';
    dateRangeWrap.style.display = isDate ? 'flex' : 'none';
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

  // ── Monthly Summary + Day-by-Day Detail ───────────────────
  $('#month-btn').addEventListener('click', async () => {
    const month = $('#month-input').value;
    if (!month) { alert('Please select a month first.'); return; }

    const btnEl = $('#month-btn');
    btnEl.disabled    = true;
    btnEl.textContent = 'Loading…';

    $('#monthly-summary-section').style.display = 'none';
    $('#monthly-empty').style.display            = 'none';
    $('#monthly-table-wrap').innerHTML           = '';
    $('#monthly-detail-wrap').innerHTML          = '';

    const [sumData, detData] = await Promise.all([
      apiFetch('/api/dashboard/monthly',        { manager_code: _managerCode, month }),
      apiFetch('/api/dashboard/monthly-detail', { manager_code: _managerCode, month }),
    ]);

    btnEl.disabled    = false;
    btnEl.textContent = 'Generate Report';

    _monthlyData = sumData.records || [];
    _detailData  = { rows: detData.rows || [], days: detData.days || [] };

    const hasData = _monthlyData.length > 0 || _detailData.rows.length > 0;

    if (!hasData) {
      $('#monthly-empty').style.display = 'block';
      return;
    }

    $('#monthly-summary-section').style.display = 'block';
    renderTable(_monthlyData, $('#monthly-table-wrap'));
    renderMonthlyDetail(_detailData.rows, _detailData.days, $('#monthly-detail-wrap'));
  });

  $('#export-month-btn').addEventListener('click', () =>
    exportCSV(_monthlyData, `monthly_summary_${$('#month-input').value || 'export'}.csv`));

  $('#export-detail-btn').addEventListener('click', () =>
    exportMonthlyDetailCSV(_detailData.rows, _detailData.days,
      `monthly_detail_${$('#month-input').value || 'export'}.csv`));

  // ── Manage Leaves ─────────────────────────────────────────
  async function loadLeavesData() {
    const data = await apiFetch('/api/dashboard/leaves', { manager_code: _managerCode });
    if (data.success) renderTable(data.records || [], $('#leaves-table-wrap'));
  }

  $('#add-leave-btn').addEventListener('click', async () => {
    const uid  = $('#leave-uid').value.trim();
    const date = $('#leave-date').value;
    const type = $('#leave-type').value;
    if (!uid || !date) { alert('Please provide Employee ID and Date.'); return; }

    const btn = $('#add-leave-btn');
    btn.disabled = true;
    const res = await apiFetch('/api/dashboard/leaves/add',
      { manager_code: _managerCode, uid, date, leave_type: type });
    btn.disabled = false;
    if (res.success) { alert('Leave record added successfully.'); loadLeavesData(); }
    else alert(res.message || 'Error adding leave.');
  });

  // ── Manage Employees ──────────────────────────────────────
  async function loadEmployeesData() {
    const data = await apiFetch('/api/dashboard/employees', { manager_code: _managerCode });
    if (data.success) renderEmployeesTable(data.records || [], $('#employees-table-wrap'));
  }

  function renderEmployeesTable(records, wrap) {
    if (!records || !records.length) {
      wrap.innerHTML = emptyState('No employees found.');
      return;
    }
    const cols  = Object.keys(records[0]);
    const heads = cols.map(c => `<th>${fmtCol(c)}</th>`).join('') + '<th>Actions</th>';
    const rows  = records.map(r => {
      const cells = cols.map(c => `<td>${r[c] ?? '—'}</td>`).join('');
      const acts  = `<td>
        <button class="btn btn-outline btn-sm edit-emp-btn"
                data-uid="${r.unique_id}" data-name="${r.name}"
                style="padding:4px 8px;font-size:11px;margin-right:4px">Edit</button>
        <button class="btn btn-sm del-emp-btn"
                data-uid="${r.unique_id}"
                style="padding:4px 8px;font-size:11px;background:var(--red);color:#fff;border:none;border-radius:var(--radius-sm);cursor:pointer">Delete</button>
      </td>`;
      return `<tr>${cells}${acts}</tr>`;
    }).join('');
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr>${heads}</tr></thead><tbody>${rows}</tbody>
    </table></div>`;

    wrap.querySelectorAll('.edit-emp-btn').forEach(b => {
      b.addEventListener('click', async () => {
        const uid     = b.dataset.uid;
        const oldName = b.dataset.name;
        const newName = prompt(`Enter new name for ${uid}:`, oldName);
        if (newName && newName.trim() && newName.trim() !== oldName) {
          const res = await apiFetch('/api/dashboard/employees/update',
            { manager_code: _managerCode, uid, new_name: newName.trim() });
          if (res.success) loadEmployeesData();
          else alert('Error updating employee name.');
        }
      });
    });
    wrap.querySelectorAll('.del-emp-btn').forEach(b => {
      b.addEventListener('click', async () => {
        const uid = b.dataset.uid;
        if (!confirm(`Delete employee ${uid}? This also removes their face data and cannot be undone.`)) return;
        const res = await apiFetch('/api/dashboard/employees/delete',
          { manager_code: _managerCode, uid });
        if (res.success) loadEmployeesData();
        else alert('Error deleting employee.');
      });
    });
  }

  // Lazy-load tab data when tabs are clicked
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.tab === 'leaves')    loadLeavesData();
      if (btn.dataset.tab === 'employees') loadEmployeesData();
      if (btn.dataset.tab === 'today')     loadTodayData();
    });
  });
}

// ── Generic Table ─────────────────────────────────────────────────────────────
function renderTable(records, wrap) {
  if (!records || !records.length) {
    wrap.innerHTML = emptyState('No records found.');
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
  wrap.innerHTML = `<div class="table-wrap">
    <table><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

// ── Monthly Day-by-Day Table ──────────────────────────────────────────────────
function renderMonthlyDetail(rows, days, wrap) {
  if (!rows?.length || !days?.length) {
    wrap.innerHTML = emptyState('No employee records for this month.');
    return;
  }

  const dayHeaders = days.map(d => `<th class="day-col">${parseInt(d.slice(8), 10)}</th>`).join('');
  const thead = `<tr>
    <th style="min-width:130px;position:sticky;left:0;background:var(--surface-2)">Name</th>
    <th style="min-width:80px">ID</th>
    ${dayHeaders}
    <th class="total-col" title="Present days">P</th>
    <th class="total-col" title="Late days">L</th>
    <th class="total-col" title="Absent days">A</th>
    <th class="total-col" title="Incomplete days">I</th>
  </tr>`;

  const tbody = rows.map(emp => {
    const dayCells = days.map(d => {
      const s   = emp.days[d] || '-';
      const cls = { P:'dc-p', L:'dc-l', A:'dc-a', I:'dc-i', OL:'dc-ol' }[s] || '';
      return `<td class="day-cell ${cls}">${s}</td>`;
    }).join('');
    const t = emp.totals;
    return `<tr>
      <td style="font-weight:600;color:var(--ink);position:sticky;left:0;background:var(--surface)">${emp.name}</td>
      <td style="color:var(--ink-muted);font-size:12px">${emp.uid}</td>
      ${dayCells}
      <td class="total-cell tc-p">${t.present}</td>
      <td class="total-cell tc-l">${t.late}</td>
      <td class="total-cell tc-a">${t.absent}</td>
      <td class="total-cell tc-i">${t.incomplete}</td>
    </tr>`;
  }).join('');

  wrap.innerHTML = `<div class="table-wrap">
    <table class="detail-table"><thead>${thead}</thead><tbody>${tbody}</tbody></table>
  </div>`;
}

// ── Monthly Detail CSV Export ─────────────────────────────────────────────────
function exportMonthlyDetailCSV(rows, days, filename) {
  if (!rows?.length) return;
  const header = ['Name', 'ID', ...days.map(d => parseInt(d.slice(8), 10)),
                   'Present', 'Late', 'Absent', 'Incomplete'];
  const csvRows = rows.map(emp => {
    const dayCols = days.map(d => emp.days[d] || '-');
    const t = emp.totals;
    return [emp.name, emp.uid, ...dayCols, t.present, t.late, t.absent, t.incomplete]
      .map(v => `"${v}"`).join(',');
  });
  downloadCSV([header.join(','), ...csvRows].join('\n'), filename);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtCol(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function statusBadge(s) {
  const cls = {
    present:    'badge-present',
    late:       'badge-late',
    absent:     'badge-absent',
    'on leave': 'badge-leave',
  }[(s || '').toLowerCase()] || 'badge-incomplete';
  return `<span class="badge ${cls}">${s || '—'}</span>`;
}

function emptyState(msg) {
  return `<div class="empty-state">
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="1.4"
         style="display:block;margin:0 auto 10px;opacity:.35">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>${msg}</div>`;
}

function exportCSV(data, filename) {
  if (!data?.length) return;
  const cols = Object.keys(data[0]);
  const rows = [cols.join(','), ...data.map(r => cols.map(c => `"${r[c] ?? ''}"`).join(','))];
  downloadCSV(rows.join('\n'), filename);
}

function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: 'text/csv' });
  Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(blob),
    download: filename,
  }).click();
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNav();
  initAttendance();
  initRegister();
  initDashboard();
});
