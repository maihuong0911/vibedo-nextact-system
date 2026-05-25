// v1775727683
// ===== GLOBAL FUNCTIONS =====
function esc(t) { 
    const d = document.createElement('div'); 
    d.textContent = t; 
    return d.innerHTML; 
}

function escAttr(t) {
    // Escape cho dùng trong HTML attribute (thêm escape dấu ")
    return esc(String(t || '')).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function formatDate(dt) {
    if (!dt) return '';

    // Parse thủ công từ ISO string để tránh lệch timezone
    // dt có thể là: "2026-04-03", "2026-04-03T09:00:00", "2026-04-03T09:00:00.000000"
    const match = dt.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/);
    if (!match) return dt;

    const year = match[1], month = match[2], day = match[3];
    const hours = match[4], mins = match[5];

    // Nếu có giờ và không phải 00:00 → hiển thị kèm giờ
    if (hours && mins && !(hours === '00' && mins === '00')) {
        return `${day}/${month}/${year} ${hours}:${mins}`;
    }
    // Chỉ có date hoặc giờ là 00:00 → hiển thị chỉ ngày
    return `${day}/${month}/${year}`;
}

function priorityLabel(p) {
    const n = Number(p);
    if (n === 3) return 'Cao';
    if (n === 2) return 'Trung bình';
    if (n === 1) return 'Thấp';
    return 'Trung bình';
}

// ===== AUTH FUNCTIONS (LOGIN & REGISTER) =====
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const eyeIcon = document.getElementById(iconId);
    if (!input || !eyeIcon) return;

    if (input.type === 'password') {
        input.type = 'text';
        eyeIcon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>';
        eyeIcon.setAttribute('viewBox', '0 0 24 24');
    } else {
        input.type = 'password';
        eyeIcon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
        eyeIcon.setAttribute('viewBox', '0 0 24 24');
    }
}

// For login.html
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email    = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorDiv   = document.getElementById('errorMessage');
        const successDiv = document.getElementById('successMessage');
        errorDiv.classList.remove('show');
        successDiv.classList.remove('show');

        // Ẩn nút submit khi đang xử lý
        const submitBtn = e.target.querySelector('[type=submit]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ email, password })
            });
            if (response.ok || response.redirected) {
                // Ẩn form, hiện dots animation (không có khung, không có text dài)
                errorDiv.classList.remove('show');

                // Xóa dotsEl cũ nếu có
                const oldDots = document.getElementById('loginDots');
                if (oldDots) oldDots.remove();

                const dotsEl = document.createElement('div');
                dotsEl.id = 'loginDots';
                dotsEl.style.cssText = [
                    'text-align:center',
                    'font-size:28px',
                    'letter-spacing:8px',
                    'color:#196B7C',
                    'margin-top:20px',
                    'font-weight:700',
                ].join(';');
                dotsEl.textContent = '.';
                document.getElementById('loginForm').after(dotsEl);

                // Animate: . → .. → ... → .... → .. (lặp)
                let d = 1;
                const timer = setInterval(() => {
                    d = d >= 5 ? 1 : d + 1;
                    dotsEl.textContent = '.'.repeat(d);
                }, 150);

                setTimeout(() => {
                    clearInterval(timer);
                    window.location.href = '/home';
                }, 750);

            } else {
                if (submitBtn) submitBtn.disabled = false;
                let msg = 'Email hoặc mật khẩu không đúng';
                try { const d = await response.json(); msg = d.detail || msg; } catch (_) {}
                errorDiv.textContent = msg;
                errorDiv.classList.add('show');
            }
        } catch (error) {
            if (submitBtn) submitBtn.disabled = false;
            errorDiv.textContent = 'Lỗi kết nối. Vui lòng thử lại.';
            errorDiv.classList.add('show');
        }
    });
}

// For register.html
if (document.getElementById('registerForm')) {
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const fullName = document.getElementById('full_name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm_password').value;
        const errorDiv = document.getElementById('errorMessage');
        const successDiv = document.getElementById('successMessage');
        errorDiv.classList.remove('show');
        successDiv.classList.remove('show');
        if (password !== confirmPassword) {
            errorDiv.textContent = 'Mật khẩu xác nhận không khớp';
            errorDiv.classList.add('show');
            return;
        }
        if (password.length < 6) {
            errorDiv.textContent = 'Mật khẩu phải có ít nhất 6 ký tự';
            errorDiv.classList.add('show');
            return;
        }
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ full_name: fullName, email, password })
            });
            if (response.ok || response.redirected) {
                // Dots animation thay cho text
                const oldDots = document.getElementById('registerDots');
                if (oldDots) oldDots.remove();
                const dotsEl = document.createElement('div');
                dotsEl.id = 'registerDots';
                dotsEl.style.cssText = 'text-align:center;font-size:28px;letter-spacing:8px;color:#196B7C;margin-top:20px;font-weight:700;';
                dotsEl.textContent = '.';
                document.getElementById('registerForm').after(dotsEl);
                let d = 1;
                const timer = setInterval(() => { d = d >= 5 ? 1 : d + 1; dotsEl.textContent = '.'.repeat(d); }, 150);
                setTimeout(() => { clearInterval(timer); window.location.href = '/login'; }, 750);
            } else {
                let msg = 'Đăng ký thất bại. Email có thể đã tồn tại.';
                try { const d = await response.json(); msg = d.detail || msg; } catch (_) {}
                errorDiv.textContent = msg;
                errorDiv.classList.add('show');
            }
        } catch (error) {
            errorDiv.textContent = 'Lỗi kết nối. Vui lòng thử lại.';
            errorDiv.classList.add('show');
        }
    });
}

// ===== DASHBOARD FUNCTIONS =====
// ===== CONSTANTS: 7 nhan PhoBERT model =====
var VALID_LABELS = ['Gửi/Trả lời email','Lên lịch họp','Tạo nhắc nhở','Soạn báo cáo','Theo dõi','Nộp tài liệu','Khác'];
var LABEL_COLORS = {
    'Gữi/Trả lời email': '#2563eb', 'Lên lịch họp': '#7c3aed',
    'Tạo nhắc nhở':      '#d97706', 'Soạn báo cáo': '#059669',
    'Theo dõi':          '#0891b2', 'Nộp tài liệu': '#dc2626',
    'Khác':              '#6b7280'
};

let classifyTimer = null;
let allNotes = [];
let __voiceRecognition = null;
let __voiceActive = false;
let editId = null;

// lưu kết quả suggest cho quickAdd áp dụng
window.__quickSuggest = null;

// ===== TASK PIN & STATUS STATE (localStorage) =====
const TASK_STATUS_CONFIG = {
    draft:       { label: 'Nháp',       color: '#6b7280', progress: 0   },
    pending:     { label: 'Chờ xử lý',  color: '#f97316', progress: 10  },
    in_progress: { label: 'Đang xử lý', color: '#3b82f6', progress: 40  },
    review:      { label: 'Chờ duyệt',  color: '#8b5cf6', progress: 70  },
    approved:    { label: 'Đã duyệt',   color: '#10b981', progress: 85  },
    rejected:    { label: 'Từ chối',    color: '#ef4444', progress: 0   },
    cancelled:   { label: 'Đã hủy',     color: '#9ca3af', progress: 0   },
    done:        { label: 'Hoàn thành', color: '#059669', progress: 100 }
};

function getTaskPins() {
    try { return JSON.parse(localStorage.getItem('taskPins') || '{}'); } catch { return {}; }
}
function setTaskPin(id, val) {
    const pins = getTaskPins();
    pins[String(id)] = val;
    localStorage.setItem('taskPins', JSON.stringify(pins));
}
function isTaskPinned(id) { return !!getTaskPins()[String(id)]; }

function getTaskStatuses() {
    try { return JSON.parse(localStorage.getItem('taskStatuses') || '{}'); } catch { return {}; }
}
function setTaskStatusLocal(id, status) {
    const s = getTaskStatuses();
    s[String(id)] = status;
    localStorage.setItem('taskStatuses', JSON.stringify(s));
}
function getTaskStatusLocal(id) { return getTaskStatuses()[String(id)] || null; }

function togglePin(id, e) {
    e.stopPropagation();
    const pinned = !isTaskPinned(id);
    setTaskPin(id, pinned);
    const btn = document.querySelector(`.pin-btn[data-id="${id}"]`);
    if (btn) btn.classList.toggle('pinned', pinned);
    // Re-sort to bring pinned tasks to top
    renderNotes();
}

function openStatusMenu(id, e) {
    e.stopPropagation();
    // Close any other open status menus
    document.querySelectorAll('.task-status-menu').forEach(m => {
        if (m.dataset.id !== String(id)) m.remove();
    });
    const existing = document.querySelector(`.task-status-menu[data-id="${id}"]`);
    if (existing) { existing.remove(); return; }

    const current = getTaskStatusLocal(id);
    const menu = document.createElement('div');
    menu.className = 'task-status-menu';
    menu.dataset.id = String(id);
    menu.style.cssText = 'position:absolute;top:calc(100% + 6px);right:0;background:#fff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.15);padding:6px;z-index:500;min-width:160px;';

    Object.entries(TASK_STATUS_CONFIG).forEach(([key, cfg]) => {
        const opt = document.createElement('div');
        opt.style.cssText = `display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:8px;font-size:12.5px;font-weight:500;color:#374151;cursor:pointer;transition:background .1s;${current===key?'background:#f3f4f6;font-weight:700;':''}`;
        opt.innerHTML = `<span style="width:10px;height:10px;border-radius:50%;background:${cfg.color};flex-shrink:0;display:inline-block;"></span>${cfg.label}`;
        opt.onmouseenter = () => opt.style.background = '#f3f4f6';
        opt.onmouseleave = () => opt.style.background = current === key ? '#f3f4f6' : '';
        opt.onclick = (ev) => { ev.stopPropagation(); setTaskStatusFromMenu(id, key); menu.remove(); };
        menu.appendChild(opt);
    });

    const dotBtn = document.querySelector(`.status-dot-btn[data-id="${id}"]`);
    if (dotBtn) {
        dotBtn.style.position = 'relative';
        dotBtn.appendChild(menu);
    }
}

function setTaskStatusFromMenu(id, status) {
    setTaskStatusLocal(id, status);
    // Update dot color on card
    const dotEl = document.querySelector(`.status-dot-btn[data-id="${id}"] .task-status-dot`);
    if (dotEl) {
        const cfg = TASK_STATUS_CONFIG[status];
        if (cfg) dotEl.style.background = cfg.color;
    }
    // If detail modal is open for this task, update it
    if (window.currentDetailId === id) updateDetailStatusSection(id);
}

function updateDetailStatusSection(id) {
    const statusKey = getTaskStatusLocal(id);
    const cfg = statusKey ? TASK_STATUS_CONFIG[statusKey] : null;
    const el = document.getElementById('detailStatusSection');
    if (!el) return;
    if (cfg) {
        el.style.display = 'block';
        const dot = el.querySelector('.detail-status-dot');
        const lbl = el.querySelector('.detail-status-label');
        const bar = el.querySelector('.detail-status-bar-fill');
        const pct = el.querySelector('.detail-status-pct');
        if (dot) dot.style.background = cfg.color;
        if (lbl) lbl.textContent = cfg.label;
        if (bar) { bar.style.width = cfg.progress + '%'; bar.style.background = cfg.color; }
        if (pct) pct.textContent = cfg.progress + '%';
    } else {
        el.style.display = 'none';
    }
}

function getToken() {
    // Token được backend lưu trong httpOnly cookie, không cần lấy thủ công.
    // Trả về null - các fetch dùng credentials: 'include' để gửi cookie tự động.
    return null;
}

function getHeaders() {
    // Cookie được gửi tự động, không cần Authorization header
    return {};
}

// loadNotes được tasks.html gọi qua DOMContentLoaded riêng
// Đây là fallback nếu chạy standalone
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (document.getElementById('notesGrid') && typeof window.__notesLoaded === 'undefined') {
            window.__notesLoaded = true;
            loadNotes();
        }
    });
}

async function loadNotes() {
    try {
        const res = await fetch('/notes', {
            credentials: 'include'  // Gửi cookie tự động
        });
        if (!res.ok) {
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error('Lỗi tải ghi chú');
        }
        allNotes = await res.json();
        updateStats();
        renderNotes();
    } catch (e) {
        console.error(e);
    }
}

function updateStats() {
    const elTotal = document.getElementById('total');
    const elWithDeadline = document.getElementById('withDeadline');
    const elHighPriority = document.getElementById('highPriority');
    const elNoDeadline = document.getElementById('noDeadline');
    if (!elTotal) return;

    elTotal.textContent = allNotes.length;
    elWithDeadline.textContent = allNotes.filter(n => n.due_date).length;
    elHighPriority.textContent = allNotes.filter(n => n.priority === 3).length;
    elNoDeadline.textContent = allNotes.filter(n => !n.due_date).length;
}


// ── Helper: extract label from task content + localStorage cache ──
function _getTaskLabel(n) {
    let label = '';
    const raw = (n.content || '').trim();

    // 1. Parse ---AI--- section
    let aiIdx = raw.indexOf('\n\n---AI---');
    if (aiIdx === -1) aiIdx = raw.indexOf('---AI---');
    const aiPart = aiIdx !== -1 ? raw.slice(aiIdx).replace(/^---AI---\n?/, '').replace(/^\n\n---AI---\n?/, '').trim() : '';
    if (aiPart) {
        const m = aiPart.match(/Nh\u00e3n:\s*([^\n]+)/);
        if (m) label = m[1].trim();
    }

    // 2. Parse template format: [style]\nNhãn: ...
    if (!label && raw.startsWith('[')) {
        const bodyAfterStyle = raw.slice(raw.indexOf(']') + 1).trim();
        const m2 = bodyAfterStyle.match(/^Nh\u00e3n:\s*([^\n]+)/m);
        if (m2) label = m2[1].trim();
    }

    // 3. Fallback: localStorage cache
    if (!label) {
        try {
            const store = JSON.parse(localStorage.getItem('vd_taskMeta') || '{}');
            const cached = store[n.id] || store[String(n.id)];
            if (cached && cached.label) label = cached.label;
        } catch (_) {}
    }

    return label;
}

