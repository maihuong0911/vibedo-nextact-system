// ===== GLOBAL FUNCTIONS =====
function esc(t) { 
    const d = document.createElement('div'); 
    d.textContent = t; 
    return d.innerHTML; 
}

function formatDate(dt) {
    if (!dt) return '';
    const d = new Date(dt);
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear();
    const hours = d.getHours().toString().padStart(2, '0');
    const mins = d.getMinutes().toString().padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${mins}`;
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
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('errorMessage');
        const successDiv = document.getElementById('successMessage');

        errorDiv.classList.remove('show');
        successDiv.classList.remove('show');

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user_id', data.user_id);
                successDiv.textContent = 'Đăng nhập thành công! Đang chuyển hướng...';
                successDiv.classList.add('show');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                errorDiv.textContent = data.detail || 'Email hoặc mật khẩu không đúng';
                errorDiv.classList.add('show');
            }
        } catch (error) {
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
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    full_name: fullName,
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user_id', data.user_id);
                successDiv.textContent = 'Đăng ký thành công! Đang chuyển hướng...';
                successDiv.classList.add('show');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                errorDiv.textContent = data.detail || 'Đăng ký thất bại. Email có thể đã tồn tại.';
                errorDiv.classList.add('show');
            }
        } catch (error) {
            errorDiv.textContent = 'Lỗi kết nối. Vui lòng thử lại.';
            errorDiv.classList.add('show');
        }
    });
}

// ===== DASHBOARD FUNCTIONS =====
let classifyTimer = null;
let allNotes = [];
let editId = null;

// lưu kết quả suggest cho quickAdd áp dụng
window.__quickSuggest = null;

function getToken() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        throw new Error('Không tìm thấy token');
    }
    return token;
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/x-www-form-urlencoded'
    };
}

if (document.getElementById('notesGrid')) {
    window.addEventListener('DOMContentLoaded', loadNotes);
}

async function loadNotes() {
    try {
        const res = await fetch('/notes', {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        if (!res.ok) {
            if (res.status === 401) {
                localStorage.clear();
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

function renderNotes() {
    const grid = document.getElementById('notesGrid');
    if (!grid) return;

    if (allNotes.length === 0) {
        grid.innerHTML = '<div class="empty">Chưa có ghi chú nào</div>';
        updateResultCount(0);
        return;
    }
    grid.innerHTML = allNotes.map(n => {
        const content = n.is_quick_add
            ? '<p style="color: #ff8c42; font-style: italic;">✨ Được tạo nhanh</p>'
            : '<p>' + esc(n.content) + '</p>';
        const badge = n.is_quick_add
            ? '<span style="background: linear-gradient(135deg, #ff8c42, #f59e0b); color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">⚡ Tạo Nhanh</span>'
            : '';
        const style = n.is_quick_add
            ? 'style="border-left: 4px solid #ff8c42; background: #fff3e6; cursor: pointer;"'
            : 'style="cursor: pointer;"';
        return `
        <div class="note-card" ${style} onclick="openDetailModal(${n.id})">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                <h3>${esc(n.title)}</h3>
                ${badge}
            </div>
            ${content}
            <div class="note-meta">
                <span>${n.due_date ? `${n.due_date}` : 'Không có hạn chót'}</span>
                <span>${formatDate(n.created_at)}</span>
            </div>
            <div class="note-actions" onclick="event.stopPropagation();">
                <button class="btn-small btn-edit" onclick="openEditModal(${n.id})">Sửa</button>
                <button class="btn-small btn-delete" onclick="delNote(${n.id})">Xóa</button>
            </div>
        </div>
    `;
    }).join('');
    
    updateResultCount(allNotes.length);
    applyFilters(); // Apply any active filters
}

async function addNote(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('title', document.getElementById('addTitle').value);
    fd.append('content', document.getElementById('addContent').value);
    fd.append('status', 'todo');
    fd.append('priority', document.getElementById('addPriority').value);
    fd.append('due_date', document.getElementById('addDueDate').value || '');
    try {
        const res = await fetch('/notes', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: fd
        });
        if (res.ok) {
            closeAddNoteModal();
            loadNotes();
        } else {
            alert('Lỗi tạo ghi chú');
        }
    } catch (e) {
        alert('Lỗi kết nối');
    }
}

async function quickAdd(e) {
    e.preventDefault();

    const title = document.getElementById('quickTitle').value.trim();
    const apply = document.getElementById('applySuggestion') ? document.getElementById('applySuggestion').checked : false;
    const suggest = window.__quickSuggest;

    // mặc định như cũ
    let dueDate = document.getElementById('quickDueDate')?.value || '';
    let priority = '2';

    // nếu áp dụng gợi ý → dùng suggested_priority + deadline (nếu có)
    if (apply && suggest) {
        if (suggest.deadline) dueDate = suggest.deadline;
        if (suggest.suggested_priority) priority = String(suggest.suggested_priority);
    }

    const fd = new FormData();
    fd.append('title', title);
    fd.append('content', '');
    fd.append('status', 'todo');
    fd.append('priority', priority);
    fd.append('due_date', dueDate);
    fd.append('is_quick_add', 'true');

    try {
        const res = await fetch('/notes', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: fd
        });
        if (res.ok) {
            closeQuickAddModal();
            loadNotes();
        } else {
            alert('Lỗi tạo ghi chú');
        }
    } catch (e) {
        alert('Lỗi kết nối');
    }
}

function handleQuickInput() {
    clearTimeout(classifyTimer);
    classifyTimer = setTimeout(() => {
        // ưu tiên suggest (vừa có label vừa có action)
        suggestTodo();
    }, 400);
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

        // ===== Populate classifyResult (cũ) =====
        if (document.getElementById('categoryName')) {
            document.getElementById('categoryName').textContent = `📌 ${data.category}`;
        }
        if (document.getElementById('confidenceScore')) {
            document.getElementById('confidenceScore').textContent = `${data.confidence}%`;
        }
        if (classifyBox) classifyBox.style.display = 'block';

        if (data.deadline) {
            if (document.getElementById('deadlineValue')) document.getElementById('deadlineValue').textContent = data.deadline;
            if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'block';
            const qdd = document.getElementById('quickDueDate');
            if (qdd) qdd.value = data.deadline;
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

        // ===== Populate suggestResult (mới) =====
        if (suggestBox) suggestBox.style.display = 'block';

        const elCat = document.getElementById('suggestCategory');
        const elConf = document.getElementById('suggestConfidence');
        const elActions = document.getElementById('suggestActions');
        const elPriority = document.getElementById('suggestPriority');
        const elDeadline = document.getElementById('suggestDeadline');

        if (elCat) elCat.textContent = `📌 ${data.category || ''}`;
        if (elConf) elConf.textContent = data.confidence != null ? `(${data.confidence}%)` : '';
        if (elPriority) elPriority.textContent = priorityLabel(data.suggested_priority);
        if (elDeadline) elDeadline.textContent = data.deadline || 'Không đề xuất';

        if (elActions) {
            elActions.innerHTML = '';
            const actions = Array.isArray(data.suggested_actions) ? data.suggested_actions : [];
            if (actions.length === 0) {
                const li = document.createElement('li');
                li.textContent = 'Chưa có gợi ý hành động';
                elActions.appendChild(li);
            } else {
                actions.forEach(a => {
                    const li = document.createElement('li');
                    li.textContent = a;
                    elActions.appendChild(li);
                });
            }
        }

        // reasons
        const reasonBox = document.getElementById('suggestReasonBox');
        const reasonsUl = document.getElementById('suggestReasons');
        const reasons = Array.isArray(data.reason) ? data.reason : [];
        if (reasonBox && reasonsUl) {
            if (reasons.length > 0) {
                reasonBox.style.display = 'block';
                reasonsUl.innerHTML = '';
                reasons.forEach(r => {
                    const li = document.createElement('li');
                    li.textContent = r;
                    reasonsUl.appendChild(li);
                });
            } else {
                reasonBox.style.display = 'none';
                reasonsUl.innerHTML = '';
            }
        }

    } catch (e) {
        console.error('Suggest error:', e);
        // fallback giữ chức năng cũ
        try { await classifyTodo(); } catch (_) {}
    }
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
            
            if (data.deadline) {
                if (document.getElementById('deadlineValue')) document.getElementById('deadlineValue').textContent = data.deadline;
                if (document.getElementById('deadlineResult')) document.getElementById('deadlineResult').style.display = 'block';
                const qdd = document.getElementById('quickDueDate');
                if (qdd) qdd.value = data.deadline;
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

async function openEditModal(id) {
    const n = allNotes.find(x => x.id === id);
    if (!n) return;

    editId = id;
    document.getElementById('editTitle').value = n.title;
    document.getElementById('editContent').value = n.content;
    document.getElementById('editPriority').value = n.priority;
    document.getElementById('editDueDate').value = n.due_date ? n.due_date.split('T')[0] : '';
    document.getElementById('editModal').classList.add('show');
}

async function updateNote(e) {
    e.preventDefault();
    const fd = new FormData();
    fd.append('title', document.getElementById('editTitle').value);
    fd.append('content', document.getElementById('editContent').value);
    fd.append('status', 'todo');
    fd.append('priority', document.getElementById('editPriority').value);
    fd.append('due_date', document.getElementById('editDueDate').value || '');
    try {
        const res = await fetch(`/notes/${editId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: fd
        });
        if (res.ok) {
            closeEditModal();
            loadNotes();
        } else {
            alert('Lỗi cập nhật ghi chú');
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
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
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
}

