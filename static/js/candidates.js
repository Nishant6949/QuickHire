(function () {
    "use strict";

    var candidates = window.__candidates || [];
    var employerCompany = window.__employerCompany || "the hiring team";
    var els = {};

    function init() {
        cacheElements();
        bindFilters();
        bindTableClicks();
        bindContactModal();
        bindDetailModal();

        if (window.feather) window.feather.replace();
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
        els.contactTemplate = document.getElementById("contact-template");
        els.contactSubject = document.getElementById("contact-subject");
        els.contactBody = document.getElementById("contact-body");
        els.contactCandidateId = document.getElementById("contact-candidate-id");
        els.interviewFields = document.getElementById("interview-fields");
        els.interviewDate = document.getElementById("interview-date");
        els.interviewTime = document.getElementById("interview-time");
        els.interviewLink = document.getElementById("interview-link");

        els.detailModal = document.getElementById("detail-modal");
        els.detailClose = document.getElementById("detail-modal-close");
        els.detailName = document.getElementById("detail-modal-name");
        els.detailBody = document.getElementById("detail-modal-body");
    }

    function getCandidate(id) {
        return candidates.find(function (candidate) {
            return candidate.id === id;
        });
    }

    function notify(message, type) {
        if (window.toast) {
            window.toast(message, type || "success");
        }
    }

    function bindFilters() {
        if (els.search) els.search.addEventListener("input", applyFilters);
        if (els.statusFilter) els.statusFilter.addEventListener("change", applyFilters);
        if (els.jobFilter) els.jobFilter.addEventListener("change", applyFilters);
    }

    function applyFilters() {
        if (!els.tbody) return;

        var query = (els.search ? els.search.value : "").toLowerCase().trim();
        var status = els.statusFilter ? els.statusFilter.value : "all";
        var jobId = els.jobFilter ? els.jobFilter.value : "all";
        var rows = els.tbody.querySelectorAll("tr[data-id]");
        var visibleCount = 0;

        rows.forEach(function (row) {
            var show = true;
            var name = (row.dataset.name || "").toLowerCase();
            var email = (row.dataset.email || "").toLowerCase();

            if (query && name.indexOf(query) === -1 && email.indexOf(query) === -1) {
                show = false;
            }
            if (show && status !== "all" && row.dataset.status !== status) {
                show = false;
            }
            if (show && jobId !== "all" && row.dataset.jobId !== jobId) {
                show = false;
            }

            row.style.display = show ? "" : "none";
            if (show) visibleCount += 1;
        });

        if (els.tableWrap) els.tableWrap.style.display = visibleCount > 0 ? "" : "none";
        if (els.empty) els.empty.style.display = visibleCount > 0 ? "none" : "flex";
    }

    function bindTableClicks() {
        if (!els.tbody) return;

        els.tbody.addEventListener("click", function (event) {
            var deleteButton = event.target.closest(".delete-cand-btn");
            if (deleteButton) {
                event.stopPropagation();
                deleteCandidate(parseInt(deleteButton.dataset.id, 10));
                return;
            }

            var contactButton = event.target.closest(".contact-btn");
            if (contactButton) {
                event.stopPropagation();
                openContactModal(parseInt(contactButton.dataset.id, 10), "application_update");
                return;
            }

            var row = event.target.closest("tr[data-id]");
            if (row) openDetailModal(parseInt(row.dataset.id, 10));
        });
    }

    function deleteCandidate(id) {
        if (!confirm("Remove this applicant? This cannot be undone.")) return;

        fetch("/dashboard/remove-resume/" + id, { method: "DELETE" })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.success) throw new Error(data.error || "Could not remove applicant");

                candidates = candidates.filter(function (candidate) {
                    return candidate.id !== id;
                });

                var row = els.tbody.querySelector('tr[data-id="' + id + '"]');
                if (row) row.remove();
                applyFilters();
                notify("Applicant removed", "success");
            })
            .catch(function (error) {
                notify(error.message || "Network error", "error");
            });
    }

    function formatInterviewDate(dateValue, timeValue) {
        if (!dateValue) return "";

        var date = new Date(dateValue + "T" + (timeValue || "09:00"));
        if (Number.isNaN(date.getTime())) return dateValue;

        return date.toLocaleString(undefined, {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: timeValue ? "numeric" : undefined,
            minute: timeValue ? "2-digit" : undefined
        });
    }

    function buildMessageTemplate(candidate, templateName) {
        var name = candidate.candidate_name || "there";
        var jobTitle = candidate.job_title || "the position";
        var company = employerCompany || "our hiring team";
        var interviewWhen = formatInterviewDate(
            els.interviewDate ? els.interviewDate.value : "",
            els.interviewTime ? els.interviewTime.value : ""
        );
        var interviewLink = els.interviewLink ? els.interviewLink.value.trim() : "";

        if (templateName === "interview_invitation") {
            var interviewBody =
                "Thank you for your application for the " + jobTitle + " position. We would like to invite you to an interview with " + company + ".";

            if (interviewWhen) {
                interviewBody += "\n\nInterview date and time: " + interviewWhen;
            }
            if (interviewLink) {
                interviewBody += "\nMeeting link / location: " + interviewLink;
            }

            interviewBody +=
                "\n\nPlease reply to this email if you have any questions or if you need to arrange another time." +
                "\n\nWe look forward to speaking with you." +
                "\n\nBest regards,\n" + company;

            return {
                subject: "Interview Invitation - " + jobTitle,
                body: interviewBody,
                markStatus: "invited"
            };
        }

        if (templateName === "shortlisted") {
            return {
                subject: "Application Update - " + jobTitle,
                body:
                    "Good news. Your application for the " + jobTitle + " position has been shortlisted for further review." +
                    "\n\nWe will contact you again when the next stage is confirmed." +
                    "\n\nThank you for your interest in " + company + "." +
                    "\n\nBest regards,\n" + company,
                markStatus: "shortlisted"
            };
        }

        if (templateName === "hired") {
            return {
                subject: "Congratulations - " + jobTitle,
                body:
                    "Congratulations. We are pleased to let you know that you have been selected for the " + jobTitle + " position." +
                    "\n\nOur team will contact you with the next steps and onboarding information." +
                    "\n\nBest regards,\n" + company,
                markStatus: "final_hired"
            };
        }

        if (templateName === "rejection") {
            return {
                subject: "Application Update - " + jobTitle,
                body:
                    "Thank you for the time and effort you invested in your application for the " + jobTitle + " position." +
                    "\n\nAfter careful consideration, we have decided to progress with another applicant on this occasion." +
                    "\n\nWe appreciate your interest in " + company + " and wish you all the best in your job search." +
                    "\n\nBest regards,\n" + company,
                markStatus: "final_rejected"
            };
        }

        if (templateName === "custom") {
            return { subject: "", body: "", markStatus: "" };
        }

        return {
            subject: "Application Update - " + jobTitle,
            body:
                "We are writing with an update about your application for the " + jobTitle + " position." +
                "\n\nYour application is still being reviewed by our hiring team. We will contact you when there is a further update." +
                "\n\nThank you for your patience and interest in " + company + "." +
                "\n\nBest regards,\n" + company,
            markStatus: ""
        };
    }

    function refreshContactTemplate() {
        if (!els.contactCandidateId || !els.contactTemplate) return;

        var candidateId = parseInt(els.contactCandidateId.value, 10);
        var candidate = getCandidate(candidateId);
        if (!candidate) return;

        var templateName = els.contactTemplate.value;
        var message = buildMessageTemplate(candidate, templateName);

        if (els.interviewFields) {
            els.interviewFields.hidden = templateName !== "interview_invitation";
        }
        els.contactSubject.value = message.subject;
        els.contactBody.value = message.body;
    }

    function openContactModal(id, templateName) {
        var candidate = getCandidate(id);
        if (!candidate || !els.contactModal) return;

        els.contactTo.value = candidate.candidate_email || "";
        els.contactCandidateId.value = id;
        els.contactTemplate.value = templateName || "application_update";

        if (els.interviewDate) els.interviewDate.value = "";
        if (els.interviewTime) els.interviewTime.value = "";
        if (els.interviewLink) els.interviewLink.value = "";

        refreshContactTemplate();
        els.contactModal.classList.add("active");
        document.body.classList.add("modal-open");

        setTimeout(function () {
            if (els.contactSubject) els.contactSubject.focus();
        }, 50);

        if (window.feather) window.feather.replace();
    }

    function closeContactModal() {
        if (!els.contactModal) return;
        els.contactModal.classList.remove("active");
        document.body.classList.remove("modal-open");
    }

    function submitContact() {
        var candidateId = parseInt(els.contactCandidateId.value, 10);
        var candidate = getCandidate(candidateId);
        var templateName = els.contactTemplate.value;
        var subject = els.contactSubject.value.trim();
        var body = els.contactBody.value.trim();
        var template = candidate ? buildMessageTemplate(candidate, templateName) : { markStatus: "" };

        if (!subject || !body) {
            notify("Please enter both a subject and message", "error");
            return;
        }

        if (templateName === "interview_invitation" && !confirm("Send this interview invitation to the applicant?")) {
            return;
        }

        els.contactSend.disabled = true;
        els.contactSend.textContent = "Sending...";

        fetch("/dashboard/send-custom-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                candidate_id: candidateId,
                subject: subject,
                body: body,
                message_type: templateName,
                mark_status: template.markStatus
            })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.success) throw new Error(data.error || "Failed to send email");
                if (!data.email_sent) throw new Error("SendGrid did not accept the email. Check your email configuration.");

                if (data.candidate) {
                    updateCandidateRowFromResponse(candidateId, data.candidate);
                }

                closeContactModal();
                closeDetailModal();
                notify(templateName === "interview_invitation" ? "Interview invitation sent" : "Email sent to applicant", "success");
            })
            .catch(function (error) {
                notify(error.message || "Network error", "error");
            })
            .finally(function () {
                els.contactSend.disabled = false;
                els.contactSend.innerHTML = '<i data-feather="send"></i> Send Email';
                if (window.feather) window.feather.replace();
            });
    }

    function bindContactModal() {
        if (!els.contactModal) return;

        if (els.contactClose) els.contactClose.addEventListener("click", closeContactModal);
        if (els.contactCancel) els.contactCancel.addEventListener("click", closeContactModal);
        if (els.contactSend) els.contactSend.addEventListener("click", submitContact);
        if (els.contactTemplate) els.contactTemplate.addEventListener("change", refreshContactTemplate);

        [els.interviewDate, els.interviewTime, els.interviewLink].forEach(function (field) {
            if (field) field.addEventListener("change", refreshContactTemplate);
        });

        els.contactModal.addEventListener("click", function (event) {
            if (event.target === els.contactModal) closeContactModal();
        });
    }

    function updateCandidateRowFromResponse(id, candidateData) {
        var candidate = getCandidate(id);
        if (candidate) {
            candidate.status = candidateData.status;
            candidate.status_html = candidateData.status_html;
        }

        if (!els.tbody) return;
        var row = els.tbody.querySelector('tr[data-id="' + id + '"]');
        if (!row) return;

        row.dataset.status = candidateData.status;
        var statusCell = row.querySelector('[data-role="candidate-status"]');
        if (statusCell) statusCell.innerHTML = candidateData.status_html;
        applyFilters();
    }

    function updateCandidateStatus(id, status) {
        return fetch("/dashboard/candidate-status/" + id, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: status })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (!data.success) throw new Error(data.error || "Could not update status");
                updateCandidateRowFromResponse(id, data.candidate);
                openDetailModal(id);
                notify("Applicant status updated", "success");
                return data;
            })
            .catch(function (error) {
                notify(error.message || "Could not update status", "error");
            });
    }

    function buildScoreBar(label, score) {
        var safeScore = Number(score) || 0;
        var color = safeScore >= 90 ? "var(--color-primary)" : safeScore >= 70 ? "var(--color-warning)" : "var(--color-danger)";

        return '<div class="score-bar-row">' +
            '<span class="score-bar-label">' + label + '</span>' +
            '<div class="score-bar-track"><div class="score-bar-fill" style="width:' + safeScore + '%;background:' + color + '"></div></div>' +
            '<span class="score-bar-value">' + safeScore + '</span></div>';
    }

    function openDetailModal(id) {
        var candidate = getCandidate(id);
        if (!candidate || !els.detailModal) return;

        els.detailName.textContent = candidate.candidate_name || "Applicant Details";

        var score = Number(candidate.match_score) || 0;
        var scoreClass = score >= 90 ? "green" : score >= 70 ? "amber" : "red";
        var skillsHtml = "";
        var summaryHtml = "";

        if (candidate.matched_skills && candidate.matched_skills.length) {
            skillsHtml = '<div class="detail-section">' +
                '<span class="analysis-field-label">Matched Skills</span>' +
                '<div class="detail-skill-list">' +
                candidate.matched_skills.map(function (skill) {
                    return '<span class="pill-tag">' + escapeHtml(skill) + '</span>';
                }).join("") +
                '</div></div>';
        }

        if (candidate.match_summary) {
            summaryHtml = '<div class="detail-section">' +
                '<span class="analysis-field-label">AI Summary</span>' +
                '<p class="detail-summary">' + escapeHtml(candidate.match_summary) + '</p>' +
                '</div>';
        }

        var actions =
            '<button class="btn-outline detail-contact-btn" data-id="' + candidate.id + '"><i data-feather="mail"></i> Contact</button>' +
            '<a class="btn-outline" target="_blank" href="/dashboard/resume-pdf/' + candidate.id + '"><i data-feather="file-text"></i> View Resume</a>' +
            '<a class="btn-outline" target="_blank" href="/dashboard/candidate-pdf/' + candidate.id + '"><i data-feather="download"></i> Report</a>';

        if (candidate.status === "scored") {
            actions += '<button class="btn-primary detail-status-btn" data-status="shortlisted" data-id="' + candidate.id + '"><i data-feather="star"></i> Shortlist</button>';
        }
        if (candidate.status === "shortlisted") {
            actions += '<button class="btn-primary detail-invite-btn" data-id="' + candidate.id + '"><i data-feather="calendar"></i> Send Interview Invite</button>';
        }
        if (candidate.status === "invited") {
            actions += '<button class="btn-primary detail-status-btn" data-status="interview_done" data-id="' + candidate.id + '"><i data-feather="check-circle"></i> Interview Done</button>';
        }
        if (candidate.status === "interview_done") {
            actions += '<button class="btn-primary detail-status-btn" data-status="final_hired" data-id="' + candidate.id + '"><i data-feather="user-check"></i> Hire</button>' +
                '<button class="btn-outline detail-status-btn" data-status="final_rejected" data-id="' + candidate.id + '">Reject</button>';
        }

        els.detailBody.innerHTML =
            '<div class="candidate-detail-heading">' +
                '<div class="result-score ' + scoreClass + '">' + score + '</div>' +
                '<div>' +
                    '<div class="candidate-detail-name">' + escapeHtml(candidate.candidate_name || "Unknown") + '</div>' +
                    '<div class="candidate-detail-email">' + escapeHtml(candidate.candidate_email || "") + '</div>' +
                    '<div class="candidate-detail-job">' + escapeHtml(candidate.job_title || "") + '</div>' +
                '</div>' +
            '</div>' +
            '<div class="result-breakdown">' +
                buildScoreBar("Skills", candidate.skills_score) +
                buildScoreBar("Experience", candidate.experience_score) +
                buildScoreBar("Education", candidate.education_score) +
            '</div>' +
            skillsHtml +
            summaryHtml +
            '<div class="candidate-detail-actions">' + actions + '</div>';

        els.detailModal.classList.add("active");
        document.body.classList.add("modal-open");
        if (window.feather) window.feather.replace();
    }

    function closeDetailModal() {
        if (!els.detailModal) return;
        els.detailModal.classList.remove("active");
        if (!els.contactModal || !els.contactModal.classList.contains("active")) {
            document.body.classList.remove("modal-open");
        }
    }

    function bindDetailModal() {
        if (!els.detailModal) return;

        if (els.detailClose) els.detailClose.addEventListener("click", closeDetailModal);

        els.detailModal.addEventListener("click", function (event) {
            if (event.target === els.detailModal) {
                closeDetailModal();
                return;
            }

            var contactButton = event.target.closest(".detail-contact-btn");
            if (contactButton) {
                openContactModal(parseInt(contactButton.dataset.id, 10), "application_update");
                return;
            }

            var inviteButton = event.target.closest(".detail-invite-btn");
            if (inviteButton) {
                openContactModal(parseInt(inviteButton.dataset.id, 10), "interview_invitation");
                return;
            }

            var statusButton = event.target.closest(".detail-status-btn");
            if (statusButton) {
                updateCandidateStatus(
                    parseInt(statusButton.dataset.id, 10),
                    statusButton.dataset.status
                );
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") return;

            if (els.contactModal && els.contactModal.classList.contains("active")) {
                closeContactModal();
                return;
            }
            if (els.detailModal && els.detailModal.classList.contains("active")) {
                closeDetailModal();
            }
        });
    }

    document.addEventListener("DOMContentLoaded", init);
})();