function renderNotes() {
    const grid = document.getElementById('notesGrid');
    if (!grid) return;

    if (allNotes.length === 0) {
        grid.innerHTML = '<div class="empty">Chưa có ghi chú nào</div>';
        updateResultCount(0);
        return;
    }

    // Sort: pinned tasks first
    const sorted = [...allNotes].sort((a, b) => {
        const pa = isTaskPinned(a.id) ? 1 : 0;
        const pb = isTaskPinned(b.id) ? 1 : 0;
        return pb - pa;
    });

    grid.innerHTML = sorted.map(n => {
        // Card preview: nếu là template thì chỉ hiện style label, tránh vỡ HTML
        let cardPreview = '';
        if (n.content) {
            const c = n.content.trim();
            if (c.startsWith('[') && c.indexOf(']') > 0 && c.includes('Tiêu đề:')) {
                const bracketEnd = c.indexOf(']');
                const styleLabel = c.slice(1, bracketEnd);
                const subjectIdx = c.indexOf('Tiêu đề:');
                const subjectEnd = c.indexOf('\n', subjectIdx);
                const subject = (subjectEnd !== -1 ? c.slice(subjectIdx + 8, subjectEnd) : c.slice(subjectIdx + 8)).trim();
                cardPreview = escAttr(styleLabel) + ' · ' + escAttr(subject.slice(0, 40));
            } else {
                cardPreview = esc(c);
            }
        }
        const contentHtml = cardPreview
            ? `<p class="card-content">${cardPreview}</p>`
            : `<p class="card-content"></p>`;

        // ── Pin state ──
        const pinned = isTaskPinned(n.id);

        // ── Extended status dot ──
        const statusKey = getTaskStatusLocal(n.id);
        const statusCfg = statusKey ? TASK_STATUS_CONFIG[statusKey] : null;
        const dotColor  = statusCfg ? statusCfg.color : '#d1d5db';

        // ── Card class + style (keep quick-add design) ──
        const cardClass = n.is_quick_add ? 'note-card quick-card' : 'note-card';
        const cardStyle = n.is_quick_add
            ? 'border-left:4px solid #f97316; background:#fff8f0; border-color:#fcd5a8;'
            : '';

        // ── Deadline ──
        const now = new Date();
        const dueDate = n.due_date ? new Date(n.due_date) : null;
        const isOverdue = dueDate && dueDate < now;
        const deadlineHtml = n.due_date
            ? `<span style="color:${isOverdue ? '#ef4444' : '#6b7280'}; font-weight:${isOverdue ? '600' : '400'};">${formatDate(n.due_date)}</span>`
            : `<span style="color:#d1d5db;">Không có hạn</span>`;

        // ── Pin icon (star) — không có vòng tròn bao quanh ──
        const pinHtml = `
        <button class="pin-btn${pinned ? ' pinned' : ''}" data-id="${n.id}"
                onclick="togglePin(${n.id}, event)" title="${pinned ? 'Bỏ ghim' : 'Ghim lên đầu'}"
                style="background:none!important;border:none!important;border-radius:0!important;box-shadow:none!important;padding:2px!important;width:auto!important;height:auto!important;min-width:unset!important;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="${pinned ? '#f59e0b' : 'none'}"
                 stroke="${pinned ? '#f59e0b' : '#d1d5db'}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
        </button>`;


        // ── Status dot — CHỈ HIỂN THỊ màu, KHÔNG click ──
        const statusDotHtml = `
        <div style="position:relative;display:inline-flex;align-items:center;flex-shrink:0;"
             onmouseenter="_showFixedTooltip(event,'${statusCfg ? statusCfg.label : 'Chưa đặt'}')"
             onmouseleave="_hideFixedTooltip()">
            <div style="width:13px;height:13px;border-radius:50%;background:${dotColor};cursor:default;"></div>
        </div>`;

        // ── Priority dot — hiển thị mức ưu tiên bằng màu ──
        const priVal = String(n.priority || '2');
        const priCfgCard = typeof PRIORITY_CONFIG !== 'undefined' ? PRIORITY_CONFIG.find(p => p.value === priVal) : null;
        const priDotColor = priCfgCard ? priCfgCard.color : (n.priority === 3 ? '#f97316' : n.priority === 1 ? '#6b7280' : '#3b82f6');
        const priDotLabel = priCfgCard ? priCfgCard.label : priorityLabel(n.priority);
        const priorityDotHtml = `
        <div style="position:relative;display:inline-flex;align-items:center;flex-shrink:0;"
             onmouseenter="_showFixedTooltip(event,'${priDotLabel}')"
             onmouseleave="_hideFixedTooltip()">
            <div style="width:13px;height:13px;border-radius:50%;background:${priDotColor};cursor:default;"></div>
        </div>`;

        // ── Label chip ──
        const _taskLabel = _getTaskLabel(n);
        const _cardLabelHtml = _taskLabel
            ? `<span style="display:inline-flex;align-items:center;padding:3px 8px;border-radius:5px;font-size:10px;font-weight:700;background:#e0f2fe;color:#0369a1;white-space:nowrap;max-width:120px;overflow:hidden;text-overflow:ellipsis;" title="${_taskLabel}">${_taskLabel}</span>`
            : '';

        return `
        <div class="${cardClass}" style="${cardStyle}" onclick="openDetailModal(${n.id})">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:6px; margin-bottom:4px;">
                <h3 style="flex:1;min-width:0;">${esc(n.title)}</h3>
                <div style="display:flex;align-items:center;gap:5px;flex-shrink:0;" onclick="event.stopPropagation();">
                    ${statusDotHtml}
                    ${priorityDotHtml}
                    ${pinHtml}
                </div>
            </div>
            ${contentHtml}
            <div class="note-meta">
                ${deadlineHtml}
                <span>${formatDate(n.created_at)}</span>
            </div>
            <div class="note-actions" onclick="event.stopPropagation();">
                ${_cardLabelHtml}
                <div style="margin-left:auto;display:flex;align-items:center;gap:10px;">
                  <button class="btn-small btn-edit" onclick="openEditModal(${n.id})">Sửa</button>
                  <button class="btn-small btn-delete" onclick="delNote(${n.id})">Xóa</button>
                </div>
            </div>
        </div>
    `;
    }).join('');

    updateResultCount(sorted.length);
    applyFilters();
}

async function addNote(e) {
    e.preventDefault();

    // Luu kem ket qua AI vao content khi submit
    var contentVal = document.getElementById('addContent').value || '';
    var sr = window.__summarizeResult;
    if (sr) {
        var labelStr  = (sr.phobert_labels || []).filter(function(l){ return VALID_LABELS.indexOf(l)!==-1; }).join(', ');
        var summLines = (sr.summary || []).map(function(s){ return '  \u2022 ' + s; }).join('\n');
        var taskLines = (sr.tasks   || []).map(function(t){
            var lbl = VALID_LABELS.indexOf(t.action_type)!==-1 ? t.action_type : 'Kh\u00e1c';
            return '  [' + lbl + '] ' + t.title;
        }).join('\n');

        var extras = [];
        if (labelStr)  extras.push('Nh\u00e3n: ' + labelStr);
        if (summLines) extras.push('Vi\u1ec7c c\u1ea7n l\u00e0m:\n' + summLines);
        if (taskLines) extras.push('G\u1ee3i \u00fd h\u00e0nh \u0111\u1ed9ng:\n' + taskLines);
        if (extras.length) {
            contentVal = contentVal.trim() + '\n\n---AI---\n' + extras.join('\n\n');
        }
    }

    var fd = new FormData();
    fd.append('title',    document.getElementById('addTitle').value);
    fd.append('content',  contentVal);
    fd.append('status',   'todo');
    fd.append('priority', document.getElementById('addPriority').value);
    fd.append('due_date', document.getElementById('addDueDate').value || '');
    // Gán project_id nếu đang trong một dự án
    if (window.__activeProjectId) fd.append('project_id', window.__activeProjectId);
    try {
        var res = await fetch('/notes', { method: 'POST', credentials: 'include', body: fd });
        if (res.ok) {
            const created = await res.json().catch(() => ({}));
            closeAddNoteModal();
            // Chỉ reload Công việc nếu task KHÔNG thuộc project nào
            if (!created.project_id) loadNotes();
            if (typeof window.onNoteCreated === 'function') window.onNoteCreated(created);
        }
        else alert('Lỗi tạo ghi chú');
    } catch(e) { alert('Lỗi kết nối'); }
}

async function quickAdd(e) {
    e.preventDefault();

    const title = document.getElementById('quickTitle').value.trim();
    const suggest = window.__quickSuggest;

    let dueDate = document.getElementById('quickDueDate')?.value || '';
    let priority = '2';

    // Tự động áp dụng deadline + priority từ AI suggest nếu có
    if (suggest) {
        if (suggest.deadline) dueDate = suggest.deadline;
        if (suggest.suggested_priority) priority = String(suggest.suggested_priority);
    }

    // Lấy nội dung mẫu đã chọn (nếu có)
    let templateContent = null;
    const selectedIdx = window.__selectedTemplate;
    if (selectedIdx !== undefined && selectedIdx !== null && window.__nextTemplates) {
        const t = window.__nextTemplates[selectedIdx];
        if (t) {
            // Lấy nhãn PhoBERT từ quickSuggest hoặc từ template
            const templateCategory = (suggest?.category) || t.category || '';
            const labelLine = templateCategory ? `Nhãn: ${templateCategory}\n` : '';
            templateContent = `[${t.style}]\n${labelLine}Tiêu đề: ${t.subject}\n\n${t.body}`;
        }
    }

    // Gom NER highlights + nhan PhoBERT vao content
    var quickContent = templateContent || null;
    var qs = window.__quickSuggest;
    if (qs && !templateContent) {
        // Chỉ thêm AI section khi KHÔNG có template (tránh duplicate nhãn)
        var nb = document.getElementById('nerPreviewBox');
        var nerParts = [];
        if (nb) {
            function gT(sel){ return Array.from(nb.querySelectorAll(sel)).map(function(s){return s.textContent.trim();}).filter(Boolean); }
            var acts = gT('.ner-highlight-action');
            var pers = gT('.ner-highlight-person');
            var tims = gT('.ner-highlight-time');
            var plcs = gT('.ner-highlight-place');
            if (acts.length) nerParts.push('H\u00e0nh \u0111\u1ed9ng: ' + acts.join(', '));
            if (pers.length) nerParts.push('Ng\u01b0\u1eddi: '        + pers.join(', '));
            if (tims.length) nerParts.push('Th\u1eddi gian: '        + tims.join(', '));
            if (plcs.length) nerParts.push('\u0110\u1ecba \u0111i\u1ec3m: '       + plcs.join(', '));
        }
        var lbl = (qs.category && VALID_LABELS.indexOf(qs.category) !== -1) ? qs.category : null;
        var extras = (lbl ? ['Nh\u00e3n: ' + lbl] : []).concat(nerParts);
        if (extras.length) {
            var extra = '---AI---\n' + extras.join('\n');
            quickContent = quickContent ? quickContent + '\n\n' + extra : extra;
        }
    }

    try {
        var res2 = await fetch('/nextact/create_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                title: title,
                priority: parseInt(priority),
                due_date: dueDate || null,
                is_quick_add: true,
                content: quickContent,
                project_id: window.__activeProjectId || null
            })
        });
        if (res2.ok) {
            const created = await res2.json().catch(() => ({}));
            window.__selectedTemplate = null;

            // ── Cache nhãn + phong cách vào localStorage ──
            if (created.id) {
                try {
                    const _qs = window.__quickSuggest;
                    let cachedLabel = '';
                    let cachedStyle = '';
                    if (_qs && _qs.category && VALID_LABELS.indexOf(_qs.category) !== -1) {
                        cachedLabel = _qs.category;
                    }
                    const _selIdx = window.__selectedTemplate;
                    if (_selIdx !== undefined && _selIdx !== null && window.__nextTemplates) {
                        const _tpl = window.__nextTemplates[_selIdx];
                        if (_tpl) {
                            cachedStyle = _tpl.style || '';
                            if (!cachedLabel && _tpl.category) cachedLabel = _tpl.category;
                        }
                    }
                    if (cachedLabel || cachedStyle) {
                        const _store = JSON.parse(localStorage.getItem('vd_taskMeta') || '{}');
                        _store[created.id] = { label: cachedLabel, style: cachedStyle };
                        localStorage.setItem('vd_taskMeta', JSON.stringify(_store));
                    }
                } catch (_e) {}
            }

            // Chỉ reload Công việc nếu task KHÔNG thuộc project nào
            if (!created.project_id) loadNotes();
            if (typeof window.onNoteCreated === 'function') window.onNoteCreated(created);

            // ── Gửi thêm calendar event nếu có execution_data ──────────────
            const category = window.__quickSuggest?.category || '';
            const execData = window.__executionData;
            const calendarLabels = ['Lên lịch họp', 'Tạo nhắc nhở'];
            if (calendarLabels.includes(category) && execData && execData.iso_time) {
                // Đọc reminder_minutes từ dropdown nếu user đã chỉnh
                const reminderEl = document.getElementById('reminderMinsSelect');
                if (reminderEl) execData.reminder_minutes = parseInt(reminderEl.value);

                // Đọc notify_list đã toggle
                const currentNotifyList = (window.__attendeesData || [])
                    .filter(a => a.is_notified).map(a => a.name);

                fetch('/nextact/add-calendar-event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        event_title:     execData.event_title || title,
                        iso_time:        execData.iso_time,
                        description:     execData.description || '',
                        attendees_list:  (window.__attendeesData || []).map(a => a.name),
                        notify_list:     currentNotifyList,
                        reminder_mins:   execData.reminder_minutes || 30,
                    })
                }).then(r => r.json()).then(d => {
                    if (d.success && d.htmlLink) {
                        console.log('[Calendar] Sự kiện đã tạo:', d.htmlLink);
                    }
                }).catch(() => {});
            }

            // Nếu nhãn "Giao việc": lưu noteId, GIỮ modal mở để chọn người nhận
            if (category === 'Giao việc' && created.id) {
                window.__lastCreatedNoteId = created.id;
                const hint = document.getElementById('assignSendHint');
                if (hint) {
                    hint.textContent = 'Đã lưu task. Chọn người nhận và nhấn Gửi.';
                    hint.style.color = '#15803d';
                }
            } else if (category === 'Lên lịch họp' && created.id) {
                window.__lastCreatedNoteId = created.id;
                const hint = document.getElementById('meetingSendHint');
                const btn  = document.getElementById('meetingSendBtn');
                if (hint) { hint.textContent = 'Đã lưu task. Nhấn Thêm để gửi lời mời.'; hint.style.color = '#15803d'; }
                if (btn)  { btn.textContent = 'Gửi lời mời'; }
            } else {
                closeQuickAddModal();
            }
        } else {
            alert('Lỗi tạo ghi chú');
        }
    } catch(e) { alert('Lỗi kết nối'); }
}

let nerPreviewTimer = null;

function handleQuickInput() {
    // Suggest debounce 400ms
    clearTimeout(classifyTimer);
    classifyTimer = setTimeout(() => {
        suggestTodo();
    }, 400);

    // NER preview debounce 500ms — chỉ render sau khi người dùng dừng gõ
    clearTimeout(nerPreviewTimer);
    nerPreviewTimer = setTimeout(() => {
        const input = document.getElementById('quickTitle');
        if (input) renderNerPreview(input.value);
    }, 500);
}

/**
 * Suggest endpoint (mới): /nextact/suggest
 * - populate classifyResult (để không mất UI cũ)
 * - populate suggestResult (gợi ý hành động)
 * - fallback: nếu suggest lỗi thì gọi classifyTodo()
 */
