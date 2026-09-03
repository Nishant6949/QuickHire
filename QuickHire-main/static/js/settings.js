document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
});

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const panel = document.querySelector(`[data-panel="${target}"]`);
            if (panel) panel.classList.add('active');
        });
    });
}

function saveSettings() {
    const data = {
        company_name: document.getElementById('org-name').value.trim(),
        company_size: document.getElementById('company-size').value,
        auto_screen: document.getElementById('auto-screen').checked,
        match_threshold: parseInt(document.getElementById('match-threshold').value),
        bias_detection: document.getElementById('bias-detect').checked,
    };

    if (!data.company_name) {
        if (window.toast) window.toast('Organization name is required', 'error');
        return;
    }

    fetch('/dashboard/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                if (window.toast) window.toast('Settings saved', 'success');
            } else {
                if (window.toast) window.toast(res.error || 'Failed to save', 'error');
            }
        })
        .catch(() => {
            if (window.toast) window.toast('Network error', 'error');
        });
}

function saveNotifications() {
    const data = {
        notif_matches: document.getElementById('notif-matches').checked,
        notif_weekly: document.getElementById('notif-weekly').checked,
        notif_expire: document.getElementById('notif-expire').checked,
        notif_updates: document.getElementById('notif-updates').checked,
    };

    fetch('/dashboard/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                if (window.toast) window.toast('Notification preferences saved', 'success');
            } else {
                if (window.toast) window.toast(res.error || 'Failed to save', 'error');
            }
        })
        .catch(() => {
            if (window.toast) window.toast('Network error', 'error');
        });
}

function showDeleteDataModal() {
    document.getElementById('delete-data-confirm').value = '';
    document.getElementById('delete-data-modal').style.display = 'flex';
}

function showCloseAccountModal() {
    document.getElementById('close-account-confirm').value = '';
    document.getElementById('close-account-modal').style.display = 'flex';
}

function hideModal(id) {
    document.getElementById(id).style.display = 'none';
}

function deleteAllData() {
    const input = document.getElementById('delete-data-confirm').value.trim();
    if (input !== COMPANY_NAME) {
        if (window.toast) window.toast('Company name does not match', 'error');
        return;
    }

    const btn = document.getElementById('delete-data-btn');
    btn.disabled = true;
    btn.textContent = 'Deleting...';

    fetch('/dashboard/settings/delete-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                hideModal('delete-data-modal');
                if (window.toast) window.toast('All data has been deleted', 'success');
            } else {
                if (window.toast) window.toast(res.error || 'Failed to delete data', 'error');
            }
        })
        .catch(() => {
            if (window.toast) window.toast('Network error', 'error');
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Delete All Data';
        });
}

function closeAccount() {
    const input = document.getElementById('close-account-confirm').value.trim();
    if (input !== 'DELETE') {
        if (window.toast) window.toast('Please type "DELETE" to confirm', 'error');
        return;
    }

    const btn = document.getElementById('close-account-btn');
    btn.disabled = true;
    btn.textContent = 'Closing...';

    fetch('/dashboard/settings/close-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                window.location.href = res.redirect || '/';
            } else {
                if (window.toast) window.toast(res.error || 'Failed to close account', 'error');
            }
        })
        .catch(() => {
            if (window.toast) window.toast('Network error', 'error');
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Close Account';
        });
}

function updateTeamCount() {
    const tbody = document.getElementById('team-tbody');
    const count = tbody ? tbody.querySelectorAll('tr').length : 1;
    const label = document.getElementById('team-count');
    if (label) label.textContent = count + ' member' + (count === 1 ? '' : 's');
}

function bindTeamManagement() {
    const addBtn = document.getElementById('team-add-btn');
    const tbody = document.getElementById('team-tbody');
    if (!addBtn || !tbody) return;

    addBtn.addEventListener('click', () => {
        const name = document.getElementById('team-name').value.trim();
        const email = document.getElementById('team-email').value.trim();
        const role = document.getElementById('team-role').value;
        if (!name || !email) {
            if (window.toast) window.toast('Enter a name and email', 'error');
            return;
        }
        addBtn.disabled = true;
        fetch('/dashboard/settings/team', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, role })
        })
            .then(r => r.json())
            .then(data => {
                if (!data.success) throw new Error(data.error || 'Could not add team member');
                const m = data.member;
                const tr = document.createElement('tr');
                tr.dataset.teamId = m.id;
                tr.innerHTML = '<td>' + escapeHtml(m.name) + '</td><td>' + escapeHtml(m.email) + '</td><td>' + escapeHtml(m.role) + '</td><td><span class="badge badge-draft">Invited</span></td><td><button type="button" class="btn-outline-sm team-remove-btn" data-id="' + m.id + '">Remove</button></td>';
                tbody.appendChild(tr);
                document.getElementById('team-name').value = '';
                document.getElementById('team-email').value = '';
                updateTeamCount();
                if (window.toast) window.toast('Team member added', 'success');
            })
            .catch(err => { if (window.toast) window.toast(err.message, 'error'); })
            .finally(() => { addBtn.disabled = false; });
    });

    tbody.addEventListener('click', e => {
        const btn = e.target.closest('.team-remove-btn');
        if (!btn) return;
        if (!confirm('Remove this team member?')) return;
        fetch('/dashboard/settings/team/' + btn.dataset.id, { method: 'DELETE' })
            .then(r => r.json())
            .then(data => {
                if (!data.success) throw new Error(data.error || 'Could not remove team member');
                const row = btn.closest('tr');
                if (row) row.remove();
                updateTeamCount();
                if (window.toast) window.toast('Team member removed', 'success');
            })
            .catch(err => { if (window.toast) window.toast(err.message, 'error'); });
    });
}

document.addEventListener('DOMContentLoaded', bindTeamManagement);
