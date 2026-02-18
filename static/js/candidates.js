(function () {
    var candidates = window.__candidates || [];
    var els = {};

    function init() {
        cacheElements();
        populateJobFilter();
        bindFilters();
        bindTableClicks();
        bindContactModal();
        bindDetailModal();
        renderTable(candidates);
        if (window.feather) feather.replace();
    }

    function cacheElements() {
        els.tbody = document.getElementById("cand-tbody");
        els.empty = document.getElementById("cand-empty");
        els.search = document.getElementById("cand-search");
        els.statusFilter = document.getElementById("cand-status-filter");
        els.jobFilter = document.getElementById("cand-job-filter");
        els.contactModal = document.getElementById("contact-modal");
        els.contactClose = document.getElementById("contact-modal-close");
        els.contactCancel = document.getElementById("contact-cancel-btn");
        els.contactSend = document.getElementById("contact-send-btn");
        els.contactTo = document.getElementById("contact-to");
        els.contactSubject = document.getElementById("contact-subject");
        els.contactBody = document.getElementById("contact-body");
        els.contactCandidateId = document.getElementById("contact-candidate-id");
        els.detailModal = document.getElementById("detail-modal");
        els.detailClose = document.getElementById("detail-modal-close");
        els.detailName = document.getElementById("detail-modal-name");
        els.detailBody = document.getElementById("detail-modal-body");
    }

    function populateJobFilter() {
        var jobs = {};
        candidates.forEach(function (c) {
            if (c.job_id && c.job_title) jobs[c.job_id] = c.job_title;
        });
        Object.keys(jobs).forEach(function (id) {
            var opt = document.createElement("option");
            opt.value = id;
            opt.textContent = jobs[id];
            els.jobFilter.appendChild(opt);
        });
    }

    function bindFilters() {
        els.search.addEventListener("input", applyFilters);
        els.statusFilter.addEventListener("change", applyFilters);
        els.jobFilter.addEventListener("change", applyFilters);
    }

    function applyFilters() {
        var query = els.search.value.toLowerCase().trim();
        var status = els.statusFilter.value;
        var jobId = els.jobFilter.value;

        var filtered = candidates.filter(function (c) {
            if (query && (c.candidate_name || "").toLowerCase().indexOf(query) === -1 &&
                (c.candidate_email || "").toLowerCase().indexOf(query) === -1) return false;
            if (status !== "all" && c.status !== status) return false;
            if (jobId !== "all" && String(c.job_id) !== jobId) return false;
            return true;
        });

        renderTable(filtered);
    }

    function renderTable(rows) {
        els.tbody.innerHTML = "";

        if (rows.length === 0) {
            els.empty.style.display = "";
            els.tbody.closest(".data-table-wrap").style.display = "none";
            if (window.feather) feather.replace();
            return;
        }

        els.empty.style.display = "none";
        els.tbody.closest(".data-table-wrap").style.display = "";

        rows.forEach(function (c) {
            var tr = document.createElement("tr");
            tr.dataset.id = c.id;
            tr.style.cursor = "pointer";

            var skillPills = (c.matched_skills || []).slice(0, 3).map(function (s) {
                return '<span class="pill-tag">' + escapeHtml(s) + '</span>';
            }).join("");
            if ((c.matched_skills || []).length > 3) {
                skillPills += '<span class="pill-tag" style="opacity:0.6;">+' + (c.matched_skills.length - 3) + '</span>';
            }

            var scoreClass = c.match_score >= 90 ? "green" : c.match_score >= 70 ? "amber" : "red";
            var statusBadge = buildStatusBadge(c.status);
            var hasEmail = c.candidate_email && c.candidate_email.length > 0;

            tr.innerHTML =
                '<td>' +
                '<div style="display:flex;flex-direction:column;">' +
                '<span style="font-weight:600;color:var(--color-text-high);">' + escapeHtml(c.candidate_name || "Unknown") + '</span>' +
                '<span style="font-size:var(--font-size-xs);color:var(--color-text-disabled);">' + escapeHtml(c.candidate_email || "") + '</span>' +
                '</div>' +
                '</td>' +
                '<td>' + escapeHtml(c.job_title || "Unknown") + '</td>' +
                '<td>' + skillPills + '</td>' +
                '<td><div class="result-score ' + scoreClass + '" style="width:40px;height:36px;font-size:var(--font-size-sm);">' + c.match_score + '</div></td>' +
                '<td>' + statusBadge + '</td>' +
                '<td style="white-space:nowrap;">' +
                '<button class="contact-btn card-pdf-btn" data-id="' + c.id + '" type="button"' + (hasEmail ? '' : ' disabled') + '><i data-feather="mail"></i> Contact</button>' +
                ' <button class="delete-cand-btn" data-id="' + c.id + '" type="button" title="Delete candidate" style="background:transparent;border:1px solid rgba(239,68,68,0.5);color:var(--color-danger);border-radius:6px;padding:6px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;font-size:var(--font-size-xs);transition:all 0.15s;"><i data-feather="trash-2" style="width:18px;height:18px;"></i></button>' +
                '</td>';

            els.tbody.appendChild(tr);
        });

        if (window.feather) feather.replace();
    }

    function buildStatusBadge(status) {
        var map = {
            "scored": { cls: "badge-ready", label: "Scored" },
            "pending": { cls: "badge-draft", label: "Pending" },
            "invited": { cls: "badge-invited", label: "Invited" },
            "interview_done": { cls: "badge-interview-done", label: "Interview Done" },
            "shortlisted": { cls: "badge-shortlisted", label: "Shortlisted" },
            "final_hired": { cls: "badge-final-hired", label: "Hired" },
            "final_rejected": { cls: "badge-final-rejected", label: "Rejected" },
            "error": { cls: "badge-draft", label: "Error" }
        };
        var info = map[status] || { cls: "badge-draft", label: status || "Unknown" };
        return '<span class="job-card-badge ' + info.cls + '">' + info.label + '</span>';
    }

    function bindTableClicks() {
        els.tbody.addEventListener("click", function (e) {
            var deleteBtn = e.target.closest(".delete-cand-btn");
            if (deleteBtn) {
                e.stopPropagation();
                deleteCandidate(parseInt(deleteBtn.dataset.id));
                return;
            }
            var contactBtn = e.target.closest(".contact-btn");
            if (contactBtn) {
                e.stopPropagation();
                openContactModal(parseInt(contactBtn.dataset.id));
                return;
            }
            var row = e.target.closest("tr");
            if (row && row.dataset.id) {
                openDetailModal(parseInt(row.dataset.id));
            }
        });
    }

    function deleteCandidate(id) {
        if (!confirm("Remove this candidate? This cannot be undone.")) return;

        fetch("/dashboard/remove-resume/" + id, { method: "DELETE" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    candidates = candidates.filter(function (c) { return c.id !== id; });
                    applyFilters();
                    if (window.toast) window.toast("Candidate removed", "success");
                } else {
                    if (window.toast) window.toast(data.error || "Could not delete candidate", "error");
                }
            })
            .catch(function () {
                if (window.toast) window.toast("Network error", "error");
            });
    }

    function openContactModal(id) {
        var c = candidates.find(function (x) { return x.id === id; });
        if (!c) return;
        els.contactTo.value = c.candidate_email || "";
        els.contactSubject.value = "";
        els.contactBody.value = "";
        els.contactCandidateId.value = id;
        els.contactModal.style.display = "";
        if (window.feather) feather.replace();
    }

    function closeContactModal() {
        els.contactModal.style.display = "none";
    }

    function submitContact() {
        var candidateId = parseInt(els.contactCandidateId.value);
        var subject = els.contactSubject.value.trim();
        var body = els.contactBody.value.trim();

        if (!subject || !body) {
            window.toast("Please fill in subject and message", "error");
            return;
        }

        els.contactSend.disabled = true;
        els.contactSend.textContent = "Sending...";

        fetch("/dashboard/send-custom-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candidate_id: candidateId, subject: subject, body: body })
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.success) {
                    closeContactModal();
                    var note = data.email_sent ? "Email sent" : "Email queued (SMTP not configured)";
                    window.toast(note, "success");
                } else {
                    window.toast(data.error || "Failed to send", "error");
                }
            })
            .catch(function () {
                window.toast("Network error", "error");
            })
            .finally(function () {
                els.contactSend.disabled = false;
                els.contactSend.innerHTML = '<i data-feather="send"></i> Send Email';
                if (window.feather) feather.replace();
            });
    }

    function bindContactModal() {
        els.contactClose.addEventListener("click", closeContactModal);
        els.contactCancel.addEventListener("click", closeContactModal);
        els.contactSend.addEventListener("click", submitContact);
        els.contactModal.addEventListener("click", function (e) {
            if (e.target === els.contactModal) closeContactModal();
        });
    }

    function openDetailModal(id) {
        var c = candidates.find(function (x) { return x.id === id; });
        if (!c) return;

        els.detailName.textContent = c.candidate_name || "Candidate Details";

        var scoreClass = c.match_score >= 90 ? "green" : c.match_score >= 70 ? "amber" : "red";

        var skillsHtml = "";
        if (c.matched_skills && c.matched_skills.length) {
            skillsHtml = '<div style="margin-top:var(--spacing-md);">' +
                '<span class="analysis-field-label">Matched Skills</span>' +
                '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:var(--spacing-xs);">' +
                c.matched_skills.map(function (s) {
                    return '<span class="pill-tag">' + escapeHtml(s) + '</span>';
                }).join("") +
                '</div></div>';
        }

        var summaryHtml = "";
        if (c.match_summary) {
            summaryHtml = '<div style="margin-top:var(--spacing-md);">' +
                '<span class="analysis-field-label">AI Summary</span>' +
                '<p style="color:var(--color-text-low);font-size:var(--font-size-sm);line-height:1.6;margin-top:var(--spacing-xs);">' + escapeHtml(c.match_summary) + '</p>' +
                '</div>';
        }

        function buildBar(label, score) {
            var color = score >= 90 ? "var(--color-primary)" : score >= 70 ? "var(--color-warning)" : "var(--color-danger)";
            return '<div class="score-bar-row">' +
                '<span class="score-bar-label">' + label + '</span>' +
                '<div class="score-bar-track"><div class="score-bar-fill" style="width:' + score + '%;background:' + color + '"></div></div>' +
                '<span class="score-bar-value">' + score + '</span></div>';
        }

        els.detailBody.innerHTML =
            '<div style="display:flex;align-items:center;gap:var(--spacing-lg);margin-bottom:var(--spacing-lg);">' +
            '<div class="result-score ' + scoreClass + '" style="width:56px;height:56px;font-size:var(--font-size-xl);">' + c.match_score + '</div>' +
            '<div>' +
            '<div style="font-weight:600;color:var(--color-text-high);font-size:var(--font-size-lg);">' + escapeHtml(c.candidate_name || "Unknown") + '</div>' +
            '<div style="color:var(--color-text-disabled);font-size:var(--font-size-sm);">' + escapeHtml(c.candidate_email || "") + '</div>' +
            '<div style="color:var(--color-text-low);font-size:var(--font-size-xs);margin-top:2px;">' + escapeHtml(c.job_title || "") + '</div>' +
            '</div>' +
            '</div>' +
            '<div class="result-breakdown">' +
            buildBar("Skills", c.skills_score) +
            buildBar("Experience", c.experience_score) +
            buildBar("Education", c.education_score) +
            '</div>' +
            skillsHtml +
            summaryHtml;

        els.detailModal.style.display = "";
        if (window.feather) feather.replace();
    }

    function closeDetailModal() {
        els.detailModal.style.display = "none";
    }

    function bindDetailModal() {
        els.detailClose.addEventListener("click", closeDetailModal);
        els.detailModal.addEventListener("click", function (e) {
            if (e.target === els.detailModal) closeDetailModal();
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                if (els.contactModal.style.display !== "none") closeContactModal();
                else if (els.detailModal.style.display !== "none") closeDetailModal();
            }
        });
    }

    function escapeHtml(str) {
        var div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    document.addEventListener("DOMContentLoaded", init);
})();