async function suggestTodo() {
    const input = document.getElementById('quickTitle');
    if (!input) return;

    const text = input.value.trim();
    const classifyBox = document.getElementById('classifyResult');
    const suggestBox = document.getElementById('suggestResult');

    if (text.length < 3) {
        if (classifyBox) classifyBox.style.display = 'none';
        if (suggestBox) suggestBox.style.display = 'none';
        window.__quickSuggest = null;
        const qdd = document.getElementById('quickDueDate');
        if (qdd) qdd.value = '';
        return;
    }

    try {
        const res = await fetch('/nextact/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        // nếu endpoint chưa có → fallback
        if (!res.ok) {
            // fallback giữ nguyên chức năng cũ
            await classifyTodo();
            return;
        }

        const data = await res.json();
        window.__quickSuggest = data;

        // ===== Kiểm tra nhãn hợp lệ — null/rỗng → ẩn toàn bộ classify UI =====
        const hasLabel = data.category && data.category.trim() !== '' && data.category !== 'null';

        if (!hasLabel) {
            // Text vô nghĩa hoặc không đủ ngưỡng → ẩn cả 2 box
            if (classifyBox) classifyBox.style.display = 'none';
            if (suggestBox) suggestBox.style.display = 'none';
            if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'none';
            const qdd = document.getElementById('quickDueDate');
            if (qdd) qdd.value = '';
            const hPri = document.getElementById('quickSuggestedPriority');
            const hCat = document.getElementById('quickSuggestedCategory');
            const hConf = document.getElementById('quickSuggestedConfidence');
            if (hPri) hPri.value = '';
            if (hCat) hCat.value = '';
            if (hConf) hConf.value = '';
            const suggestCont = document.getElementById('suggestNextContent');
            if (suggestCont) suggestCont.innerHTML = '';
            return;
        }

        // ===== Populate classifyResult (cũ) =====
        if (document.getElementById('categoryName')) {
            document.getElementById('categoryName').textContent = `📌 ${data.category}`;
        }
        if (document.getElementById('confidenceScore')) {
            document.getElementById('confidenceScore').textContent = `${data.confidence}%`;
        }
        if (classifyBox) classifyBox.style.display = 'block';

        if (data.deadline_display && data.deadline_display !== 'Không có') {
            // Dùng deadline_display từ backend (đã format dd/mm/yyyy HH:MM)
            if (document.getElementById('deadlineValue')) document.getElementById('deadlineValue').textContent = data.deadline_display;
            if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'block';
            const qdd = document.getElementById('quickDueDate');
            if (qdd) qdd.value = data.deadline || '';  // Lưu full ISO datetime (có giờ)
        } else {
            if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'none';
            const qdd = document.getElementById('quickDueDate');
            if (qdd) qdd.value = '';
        }

        // ===== Populate hidden (nếu có) =====
        const hPri = document.getElementById('quickSuggestedPriority');
        const hCat = document.getElementById('quickSuggestedCategory');
        const hConf = document.getElementById('quickSuggestedConfidence');
        if (hPri) hPri.value = data.suggested_priority ?? '';
        if (hCat) hCat.value = data.category ?? '';
        if (hConf) hConf.value = data.confidence ?? '';

        // ===== Hiện block "Gợi Ý Tiếp Theo" + gọi AI sinh template =====
        if (suggestBox) suggestBox.style.display = 'block';

        // Gọi AI sinh gợi ý template dựa theo nhãn
        fetchNextActionTemplates(text, data.category || '');

    } catch (e) {
        console.error('Suggest error:', e);
        try { await classifyTodo(); } catch (_) {}
    }
}

// ===== GỢI Ý TIẾP THEO: phân nhánh theo nhãn =====
async function fetchNextActionTemplates(text, category) {
    const container = document.getElementById('suggestNextContent');
    if (!container) return;
    if (!category || !text || text.length < 3) { container.innerHTML = ''; return; }

    // ── Nhãn "Giao việc": hiển thị UI chọn người nhận thay vì template ──
    if (category === 'Giao việc') {
        renderAssignUI(container);
        return;
    }

    // ── Các nhãn khác: gọi Groq sinh template như cũ ──────────────────
    const deadlineDisplay = window.__quickSuggest?.deadline_display || '';
    container.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;color:#9ca3af;font-size:13px;padding:8px 0;">
            Chờ chút nhé!!
        </div>`;
    try {
        const res = await fetch('/nextact/groq-suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ text, category, deadline_display: deadlineDisplay })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            container.innerHTML = `<div style="color:#ef4444;font-size:12px;padding:8px 0;">⚠️ ${err.detail || 'Không thể tải gợi ý.'}</div>`;
            return;
        }
        const data = await res.json();
        const templates = data.templates;
        if (!Array.isArray(templates) || templates.length === 0) { container.innerHTML = ''; return; }
        window.__nextTemplates = templates;

        // Lưu execution_data và attendees cho "Lên lịch họp" / "Tạo nhắc nhở"
        window.__executionData = data.execution_data || null;
        window.__attendeesData = data.attendees || [];      // [{name, is_notified}]
        window.__calendarLink  = data.calendar_link || null;

        renderTemplateCards(container, templates, category);

        // Meeting panel đã tích hợp attendees bên trong renderTemplateCards
    } catch (e) {
        console.error('fetchNextActionTemplates error:', e);
        container.innerHTML = `<div style="color:#ef4444;font-size:12px;padding:8px 0;">⚠️ Lỗi kết nối.</div>`;
    }
}

// ===== UI GIAO VIỆC: chọn người nhận + gửi =====
async function renderAssignUI(container) {
    container.innerHTML = `<div style="color:#9ca3af;font-size:13px;padding:8px 0;">Đang tải danh sách...</div>`;
    try {
        const res = await fetch('/users/list', { credentials: 'include' });
        if (!res.ok) throw new Error('Không lấy được danh sách người dùng');
        const users = await res.json();

        if (!users || users.length === 0) {
            container.innerHTML = `<div style="color:#6b7280;font-size:13px;padding:12px 0;text-align:center;">
                Hiện chưa có tài khoản nào khác trong hệ thống.
            </div>`;
            return;
        }

        // Build options
        const options = users.map(u =>
            `<option value="${u.id}" data-name="${esc(u.full_name)}">${esc(u.full_name)} (${esc(u.email)})</option>`
        ).join('');

        container.innerHTML = `
        <div class="assign-ui-wrap">
            <div class="assign-ui-label">👤 Chọn người nhận công việc</div>
            <select id="assignReceiverSelect" class="assign-select">
                <option value="">-- Chọn tài khoản --</option>
                ${options}
            </select>
            <div id="assignMsgWrap" style="margin-top:10px;display:none;">
                <div class="assign-ui-label">💬 Ghi chú kèm theo (tuỳ chọn)</div>
                <textarea id="assignMsgInput" class="assign-msg-input"
                    placeholder="Ví dụ: Deadline ngày mai, ưu tiên cao..."></textarea>
            </div>
            <button class="assign-send-btn" id="assignSendBtn"
                    onclick="confirmAndSendTask()" disabled>
                📤 Gửi công việc
            </button>
            <div id="assignSendHint">Nhấn "Thêm" phía dưới để lưu task trước khi gửi</div>
        </div>`;

        // Hiện textarea khi chọn người
        document.getElementById('assignReceiverSelect').addEventListener('change', function () {
            const wrap = document.getElementById('assignMsgWrap');
            const btn  = document.getElementById('assignSendBtn');
            if (this.value) {
                wrap.style.display = 'block';
                btn.disabled = false;
            } else {
                wrap.style.display = 'none';
                btn.disabled = true;
            }
        });

    } catch (e) {
        console.error('renderAssignUI error:', e);
        container.innerHTML = `<div style="color:#ef4444;font-size:12px;padding:8px 0;">⚠️ ${e.message}</div>`;
    }
}

// ===== MEETING PANEL CSS =====
(function injectMeetingCSS() {
    if (document.getElementById('meeting-panel-style')) return;
    const s = document.createElement('style');
    s.id = 'meeting-panel-style';
    s.textContent = `
        .meeting-panel {
            margin-top: 14px;
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            font-family: inherit;
        }
        .meeting-panel-title {
            font-size: 13px;
            font-weight: 700;
            color: #1e3a5f;
            text-transform: uppercase;
            letter-spacing: .06em;
            margin-bottom: 14px;
        }
        .meeting-field-label {
            font-size: 11px;
            font-weight: 700;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: .07em;
            margin-bottom: 5px;
            font-style: normal;
        }
        .meeting-field-value {
            font-size: 13px;
            font-weight: 600;
            color: #1e3a5f;
            font-style: normal;
        }
        .meeting-field-row {
            display: flex;
            gap: 16px;
            margin-bottom: 14px;
        }
        .meeting-field-col {
            flex: 1;
        }
        .meeting-location-input {
            width: 100%;
            padding: 7px 10px;
            border: 1.5px solid #d1d5db;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            font-style: normal;
            color: #374151;
            background: #fff;
            outline: none;
            box-sizing: border-box;
            transition: border .15s;
        }
        .meeting-location-input:focus { border-color: #196B7C; }
        .meeting-tags-section { margin-bottom: 14px; }
        .meeting-tags-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .meeting-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px 4px 4px;
            border-radius: 20px;
            font-size: 12.5px;
            font-weight: 500;
            font-style: normal;
            background: #e8f4f8;
            color: #1e3a5f;
            border: 1.5px solid #b8dce8;
            user-select: none;
            animation: tagIn .15s ease;
        }
        @keyframes tagIn { from { opacity:0; transform:scale(.85); } to { opacity:1; transform:scale(1); } }
        .meeting-tag-avatar {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 700;
            font-style: normal;
            color: #fff;
            flex-shrink: 0;
            overflow: hidden;
        }
        .meeting-tag-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 50%;
        }
        .meeting-tag-remove {
            cursor: pointer;
            font-size: 13px;
            color: #6b7280;
            line-height: 1;
            transition: color .15s;
            font-style: normal;
        }
        .meeting-tag-remove:hover { color: #dc2626; }
        .meeting-search-input {
            width: 100%;
            padding: 7px 10px;
            border: 1.5px solid #d1d5db;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            font-style: normal;
            color: #374151;
            background: #fff;
            outline: none;
            box-sizing: border-box;
            transition: border .15s;
        }
        .meeting-search-input:focus { border-color: #196B7C; }
        .meeting-search-dropdown {
            position: absolute;
            z-index: 100;
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,.1);
            max-height: 180px;
            overflow-y: auto;
            width: 100%;
            left: 0;
            top: calc(100% + 4px);
        }
        .meeting-search-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 13px;
            font-style: normal;
            color: #374151;
            transition: background .1s;
        }
        .meeting-search-item:hover { background: #f0f9ff; }
        .meeting-search-avatar {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            color: #fff;
            flex-shrink: 0;
            overflow: hidden;
        }
        .meeting-search-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 50%;
        }
        .meeting-invite-textarea {
            width: 100%;
            min-height: 80px;
            padding: 9px 12px;
            border: 1.5px solid #d1d5db;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            font-style: normal;
            color: #374151;
            resize: vertical;
            outline: none;
            box-sizing: border-box;
            transition: border .15s;
        }
        .meeting-invite-textarea:focus { border-color: #196B7C; }
        .meeting-reminder-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-style: normal;
            color: #374151;
            margin-bottom: 14px;
        }
        .meeting-reminder-select {
            padding: 5px 8px;
            border: 1.5px solid #d1d5db;
            border-radius: 6px;
            font-size: 13px;
            font-family: inherit;
            font-style: normal;
            background: #fff;
            cursor: pointer;
            color: #374151;
            outline: none;
        }
        .meeting-reminder-select:focus { border-color: #196B7C; }
        .meeting-send-btn {
            width: 100%;
            padding: 10px;
            background: #196B7C;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            font-style: normal;
            font-family: inherit;
            cursor: pointer;
            transition: background .15s;
        }
        .meeting-send-btn:hover:not(:disabled) { background: #145a68; }
        .meeting-send-btn:disabled { background: #9ca3af; cursor: not-allowed; }
        .meeting-send-hint {
            font-size: 12px;
            margin-top: 8px;
            text-align: center;
            color: #6b7280;
            font-style: normal;
        }
    `;
    document.head.appendChild(s);
})();

// ===== MEETING PANEL: avatar color palette =====
const _AVATAR_COLORS = [
    '#196B7C','#7c3aed','#d97706','#059669','#0891b2','#dc2626','#6b7280',
    '#be185d','#0f766e','#b45309','#4338ca','#0369a1'
];

function _avatarColor(name) {
    let h = 0;
    for (let i = 0; i < (name||'').length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
    return _AVATAR_COLORS[h % _AVATAR_COLORS.length];
}

function _avatarInitials(name) {
    const parts = (name || '').trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function _avatarHTML(person, size = 22, fontSize = 10) {
    // person = { name, avatar_url? }
    const name = person.name || person;
    const url  = person.avatar_url || null;
    const color = _avatarColor(name);
    if (url) {
        return `<span class="meeting-tag-avatar" style="width:${size}px;height:${size}px;">
            <img src="${escAttr(url)}" alt="${escAttr(name)}" onerror="this.parentElement.innerHTML='<span style=font-size:${fontSize}px;font-weight:700>${escAttr(_avatarInitials(name))}</span>';this.parentElement.style.background='${color}';">
        </span>`;
    }
    return `<span class="meeting-tag-avatar" style="width:${size}px;height:${size}px;background:${color};font-size:${fontSize}px;">
        ${_avatarInitials(name)}
    </span>`;
}

// window.__meetingAttendees = [{ name, avatar_url, email, id }]
window.__meetingAttendees = [];

function _initMeetingAttendees(attendeesData) {
    window.__meetingAttendees = (attendeesData || []).map(a => ({
        name: a.name || a,
        avatar_url: a.avatar_url || null,
        email: a.email || null,
        id: a.id || null,
    }));
}

function _rebuildMeetingTags() {
    const row = document.getElementById('meetingTagsRow');
    if (!row) return;
    row.innerHTML = (window.__meetingAttendees || []).map((p, i) => `
        <span class="meeting-tag" id="mtag_${i}">
            ${_avatarHTML(p, 22, 10)}
            <span style="font-style:normal;">${esc(p.name)}</span>
            <span class="meeting-tag-remove" onclick="removeMeetingAttendee(${i})" title="Xóa">×</span>
        </span>`).join('');
}

function removeMeetingAttendee(idx) {
    window.__meetingAttendees.splice(idx, 1);
    _rebuildMeetingTags();
}

let _attendeeSearchTimer = null;
function onAttendeeSearch(val) {
    clearTimeout(_attendeeSearchTimer);
    const dd = document.getElementById('attendeeSearchDropdown');
    if (!val || val.trim().length < 1) { if (dd) dd.innerHTML = ''; return; }
    _attendeeSearchTimer = setTimeout(() => _doAttendeeSearch(val.trim()), 250);
}

async function _doAttendeeSearch(q) {
    const dd = document.getElementById('attendeeSearchDropdown');
    if (!dd) return;
    try {
        const res = await fetch(`/users/search?q=${encodeURIComponent(q)}`, { credentials: 'include' });
        if (!res.ok) throw new Error();
        const users = await res.json();
        const current = new Set((window.__meetingAttendees || []).map(a => a.name));
        const filtered = users.filter(u => !current.has(u.full_name));
        if (!filtered.length) { dd.innerHTML = '<div class="meeting-search-item" style="color:#9ca3af;">Không tìm thấy</div>'; return; }
        dd.innerHTML = filtered.map(u => {
            const person = { name: u.full_name, avatar_url: u.avatar_url || null, email: u.email, id: u.id };
            const avatarSz = _avatarHTML(person, 28, 11);
            return `<div class="meeting-search-item" onclick="addMeetingAttendeeFromSearch(${u.id}, '${escAttr(u.full_name)}', '${escAttr(u.email)}', '${escAttr(u.avatar_url || '')}')">
                ${avatarSz}
                <div>
                    <div style="font-weight:600;font-style:normal;">${esc(u.full_name)}</div>
                    <div style="font-size:11px;color:#9ca3af;font-style:normal;">${esc(u.email)}</div>
                </div>
            </div>`;
        }).join('');
    } catch (_) {
        if (dd) dd.innerHTML = '<div class="meeting-search-item" style="color:#9ca3af;">Lỗi tìm kiếm</div>';
    }
}

function addMeetingAttendeeFromSearch(id, name, email, avatarUrl) {
    if ((window.__meetingAttendees || []).some(a => a.name === name)) return;
    window.__meetingAttendees.push({ name, email, id, avatar_url: avatarUrl || null });
    _rebuildMeetingTags();
    const inp = document.getElementById('attendeeSearchInput');
    const dd  = document.getElementById('attendeeSearchDropdown');
    if (inp) inp.value = '';
    if (dd)  dd.innerHTML = '';
}

function _buildMeetingPanel(execData, attendees) {
    const reminderMins = (execData && execData.reminder_minutes) || 30;
    const timeDisplay  = (execData && execData.datetime_display) || (execData && execData.iso_time) || '';
    const inviteText   = (execData && execData.invite_text) || '';

    return `
    <div class="meeting-panel" id="meetingPanel">
        <div class="meeting-panel-title">Lên lịch họp</div>
        <div class="meeting-field-row">
            <div class="meeting-field-col">
                <div class="meeting-field-label">Thời gian</div>
                <div class="meeting-field-value" id="meetingTimeDisplay">${esc(timeDisplay || 'Chưa xác định')}</div>
            </div>
            <div class="meeting-field-col">
                <div class="meeting-field-label">Địa điểm</div>
                <input class="meeting-location-input" id="meetingLocation" type="text" placeholder="Phòng họp 1, Link Zoom...">
            </div>
        </div>

        <div class="meeting-tags-section">
            <div class="meeting-field-label">Người tham gia</div>
            <div class="meeting-tags-row" id="meetingTagsRow"></div>
            <div style="position:relative;">
                <input class="meeting-search-input" id="attendeeSearchInput"
                    type="text" placeholder="Tìm và thêm người..."
                    oninput="onAttendeeSearch(this.value)"
                    onblur="setTimeout(()=>{ const d=document.getElementById('attendeeSearchDropdown'); if(d) d.innerHTML=''; },200)">
                <div class="meeting-search-dropdown" id="attendeeSearchDropdown"></div>
            </div>
        </div>

        <div style="margin-bottom:14px;">
            <div class="meeting-field-label">Lời mời</div>
            <textarea class="meeting-invite-textarea" id="meetingInviteText" placeholder="Nội dung lời mời...">${esc(inviteText)}</textarea>
        </div>

        <div class="meeting-reminder-row">
            Nhắc trước:
            <select class="meeting-reminder-select" id="reminderMinsSelect">
                <option value="15" ${reminderMins===15?'selected':''}>15 phút</option>
                <option value="30" ${reminderMins===30?'selected':''}>30 phút</option>
                <option value="60" ${reminderMins===60?'selected':''}>1 giờ</option>
                <option value="120" ${reminderMins===120?'selected':''}>2 giờ</option>
            </select>
        </div>

        <button class="meeting-send-btn" id="meetingSendBtn" onclick="sendMeetingInvite()">Thêm</button>
        <div class="meeting-send-hint" id="meetingSendHint">Nhấn "Thêm" phía dưới để lưu task trước khi gửi</div>
    </div>`;
}

async function sendMeetingInvite() {
    const btn = document.getElementById('meetingSendBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Đang xử lý...'; }

    const noteId = window.__lastCreatedNoteId;
    if (!noteId) {
        alert('Vui lòng nhấn "Thêm" ở form chính để lưu task trước.');
        if (btn) { btn.disabled = false; btn.textContent = 'Thêm'; }
        return;
    }

    const execData = window.__executionData || {};
    const reminderEl = document.getElementById('reminderMinsSelect');
    if (reminderEl) execData.reminder_minutes = parseInt(reminderEl.value);

    const attendees = window.__meetingAttendees || [];
    const receivers = attendees.filter(a => a.id).map(a => a.id);

    try {
        // 1. Giao việc / mời họp
        if (receivers.length > 0) {
            const inviteText = document.getElementById('meetingInviteText')?.value || '';
            const res = await fetch('/assignments/assign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    note_id:         noteId,
                    receiver_ids:    receivers,
                    message:         inviteText,
                    assignment_type: 'meeting'
                })
            });
            const d = await res.json();
            if (!res.ok) throw new Error(d.detail || 'Gửi lời mời thất bại');
        }

        // 2. Thêm calendar event
        if (execData.iso_time) {
            const location = document.getElementById('meetingLocation')?.value || '';
            fetch('/nextact/add-calendar-event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    event_title:    execData.event_title || document.getElementById('quickTitle')?.value || '',
                    iso_time:       execData.iso_time,
                    description:    document.getElementById('meetingInviteText')?.value || execData.description || '',
                    attendees_list: attendees.map(a => a.email || a.name),
                    notify_list:    attendees.filter(a => a.email).map(a => a.email),
                    reminder_mins:  execData.reminder_minutes || 30,
                    location:       location,
                })
            }).catch(() => {});
        }

        // 3. Hiển thị thành công
        const panel = document.getElementById('meetingPanel');
        if (panel) {
            panel.innerHTML = `
            <div style="text-align:center;padding:20px 0;">
                <div style="font-size:14px;font-weight:700;color:#15803d;margin-bottom:4px;">Đã gửi lời mời thành công</div>
                <div style="font-size:12px;color:#6b7280;">${receivers.length > 0 ? receivers.length + ' người sẽ nhận được thông báo.' : 'Đã lưu vào lịch.'}</div>
            </div>`;
        }
        window.__lastCreatedNoteId = null;

    } catch (e) {
        console.error('sendMeetingInvite error:', e);
        alert('Lỗi: ' + e.message);
        if (btn) { btn.disabled = false; btn.textContent = 'Thêm'; }
    }
}

// ===== XÁC NHẬN VÀ GỬI TASK =====
async function confirmAndSendTask() {
    const select = document.getElementById('assignReceiverSelect');
    if (!select || !select.value) { alert('Vui lòng chọn người nhận!'); return; }

    const receiverId   = parseInt(select.value);
    const receiverName = select.options[select.selectedIndex]?.dataset?.name || 'người này';
    const message      = document.getElementById('assignMsgInput')?.value?.trim() || '';

    // ── Hộp thoại xác nhận ──────────────────────────────────────────
    const confirmed = confirm(`Bạn có chắc chắn muốn gửi công việc cho "${receiverName}" không?`);
    if (!confirmed) return;

    // ── Lấy noteId từ task vừa tạo (lưu ở window.__lastCreatedNoteId) ─
    const noteId = window.__lastCreatedNoteId;
    if (!noteId) {
        alert('Vui lòng nhấn "Thêm" để lưu task trước, rồi mới gửi.');
        return;
    }

    const btn = document.getElementById('assignSendBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Đang gửi...'; }

    try {
        const res = await fetch('/assignments/assign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                note_id:         noteId,
                receiver_ids:    [receiverId],
                message:         message,
                assignment_type: 'task'
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Gửi thất bại');

        // ── Thành công ───────────────────────────────────────────────
        const container = document.getElementById('suggestNextContent');
        if (container) {
            container.innerHTML = `
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 16px;text-align:center;">
                <div style="font-size:22px;margin-bottom:6px;">✅</div>
                <div style="font-size:14px;font-weight:600;color:#15803d;">
                    Đã gửi công việc cho <strong>${esc(receiverName)}</strong>
                </div>
                <div style="font-size:12px;color:#6b7280;margin-top:4px;">
                    ${esc(receiverName)} sẽ nhận được thông báo và có thể xác nhận hoặc từ chối.
                </div>
            </div>`;
        }

        // Reset lastCreatedNoteId để tránh gửi lại
        window.__lastCreatedNoteId = null;

    } catch (e) {
        console.error('sendTask error:', e);
        alert('Gửi thất bại: ' + e.message);
        if (btn) { btn.disabled = false; btn.textContent = '📤 Gửi công việc'; }
    }
}

// ===== NEXT-TEMPLATE CARDS CSS =====
(function injectNextCardCSS() {
    if (document.getElementById('next-card-style')) return;
    const s = document.createElement('style');
    s.id = 'next-card-style';
    s.textContent = `
        /* ── Scroll wrapper ── */
        .next-templates-scroll-container {
            display: flex;
            flex-wrap: nowrap;
            gap: 14px;
            overflow-x: auto;
            padding: 8px 6px 14px 6px;
            scroll-snap-type: x mandatory;
            scrollbar-width: thin;
        }
        .next-templates-scroll-container::-webkit-scrollbar { height: 6px; }
        .next-templates-scroll-container::-webkit-scrollbar-thumb {
            background: #fbbf24;
            border-radius: 999px;
        }

        /* ── Individual card ── */
        .next-template-card {
            flex: 0 0 300px;
            scroll-snap-align: start;
            background: #ffffff !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 22px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            cursor: pointer;
            transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
            min-height: 270px;
            font-family: inherit;
            overflow: hidden;
        }
        .next-template-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.09) !important;
        }
        .next-template-card.selected-active {
            border-color: #ea6f1e !important;
            border-width: 2.5px !important;
            background-color: #fff8f2 !important;
            box-shadow: 0 8px 28px rgba(249,115,22,0.14) !important;
        }

        /* ── Card header ── */
        .next-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            margin-bottom: 14px;
        }
        .next-card-style-badge {
            font-size: 13px;
            font-weight: 700;
            color: #1e3a5f;
            background: none !important;
            padding: 0 !important;
            border-radius: 0 !important;
            text-transform: none !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .next-template-card.selected-active .next-card-style-badge { color: #1e3a5f; }
        .next-card-category-tag {
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            background: #f1f5f9;
            border: 1.5px solid #cbd5e1;
            padding: 4px 12px;
            border-radius: 9999px;
            white-space: nowrap;
            flex-shrink: 0;
        }
        .next-template-card.selected-active .next-card-category-tag {
            color: #ea6f1e;
            background: #fff3e8;
            border-color: #f97316;
        }

        /* ── Subject block: no box, just a gray separator line ── */
        .next-card-subject-box {
            padding-bottom: 12px;
            margin-bottom: 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        .next-template-card.selected-active .next-card-subject-box {
            border-bottom-color: #fcd5a8;
        }
        .next-subject-label {
            font-size: 11px;
            color: #9ca3af;
            font-weight: 600;
            letter-spacing: 0.03em;
            margin-bottom: 4px;
        }
        .next-subject-content {
            font-size: 13px;
            font-weight: 600;
            color: #1e293b;
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        /* ── Body text ── */
        .next-card-body-content {
            font-size: 13px;
            color: #334155;
            line-height: 1.75;
            margin-bottom: 16px;
            display: -webkit-box;
            -webkit-line-clamp: 5;
            -webkit-box-orient: vertical;
            overflow: hidden;
            flex-grow: 1;
            white-space: pre-wrap;
            word-break: break-word;
        }

        /* ── Copy button ── */
        .next-card-actions {
            display: flex;
            justify-content: center;
            margin-top: auto;
        }
        .next-inner-copy-btn {
            width: 100%;
            padding: 10px 0;
            background: #f1f5f9;
            color: #1e3a5f;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            font-family: inherit;
            transition: background .15s, color .15s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .next-inner-copy-btn:hover { background: #e2e8f0; color: #0f172a; }
        .next-inner-copy-btn.copied { background: #10b981; color: #fff; }

        /* ── Hint bar ── */
        .next-scroll-hint-bar {
            font-size: 12px;
            color: #475569;
            text-align: center;
            margin-top: 6px;
            padding: 6px 4px 0;
            border-top: 1px dashed #e2e8f0;
        }
    `;
    document.head.appendChild(s);
})();

function renderTemplateCards(container, templates, category) {
    if (!templates || templates.length === 0) {
        container.innerHTML = '<div class="p-3 text-muted text-xs">Không có mẫu gợi ý nào.</div>';
        return;
    }

    const cardsHTML = templates.map((t, i) => {
        const rawStyle = t.style || 'Mẫu ' + (i + 1);
        // Chuyển sang dạng "Viết hoa chữ đầu, còn lại thường" — hỗ trợ tiếng Việt
        const styleSentenceCase = rawStyle.charAt(0).toLocaleUpperCase('vi') + rawStyle.slice(1).toLocaleLowerCase('vi');
        const styleText = esc(styleSentenceCase);
        const subjectText = esc(t.subject || '');
        const bodyText = esc(t.body || '').replace(/\n/g, '<br>');

        return `
        <div class="next-template-card" onclick="selectTemplateCard(this, ${i})">
            <div class="next-card-header">
                <span class="next-card-style-badge">${styleText}</span>
                <span class="next-card-category-tag">${esc(category)}</span>
            </div>
            <div class="next-card-subject-box">
                <div class="next-subject-label">Tiêu đề email</div>
                <div class="next-subject-content">${subjectText}</div>
            </div>
            <div class="next-card-body-content">${bodyText}</div>
            <div class="next-card-actions">
                <button type="button" class="next-inner-copy-btn" onclick="event.stopPropagation(); copyTemplateByIndex(this, ${i})">
                    <i class="lucide-copy w-3 h-3 inline-block mr-1"></i> Sao chép
                </button>
            </div>
        </div>`;
    }).join('');

    container.innerHTML = `
        <div class="next-templates-scroll-container">
            ${cardsHTML}
        </div>
        <div class="next-scroll-hint-bar" id="nextScrollHint">
            Đang chọn mẫu: <span class="font-semibold text-secondary">Chuyên nghiệp</span> — Nhấn "Thêm" để lưu task
        </div>
    `;

    window.__nextTemplates = templates;

    setTimeout(() => {
        const firstCard = container.querySelector('.next-template-card');
        if (firstCard) selectTemplateCard(firstCard, 0);
    }, 50);
}

function selectTemplateCard(element, index) {
    const container = element.closest('.next-templates-scroll-container');
    if (container) {
        container.querySelectorAll('.next-template-card').forEach(c => c.classList.remove('selected-active'));
    }
    element.classList.add('selected-active');
    window.__selectedTemplateIndex = index;
    window.__selectedTemplate = index;

    const hintBar = document.getElementById('nextScrollHint');
    if (hintBar && window.__nextTemplates && window.__nextTemplates[index]) {
        const currentStyle = window.__nextTemplates[index].style || 'Hiện tại';
        hintBar.innerHTML = `Đang chọn mẫu: <span class="font-semibold text-secondary">${esc(currentStyle)}</span> — Nhấn "Thêm" để lưu với mẫu này`;
    }
}

async function copyTemplateByIndex(button, index) {
    const template = window.__nextTemplates?.[index];
    if (!template) return;

    const textToCopy = `Tiêu đề: ${template.subject || ''}\n\n${template.body || ''}`;
    try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = button.innerHTML;
        button.innerHTML = '✓ Đã chép';
        button.classList.add('copied');
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('copied');
        }, 1500);
    } catch (err) {
        console.error('Lỗi sao chép:', err);
    }
}

function useTemplate(idx) {
    const t = window.__nextTemplates?.[idx];
    if (!t) return;
    // Điền subject vào quickTitle nếu trống, hoặc lưu vào hidden field
    const titleEl = document.getElementById('quickTitle');
    if (titleEl && !titleEl.value.includes(t.subject)) {
        // Không ghi đè input người dùng - chỉ lưu template để dùng sau
    }
    window.__selectedTemplate = idx;
    selectTemplateCard(document.querySelectorAll('.next-template-card')[idx], idx);
}

// ====== CLASSIFY (CŨ) - giữ lại để fallback ======
async function classifyTodo() {
    const text = document.getElementById('quickTitle')?.value || '';
    if (text.trim().length < 3) {
        const box = document.getElementById('classifyResult');
        if (box) box.style.display = 'none';
        return;
    }
    try {
        const res = await fetch('/nextact/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        if (res.ok) {
            const data = await res.json();
            if (document.getElementById('categoryName')) document.getElementById('categoryName').textContent = `📌 ${data.category}`;
            if (document.getElementById('confidenceScore')) document.getElementById('confidenceScore').textContent = `${data.confidence}%`;
            const box = document.getElementById('classifyResult');
            if (box) box.style.display = 'block';
            
            if (data.deadline_display && data.deadline_display !== 'Không có') {
                // Dùng deadline_display từ backend (đã format dd/mm/yyyy HH:MM)
                if (document.getElementById('deadlineValue')) document.getElementById('deadlineValue').textContent = data.deadline_display;
                if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'block';
                const qdd = document.getElementById('quickDueDate');
                if (qdd) qdd.value = data.deadline ? data.deadline.split('T')[0] : '';
            } else {
                if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'none';
                const qdd = document.getElementById('quickDueDate');
                if (qdd) qdd.value = '';
            }
        }
    } catch (e) {
        console.error('Classification error:', e);
    }
}

// ===== PRIORITY CONFIG (cho dropdown Ưu Tiên) =====
const PRIORITY_CONFIG = [
    { value: '4', label: 'Khẩn cấp',   color: '#ef4444' },
    { value: '3', label: 'Cao',         color: '#f97316' },
    { value: '2', label: 'Trung bình',  color: '#3b82f6' },
    { value: '1', label: 'Thấp',        color: '#6b7280' },
];

// ===== Helper: render trigger button cho custom dropdown =====
function _dropdownTriggerHTML(id, dotColor, label, placeholder) {
    return `
    <div id="${id}Trigger" onclick="_toggleCustomDropdown('${id}')"
         style="display:flex;align-items:center;gap:8px;padding:10px 14px;border:1.5px solid #d1d5db;border-radius:8px;cursor:pointer;background:#fff;user-select:none;transition:border .15s;"
         onmouseenter="this.style.borderColor='#196B7C'" onmouseleave="this.style.borderColor=document.getElementById('${id}').value?'#196B7C':'#d1d5db'">
        <span id="${id}Dot" style="width:10px;height:10px;border-radius:50%;background:${dotColor};flex-shrink:0;display:${dotColor?'inline-block':'none'};"></span>
        <span id="${id}Label" style="flex:1;font-size:14px;color:${label?'#1f2937':'#9ca3af'};">${label || placeholder}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
    </div>`;
}

function _toggleCustomDropdown(id) {
    // Đóng tất cả dropdown khác
    document.querySelectorAll('.custom-dd-panel').forEach(p => {
        if (p.id !== id + 'Panel') p.style.display = 'none';
    });
    const panel = document.getElementById(id + 'Panel');
    if (panel) panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
}

// Đóng dropdown khi click ngoài
document.addEventListener('click', function(e) {
    if (!e.target.closest('[id$="Trigger"]') && !e.target.closest('.custom-dd-panel')) {
        document.querySelectorAll('.custom-dd-panel').forEach(p => p.style.display = 'none');
    }
});

async function openEditModal(id) {
    const n = allNotes.find(x => x.id === id);
    if (!n) return;

    editId = id;
    document.getElementById('editTitle').value = n.title;
    document.getElementById('editContent').value = n.content;
    document.getElementById('editDueDate').value = n.due_date ? n.due_date.split('T')[0] : '';

    // ── Inject custom dropdowns lần đầu ──
    if (!document.getElementById('editStatus')) {
        // Ẩn select Ưu Tiên gốc
        const nativePriority = document.getElementById('editPriority');
        if (nativePriority) nativePriority.style.display = 'none';

        // Tìm form để chèn row
        const editForm = document.getElementById('editForm');

        // Tìm nhóm chứa priority gốc
        const priorityGroup = nativePriority?.closest('.form-group') || nativePriority?.closest('div');

        // Build status dropdown panel
        const statusOptionsHTML = Object.entries(TASK_STATUS_CONFIG).map(([key, cfg]) => `
            <div class="edit-dd-option" data-dd="editStatus" data-val="${key}" data-color="${cfg.color}" data-label="${cfg.label}"
                 onclick="_selectDropdownOption('editStatus', '${key}', '${cfg.color}', '${cfg.label}')"
                 style="display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;font-size:14px;color:#374151;transition:background .1s;"
                 onmouseenter="this.style.background='#f9fafb'" onmouseleave="this.style.background=''">
                <span style="width:10px;height:10px;border-radius:50%;background:${cfg.color};flex-shrink:0;display:inline-block;"></span>
                <span>${cfg.label}</span>
            </div>`).join('');

        // Build priority dropdown panel
        const priorityOptionsHTML = PRIORITY_CONFIG.map(p => `
            <div class="edit-dd-option" data-dd="editPriorityCustom" data-val="${p.value}" data-color="${p.color}" data-label="${p.label}"
                 onclick="_selectDropdownOption('editPriorityCustom', '${p.value}', '${p.color}', '${p.label}')"
                 style="display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;font-size:14px;color:#374151;transition:background .1s;"
                 onmouseenter="this.style.background='#f9fafb'" onmouseleave="this.style.background=''">
                <span style="width:10px;height:10px;border-radius:50%;background:${p.color};flex-shrink:0;display:inline-block;"></span>
                <span>${p.label}</span>
            </div>`).join('');

        const rowHTML = `
        <div id="statusPriorityRow" style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px;">
            <div style="position:relative;">
                <label style="display:block;font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">Trạng Thái</label>
                ${_dropdownTriggerHTML('editStatus', '', '', 'Chọn trạng thái')}
                <div id="editStatusPanel" class="custom-dd-panel"
                     style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1.5px solid #e5e7eb;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.12);z-index:999;overflow-y:auto;max-height:220px;">
                    ${statusOptionsHTML}
                </div>
                <input type="hidden" id="editStatus" value="">
            </div>
            <div style="position:relative;">
                <label style="display:block;font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">Ưu Tiên</label>
                ${_dropdownTriggerHTML('editPriorityCustom', '', '', 'Chọn mức ưu tiên')}
                <div id="editPriorityCustomPanel" class="custom-dd-panel"
                     style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;background:#fff;border:1.5px solid #e5e7eb;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.12);z-index:999;overflow:hidden;">
                    ${priorityOptionsHTML}
                </div>
                <input type="hidden" id="editPriorityCustom" value="">
            </div>
        </div>`;

        // Chèn trước nhóm priority gốc (hoặc trước div đầu tiên)
        if (priorityGroup) {
            priorityGroup.insertAdjacentHTML('beforebegin', rowHTML);
        } else {
            const firstDiv = editForm?.querySelector('div');
            if (firstDiv) firstDiv.insertAdjacentHTML('beforebegin', rowHTML);
        }
    }

    // ── Set current status ──
    const currentStatus = getTaskStatusLocal(n.id);
    if (currentStatus && TASK_STATUS_CONFIG[currentStatus]) {
        const cfg = TASK_STATUS_CONFIG[currentStatus];
        _selectDropdownOption('editStatus', currentStatus, cfg.color, cfg.label);
    } else {
        _resetDropdown('editStatus', 'Chọn trạng thái');
    }

    // ── Set current priority ──
    const currentPriority = String(n.priority || '2');
    const priCfg = PRIORITY_CONFIG.find(p => p.value === currentPriority);
    if (priCfg) {
        _selectDropdownOption('editPriorityCustom', priCfg.value, priCfg.color, priCfg.label);
    } else {
        _resetDropdown('editPriorityCustom', 'Chọn mức ưu tiên');
    }

    document.getElementById('editModal').classList.add('show');
}

function _selectDropdownOption(ddId, val, color, label) {
    // Cập nhật hidden input
    const hidden = document.getElementById(ddId);
    if (hidden) hidden.value = val;
    // Cập nhật trigger
    const dot = document.getElementById(ddId + 'Dot');
    const lbl = document.getElementById(ddId + 'Label');
    if (dot) { dot.style.background = color; dot.style.display = 'inline-block'; }
    if (lbl) { lbl.textContent = label; lbl.style.color = '#1f2937'; }
    // Đổi border màu trigger
    const trigger = document.getElementById(ddId + 'Trigger');
    if (trigger) trigger.style.borderColor = color || '#196B7C';
    // Đóng panel
    const panel = document.getElementById(ddId + 'Panel');
    if (panel) panel.style.display = 'none';
}

function _resetDropdown(ddId, placeholder) {
    const hidden = document.getElementById(ddId);
    if (hidden) hidden.value = '';
    const dot = document.getElementById(ddId + 'Dot');
    const lbl = document.getElementById(ddId + 'Label');
    if (dot) dot.style.display = 'none';
    if (lbl) { lbl.textContent = placeholder; lbl.style.color = '#9ca3af'; }
    const trigger = document.getElementById(ddId + 'Trigger');
    if (trigger) trigger.style.borderColor = '#d1d5db';
}

function _showDotTooltip(el) {
    const tip = el.querySelector('.dot-tooltip');
    if (tip) tip.style.display = 'block';
}
function _hideDotTooltip(el) {
    const tip = el.querySelector('.dot-tooltip');
    if (tip) tip.style.display = 'none';
}

// ── Global fixed tooltip (thoát khỏi overflow:hidden của card) ──
(function _initGlobalTooltip() {
    if (document.getElementById('_globalDotTip')) return;
    const tip = document.createElement('div');
    tip.id = '_globalDotTip';
    tip.style.cssText = 'position:fixed;display:none;background:none;color:#6b7280;font-size:11px;font-weight:500;white-space:nowrap;pointer-events:none;z-index:9999;transform:translateX(-50%);';
    document.body.appendChild(tip);
})();

function _showFixedTooltip(e, text) {
    const tip = document.getElementById('_globalDotTip');
    if (!tip) return;
    const r = e.currentTarget.getBoundingClientRect();
    tip.textContent = text;
    tip.style.display = 'block';
    tip.style.left = (r.left + r.width / 2) + 'px';
    tip.style.top = (r.top - 26) + 'px';
}
function _hideFixedTooltip() {
    const tip = document.getElementById('_globalDotTip');
    if (tip) tip.style.display = 'none';
}

async function updateNote(e) {
    e.preventDefault();

    // Lấy priority từ custom dropdown hoặc native select
    const priorityVal = parseInt(
        document.getElementById('editPriorityCustom')?.value ||
        document.getElementById('editPriority')?.value || '2'
    );

    // Lưu status vào localStorage (UI-only, không gửi server)
    const newStatus = document.getElementById('editStatus')?.value;
    if (newStatus && editId) setTaskStatusLocal(editId, newStatus);

    const payload = {
        title:    document.getElementById('editTitle').value.trim(),
        content:  document.getElementById('editContent').value.trim() || null,
        status:   newStatus || 'todo',
        priority: priorityVal,
        due_date: document.getElementById('editDueDate').value || null,
    };

    try {
        const res = await fetch(`/notes/${editId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            closeEditModal();
            loadNotes();
        } else {
            const err = await res.json().catch(() => ({}));
            alert('Lỗi cập nhật: ' + (err.detail || 'Thử lại sau'));
        }
    } catch (e) {
        alert('Lỗi kết nối');
    }
}

async function delNote(id) {
    if (!confirm('Bạn chắc chắn muốn xóa ghi chú này?')) return;
    try {
        const res = await fetch(`/notes/${id}`, {
            method: 'DELETE',
            credentials: 'include'  // Gửi cookie tự động
        });
        if (res.ok) {
            loadNotes();
        } else {
            alert('Lỗi xóa ghi chú');
        }
    } catch (e) {
        alert('Lỗi kết nối');
    }
}

function openAddNoteModal() { 
    document.getElementById('addModal').classList.add('show'); 
    // Reset summarize panel
    const placeholder = document.getElementById('summarizePlaceholder');
    const loading = document.getElementById('summarizeLoading');
    const result = document.getElementById('summarizeResult');
    if (placeholder) placeholder.style.display = 'flex';
    if (loading) loading.style.display = 'none';
    if (result) result.style.display = 'none';
    window.__summarizeResult = null;
    window.__suggestedTasks = [];
}

function closeAddNoteModal() { 
    document.getElementById('addModal').classList.remove('show'); 
    document.getElementById('addForm').reset();
    // Reset summarize panel
    const placeholder = document.getElementById('summarizePlaceholder');
    const loading = document.getElementById('summarizeLoading');
    const result = document.getElementById('summarizeResult');
    if (placeholder) placeholder.style.display = 'flex';
    if (loading) loading.style.display = 'none';
    if (result) result.style.display = 'none';
    window.__summarizeResult = null;
    window.__suggestedTasks = [];
    // Reset active project context
    window.__activeProjectId   = null;
    window.__activeProjectName = null;
}

function openQuickAddModal() { 
    // Nếu KHÔNG được gọi từ openQuickAddModalInProject thì reset project context
    if (!window.__calledFromProject) {
        window.__activeProjectId   = null;
        window.__activeProjectName = null;
    }
    window.__calledFromProject = false;

    document.getElementById('quickModal').classList.add('show'); 

    // reset UI phụ
    const classifyBox = document.getElementById('classifyResult');
    const suggestBox = document.getElementById('suggestResult');
    if (classifyBox) classifyBox.style.display = 'none';
    if (suggestBox) suggestBox.style.display = 'none';
    const nextContent = document.getElementById('suggestNextContent');
    if (nextContent) nextContent.innerHTML = '';
    window.__quickSuggest = null;
}

function closeQuickAddModal() { 
    document.getElementById('quickModal').classList.remove('show'); 
    document.getElementById('quickForm').reset(); 

    const classifyBox = document.getElementById('classifyResult');
    const suggestBox = document.getElementById('suggestResult');
    if (classifyBox) classifyBox.style.display = 'none';
    if (suggestBox) suggestBox.style.display = 'none';

    const deadlineResult = document.getElementById('deadlineResult');
    if (deadlineResult) deadlineResult.style.display = 'none';

    // Reset NER preview
    clearTimeout(nerPreviewTimer);
    const nerPreviewBox = document.getElementById('nerPreviewBox');
    if (nerPreviewBox) { nerPreviewBox.innerHTML = ''; nerPreviewBox.style.display = 'none'; }
    const nerLegend = document.getElementById('nerLegend');
    if (nerLegend) nerLegend.classList.remove('show');

    // Dừng voice nếu đang ghi
    if (__voiceActive && __voiceRecognition) {
        __voiceRecognition.stop();
    }
    const micBtn = document.getElementById('micBtn');
    const voiceStatus = document.getElementById('voiceStatus');
    if (micBtn) micBtn.classList.remove('recording');
    if (voiceStatus) { voiceStatus.textContent = ''; voiceStatus.classList.remove('active'); }

    window.__quickSuggest = null;
    window.__executionData = null;
    window.__attendeesData = [];
    window.__meetingAttendees = [];
    window.__calendarLink  = null;
    const qdd = document.getElementById('quickDueDate');
    if (qdd) qdd.value = '';
    const hPri = document.getElementById('quickSuggestedPriority');
    const hCat = document.getElementById('quickSuggestedCategory');
    const hConf = document.getElementById('quickSuggestedConfidence');
    if (hPri) hPri.value = '';
    if (hCat) hCat.value = '';
    if (hConf) hConf.value = '';

    // Reset active project context sau khi đóng modal
    window.__activeProjectId   = null;
    window.__activeProjectName = null;
}

function closeEditModal() { 
    document.getElementById('editModal').classList.remove('show'); 
}

function openDetailModal(id) {
    const n = allNotes.find(x => x.id === id);
    if (!n) return;

    document.getElementById('detailTitle').textContent = n.title;

    // Render NỘI DUNG: form đẹp nếu là template, plain text nếu không
    const contentEl = document.getElementById('detailContent');
    const raw = (n.content || '').trim();

    // Detect template bằng string check
    const isTemplate = raw.startsWith('[') && raw.indexOf(']') > 0 && raw.includes('Tiêu đề:');

    if (isTemplate) {
        // Parse [style]
        const closeBracket = raw.indexOf(']');
        const styleLabel = raw.slice(1, closeBracket).trim();
        const afterBracket = raw.slice(closeBracket + 1).replace(/^\n/, '');

        // Parse "Nhãn: ..." nếu có
        let categoryLabel = '';
        let remainder = afterBracket;
        const nhanMatch = afterBracket.match(/^Nhãn:\s*(.+)\n/);
        if (nhanMatch) {
            categoryLabel = nhanMatch[1].trim();
            remainder = afterBracket.slice(nhanMatch[0].length);
        }

        // Parse "Tiêu đề: ..."
        const tieudeLbl = 'Ti\u00eau \u0111\u1ec1:';
        const tieudeIdx = remainder.indexOf('Ti\u00eau \u0111\u1ec1:');
        const subjectStart = tieudeIdx !== -1 ? tieudeIdx + 'Ti\u00eau \u0111\u1ec1:'.length : -1;
        const subjectEnd   = subjectStart !== -1 ? remainder.indexOf('\n', subjectStart) : -1;
        const subject = subjectStart !== -1
            ? (subjectEnd !== -1 ? remainder.slice(subjectStart, subjectEnd) : remainder.slice(subjectStart)).trim()
            : '';

        // Body: toàn bộ phần sau dòng subject
        const bodyStart = subjectEnd !== -1 ? subjectEnd + 1 : (subjectStart !== -1 ? remainder.length : 0);
        const body = remainder.slice(bodyStart).replace(/^[\r\n]+/, '').trim();

        const sep = '<div style="height:1px;background:#e5e7eb;margin:0;"></div>';

        const nhanRow = categoryLabel
            ? sep +
              '<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;">' +
                '<span style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;min-width:80px;">Nhãn</span>' +
                '<span style="font-size:13px;font-weight:600;color:#64748b;background:#f1f5f9;border:1.5px solid #cbd5e1;padding:3px 12px;border-radius:9999px;">' + esc(categoryLabel) + '</span>' +
              '</div>'
            : '';

        // Body: hiển thị nội dung thư hoặc thông báo trống
        const bodyHtml = body
            ? '<div style="line-height:1.7;white-space:pre-wrap;color:#374151;overflow-wrap:break-word;">' + esc(body) + '</div>'
            : '<div style="color:#9ca3af;font-style:italic;font-size:12px;">Không có nội dung thư</div>';

        contentEl.innerHTML =
            '<div style="border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;font-size:13px;color:#374151;">' +
              // Tầng 1: Phong cách + Nhãn (header row)
              '<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:#f8fafc;">' +
                '<span style="font-size:13px;font-weight:700;color:#1e3a5f;">' + esc(styleLabel) + '</span>' +
                (categoryLabel
                  ? '<span style="font-size:12px;font-weight:600;color:#64748b;background:#f1f5f9;border:1.5px solid #cbd5e1;padding:3px 10px;border-radius:9999px;">' + esc(categoryLabel) + '</span>'
                  : '') +
              '</div>' +
              sep +
              // Tầng 2: Tiêu đề email
              (subject
                ? '<div style="padding:10px 14px 8px;">' +
                    '<div style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Tiêu đề email</div>' +
                    '<div style="font-weight:600;color:#1e3a5f;font-size:14px;line-height:1.5;">' + esc(subject) + '</div>' +
                  '</div>' +
                  sep
                : '') +
              // Tầng 3: Nội dung thư (body)
              '<div style="padding:12px 14px;">' +
                bodyHtml +
              '</div>' +
            '</div>';
    } else if (raw) {
        contentEl.innerHTML = '<p style="color:#6b7280;margin:0;line-height:1.6;">' + esc(raw) + '</p>';
    } else {
        contentEl.innerHTML = '<p style="color:#d1d5db;margin:0;font-style:italic;">Không có nội dung</p>';
    }
    document.getElementById('detailPriority').textContent = ['', 'Thấp', 'Trung Bình', 'Cao'][n.priority];
    const detailTitleMetaText = document.getElementById('detailTitleMetaText');
    if (detailTitleMetaText) detailTitleMetaText.textContent = n.title || '';
    
    // Thêm trạng thái vào detail modal
    const statusKey2 = getTaskStatusLocal(n.id);
    const statusCfg2 = statusKey2 ? TASK_STATUS_CONFIG[statusKey2] : null;
    const detailStatusEl = document.getElementById('detailStatusLabel');
    if (detailStatusEl) {
        if (statusCfg2) {
            detailStatusEl.innerHTML = `
                <span style="display:inline-flex;align-items:center;gap:6px;">
                    <span style="width:10px;height:10px;border-radius:50%;background:${statusCfg2.color};display:inline-block;"></span>
                    <span style="font-weight:600;color:${statusCfg2.color};">${statusCfg2.label}</span>
                </span>`;
        } else {
            detailStatusEl.innerHTML = '<span style="color:#9ca3af;">Chưa đặt</span>';
        }
    }
    
    // Format due_date nếu có
    if (n.due_date) {
        // due_date có thể là "2026-04-03" hoặc "2026-04-03T09:00:00"
        if (n.due_date.includes('T')) {
            // Có giờ: format thành "03/04/2026 09:00"
            const dt = new Date(n.due_date);
            const day = String(dt.getDate()).padStart(2, '0');
            const month = String(dt.getMonth() + 1).padStart(2, '0');
            const year = dt.getFullYear();
            const hours = String(dt.getHours()).padStart(2, '0');
            const mins = String(dt.getMinutes()).padStart(2, '0');
            document.getElementById('detailDueDate').textContent = `${day}/${month}/${year} ${hours}:${mins}`;
        } else {
            // Chỉ có ngày
            document.getElementById('detailDueDate').textContent = n.due_date;
        }
    } else {
        document.getElementById('detailDueDate').textContent = 'Không có';
    }
    
    document.getElementById('detailCreatedAt').textContent = formatDate(n.created_at);
    
    if (n.is_quick_add) {
        document.getElementById('detailQuickAdd').style.display = 'block';
    } else {
        document.getElementById('detailQuickAdd').style.display = 'none';
    }

    // ── Trạng Thái: màu sắc + tiến độ ──
    updateDetailStatusSection(n.id);
    
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '<div class="chat-msg bot-msg">Hỏi tôi về cách chuẩn bị cho công việc này!</div>';
    }
    
    window.currentDetailId = id;
    document.getElementById('detailModal').classList.add('show');
    loadAiSummary(n);
}

async function loadAiSummary(note) {
    const box     = document.getElementById('aiSummaryBox');
    const loading = document.getElementById('aiSummaryLoading');
    const cont    = document.getElementById('aiSummaryContent');
    const sumEl   = document.getElementById('aiSummaryText');
    const hlBox   = document.getElementById('aiHighlightsBox');
    const hlList  = document.getElementById('aiHighlightsList');
    if (!box) return;

    box.style.display     = 'block';
    loading.style.display = 'block';
    cont.style.display    = 'none';
    if (hlBox)  hlBox.style.display  = 'none';
    if (hlList) hlList.innerHTML     = '';

    try {
        const res = await fetch('/nextact/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_title: note.title, task_description: note.content || '',
                due_date: note.due_date || '',
                message: 'Tóm tắt ngắn gọn 1 câu nội dung công việc và nêu 2-3 điểm quan trọng cần lưu ý.'
            })
        });
        loading.style.display = 'none';
        // Gemini 503/unavailable → ẩn box, không báo lỗi đỏ
        if (!res.ok) { box.style.display = 'none'; return; }
        const data = await res.json();
        cont.style.display = 'block';
        if (sumEl) sumEl.textContent = data.summary || '';
        const highlights = Array.isArray(data.highlights) ? data.highlights : [];
        if (hlBox && hlList && highlights.length > 0) {
            hlBox.style.display  = 'block';
            hlList.innerHTML = highlights.map(h => `
                <div style="background:#f0f4ff;border-left:3px solid #2c5f7d;border-radius:6px;padding:7px 12px;font-size:13px;color:#1e3a5f;line-height:1.5;">
                    ${esc(h)}
                </div>`).join('');
        }
    } catch(e) {
        loading.style.display = 'none';
        box.style.display     = 'none';
    }
}

function closeDetailModal() {
    const modal = document.getElementById('detailModal');
    if (!modal) return;
    modal.classList.remove('show');
    modal.style.display = 'none';
    if (typeof window !== 'undefined') window.currentDetailId = null;
}

function openEditModalFromDetail() {
    closeDetailModal();
    openEditModal(window.currentDetailId);
}

function deleteAndClose() {
    if (confirm('Bạn chắc chắn muốn xóa ghi chú này?')) {
        delNote(window.currentDetailId);
        closeDetailModal();
    }
}

function renderMarkdown(text) {
    if (!text) return '';
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    const n = allNotes.find(x => x.id === window.currentDetailId);
    if (!n) return;
    
    const messagesDiv = document.getElementById('chatMessages');
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user-msg';
    userMsg.textContent = message;
    messagesDiv.appendChild(userMsg);
    
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    typingIndicator.id = 'typingIndicator';
    messagesDiv.appendChild(typingIndicator);
    
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    try {
        const res = await fetch('/nextact/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_title: n.title,
                task_description: n.content || '',
                due_date: n.due_date || '',
                message: message
            })
        });
        
        const typingEl = document.getElementById('typingIndicator');
        if (typingEl) typingEl.remove();
        
        if (res.ok) {
            const data = await res.json();
            const botMsg = document.createElement('div');
            botMsg.className = 'chat-msg bot-msg';
            
            let html = '';

            // Hiển thị tóm tắt nếu có (bỏ icon)
            if (data.summary) {
                html += `<div class="chat-summary" style="font-weight:600; margin-bottom:8px; color:#1e3a5f; font-size:13px;">${esc(data.summary)}</div>`;
            }

            // Hiển thị highlights nếu có (bỏ icon)
            if (data.highlights && data.highlights.length > 0) {
                html += '<div style="margin-bottom:8px;">';
                data.highlights.forEach(h => {
                    html += `<div style="background:#f0f4ff;border-left:3px solid #2c5f7d;border-radius:6px;padding:6px 10px;font-size:12px;color:#1e3a5f;margin-bottom:4px;">${esc(h)}</div>`;
                });
                html += '</div>';
            }
            
            // Reply với highlight nếu có highlights
            let replyHtml = renderMarkdown(data.reply);
            if (data.highlights && data.highlights.length > 0) {
                data.highlights.forEach(h => {
                    const escaped = esc(h);
                    replyHtml = replyHtml.replace(new RegExp(escaped, 'gi'), `<mark style="background-color: #fef3c7; padding: 2px 4px; border-radius: 3px;">${escaped}</mark>`);
                });
            }
            html += replyHtml;
            
            botMsg.innerHTML = html;
            messagesDiv.appendChild(botMsg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        } else {
            const errMsg = document.createElement('div');
            errMsg.className = 'chat-msg error-msg';
            errMsg.textContent = 'Lỗi: Không thể lấy gợi ý';
            messagesDiv.appendChild(errMsg);
        }
    } catch (e) {
        const typingEl = document.getElementById('typingIndicator');
        if (typingEl) typingEl.remove();
        
        const errMsg = document.createElement('div');
        errMsg.className = 'chat-msg error-msg';
        errMsg.textContent = 'Lỗi kết nối: ' + e.message;
        messagesDiv.appendChild(errMsg);
    }
}

