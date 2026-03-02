(function () {
    var tbody = document.getElementById('jobs-tbody');
    var emptyState = document.getElementById('jobs-empty');
    var searchInput = document.getElementById('jobs-search');
    var deptFilter = document.getElementById('jobs-dept-filter');
    var statusFilter = document.getElementById('jobs-status-filter');
    var dateFilter = document.getElementById('jobs-date-filter');

    var tableSection = document.querySelector('.data-table-wrap');
    var statsGrid = document.querySelector('.stats-grid');
    var sectionHeading = document.querySelector('.section-heading');
    var detailPanel = document.getElementById('job-detail-panel');
    var detailBack = document.getElementById('job-detail-back');
    var detailTitle = document.getElementById('job-detail-title');
    var detailBadge = document.getElementById('job-detail-badge');
    var detailMeta = document.getElementById('job-detail-meta');
    var detailJd = document.getElementById('job-detail-jd');
    var detailCandidates = document.getElementById('job-detail-candidates');
    var detailTabs = detailPanel ? detailPanel.querySelectorAll('.jd-toggle-btn') : [];
    var jobDetailId = document.getElementById('job-detail-id');
    var jobStatusSelect = document.getElementById('job-status-select');

    var resumeModal = document.getElementById('resume-preview-modal');
    var resumeClose = document.getElementById('resume-preview-close');
    var resumeName = document.getElementById('resume-preview-name');
    var resumeIframe = document.getElementById('resume-preview-iframe');

    var _searchTimer = null;

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
                '<td>' + escapeHtml(j.department || '\u2014') + '</td>' +
                '<td>' + escapeHtml(j.location || '\u2014') + '</td>' +
                '<td>' + j.candidate_count + '</td>' +
                '<td>' + j.created_at + '</td>' +
                '<td>' + (j.status_html || '') + '</td>' +
                '<td style="text-align:right;">' +
                '<button class="btn-outline-sm job-row-delete-btn" data-job-id="' + j.id + '" data-title="' + escapeHtml(j.title) + '" type="button" title="Delete job" style="color:var(--color-danger,#ef4444);border-color:var(--color-danger,#ef4444);padding:4px 8px;">' +
                '<i data-feather="trash-2"></i>' +
                '</button>' +
                '</td>' +
                '</tr>';
        }).join('');
        if (window.feather) feather.replace();
    }

    function refreshStats(stats) {
        var cards = document.querySelectorAll('.stat-card .stat-value');
        if (cards.length < 4 || !stats) return;
        cards[0].textContent = stats.total;
        cards[1].textContent = stats.open;
        cards[2].textContent = stats.draft;
        cards[3].textContent = stats.completed;
    }

    function applyFilters() {
        var search = (searchInput ? searchInput.value : '').trim();
        var dept = deptFilter ? deptFilter.value : 'all';
        var status = statusFilter ? statusFilter.value : 'all';
        var days = dateFilter ? dateFilter.value : 'all';

        var params = new URLSearchParams();
        if (search) params.set('q', search);
        if (dept !== 'all') params.set('dept', dept);
        if (status !== 'all') params.set('status', status);
        if (days !== 'all') params.set('days', days);

        fetch('/dashboard/jobs-filtered?' + params.toString())
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    renderTable(data.jobs);
                    refreshStats(data.stats);
                }
            })
            .catch(function () {});
    }

    function debouncedApplyFilters() {
        if (_searchTimer) clearTimeout(_searchTimer);
        _searchTimer = setTimeout(applyFilters, 250);
    }

    if (searchInput) searchInput.addEventListener('input', debouncedApplyFilters);
    if (deptFilter) deptFilter.addEventListener('change', applyFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    if (dateFilter) dateFilter.addEventListener('change', applyFilters);

    renderTable(window.__jobs || []);

    if (tbody) {
        tbody.addEventListener('click', function (e) {
            if (e.target.closest('.job-row-delete-btn')) {
                var btn = e.target.closest('.job-row-delete-btn');
                deleteJob(parseInt(btn.dataset.jobId), btn.dataset.title, btn);
                return;
            }
            var row = e.target.closest('tr[data-job-id]');
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
        detailBadge.innerHTML = job.status_html || '';
        if (jobDetailId) jobDetailId.value = job.id;
        if (jobStatusSelect) jobStatusSelect.value = job.status;

        var metaPills = [];
        if (job.department) metaPills.push('<span class="pill-tag">' + escapeHtml(job.department) + '</span>');
        if (job.location) metaPills.push('<span class="pill-tag">' + escapeHtml(job.location) + '</span>');
        if (job.salary_min || job.salary_max) {
            var sal = '';
            if (job.salary_min && job.salary_max) sal = '$' + job.salary_min.toLocaleString() + ' \u2013 $' + job.salary_max.toLocaleString();
            else if (job.salary_min) sal = 'From $' + job.salary_min.toLocaleString();
            else sal = 'Up to $' + job.salary_max.toLocaleString();
            metaPills.push('<span class="pill-tag">' + sal + '</span>');
        }
        if (job.required_skills) metaPills.push('<span class="pill-tag">' + escapeHtml(job.required_skills) + '</span>');
        detailMeta.innerHTML = metaPills.join('');

        detailJd.innerHTML = job.jd_text_html
            ? '<div class="job-detail-jd-text">' + job.jd_text_html + '</div>'
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

        var cardsHtml = '';
        if (!candidates || candidates.length === 0) {
            cardsHtml = '<p style="color:var(--color-text-disabled);padding:var(--spacing-lg) 0;">No candidates yet \u2014 upload resumes above and click Analyse.</p>';
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

        var fileInput = document.getElementById('jd-resume-file-input');
        var analyseBtn = document.getElementById('jd-analyse-btn');
        var uploadStatus = document.getElementById('jd-upload-status');

        if (fileInput) {
            fileInput.addEventListener('change', function () {
                if (fileInput.files.length) uploadNewResumes(jobId, fileInput.files, uploadStatus, analyseBtn);
            });
        }

        if (analyseBtn) {
            analyseBtn.addEventListener('click', function () {
                analyseNewCandidates(jobId, analyseBtn);
            });
        }

        if (window.feather) feather.replace();
    }

    function uploadNewResumes(jobId, files, statusEl, analyseBtn) {
        if (!jobId) return;
        var pdfFiles = Array.from(files).filter(function (f) {
            return f.name.toLowerCase().endsWith('.pdf');
        });
        if (!pdfFiles.length) { if (window.toast) window.toast('Only PDF files are supported', 'error'); return; }

        if (statusEl) { statusEl.style.display = ''; statusEl.textContent = 'Uploading 0/' + pdfFiles.length + ' file(s)\u2026'; }
        if (analyseBtn) analyseBtn.disabled = true;

        var totalCandidates = [];

        function uploadNext(index) {
            if (index >= pdfFiles.length) {
                if (analyseBtn) analyseBtn.disabled = false;
                if (totalCandidates.length) {
                    if (statusEl) statusEl.textContent = totalCandidates.length + ' resume(s) uploaded. Click "Analyse" to score them.';
                    if (window.toast) window.toast(totalCandidates.length + ' resume(s) uploaded', 'success');
                } else {
                    if (statusEl) statusEl.textContent = 'No valid resumes could be processed';
                    if (window.toast) window.toast('Upload failed', 'error');
                }
                return;
            }

            var form = new FormData();
            form.append('resumes', pdfFiles[index]);
            if (statusEl) statusEl.textContent = 'Uploading ' + (index + 1) + '/' + pdfFiles.length + ' \u2014 ' + pdfFiles[index].name;

            fetch('/dashboard/upload-resumes/' + jobId, { method: 'POST', body: form })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.success) {
                        totalCandidates = totalCandidates.concat(data.candidates);
                    }
                    uploadNext(index + 1);
                })
                .catch(function () {
                    uploadNext(index + 1);
                });
        }

        uploadNext(0);
    }

    function analyseNewCandidates(jobId, btn) {
        if (!jobId) return;
        if (btn) { btn.disabled = true; btn.innerHTML = '<i data-feather="loader"></i> Analysing\u2026'; if (window.feather) feather.replace(); }

        fetch('/dashboard/screen-new-candidates/' + jobId, { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (btn) { btn.disabled = false; btn.innerHTML = '<i data-feather="zap"></i> Analyse'; if (window.feather) feather.replace(); }
                if (data.success) {
                    renderDetailCandidates(data.results);
                    if (window.toast) window.toast(data.new_count + ' new candidate(s) analysed and ranked', 'success');
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

    var _prevStatus = null;
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
                        detailBadge.innerHTML = data.status_html || '';
                        var row = tbody ? tbody.querySelector('tr[data-job-id="' + jobId + '"]') : null;
                        if (row) {
                            var statusCell = row.cells[5];
                            if (statusCell) statusCell.innerHTML = data.status_html || '';
                        }
                        refreshStats(data.stats);
                        if (window.toast) window.toast('Status updated to ' + data.status, 'success');
                        _prevStatus = data.status;
                    } else {
                        if (window.toast) window.toast(data.error || 'Failed to update status', 'error');
                        if (_prevStatus) jobStatusSelect.value = _prevStatus;
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
        if (statsGrid) statsGrid.style.display = visible ? '' : 'none';
        if (sectionHeading) sectionHeading.style.display = visible ? '' : 'none';
        if (tableSection) tableSection.style.display = visible ? '' : 'none';
        if (visible) applyFilters();
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
        var modal = document.getElementById('new-job-modal');
        var openBtn = document.getElementById('new-job-btn');
        var backdrop = document.getElementById('njm-backdrop');
        var closeBtn = document.getElementById('njm-close');
        var cancelBtn = document.getElementById('njm-cancel');
        var submitBtn = document.getElementById('njm-submit');
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
        var title = document.getElementById('njm-title').value.trim();
        if (!title) {
            if (window.toast) window.toast('Please enter a job title', 'error');
            return;
        }

        var submitBtn = document.getElementById('njm-submit');
        submitBtn.disabled = true;

        var form = new FormData();
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
                    applyFilters();
                    refreshStats(data.stats);
                    document.getElementById('new-job-modal').classList.remove('active');
                    clearForm();
                    if (window.toast) window.toast('Job created successfully', 'success');
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

    function deleteJob(jobId, title, btn) {
        if (!confirm('Permanently delete "' + (title || 'this job') + '" and all its candidates?')) return;
        if (btn) btn.disabled = true;
        fetch('/dashboard/delete-job/' + jobId, { method: 'DELETE' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    if (detailPanel && detailPanel.style.display !== 'none') {
                        var currentId = jobDetailId ? parseInt(jobDetailId.value) : null;
                        if (currentId === jobId) {
                            detailPanel.style.display = 'none';
                            showTableView(true);
                            return;
                        }
                    }
                    applyFilters();
                    refreshStats(data.stats);
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

    var detailDeleteBtn = document.getElementById('job-detail-delete');
    if (detailDeleteBtn) {
        detailDeleteBtn.addEventListener('click', function () {
            var jobId = jobDetailId ? parseInt(jobDetailId.value) : null;
            if (!jobId) return;
            var titleEl = detailTitle;
            deleteJob(jobId, titleEl ? titleEl.textContent : '', detailDeleteBtn);
        });
    }

    function deleteCandidate(candidateId, name, btn) {
        if (!confirm('Remove ' + (name || 'this candidate') + ' from the pool?')) return;
        if (btn) btn.disabled = true;
        fetch('/dashboard/delete-candidate/' + candidateId, { method: 'DELETE' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    var card = btn ? btn.closest('.result-card') : null;
                    if (card) card.remove();
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

    var _inviteCandidateId = null;

    function openInviteModal(candidateId, name, email) {
        var modal = document.getElementById('jd-invite-modal');
        if (!modal) return;
        _inviteCandidateId = candidateId;
        var toEl = document.getElementById('jd-invite-modal-to');
        if (toEl) toEl.textContent = 'To: ' + (name || '') + (email ? ' <' + email + '>' : '');
        var linkEl = document.getElementById('jd-invite-link');
        var msgEl = document.getElementById('jd-invite-message');

        if (linkEl && !linkEl.value) {
            linkEl.value = "";
        }

        if (msgEl && !msgEl.value) {
            msgEl.value = msgEl.dataset.default || '';
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
        modal.addEventListener('click', function (e) { if (e.target === modal) closeInviteModal(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.style.display !== 'none') closeInviteModal(); });

        if (sendBtn) {
            sendBtn.addEventListener('click', function () {
                var link = (document.getElementById('jd-invite-link') || {}).value || '';
                var msg = (document.getElementById('jd-invite-message') || {}).value || '';
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending\u2026';

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
                            var invBtn = detailCandidates.querySelector('.jd-invite-btn[data-id="' + _inviteCandidateId + '"]');
                            if (invBtn) {
                                var card = invBtn.closest('.result-card');
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
    if (window.setupDashboardReveal) window.setupDashboardReveal();
})();