function closeAddNoteModal() { 
    document.getElementById('addModal').classList.remove('show'); 
    document.getElementById('addForm').reset(); 
}

function openQuickAddModal() { 
    document.getElementById('quickModal').classList.add('show'); 

    // reset UI phụ (đỡ bị giữ kết quả cũ)
    const classifyBox = document.getElementById('classifyResult');
    const suggestBox = document.getElementById('suggestResult');
    if (classifyBox) classifyBox.style.display = 'none';
    if (suggestBox) suggestBox.style.display = 'none';
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

    window.__quickSuggest = null;

    // clear hidden
    const qdd = document.getElementById('quickDueDate');
    if (qdd) qdd.value = '';
    const hPri = document.getElementById('quickSuggestedPriority');
    const hCat = document.getElementById('quickSuggestedCategory');
    const hConf = document.getElementById('quickSuggestedConfidence');
    if (hPri) hPri.value = '';
    if (hCat) hCat.value = '';
    if (hConf) hConf.value = '';
}

function closeEditModal() { 
    document.getElementById('editModal').classList.remove('show'); 
}

function openDetailModal(id) {
    const n = allNotes.find(x => x.id === id);
    if (!n) return;

    document.getElementById('detailTitle').textContent = n.title;
    document.getElementById('detailContent').textContent = n.content || '(Không có mô tả)';
    document.getElementById('detailPriority').textContent = ['', 'Thấp', 'Trung Bình', 'Cao'][n.priority];
    document.getElementById('detailDueDate').textContent = n.due_date ? n.due_date : 'Không có';
    document.getElementById('detailCreatedAt').textContent = formatDate(n.created_at);
    
    if (n.is_quick_add) {
        document.getElementById('detailQuickAdd').style.display = 'block';
    } else {
        document.getElementById('detailQuickAdd').style.display = 'none';
    }
    
    // Reset chat messages
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '<div class="chat-msg bot-msg">👋 Hỏi tôi về cách chuẩn bị cho công việc này!</div>';
    }
    
    window.currentDetailId = id;
    document.getElementById('detailModal').classList.add('show');
}