// Enter key to send message
if (document.getElementById('chatInput')) {
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && document.getElementById('chatInput') === document.activeElement) {
            sendChatMessage();
        }
    });
}

function logout() { 
    if (confirm('Bạn muốn đăng xuất?')) {
        // Xóa cookie phía client (nếu không httpOnly) rồi redirect về login
        document.cookie = 'access_token=; Max-Age=0; path=/';
        location.href = '/login';
    }
}

// ===== FILTER & SEARCH FUNCTIONS =====
let currentFilters = {};

function toggleFilters() {
    const content = document.getElementById('filtersContent');
    const toggleText = document.getElementById('toggleText');
    if (!content || !toggleText) return;

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggleText.textContent = 'Thu gọn';
    } else {
        content.style.display = 'none';
        toggleText.textContent = 'Mở rộng';
    }
}

function handleSearch() {
    const input = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    if (!input || !clearBtn) return;
    
    if (input.value.length > 0) {
        clearBtn.classList.add('show');
    } else {
        clearBtn.classList.remove('show');
    }
    
    applyFilters();
}

function clearSearch() {
    const input = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    if (!input || !clearBtn) return;

    input.value = '';
    clearBtn.classList.remove('show');
    applyFilters();
}

function applyFilters() {
    const searchEl = document.getElementById('searchInput');
    const priorityEl = document.getElementById('priorityFilter');
    const deadlineEl = document.getElementById('deadlineFilter');
    const typeEl = document.getElementById('typeFilter');
    const grid = document.getElementById('notesGrid');

    if (!grid) return;

    const searchTerm = searchEl ? searchEl.value.toLowerCase() : '';
    const priority   = priorityEl ? priorityEl.value : '';
    const deadline   = deadlineEl ? deadlineEl.value : '';
    const type       = typeEl ? typeEl.value : '';

    // Header filter state
    const hf = window.__headerFilters || {};

    currentFilters = { search: searchTerm, priority, deadline, type };

    let visibleCount = 0;
    const cards = grid.querySelectorAll('.note-card');

    cards.forEach(card => {
        let show = true;
        const onclickAttr = card.getAttribute('onclick') || '';
        const match = onclickAttr.match(/\d+/);
        const noteId = match ? parseInt(match[0]) : null;
        const note = allNotes.find(n => n.id === noteId);

        if (!note) {
            show = false;
        } else {
            // Search
            if (searchTerm && !note.title.toLowerCase().includes(searchTerm)) show = false;

            // Priority (header filter takes precedence over select box)
            const rawPri = (hf.priority !== null && hf.priority !== undefined) ? hf.priority : priority;
            if (rawPri !== '' && rawPri !== null && rawPri !== undefined) {
                const notePri = (note.priority !== null && note.priority !== undefined) ? parseInt(note.priority) : 1;
                if (notePri !== parseInt(rawPri)) show = false;
            }

            // Type
            if (type === 'quick' && !note.is_quick_add) show = false;
            else if (type === 'normal' && note.is_quick_add) show = false;

            // Header extended status filter
            if (hf.status) {
                const taskStatus = getTaskStatusLocal(note.id) || 'draft';
                if (taskStatus !== hf.status) show = false;
            }

            // Header label filter
            if (hf.label) {
                const content = (note.content || '').toLowerCase();
                if (!content.includes(hf.label.toLowerCase()) && !note.title.toLowerCase().includes(hf.label.toLowerCase())) show = false;
            }

            // Header date range filter
            if (hf.dateRange) {
                const now = new Date();
                const createdAt = new Date(note.created_at);
                let daysAgo = 0;
                if (hf.dateRange === '7') daysAgo = 7;
                else if (hf.dateRange === '14') daysAgo = 14;
                else if (hf.dateRange === '60') daysAgo = 60;
                else if (hf.dateRange === 'custom' && hf.dateRangeStart && hf.dateRangeEnd) {
                    const start = new Date(hf.dateRangeStart);
                    const end   = new Date(hf.dateRangeEnd); end.setHours(23,59,59);
                    if (createdAt < start || createdAt > end) show = false;
                    daysAgo = 0;
                }
                if (daysAgo > 0) {
                    const cutoff = new Date(now.getTime() - daysAgo * 86400000);
                    if (createdAt < cutoff) show = false;
                }
            }

            // Header sort is handled by re-sorting allNotes, not hiding
            // Deadline filter (select box)
            if (deadline && note.due_date) {
                const today = new Date(); today.setHours(0,0,0,0);
                const taskDate = new Date(note.due_date); taskDate.setHours(0,0,0,0);
                if (deadline === 'today') { if (taskDate.getTime() !== today.getTime()) show = false; }
                else if (deadline === 'tomorrow') {
                    const tm = new Date(today); tm.setDate(tm.getDate() + 1);
                    if (taskDate.getTime() !== tm.getTime()) show = false;
                } else if (deadline === 'week') {
                    const wl = new Date(today); wl.setDate(wl.getDate() + 7);
                    if (taskDate > wl) show = false;
                } else if (deadline === 'month') {
                    const ml = new Date(today); ml.setMonth(ml.getMonth() + 1);
                    if (taskDate > ml) show = false;
                }
            } else if (deadline === 'none' && note.due_date) {
                show = false;
            } else if (deadline && deadline !== 'none' && !note.due_date) {
                show = false;
            }
        }

        if (show) { card.classList.remove('hidden'); visibleCount++; }
        else       { card.classList.add('hidden'); }
    });

    updateResultCount(visibleCount);
    updateActiveFilters();
}

