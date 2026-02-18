(function () {
    const jobs = window.__jobs || [];
    const tbody = document.getElementById('jobs-tbody');
    const emptyState = document.getElementById('jobs-empty');
    const searchInput = document.getElementById('jobs-search');
    const deptFilter = document.getElementById('jobs-dept-filter');
    const statusFilter = document.getElementById('jobs-status-filter');
    const dateFilter = document.getElementById('jobs-date-filter');

    const tableSection = document.querySelector('.data-table-wrap');
    const statsGrid = document.querySelector('.stats-grid');
    const sectionHeading = document.querySelector('.section-heading');
    const detailPanel = document.getElementById('job-detail-panel');
    const detailBack = document.getElementById('job-detail-back');
    const detailTitle = document.getElementById('job-detail-title');
    const detailBadge = document.getElementById('job-detail-badge');
    const detailMeta = document.getElementById('job-detail-meta');
    const detailJd = document.getElementById('job-detail-jd');
    const detailCandidates = document.getElementById('job-detail-candidates');
    const detailTabs = detailPanel ? detailPanel.querySelectorAll('.jd-toggle-btn') : [];
    const jobDetailId = document.getElementById('job-detail-id');
    const jobStatusSelect = document.getElementById('job-status-select');

    const resumeModal = document.getElementById('resume-preview-modal');
    const resumeClose = document.getElementById('resume-preview-close');
    const resumeName = document.getElementById('resume-preview-name');
    const resumeIframe = document.getElementById('resume-preview-iframe');

    function statusBadge(status) {
        const map = {
            open: 'badge-open',
            draft: 'badge-draft',
            completed: 'badge-completed',
            closed: 'badge-closed',
            ready: 'badge-open',
            processing: 'badge-draft'
        };
        const cls = map[status] || 'badge-draft';
        const label = status.charAt(0).toUpperCase() + status.slice(1);
        return '<span class="badge ' + cls + '">' + label + '</span>';
    }

    function renderTable(filtered) {
        if (!tbody) return;
        if (filtered.length === 0) {
            tbody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'flex';
            tbody.closest('.data-table-wrap').style.display = 'none';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';
        tbody.closest('.data-table-wrap').style.display = '';

        tbody.innerHTML = filtered.map(function (j) {
            return '<tr data-job-id="' + j.id + '">' +
                '<td>' + escapeHtml(j.title) + '</td>' +
                '<td>' + escapeHtml(j.department || '—') + '</td>' +
                '<td>' + escapeHtml(j.location || '—') + '</td>' +
                '<td>' + j.candidate_count + '</td>' +
                '<td>' + j.created_at + '</td>' +
                '<td>' + statusBadge(j.status) + '</td>' +
                '<td style="text-align:right;">' +
                '<button class="btn-outline-sm job-row-delete-btn" data-job-id="' + j.id + '" data-title="' + escapeHtml(j.title) + '" type="button" title="Delete job" style="color:var(--color-danger,#ef4444);border-color:var(--color-danger,#ef4444);padding:4px 8px;">' +
                '<i data-feather="trash-2"></i>' +
                '</button>' +
                '</td>' +
                '</tr>';
        }).join('');
        if (window.feather) feather.replace();
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatJdText(text) {
        var lines = text.split('\n');
        var html = '';
        var listOpen = false;

        function closeList() {
            if (listOpen) { html += '</ul>'; listOpen = false; }
        }

        lines.forEach(function (line) {
            var trimmed = line.trim();
            if (!trimmed) { closeList(); return; }

            // Detect headings: ALL CAPS line, or line ending with ':', or starts with '#'
            var isHeading = /^#+\s/.test(trimmed) ||
                (trimmed.endsWith(':') && trimmed.length < 80 && !/^[-•*]/.test(trimmed)) ||
                (trimmed === trimmed.toUpperCase() && trimmed.length > 3 && trimmed.length < 80 && /[A-Z]/.test(trimmed));

            // Detect bullet lines
            var isBullet = /^[-•*]\s/.test(trimmed) || /^\d+[.)\s]/.test(trimmed);

            if (isHeading) {
                closeList();
                var headingText = trimmed.replace(/^#+\s*/, '').replace(/:$/, '');
                html += '<div class="jd-section-heading">' + escapeHtml(headingText) + '</div>';
            } else if (isBullet) {
                if (!listOpen) { html += '<ul class="jd-list">'; listOpen = true; }
                var bulletText = trimmed.replace(/^[-•*]\s*/, '').replace(/^\d+[.)\s]+/, '');
                html += '<li>' + escapeHtml(bulletText) + '</li>';
            } else {
                closeList();
                html += '<p class="jd-paragraph">' + escapeHtml(trimmed) + '</p>';
            }
        });

        closeList();
        return html;
    }

    function applyFilters() {
        const search = (searchInput ? searchInput.value : '').toLowerCase();
        const dept = deptFilter ? deptFilter.value : 'all';
        const status = statusFilter ? statusFilter.value : 'all';
        const days = dateFilter ? dateFilter.value : 'all';

        let cutoff = null;
        if (days !== 'all') {
            cutoff = new Date();
            cutoff.setDate(cutoff.getDate() - parseInt(days, 10));
        }

        const filtered = jobs.filter(function (j) {
            if (search && !j.title.toLowerCase().includes(search)) return false;
            if (dept !== 'all' && j.department !== dept) return false;
            if (status !== 'all' && j.status !== status) return false;
            if (cutoff) {
                const posted = new Date(j.created_at);
                if (posted < cutoff) return false;
            }
            return true;
        });

        renderTable(filtered);
    }

    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (deptFilter) deptFilter.addEventListener('change', applyFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    if (dateFilter) dateFilter.addEventListener('change', applyFilters);

    applyFilters();

    if (tbody) {
        tbody.addEventListener('click', function (e) {
            // Don't open detail if delete button was clicked
            if (e.target.closest('.job-row-delete-btn')) {
                var btn = e.target.closest('.job-row-delete-btn');
                deleteJob(parseInt(btn.dataset.jobId), btn.dataset.title, btn);
                return;
            }
            const row = e.target.closest('tr[data-job-id]');
            if (!row) return;
            openJobDetail(parseInt(row.dataset.jobId));
        });
    }

    function openJobDetail(jobId) {
        if (!detailPanel) return;

        detailPanel.style.display = '';
        detailJd.innerHTML = '<p style="color:var(--color-text-disabled);">Loading...</p>';
        detailCandidates.innerHTML = '';
        showTableView(false);

        fetch('/dashboard/job-detail/' + jobId)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data.success) {
                    if (window.toast) window.toast(data.error || 'Could not load job', 'error');
                    closeJobDetail();
                    return;
                }
                populateDetail(data.job, data.candidates);
            })
            .catch(function () {
                if (window.toast) window.toast('Network error loading job', 'error');
                closeJobDetail();
            });
    }

    function populateDetail(job, candidates) {
        detailTitle.textContent = job.title;
        detailBadge.innerHTML = statusBadge(job.status);
        if (jobDetailId) jobDetailId.value = job.id;
        if (jobStatusSelect) jobStatusSelect.value = job.status;

        var metaPills = [];
        if (job.department) metaPills.push('<span class="pill-tag">' + escapeHtml(job.department) + '</span>');
        if (job.location) metaPills.push('<span class="pill-tag">' + escapeHtml(job.location) + '</span>');
        if (job.salary_min || job.salary_max) {
            var sal = '';
            if (job.salary_min && job.salary_max) sal = '$' + job.salary_min.toLocaleString() + ' – $' + job.salary_max.toLocaleString();
            else if (job.salary_min) sal = 'From $' + job.salary_min.toLocaleString();
            else sal = 'Up to $' + job.salary_max.toLocaleString();
            metaPills.push('<span class="pill-tag">' + sal + '</span>');
        }
        if (job.required_skills) metaPills.push('<span class="pill-tag">' + escapeHtml(job.required_skills) + '</span>');
        detailMeta.innerHTML = metaPills.join('');

        detailJd.innerHTML = job.jd_text
            ? '<div class="job-detail-jd-text">' + formatJdText(job.jd_text) + '</div>'
            : '<p style="color:var(--color-text-disabled);">No job description provided.</p>';

        renderDetailCandidates(candidates);

        detailTabs.forEach(function (btn) { btn.classList.remove('active'); });
        if (detailTabs.length) detailTabs[0].classList.add('active');
        detailJd.style.display = '';
        detailCandidates.style.display = 'none';

        if (window.feather) feather.replace();
    }

    function renderDetailCandidates(candidates) {
        var jobId = jobDetailId ? jobDetailId.value : null;

        // ── Upload + Analyse toolbar ──────────────────────────────────
        var toolbar = '<div class="jd-candidates-toolbar">' +
            '<label class="btn-outline" id="jd-upload-zone" for="jd-resume-file-input" style="cursor:pointer;">' +
            '<i data-feather="upload"></i> Upload Resumes' +
            '<input type="file" id="jd-resume-file-input" accept=".pdf" multiple style="display:none;">' +
            '</label>' +
            '<div id="jd-upload-status" class="jd-upload-status" style="display:none;"></div>' +
            '<button class="btn-primary" id="jd-analyse-btn" type="button" style="white-space:nowrap;">' +
            '<i data-feather="zap"></i> Analyse' +
            '</button>' +
            '</div>';

        // ── Candidate cards ───────────────────────────────────────────
        var cardsHtml = '';
        if (!candidates || candidates.length === 0) {
            cardsHtml = '<p style="color:var(--color-text-disabled);padding:var(--spacing-lg) 0;">No candidates yet — upload resumes above and click Analyse.</p>';
        } else {
            cardsHtml = '<div class="results-grid">';
            candidates.forEach(function (r) {
                var scoreClass = r.match_score >= 90 ? 'green' : r.match_score >= 70 ? 'amber' : 'red';

                var candidateStatusBadge = '';
                var statusMap = {
                    invited: { cls: 'badge-invited', label: 'Invited' },
                    shortlisted: { cls: 'badge-shortlisted', label: 'Shortlisted' },
                    interview_done: { cls: 'badge-interview-done', label: 'Interview Done' },
                    final_hired: { cls: 'badge-final-hired', label: 'Hired' },
                    final_rejected: { cls: 'badge-final-rejected', label: 'Rejected' },
                    scored: { cls: 'badge-open', label: 'Scored' },
                    pending: { cls: 'badge-draft', label: 'Pending' },
                    error: { cls: 'badge-closed', label: 'Error' }
                };
                var st = statusMap[r.status];
                if (st) {
                    candidateStatusBadge = '<span class="job-card-badge ' + st.cls + '">' + st.label + '</span>';
                }

                var skillsHtml = '';
                if (r.matched_skills && r.matched_skills.length) {
                    skillsHtml = '<div class="result-skills">' +
                        r.matched_skills.map(function (s) {
                            return '<span class="pill-tag">' + escapeHtml(s) + '</span>';
                        }).join('') +
                        '</div>';
                }

                cardsHtml += '<div class="result-card">' +
                    '<div class="result-card-header">' +
                    '<div class="result-card-info">' +
                    '<i data-feather="user"></i>' +
                    '<div class="result-card-text">' +
                    '<span class="result-card-name">' + escapeHtml(r.candidate_name || r.filename) + '</span>' +
                    '<span class="result-card-filename">' + escapeHtml(r.candidate_email || r.filename) + '</span>' +
                    '</div>' +
                    '</div>' +
                    '<div style="display:flex;align-items:center;gap:8px;">' +
                    candidateStatusBadge +
                    '<div class="result-score ' + scoreClass + '">' + r.match_score + '</div>' +
                    '</div>' +
                    '</div>' +
                    skillsHtml +
                    (r.match_summary ? '<p class="result-card-summary">' + escapeHtml(r.match_summary) + '</p>' : '') +
                    '<div class="result-card-actions">' +
                    '<button class="btn-outline-sm jd-resume-btn" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" type="button"><i data-feather="file-text"></i> Resume</button>' +
                    (r.candidate_email ? '<button class="btn-outline-sm jd-invite-btn" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" data-email="' + escapeHtml(r.candidate_email) + '" type="button"><i data-feather="calendar"></i> Invite</button>' : '') +
                    '<button class="btn-outline-sm jd-delete-btn" data-id="' + r.id + '" data-name="' + escapeHtml(r.candidate_name || r.filename) + '" type="button" style="color:var(--color-danger,#ef4444);"><i data-feather="trash-2"></i></button>' +
                    '</div>' +
                    '</div>';
            });
            cardsHtml += '</div>';
        }

        detailCandidates.innerHTML = toolbar + cardsHtml;

        // Wire up file input
        var fileInput = document.getElementById('jd-resume-file-input');
        var uploadZone = document.getElementById('jd-upload-zone');
        var analyseBtn = document.getElementById('jd-analyse-btn');
        var uploadStatus = document.getElementById('jd-upload-status');

        if (fileInput) {
            fileInput.addEventListener('change', function () {
                if (fileInput.files.length) uploadNewResumes(jobId, fileInput.files, uploadStatus, analyseBtn);
            });
        }

        // Drag-and-drop removed — using button upload instead

        if (analyseBtn) {
            analyseBtn.addEventListener('click', function () {
                analyseNewCandidates(jobId, analyseBtn);
            });
        }

        if (window.feather) feather.replace();
    }

    function uploadNewResumes(jobId, files, statusEl, analyseBtn) {
        if (!jobId) return;
        var form = new FormData();
        var count = 0;
        Array.from(files).forEach(function (f) {
            if (f.name.toLowerCase().endsWith('.pdf')) { form.append('resumes', f); count++; }
        });
        if (!count) { if (window.toast) window.toast('Only PDF files are supported', 'error'); return; }

        if (statusEl) { statusEl.style.display = ''; statusEl.textContent = 'Uploading ' + count + ' file(s)…'; }
        if (analyseBtn) analyseBtn.disabled = true;

        fetch('/dashboard/upload-resumes/' + jobId, { method: 'POST', body: form })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (analyseBtn) analyseBtn.disabled = false;
                if (data.success) {
                    if (statusEl) statusEl.textContent = data.candidates.length + ' resume(s) uploaded. Click "Analyse" to score them.';
                    if (window.toast) window.toast(data.candidates.length + ' resume(s) uploaded', 'success');
                } else {
                    if (statusEl) statusEl.textContent = data.error || 'Upload failed';
                    if (window.toast) window.toast(data.error || 'Upload failed', 'error');
                }
            })
            .catch(function () {
                if (analyseBtn) analyseBtn.disabled = false;
                if (statusEl) statusEl.textContent = 'Network error during upload';
                if (window.toast) window.toast('Network error', 'error');
            });
    }

    function analyseNewCandidates(jobId, btn) {
        if (!jobId) return;
        if (btn) { btn.disabled = true; btn.innerHTML = '<i data-feather="loader"></i> Analysing…'; if (window.feather) feather.replace(); }

        fetch('/dashboard/screen-new-candidates/' + jobId, { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (btn) { btn.disabled = false; btn.innerHTML = '<i data-feather="zap"></i> Analyse'; if (window.feather) feather.replace(); }
                if (data.success) {
                    renderDetailCandidates(data.results);
                    if (window.toast) window.toast(data.new_count + ' new candidate(s) analysed and ranked', 'success');
                    // Update candidate count in the jobs table
                    var job = jobs.find(function (j) { return j.id === parseInt(jobId); });
                    if (job) { job.candidate_count = data.results.length; }
                    var row = tbody ? tbody.querySelector('tr[data-job-id="' + jobId + '"]') : null;
                    if (row && row.cells[3]) row.cells[3].textContent = data.results.length;
                } else {
                    if (window.toast) window.toast(data.error || 'No new candidates to analyse', 'error');
                }
            })
            .catch(function () {
                if (btn) { btn.disabled = false; btn.innerHTML = '<i data-feather="zap"></i> Analyse'; if (window.feather) feather.replace(); }
                if (window.toast) window.toast('Network error', 'error');
            });
    }



    if (detailPanel) {
        detailPanel.addEventListener('click', function (e) {
            var resumeBtn = e.target.closest('.jd-resume-btn');
            if (resumeBtn) {
                openResumePreview(resumeBtn.dataset.id, resumeBtn.dataset.name);
                return;
            }
            var inviteBtn = e.target.closest('.jd-invite-btn');
            if (inviteBtn) {
                openInviteModal(inviteBtn.dataset.id, inviteBtn.dataset.name, inviteBtn.dataset.email);
                return;
            }
            var deleteBtn = e.target.closest('.jd-delete-btn');
            if (deleteBtn) {
                deleteCandidate(deleteBtn.dataset.id, deleteBtn.dataset.name, deleteBtn);
                return;
            }
        });
    }

    detailTabs.forEach(function (btn) {
        btn.addEventListener('click', function () {
            detailTabs.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var tab = btn.dataset.tab;
            detailJd.style.display = tab === 'jd' ? '' : 'none';
            detailCandidates.style.display = tab === 'candidates' ? '' : 'none';
        });
    });

    if (detailBack) {
        detailBack.addEventListener('click', closeJobDetail);
    }

    if (jobStatusSelect) {
        jobStatusSelect.addEventListener('change', function () {
            var newStatus = jobStatusSelect.value;
            var jobId = jobDetailId ? parseInt(jobDetailId.value) : null;
            if (!jobId) return;

            fetch('/dashboard/update-job-status/' + jobId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.success) {
                        // Update badge in detail panel
                        detailBadge.innerHTML = statusBadge(data.status);
                        // Update in-memory jobs array
                        var job = jobs.find(function (j) { return j.id === jobId; });
                        if (job) job.status = data.status;
                        // Refresh table row badge
                        var row = tbody ? tbody.querySelector('tr[data-job-id="' + jobId + '"]') : null;
                        if (row) {
                            var statusCell = row.cells[5];
                            if (statusCell) statusCell.innerHTML = statusBadge(data.status);
                        }
                        // Refresh stat cards
                        updateStats();
                        if (window.toast) window.toast('Status updated to ' + data.status, 'success');
                    } else {
                        if (window.toast) window.toast(data.error || 'Failed to update status', 'error');
                        // Revert select to previous value
                        var job = jobs.find(function (j) { return j.id === jobId; });
                        if (job) jobStatusSelect.value = job.status;
                    }
                })
                .catch(function () {
                    if (window.toast) window.toast('Network error', 'error');
                });
        });
    }

    function closeJobDetail() {
        if (detailPanel) detailPanel.style.display = 'none';
        showTableView(true);
    }

    function showTableView(visible) {
        var display = visible ? '' : 'none';
        if (statsGrid) statsGrid.style.display = visible ? '' : 'none';
        if (sectionHeading) sectionHeading.style.display = visible ? '' : 'none';
        if (tableSection) tableSection.style.display = visible ? '' : 'none';
        if (emptyState && visible) applyFilters();
    }

    function openResumePreview(candidateId, name) {
        if (!resumeModal) return;
        resumeName.textContent = name || 'Resume Preview';
        resumeIframe.src = '/dashboard/resume-pdf/' + candidateId;
        resumeModal.style.display = '';
        if (window.feather) feather.replace();
    }

    function closeResumePreview() {
        if (!resumeModal) return;
        resumeModal.style.display = 'none';
        resumeIframe.src = '';
    }

    if (resumeClose) resumeClose.addEventListener('click', closeResumePreview);
    if (resumeModal) {
        resumeModal.addEventListener('click', function (e) {
            if (e.target === resumeModal) closeResumePreview();
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && resumeModal && resumeModal.style.display !== 'none') {
            closeResumePreview();
        }
    });

    setupNewJobModal();

    function setupNewJobModal() {
        const modal = document.getElementById('new-job-modal');
        const openBtn = document.getElementById('new-job-btn');
        const backdrop = document.getElementById('njm-backdrop');
        const closeBtn = document.getElementById('njm-close');
        const cancelBtn = document.getElementById('njm-cancel');
        const submitBtn = document.getElementById('njm-submit');
        if (!modal || !openBtn) return;

        function open() { modal.classList.add('active'); }
        function close() { modal.classList.remove('active'); }

        openBtn.addEventListener('click', open);
        if (backdrop) backdrop.addEventListener('click', close);
        if (closeBtn) closeBtn.addEventListener('click', close);
        if (cancelBtn) cancelBtn.addEventListener('click', close);
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

        if (submitBtn) submitBtn.addEventListener('click', handleSubmit);
    }

    function handleSubmit() {
        const title = document.getElementById('njm-title').value.trim();
        if (!title) {
            if (window.toast) window.toast('Please enter a job title', 'error');
            return;
        }

        const submitBtn = document.getElementById('njm-submit');
        submitBtn.disabled = true;

        const form = new FormData();
        form.append('title', title);
        form.append('department', document.getElementById('njm-dept').value);
        form.append('location', document.getElementById('njm-location').value.trim());
        form.append('salary_min', document.getElementById('njm-sal-min').value);
        form.append('salary_max', document.getElementById('njm-sal-max').value);
        form.append('description', document.getElementById('njm-desc').value.trim());
        form.append('skills', document.getElementById('njm-skills').value.trim());

        fetch('/dashboard/create-job', { method: 'POST', body: form })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                submitBtn.disabled = false;
                if (data.success) {
                    jobs.unshift(data.job);
                    applyFilters();
                    document.getElementById('new-job-modal').classList.remove('active');
                    clearForm();
                    if (window.toast) window.toast('Job created successfully', 'success');
                    updateStats();
                } else {
                    if (window.toast) window.toast(data.error || 'Failed to create job', 'error');
                }
            })
            .catch(function () {
                submitBtn.disabled = false;
                if (window.toast) window.toast('Network error', 'error');
            });
    }

    function clearForm() {
        document.getElementById('njm-title').value = '';
        document.getElementById('njm-dept').selectedIndex = 0;
        document.getElementById('njm-location').value = '';
        document.getElementById('njm-sal-min').value = '';
        document.getElementById('njm-sal-max').value = '';
        document.getElementById('njm-desc').value = '';
        document.getElementById('njm-skills').value = '';
    }

    function updateStats() {
        const cards = document.querySelectorAll('.stat-card .stat-value');
        if (cards.length < 4) return;
        const total = jobs.length;
        const open = jobs.filter(function (j) { return j.status === 'open'; }).length;
        const draft = jobs.filter(function (j) { return j.status === 'draft'; }).length;
        const completed = jobs.filter(function (j) { return j.status === 'completed'; }).length;
        cards[0].textContent = total;
        cards[1].textContent = open;
        cards[2].textContent = draft;
        cards[3].textContent = completed;
    }

    function deleteJob(jobId, title, btn) {
        if (!confirm('Permanently delete "' + (title || 'this job') + '" and all its candidates?')) return;
        if (btn) btn.disabled = true;
        fetch('/dashboard/delete-job/' + jobId, { method: 'DELETE' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    // Remove from in-memory array
                    var idx = jobs.findIndex(function (j) { return j.id === jobId; });
                    if (idx !== -1) jobs.splice(idx, 1);
                    // If detail panel is open for this job, close it
                    if (detailPanel && detailPanel.style.display !== 'none') {
                        var currentId = jobDetailId ? parseInt(jobDetailId.value) : null;
                        if (currentId === jobId) {
                            detailPanel.style.display = 'none';
                            showTableView(true);
                        }
                    }
                    applyFilters();
                    updateStats();
                    if (window.toast) window.toast('Job deleted', 'success');
                } else {
                    if (btn) btn.disabled = false;
                    if (window.toast) window.toast(data.error || 'Failed to delete job', 'error');
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                if (window.toast) window.toast('Network error', 'error');
            });
    }

    // Wire up the detail panel Delete Job button
    var detailDeleteBtn = document.getElementById('job-detail-delete');
    if (detailDeleteBtn) {
        detailDeleteBtn.addEventListener('click', function () {
            var jobId = jobDetailId ? parseInt(jobDetailId.value) : null;
            if (!jobId) return;
            var job = jobs.find(function (j) { return j.id === jobId; });
            deleteJob(jobId, job ? job.title : '', detailDeleteBtn);
        });
    }

    function deleteCandidate(candidateId, name, btn) {
        if (!confirm('Remove ' + (name || 'this candidate') + ' from the pool?')) return;
        if (btn) btn.disabled = true;
        fetch('/dashboard/delete-candidate/' + candidateId, { method: 'DELETE' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    // Remove card from DOM
                    var card = btn ? btn.closest('.result-card') : null;
                    if (card) card.remove();
                    // Update candidate count in table row
                    var jobId = jobDetailId ? jobDetailId.value : null;
                    if (jobId) {
                        var row = tbody ? tbody.querySelector('tr[data-job-id="' + jobId + '"]') : null;
                        if (row && row.cells[3]) {
                            var cur = parseInt(row.cells[3].textContent) || 0;
                            row.cells[3].textContent = Math.max(0, cur - 1);
                        }
                    }
                    if (window.toast) window.toast('Candidate removed', 'success');
                } else {
                    if (btn) btn.disabled = false;
                    if (window.toast) window.toast(data.error || 'Failed to remove candidate', 'error');
                }
            })
            .catch(function () {
                if (btn) btn.disabled = false;
                if (window.toast) window.toast('Network error', 'error');
            });
    }

    // ── Invite modal ───────────────────────────────────────────────────
    var _inviteCandidateId = null;
    var _inviteCandidateCard = null;

    var DEFAULT_INVITE_MSG =
        "Congratulations – you've been selected to move forward in our interview process for this role.\n\n" +
        "As the next step, please use the scheduling link below to choose an interview time that works best for you. " +
        "Once you've selected a slot, you'll receive a calendar invite with all the details.\n\n" +
        "If you have any questions or need to reschedule later, feel free to reply directly to this email.\n\n" +
        "Best regards";

    function openInviteModal(candidateId, name, email) {
        var modal = document.getElementById('jd-invite-modal');
        if (!modal) return;
        _inviteCandidateId = candidateId;
        var toEl = document.getElementById('jd-invite-modal-to');
        if (toEl) toEl.textContent = 'To: ' + (name || '') + (email ? ' <' + email + '>' : '');
        var linkEl = document.getElementById('jd-invite-link');
        var msgEl = document.getElementById('jd-invite-message');

        if (linkEl && !linkEl.value) {
            linkEl.value = "https://calendly.com/dahalaatmik/30min";
        }

        if (msgEl && !msgEl.value) {
            msgEl.value = DEFAULT_INVITE_MSG;
        }

        modal.style.display = '';
        if (window.feather) feather.replace();
    }

    function closeInviteModal() {
        var modal = document.getElementById('jd-invite-modal');
        if (modal) modal.style.display = 'none';
        _inviteCandidateId = null;
    }

    (function setupInviteModal() {
        var modal = document.getElementById('jd-invite-modal');
        if (!modal) return;
        var closeBtn = document.getElementById('jd-invite-modal-close');
        var cancelBtn = document.getElementById('jd-invite-cancel');
        var sendBtn = document.getElementById('jd-invite-send');

        if (closeBtn) closeBtn.addEventListener('click', closeInviteModal);
        if (cancelBtn) cancelBtn.addEventListener('click', closeInviteModal);
        // Click outside modal content to close
        modal.addEventListener('click', function (e) { if (e.target === modal) closeInviteModal(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.style.display !== 'none') closeInviteModal(); });

        if (sendBtn) {
            sendBtn.addEventListener('click', function () {
                var link = (document.getElementById('jd-invite-link') || {}).value || '';
                var msg = (document.getElementById('jd-invite-message') || {}).value || '';
                // scheduling link is optional (matches dashboard behaviour)
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending…';

                fetch('/dashboard/send-invites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candidate_ids: [parseInt(_inviteCandidateId)],
                        scheduling_link: link.trim(),
                        message: msg
                    })
                })
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        sendBtn.disabled = false;
                        sendBtn.innerHTML = '<i data-feather="send"></i> Send Invite';
                        if (window.feather) feather.replace();
                        if (data.success) {
                            closeInviteModal();
                            var sent = data.results && data.results[0] && data.results[0].email_sent;
                            if (window.toast) window.toast(sent ? 'Invite sent!' : 'Invite recorded (email not configured)', 'success');
                            // Update the badge on the card
                            var btn = detailCandidates.querySelector('.jd-invite-btn[data-id="' + _inviteCandidateId + '"]');
                            if (btn) {
                                var card = btn.closest('.result-card');
                                if (card) {
                                    var badge = card.querySelector('.job-card-badge');
                                    if (badge) { badge.className = 'job-card-badge badge-invited'; badge.textContent = 'Invited'; }
                                }
                            }
                        } else {
                            if (window.toast) window.toast(data.error || 'Failed to send invite', 'error');
                        }
                    })
                    .catch(function () {
                        sendBtn.disabled = false;
                        sendBtn.innerHTML = '<i data-feather="send"></i> Send Invite';
                        if (window.feather) feather.replace();
                        if (window.toast) window.toast('Network error', 'error');
                    });
            });
        }
    })();
})();