function closeDetailModal() {
    document.getElementById('detailModal').classList.remove('show');
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
            botMsg.innerHTML = renderMarkdown(data.reply);
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
    if(confirm('Bạn muốn đăng xuất?')) {
        localStorage.clear();
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

    if (!searchEl || !priorityEl || !deadlineEl || !typeEl || !grid) return;

    const searchTerm = searchEl.value.toLowerCase();
    const priority = priorityEl.value;
    const deadline = deadlineEl.value;
    const type = typeEl.value;

    currentFilters = {
        search: searchTerm,
        priority: priority,
        deadline: deadline,
        type: type
    };

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
            // Search filter
            if (searchTerm && !note.title.toLowerCase().includes(searchTerm)) {
                show = false;
            }

            // Priority filter
            if (priority && note.priority !== parseInt(priority)) {
                show = false;
            }

            // Type filter
            if (type === 'quick' && !note.is_quick_add) {
                show = false;
            } else if (type === 'normal' && note.is_quick_add) {
                show = false;
            }

            // Deadline filter
            if (deadline && note.due_date) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const taskDate = new Date(note.due_date);
                taskDate.setHours(0, 0, 0, 0);
                
                if (deadline === 'today') {
                    if (taskDate.getTime() !== today.getTime()) show = false;
                } else if (deadline === 'tomorrow') {
                    const tomorrow = new Date(today);
                    tomorrow.setDate(tomorrow.getDate() + 1);
                    if (taskDate.getTime() !== tomorrow.getTime()) show = false;
                } else if (deadline === 'week') {
                    const weekLater = new Date(today);
                    weekLater.setDate(weekLater.getDate() + 7);
                    if (taskDate > weekLater) show = false;
                } else if (deadline === 'month') {
                    const monthLater = new Date(today);
                    monthLater.setMonth(monthLater.getMonth() + 1);
                    if (taskDate > monthLater) show = false;
                }
            } else if (deadline === 'none' && note.due_date) {
                show = false;
            } else if (deadline && deadline !== 'none' && !note.due_date) {
                // nếu lọc theo hôm nay/mai/tuần/tháng mà task không có hạn -> ẩn
                show = false;
            }
        }

        if (show) {
            card.classList.remove('hidden');
            visibleCount++;
        } else {
            card.classList.add('hidden');
        }
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

// ===== EDIT & DELETE FUNCTIONS FOR NEW UI =====
async function delNote(id) {
    if (!confirm('Bạn chắc chắn muốn xóa ghi chú này?')) return;
    try {
        const res = await fetch(`/notes/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });
        if (res.ok) {
            loadTasksData();
            loadDashboardData();
        } else {
            alert('Lỗi xóa ghi chú');
        }
    } catch (e) {
        alert('Lỗi kết nối');
    }
}

async function openEditModal(id) {
    const note = allNotes.find(n => n.id === id);
    if (!note) return;
    editId = id;
    // For new dashboard UI - simplified
    alert('Tính năng chỉnh sửa sẽ được cập nhật sớm!');
}

function closeEditModal() {
    // For compatibility
}