function resetFilters() {
    const searchEl = document.getElementById('searchInput');
    const priorityEl = document.getElementById('priorityFilter');
    const deadlineEl = document.getElementById('deadlineFilter');
    const typeEl = document.getElementById('typeFilter');
    const clearBtn = document.getElementById('clearSearch');

    if (!searchEl || !priorityEl || !deadlineEl || !typeEl || !clearBtn) return;

    searchEl.value = '';
    priorityEl.value = '';
    deadlineEl.value = '';
    typeEl.value = '';
    clearBtn.classList.remove('show');
    
    currentFilters = {};
    applyFilters();
}

function updateActiveFilters() {
    const container = document.getElementById('activeFilters');
    if (!container) return;

    container.innerHTML = '';

    const labels = {
        priority: { '3': 'Ưu tiên: Cao', '2': 'Ưu tiên: Trung bình', '1': 'Ưu tiên: Thấp' },
        deadline: {
            'today': 'Hôm nay',
            'tomorrow': 'Ngày mai',
            'week': 'Tuần này',
            'month': 'Tháng này',
            'none': 'Không có hạn'
        },
        type: {
            'quick': 'Tạo nhanh',
            'normal': 'Thường'
        }
    };

    Object.keys(currentFilters).forEach(key => {
        if (currentFilters[key] && key !== 'search') {
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `
                ${labels[key][currentFilters[key]] || currentFilters[key]}
                <button onclick="removeFilter('${key}')">×</button>
            `;
            container.appendChild(tag);
        }
    });

    if (currentFilters.search) {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        tag.innerHTML = `
            Tìm kiếm: "${currentFilters.search}"
            <button onclick="clearSearch()">×</button>
        `;
        container.appendChild(tag);
    }
}

