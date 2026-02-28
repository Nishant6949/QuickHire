(function () {
    var candidates = window.__candidates || [];
    var els = {};

    function init() {
        cacheElements();
        bindFilters();
        bindTableClicks();
        bindContactModal();
        bindDetailModal();
        if (window.feather) feather.replace();
        if (window.setupDashboardReveal) window.setupDashboardReveal();
    }

    function cacheElements() {
        els.tbody = document.getElementById("cand-tbody");
        els.empty = document.getElementById("cand-empty");
        els.tableWrap = els.tbody ? els.tbody.closest(".data-table-wrap") : null;
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

    function bindFilters() {
        if (els.search) els.search.addEventListener("input", applyFilters);
        if (els.statusFilter) els.statusFilter.addEventListener("change", applyFilters);
        if (els.jobFilter) els.jobFilter.addEventListener("change", applyFilters);
    }

    function applyFilters() {
        var query = (els.search ? els.search.value : "").toLowerCase().trim();
        var status = els.statusFilter ? els.statusFilter.value : "all";
        var jobId = els.jobFilter ? els.jobFilter.value : "all";

        var rows = els.tbody.querySelectorAll("tr[data-id]");
        var visibleCount = 0;

        rows.forEach(function (row) {
            var show = true;
            if (query) {
                var name = (row.dataset.name || "").toLowerCase();
                var email = (row.dataset.email || "").toLowerCase();
                if (name.indexOf(query) === -1 && email.indexOf(query) === -1) show = false;
            }
            if (show && status !== "all" && row.dataset.status !== status) show = false;
            if (show && jobId !== "all" && row.dataset.jobId !== jobId) show = false;

            row.style.display = show ? "" : "none";
            if (show) visibleCount++;
        });

        if (els.tableWrap) els.tableWrap.style.display = visibleCount > 0 ? "" : "none";
        if (els.empty) els.empty.style.display = visibleCount > 0 ? "none" : "";
    }

    function bindTableClicks() {
        if (!els.tbody) return;
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
                    var row = els.tbody.querySelector('tr[data-id="' + id + '"]');
                    if (row) row.remove();
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
        if (!els.contactModal) return;
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
        if (!els.detailModal) return;
        els.detailClose.addEventListener("click", closeDetailModal);
        els.detailModal.addEventListener("click", function (e) {
            if (e.target === els.detailModal) closeDetailModal();
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                if (els.contactModal && els.contactModal.style.display !== "none") closeContactModal();
                else if (els.detailModal && els.detailModal.style.display !== "none") closeDetailModal();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", init);
})();