function removeFilter(key) {
    const el = document.getElementById(key + 'Filter');
    if (!el) return;
    el.value = '';
    applyFilters();
}

function updateResultCount(count) {
    const el = document.getElementById('resultCount');
    if (!el) return;

    if (count === undefined) {
        count = allNotes.length;
    }
    el.textContent = count;
}

function sortBy(type) {
    // vì onclick không truyền event, dùng window.event để tương thích
    const e = window.event;
    const target = e && e.target ? e.target : null;

    document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
    if (target && target.classList) target.classList.add('active');

    allNotes.sort((a, b) => {
        if (type === 'deadline') {
            const dateA = a.due_date || '9999-12-31';
            const dateB = b.due_date || '9999-12-31';
            return dateA.localeCompare(dateB);
        } else if (type === 'priority') {
            return b.priority - a.priority;
        } else if (type === 'created') {
            return new Date(b.created_at) - new Date(a.created_at);
        }
        return 0;
    });

    renderNotes();
    applyFilters(); // Re-apply filters after sorting
}



// Mở Google Calendar trong tab mới
function openGoogleCalendar() {
    window.open('https://calendar.google.com', '_blank');
}

// ===== HOME SUMMARY =====
async function loadHomeSummary() {
    const overdueBody = document.getElementById('overdueListBody');
    if (!overdueBody) return;

    try {
        const res = await fetch('/notes', {
            credentials: 'include'  // Gửi cookie tự động
        });
        if (!res.ok) {
            if (res.status === 401) {
                window.location.href = '/login';
            }
            return;
        }

        const notes = await res.json();
        const now = new Date();

        // Lọc các task đã quá hạn (due_date < hôm nay)
        const overdue = notes.filter(n => {
            if (!n.due_date) return false;
            const d = new Date(n.due_date);
            return d < now;
        }).sort((a, b) => new Date(a.due_date) - new Date(b.due_date));

        if (overdue.length === 0) {
            overdueBody.innerHTML = `
                <div class="placeholder-text">
                    <strong>(Hiện tại chưa có việc nào trễ hạn)</strong>
                    <span>Các công việc đã quá hạn sẽ hiển thị ở đây</span>
                </div>`;
            return;
        }

        overdueBody.innerHTML = overdue.map(n => {
            const priorityColors = { 3: '#ef4444', 2: '#f97316', 1: '#6b7280' };
            const priorityLabels = { 3: 'Cao', 2: 'Trung bình', 1: 'Thấp' };
            const p = Number(n.priority) || 2;
            const daysOverdue = Math.floor((now - new Date(n.due_date)) / (1000 * 60 * 60 * 24));

            return `
            <div style="
                background: #fff5f5;
                border: 1px solid #fecaca;
                border-left: 4px solid #ef4444;
                border-radius: 10px;
                padding: 10px 14px;
                margin-bottom: 10px;
                cursor: pointer;
                transition: box-shadow 0.2s;
            " onclick="window.location.href='/tasks'" onmouseover="this.style.boxShadow='0 2px 8px rgba(239,68,68,0.15)'" onmouseout="this.style.boxShadow='none'">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                    <strong style="font-size:13px; color:#1e3a5f; line-height:1.4; flex:1;">${esc(n.title)}</strong>
                    <span style="font-size:11px; font-weight:700; color:white; background:${priorityColors[p]}; padding:2px 8px; border-radius:20px; white-space:nowrap; flex-shrink:0;">${priorityLabels[p]}</span>
                </div>
                <div style="margin-top:6px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:12px; color:#ef4444; font-weight:600;">📅 Hạn: ${formatDate(n.due_date)}</span>
                    <span style="font-size:11px; color:#9ca3af;">Trễ ${daysOverdue} ngày</span>
                </div>
            </div>`;
        }).join('');

    } catch (e) {
        console.error('loadHomeSummary error:', e);
    }
}

// ===== VOICE INPUT =====
function toggleVoiceInput() {
    const micBtn      = document.getElementById('micBtn');
    const voiceStatus = document.getElementById('voiceStatus');
    const input       = document.getElementById('quickTitle');

    // Kiểm tra hỗ trợ
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        if (voiceStatus) voiceStatus.textContent = '⚠️ Trình duyệt chưa hỗ trợ. Dùng Chrome/Edge.';
        return;
    }

    // Đang ghi → dừng
    if (__voiceActive) {
        if (__voiceRecognition) __voiceRecognition.stop();
        __voiceActive = false;
        if (micBtn)      micBtn.classList.remove('recording');
        if (voiceStatus) { voiceStatus.textContent = ''; voiceStatus.classList.remove('active'); }
        return;
    }

    // Khởi tạo mới
    __voiceRecognition = new SR();
    __voiceRecognition.lang            = 'vi-VN';
    __voiceRecognition.continuous      = false;  // false để tương thích Safari/Chrome macOS
    __voiceRecognition.interimResults  = true;
    __voiceRecognition.maxAlternatives = 1;

    // Bắt đầu
    __voiceRecognition.onaudiostart = () => {
        if (voiceStatus) voiceStatus.textContent = 'Đã kết nối mic, đang nghe...';
    };

    __voiceRecognition.onstart = () => {
        __voiceActive = true;
        if (micBtn)      micBtn.classList.add('recording');
        if (voiceStatus) {
            voiceStatus.textContent = '🎙 Đang nghe... (bấm mic lần nữa để dừng)';
            voiceStatus.classList.add('active');
        }
    };

    // Nhận kết quả — ghi vào input ngay
    __voiceRecognition.onresult = (event) => {
        let finalText   = '';
        let interimText = '';

        for (let i = 0; i < event.results.length; i++) {
            const t = event.results[i][0].transcript;
            if (event.results[i].isFinal) finalText   += t;
            else                          interimText += t;
        }

        // Ưu tiên hiển thị final, fallback interim
        if (input) {
            input.value = finalText || interimText;
        }

        // Cập nhật status với interim để người dùng thấy đang nhận diện
        if (voiceStatus && interimText) {
            voiceStatus.textContent = `🎙 ${interimText}`;
        }

        // Khi có final text → trigger AI phân loại
        if (finalText.trim().length >= 3) {
            input.dispatchEvent(new Event('input', { bubbles: true }));
            if (voiceStatus) {
                voiceStatus.textContent = 'Đã nhận: ' + finalText.trim();
            }
        }
    };

    // Kết thúc - tự restart nếu người dùng chưa dừng thủ công
    __voiceRecognition.onend = () => {
        if (__voiceActive) {
            // Restart để ghi âm liên tục (continuous=false workaround)
            try { __voiceRecognition.start(); return; } catch(e) {}
        }
        __voiceActive = false;
        if (micBtn)      micBtn.classList.remove('recording');
        if (voiceStatus) {
            voiceStatus.classList.remove('active');
            setTimeout(() => { if (voiceStatus) voiceStatus.textContent = ''; }, 2000);
        }
        if (input && input.value.trim().length >= 3) {
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };

    // Lỗi
    __voiceRecognition.onerror = (event) => {
        __voiceActive = false;
        if (micBtn) micBtn.classList.remove('recording');

        const errorMap = {
            'not-allowed' : '⚠️ Chưa cấp quyền micro. Kiểm tra cài đặt trình duyệt.',
            'no-speech'   : '⚠️ Không nghe thấy giọng nói, thử lại.',
            'network'     : '⚠️ Lỗi mạng. Cần HTTPS hoặc localhost.',
            'aborted'     : '',   // người dùng tự dừng, không cần báo lỗi
            'audio-capture': '⚠️ Không tìm thấy micro trên thiết bị.',
        };
        const msg = errorMap[event.error] !== undefined
            ? errorMap[event.error]
            : `⚠️ Lỗi nhận diện: ${event.error}`;

        if (voiceStatus) {
            voiceStatus.classList.remove('active');
            voiceStatus.textContent = msg;
            if (msg) setTimeout(() => { if (voiceStatus) voiceStatus.textContent = ''; }, 4000);
        }
    ;}

    // Bắt đầu ghi âm
    try {
        __voiceRecognition.start();
    } catch(e) {
        if (voiceStatus) voiceStatus.textContent = '⚠️ Không thể khởi động micro: ' + e.message;
    }
}


// ============================================================
// ===== HIGHLIGHT FEATURE: Action→xanh, Time→vàng, Person→tím
// ============================================================

window.__highlightMode = false;

function openHighlightModal() {
    const modal = document.getElementById('highlightModal');
    if (modal) modal.classList.add('show');
}

function closeHighlightModal() {
    const modal = document.getElementById('highlightModal');
    if (modal) modal.classList.remove('show');
    // Reset
    const area = document.getElementById('highlightTextArea');
    const result = document.getElementById('highlightResult');
    if (area) area.value = '';
    if (result) result.innerHTML = '';
    document.querySelectorAll('.hl-btn').forEach(b => b.classList.remove('active'));
    window.__highlightSelType = null;
    window.__highlightData = { action: [], time: [], person: [] };
}

window.__highlightData = { action: [], time: [], person: [] };
window.__highlightSelType = null;

const HL_COLORS = {
    action: { bg: '#dbeafe', border: '#3b82f6', text: '#1d4ed8', label: 'Action' },
    time:   { bg: '#fef9c3', border: '#eab308', text: '#92400e', label: 'Time'   },
    person: { bg: '#f3e8ff', border: '#a855f7', text: '#6b21a8', label: 'Person' },
};

function selectHighlightType(type) {
    window.__highlightSelType = type;
    document.querySelectorAll('.hl-btn').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById('hl-btn-' + type);
    if (btn) btn.classList.add('active');
}

function applyHighlight() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    const type = window.__highlightSelType;
    if (!type) {
        alert('Chọn loại highlight trước (Action / Time / Person)');
        return;
    }
    const text = selection.toString().trim();
    if (!text) return;

    const c = HL_COLORS[type];
    const range = selection.getRangeAt(0);

    const mark = document.createElement('mark');
    mark.style.cssText = `background:${c.bg};border:1px solid ${c.border};color:${c.text};border-radius:4px;padding:1px 4px;font-weight:600;cursor:pointer;`;
    mark.dataset.type = type;
    mark.dataset.text = text;
    mark.title = `${c.label}: ${text} (click để bỏ)`;
    mark.onclick = function() {
        // Bỏ highlight
        const t = document.createTextNode(this.dataset.text);
        this.replaceWith(t);
        syncHighlightData();
        updateHighlightPreview();
    };

    try {
        range.surroundContents(mark);
    } catch(e) {
        // Nếu selection vắt qua nhiều node → dùng extractContents
        const frag = range.extractContents();
        mark.appendChild(frag);
        range.insertNode(mark);
    }
    selection.removeAllRanges();
    syncHighlightData();
    updateHighlightPreview();
}

function syncHighlightData() {
    const result = { action: [], time: [], person: [] };
    document.querySelectorAll('#highlightResult mark[data-type]').forEach(m => {
        const t = m.dataset.type;
        const txt = m.dataset.text || m.textContent;
        if (result[t] && !result[t].includes(txt)) result[t].push(txt);
    });
    window.__highlightData = result;
}

function updateHighlightPreview() {
    const d = window.__highlightData;
    const prev = document.getElementById('highlightPreview');
    if (!prev) return;

    const parts = [];
    if (d.action.length) parts.push(`<span style="color:#1d4ed8;font-weight:600;">Action:</span> ${d.action.map(t => `<span style="background:#dbeafe;padding:1px 6px;border-radius:4px;">${esc(t)}</span>`).join(' ')}`);
    if (d.time.length)   parts.push(`<span style="color:#92400e;font-weight:600;">Time:</span> ${d.time.map(t => `<span style="background:#fef9c3;padding:1px 6px;border-radius:4px;">${esc(t)}</span>`).join(' ')}`);
    if (d.person.length) parts.push(`<span style="color:#6b21a8;font-weight:600;">Person:</span> ${d.person.map(t => `<span style="background:#f3e8ff;padding:1px 6px;border-radius:4px;">${esc(t)}</span>`).join(' ')}`);

    prev.innerHTML = parts.length
        ? parts.join('<br>')
        : '<span style="color:#9ca3af;font-style:italic;">Chưa highlight gì</span>';
}

function pasteHighlightText() {
    const area = document.getElementById('highlightTextArea');
    const result = document.getElementById('highlightResult');
    if (!area || !result) return;
    const text = area.value.trim();
    if (!text) return;
    // Render text vào vùng highlight, giữ nguyên xuống dòng
    result.innerHTML = esc(text).replace(/\n/g, '<br>');
    result.style.display = 'block';
    area.style.display = 'none';
    document.getElementById('hl-paste-btn').style.display = 'none';
    window.__highlightData = { action: [], time: [], person: [] };
    updateHighlightPreview();
}

async function createTaskFromHighlight() {
    const d = window.__highlightData;
    const actionText = d.action.join(', ');
    const timeText   = d.time.join(', ');
    const personText = d.person.join(', ');

    if (!actionText) {
        alert('Hãy highlight ít nhất 1 Action (tiêu đề task)');
        return;
    }

    // Gọi AI suggest để lấy deadline + nhãn
    let dueDate = null;
    let priority = 2;
    if (timeText) {
        try {
            const res = await fetch('/nextact/suggest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: actionText + ' ' + timeText })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.deadline) dueDate = data.deadline;
                if (data.suggested_priority) priority = data.suggested_priority;
            }
        } catch(e) {}
    }

    // Build content note từ person
    const contentNote = personText ? 'Liên quan: ' + personText : null;

    const res = await fetch('/nextact/create_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
            title: actionText,
            priority: priority,
            due_date: dueDate || null,
            is_quick_add: false,
            content: contentNote
        })
    });

    if (res.ok) {
        const statusEl = document.getElementById('hl-create-status');
        if (statusEl) {
            statusEl.textContent = '✓ Đã tạo task: ' + actionText;
            statusEl.style.color = '#16a34a';
        }
        loadNotes();
        setTimeout(closeHighlightModal, 1500);
    } else {
        alert('Lỗi tạo task từ highlight');
    }
}

// =====================================================================
// ===== AI SUMMARIZE — Tóm tắt hội thoại dài trong modal Tạo Ghi Chú
// =====================================================================
window.__summarizeResult = null;

function onAddContentChange() {
    // Reset kết quả cũ nếu người dùng thay đổi nội dung
    const content = (document.getElementById('addContent')?.value || '').trim();
    if (content.length < 10) {
        document.getElementById('summarizeResult')?.style && (document.getElementById('summarizeResult').style.display = 'none');
        document.getElementById('summarizePlaceholder')?.style && (document.getElementById('summarizePlaceholder').style.display = 'flex');
        window.__summarizeResult = null;
    }
}

async function runSummarize() {
    const title = (document.getElementById('addTitle')?.value || '').trim();
    const content = (document.getElementById('addContent')?.value || '').trim();

    if (content.length < 20) {
        alert('Vui lòng nhập nội dung hội thoại (ít nhất 20 ký tự) trước khi tóm tắt.');
        return;
    }

    // Hiện loading, ẩn placeholder và result
    const placeholder = document.getElementById('summarizePlaceholder');
    const loading = document.getElementById('summarizeLoading');
    const result = document.getElementById('summarizeResult');

    if (placeholder) placeholder.style.display = 'none';
    if (loading) loading.style.display = 'flex';
    if (result) result.style.display = 'none';

    // Disable nút
    const btn = document.getElementById('summarizeBtn');
    if (btn) { btn.disabled = true; btn.style.opacity = '0.6'; }

    try {
        const res = await fetch('/nextact/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ title, content })
        });

        if (loading) loading.style.display = 'none';

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert('Lỗi tóm tắt: ' + (err.detail || 'Thử lại sau'));
            if (placeholder) placeholder.style.display = 'flex';
            return;
        }

        const data = await res.json();

        // === Lay NHIEU nhan tu PhoBERT: tach content thanh doan nho, goi song song ===
        data.phobert_labels = [];
        try {
            const sentences = content
                .split(/[\n.;]+/)
                .map(s => s.trim())
                .filter(s => s.length > 10)
                .slice(0, 5);
            const texts = [...sentences, content.slice(0, 300)];

            const results = await Promise.all(
                texts.map(function(t) {
                    return fetch('/nextact/suggest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ text: t, mode: 'single' })
                    }).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; });
                })
            );

            var labelSet = {};
            results.forEach(function(r) {
                if (r && r.category && VALID_LABELS.indexOf(r.category) !== -1 && r.category !== 'Kh\u00e1c') {
                    labelSet[r.category] = true;
                }
            });
            var lblArr = Object.keys(labelSet);
            if (lblArr.length === 0) lblArr = ['Kh\u00e1c'];
            data.phobert_labels = lblArr;
        } catch(e) { data.phobert_labels = []; }

        window.__summarizeResult = data;
        renderSummarizeResult(data);

    } catch(e) {
        if (loading) loading.style.display = 'none';
        if (placeholder) placeholder.style.display = 'flex';
        alert('Lỗi kết nối khi tóm tắt: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
    }
}

function renderSummarizeResult(data) {
    var result = document.getElementById('summarizeResult');
    if (!result) return;
    result.style.display = 'block';

    var ner      = data.ner || {};
    var nerActions = ner.actions || [];
    var nerPeople  = ner.people  || [];
    var nerTimes   = ner.times   || [];
    var nerPlaces  = ner.places  || [];

    // === Tu khoa: action(tim) -> nguoi(hong) -> time(vang) -> place(xanh) ===
    var nerContent = document.getElementById('nerContent');
    var nerBox     = document.getElementById('nerBox');
    if (nerContent && nerBox) {
        var tags = [];
        nerActions.forEach(function(a) { tags.push('<span class="ner-tag-sum action-sum">' + esc(a) + '</span>'); });
        nerPeople .forEach(function(p) { tags.push('<span class="ner-tag-sum person-sum">' + esc(p) + '</span>'); });
        nerTimes  .forEach(function(t) { tags.push('<span class="ner-tag-sum time-sum">'   + esc(t) + '</span>'); });
        nerPlaces .forEach(function(p) { tags.push('<span class="ner-tag-sum place-sum">'  + esc(p) + '</span>'); });
        nerContent.innerHTML = tags.length
            ? tags.join('')
            : '<span style="color:#9ca3af;font-size:12px;font-style:italic;">Ch\u01b0a nh\u1eadn di\u1ec7n \u0111\u01b0\u1ee3c t\u1eeb kh\u00f3a</span>';
        nerBox.style.display = 'block';
    }

    // === Nhan phan loai: CHI tu PhoBERT (phobert_labels), nhieu nhan ===
    var labelsContent = document.getElementById('labelsContent');
    var labelsBox     = document.getElementById('labelsBox');
    if (labelsContent && labelsBox) {
        var labels = (data.phobert_labels || []).filter(function(l) { return VALID_LABELS.indexOf(l) !== -1; });
        if (labels.length > 0) {
            labelsContent.innerHTML = labels.map(function(l) {
                var color = LABEL_COLORS[l] || '#6b7280';
                return '<span style="background:' + color + '1a;color:' + color + ';border:1px solid ' + color + '40;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:700;">' + esc(l) + '</span>';
            }).join('');
            labelsBox.style.display = 'block';
        } else {
            labelsContent.innerHTML = '<span style="color:#9ca3af;font-size:12px;font-style:italic;">\u0110ang ph\u00e2n lo\u1ea1i b\u1eb1ng model AI...</span>';
            labelsBox.style.display = 'block';
        }
    }

    // === Noi dung chinh: viec can lam, plain text, khong highlight ===
    var summaryContent = document.getElementById('summaryContent');
    if (summaryContent) {
        var points = data.summary || [];
        if (points.length > 0) {
            summaryContent.innerHTML =
                '<ul style="margin:0;padding-left:18px;display:flex;flex-direction:column;gap:7px;">' +
                points.map(function(p) {
                    return '<li style="font-size:13px;color:#1e3a5f;line-height:1.6;font-weight:500;">' + esc(p) + '</li>';
                }).join('') +
                '</ul>';
        } else {
            summaryContent.innerHTML = '<span style="color:#9ca3af;font-style:italic;">Kh\u00f4ng c\u00f3 n\u1ed9i dung ch\u00ednh</span>';
        }
    }

    // === Task de xuat: normalize nhan ve VALID_LABELS ===
    var tasksList = document.getElementById('suggestedTasksList');
    if (!tasksList) return;
    var tasks = (data.tasks || []).map(function(t) {
        return Object.assign({}, t, {
            action_type: VALID_LABELS.indexOf(t.action_type) !== -1 ? t.action_type : 'Kh\u00e1c'
        });
    });
    window.__suggestedTasks = tasks;
    window.__createdTaskIds = {};

    if (tasks.length === 0) {
        tasksList.innerHTML = '<div style="color:#9ca3af;font-size:13px;font-style:italic;">Kh\u00f4ng c\u00f3 task n\u00e0o \u0111\u01b0\u1ee3c \u0111\u1ec1 xu\u1ea5t</div>';
        return;
    }

    var PRI_MAP = { 1: ['Th\u1ea5p', '#6b7280'], 2: ['Trung b\u00ecnh', '#f97316'], 3: ['Cao', '#ef4444'] };
    tasksList.innerHTML = tasks.map(function(t, i) {
        var pri    = PRI_MAP[t.priority] || PRI_MAP[2];
        var pLabel = pri[0], pColor = pri[1];
        var lColor = LABEL_COLORS[t.action_type] || '#6b7280';
        var dlStr  = (t.deadline && t.deadline !== 'null')
            ? '<span style="color:#6b7280;font-size:11px;">H\u1ea1n: ' + esc(t.deadline) + '</span>'
            : '';
        var reasonHtml = t.reason
            ? '<div style="font-size:11px;color:#9ca3af;margin-top:4px;line-height:1.4;">' + esc(t.reason) + '</div>'
            : '';
        return '<div class="suggested-task-card" id="stask-' + i + '">'
            + '<div class="task-info">'
            + '<div class="task-title">' + esc(t.title) + '</div>'
            + '<div class="task-meta" style="margin-top:5px;">'
            + '<span style="background:' + pColor + '1a;color:' + pColor + ';border-radius:12px;padding:1px 8px;font-size:11px;font-weight:700;">' + pLabel + '</span>'
            + dlStr
            + '<span style="background:' + lColor + '1a;color:' + lColor + ';border-radius:12px;padding:1px 8px;font-size:11px;font-weight:600;">' + esc(t.action_type) + '</span>'
            + '</div>'
            + reasonHtml
            + '</div>'
            + '<button class="btn-create-task" id="stask-btn-' + i + '" onclick="createSingleSuggestedTask(' + i + ')">+ T\u1ea1o</button>'
            + '</div>';
    }).join('');
}
async function createSingleSuggestedTask(idx) {
    const tasks = window.__suggestedTasks || [];
    const task = tasks[idx];
    if (!task) return;

    const btn = document.getElementById(`stask-btn-${idx}`);
    if (btn) { btn.disabled = true; btn.textContent = '...'; }

    try {
        const res = await fetch('/nextact/create_multi_tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                tasks: [task],
                source_title: document.getElementById('addTitle')?.value || '',
                source_content: ''
            })
        });

        if (res.ok) {
            if (btn) {
                btn.textContent = '✓ Đã tạo';
                btn.classList.add('created');
            }
            window.__createdTaskIds = window.__createdTaskIds || {};
            window.__createdTaskIds[idx] = true;
            loadNotes();
        } else {
            if (btn) { btn.disabled = false; btn.textContent = '+ Tạo'; }
            alert('Lỗi tạo task');
        }
    } catch(e) {
        if (btn) { btn.disabled = false; btn.textContent = '+ Tạo'; }
        alert('Lỗi kết nối');
    }
}

async function createAllSuggestedTasks() {
    const tasks = window.__suggestedTasks || [];
    if (!tasks.length) return;

    const btn = document.getElementById('createAllBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Đang tạo...'; }

    const statusEl = document.getElementById('createTasksStatus');

    try {
        const res = await fetch('/nextact/create_multi_tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                tasks: tasks,
                source_title: document.getElementById('addTitle')?.value || '',
                source_content: ''
            })
        });

        if (res.ok) {
            const data = await res.json();
            // Mark all buttons as created
            tasks.forEach((_, i) => {
                const b = document.getElementById(`stask-btn-${i}`);
                if (b) { b.textContent = '✓ Đã tạo'; b.classList.add('created'); b.disabled = true; }
            });
            if (btn) { btn.textContent = '✓ Đã tạo tất cả'; }
            if (statusEl) {
                statusEl.textContent = `✓ Đã tạo ${data.count} task thành công!`;
                statusEl.style.color = '#16a34a';
            }
            loadNotes();
        } else {
            if (btn) { btn.disabled = false; btn.textContent = '+ Tạo tất cả'; }
            alert('Lỗi tạo task');
        }
    } catch(e) {
        if (btn) { btn.disabled = false; btn.textContent = '+ Tạo tất cả'; }
        alert('Lỗi kết nối');
    }
}


// =====================================================================
// ===== NER HIGHLIGHT — hiện preview bên dưới ô nhập sau khi dừng gõ
// action=tím, time=vàng, place=xanh lá
// =====================================================================

// Định nghĩa cụm từ cần nhận diện — cụm DÀI ưu tiên trước
var NER_RULES = [
    // === NGUOI (person) ===
    { re: /\bkh\u00e1ch h\u00e0ng\b/gi, type: 'person' },
    { re: /\b\u0111\u1ed1i t\u00e1c\b/gi,    type: 'person' },
    { re: /\b(ch\u1ecb|anh|em)\b/gi,         type: 'person' },
    { re: /\bc\b(?=\s|$)/gi,                 type: 'person' },
    { re: /\bs\u1ebfp\b|\bgi\u00e1m \u0111\u1ed1c\b/gi, type: 'person' },
    { re: /\bteam\b|\bnh\u00f3m\b/gi,       type: 'person' },

    // === HÀNH ĐỘNG (action) ===
    { re: /tạo thông báo|gửi thông báo|soạn thông báo|đăng thông báo/gi, type: 'action' },
    { re: /gửi email|viết email|soạn email|trả lời email/gi,              type: 'action' },
    { re: /lên lịch họp|đặt lịch họp|tổ chức họp/gi,                     type: 'action' },
    { re: /nộp báo cáo|soạn báo cáo|viết báo cáo/gi,                     type: 'action' },
    { re: /nộp tài liệu|bàn giao tài liệu/gi,                             type: 'action' },
    { re: /theo dõi tiến độ|kiểm tra tiến độ|follow up/gi,                type: 'action' },
    { re: /tạo nhắc nhở|đặt nhắc nhở/gi,                                  type: 'action' },
    { re: /gọi điện|gọi cho|nhắn tin|liên hệ/gi,                          type: 'action' },
    { re: /chuẩn bị|hoàn thành|xử lý|thực hiện/gi,                       type: 'action' },
    { re: /đăng lên|post lên/gi,                                           type: 'action' },
    { re: /viết cái|soạn cái|làm cái/gi,                                  type: 'action' },
    { re: /\bgiúp\b|\bgửi\b|\bsoạn\b|\bviết\b|\btạo\b|\blàm\b/gi, type: 'action' },

    // === THỜI GIAN (time) ===
    { re: /trong chiều nay|trong sáng nay|trong tối nay|trong hôm nay/gi, type: 'time' },
    { re: /sáng nay|chiều nay|tối nay|trưa nay/gi,                        type: 'time' },
    { re: /sáng mai|chiều mai|tối mai|trưa mai/gi,                        type: 'time' },
    { re: /hôm nay|ngày mai|hôm qua|ngày kia/gi,                          type: 'time' },
    { re: /cuối tuần|cuối tháng|đầu tuần|đầu tháng/gi,                    type: 'time' },
    { re: /tuần này|tuần sau|tháng này|tháng sau|tháng tới/gi,            type: 'time' },
    { re: /thứ (?:hai|ba|tư|năm|sáu|bảy|chủ nhật)/gi,                    type: 'time' },
    { re: /\d{1,2}h\d{0,2}(?:\s*(?:sáng|chiều|tối|trưa))?/gi,           type: 'time' },
    { re: /\d{1,2} giờ(?:\s*\d{1,2} phút)?(?:\s*(?:sáng|chiều|tối|trưa))?/gi, type: 'time' },
    { re: /\d{1,2}\/\d{1,2}(?:\/\d{2,4})?/gi,                          type: 'time' },
    { re: /\bdeadline\b|hạn chót/gi,                                      type: 'time' },
    { re: /\bngay bây giờ|ngay hôm nay\b/gi,                              type: 'time' },

    // === ĐỊA ĐIỂM (place) ===
    { re: /văn phòng|phòng họp|phòng \d+|tầng \d+/gi,                    type: 'place' },
    { re: /hà nội|tp\.?\s*hcm|hồ chí minh|đà nẵng|hải phòng/gi,          type: 'place' },
    { re: /\bonline\b|\bzoom\b|google meet|\bteams\b|\boffline\b/gi,   type: 'place' },
    { re: /tại văn phòng|tại công ty|tại nhà|tại phòng/gi,                 type: 'place' },
];

var NER_CSS = {
    action:  'ner-highlight-action',
    person:  'ner-highlight-person',
    time:   'ner-highlight-time',
    place:  'ner-highlight-place',
};

function extractNERSpans(text) {
    // Dùng mảng đánh dấu để tránh overlap — ưu tiên rule đầu tiên match
    var taken = new Array(text.length).fill(false);
    var spans = [];

    for (var ri = 0; ri < NER_RULES.length; ri++) {
        var rule = NER_RULES[ri];
        rule.re.lastIndex = 0;
        var m;
        while ((m = rule.re.exec(text)) !== null) {
            var s = m.index;
            var e = s + m[0].length;
            // Trim spaces
            while (s < e && text[s] === ' ') s++;
            while (e > s && text[e-1] === ' ') e--;
            if (e - s < 2) continue;
            // Check overlap
            var ok = true;
            for (var i = s; i < e; i++) if (taken[i]) { ok = false; break; }
            if (ok) {
                spans.push({ start: s, end: e, type: rule.type });
                for (var i = s; i < e; i++) taken[i] = true;
            }
        }
    }

    return spans.sort(function(a, b) { return a.start - b.start; });
}

function escHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Hiện preview bên dưới ô nhập — luôn nhắc lại toàn bộ text + highlight
function renderNerPreview(text) {
    var box    = document.getElementById('nerPreviewBox');
    var legend = document.getElementById('nerLegend');
    if (!box) return;

    var trimmed = (text || '').trim();
    if (trimmed.length < 2) {
        box.style.display = 'none';
        if (legend) legend.classList.remove('show');
        return;
    }

    var spans = extractNERSpans(text);
    var html  = '';
    var cur   = 0;

    for (var i = 0; i < spans.length; i++) {
        var sp = spans[i];
        if (sp.start > cur) html += escHTML(text.slice(cur, sp.start));
        html += '<span class="' + NER_CSS[sp.type] + '">'
              + escHTML(text.slice(sp.start, sp.end))
              + '</span>';
        cur = sp.end;
    }
    if (cur < text.length) html += escHTML(text.slice(cur));

    box.innerHTML  = html;
    box.style.display = 'block';

    if (legend) {
        if (spans.length > 0) legend.classList.add('show');
        else legend.classList.remove('show');
    }
}

// Legacy stubs — giữ để không break bất kỳ call cũ nào
function renderNerOverlay(text) {}
function escOverlay(str) { return str; }
function renderNerHighlight(ner) {}
function extractNER(text) { return { person: [], time: [], place: [] }; }
// ===== CSS INJECT: Assign UI styles =====
(function injectAssignCSS() {
    if (document.getElementById('assign-ui-style')) return;
    const s = document.createElement('style');
    s.id = 'assign-ui-style';
    s.textContent = `
        .assign-ui-wrap {
            background: #f8faff;
            border: 1px solid #dbeafe;
            border-radius: 10px;
            padding: 16px;
            margin-top: 4px;
        }
        .assign-ui-label {
            font-size: 13px;
            font-weight: 600;
            color: #1e3a5f;
            margin-bottom: 8px;
        }
        .assign-select {
            width: 100%;
            padding: 9px 12px;
            border: 1.5px solid #d1d5db;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            color: #374151;
            background: #fff;
            outline: none;
            transition: border .15s;
            cursor: pointer;
        }
        .assign-select:focus { border-color: #2563eb; }
        .assign-msg-input {
            width: 100%;
            min-height: 70px;
            padding: 9px 12px;
            border: 1.5px solid #d1d5db;
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            color: #374151;
            resize: vertical;
            outline: none;
            box-sizing: border-box;
            transition: border .15s;
        }
        .assign-msg-input:focus { border-color: #2563eb; }
        .assign-send-btn {
            width: 100%;
            margin-top: 12px;
            padding: 10px;
            background: #196B7C;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            font-family: inherit;
            transition: background .15s;
        }
        .assign-send-btn:hover:not(:disabled) { background: #145a68; }
        .assign-send-btn:disabled { background: #9ca3af; cursor: not-allowed; }
        #assignSendHint {
            font-size: 12px;
            margin-top: 8px;
            min-height: 16px;
            text-align: center;
            color: #6b7280;
        }
    `;
    document.head.appendChild(s);
})();